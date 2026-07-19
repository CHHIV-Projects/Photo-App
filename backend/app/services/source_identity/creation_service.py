"""Transactional, path-first filesystem Source creation."""

from __future__ import annotations

import hashlib
import json
import ntpath
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, inspect, or_, select, text
from sqlalchemy.orm import Session

from app.models.ingestion_source import IngestionSource
from app.models.source_endpoint import (
    AccessNode,
    SourceEndpoint,
    SourceEndpointAliasEvent,
    SourceEndpointObservedPath,
)
from app.services.ingestion.ingestion_context_service import (
    normalize_source_label,
    normalize_source_root_path,
)
from app.services.source_identity.creation_schema import (
    SourceCreationConfirmRequest,
    SourceCreationConfirmResponse,
    SourceCreationEndpointMatch,
    SourceCreationMessage,
    SourceCreationPlanRequest,
    SourceCreationPlanResponse,
    SourceCreationSourceMatch,
)
from app.services.source_identity.durable_identity import summarize_durable_identity
from app.services.source_identity.identity_fingerprint import (
    FingerprintResult,
    fingerprint_from_probe,
    parse_unc_server_share,
    stable_hash,
)
from app.services.source_identity.probe_schema import (
    SourceIdentityProbeRequest,
    SourceIdentityProbeResponse,
)
from app.services.source_identity.probe_service import SourceIdentityProbeService


_ALIAS_MAX_LENGTH = 255
_SOURCE_LABEL_MAX_LENGTH = 255
_DRIVE_PATH_RE = re.compile(r"^[a-zA-Z]:[\\/]")
_CONTROL_CHARACTER_RE = re.compile(r"[\x00-\x1f]")
_COMPLETED_PROBE_STATUSES = {"completed", "completed_with_warnings"}
_LOCAL_ENDPOINT_TYPES = {"local", "external_device"}
_MANAGEMENT_REVIEW_STATUSES = {"archived", "test", "deprecated"}
_LOCATION_BLOCKER_CODES = {
    "absolute_source_path_required",
    "access_denied",
    "drive_root_not_derived",
    "invalid_source_root",
    "mapped_nas_unc_resolution_failed",
    "nas_path_required",
    "nas_server_not_runnable",
    "nas_share_not_derived",
    "network_path_requires_nas",
    "path_not_found",
    "path_not_readable",
    "probe_not_completed",
    "removable_media_requires_supported_flow",
    "source_path_required",
    "source_root_invalid",
}


@dataclass(frozen=True)
class _DerivedRoot:
    canonical_source_root_path: str
    endpoint_relative_root: str
    entire_endpoint: bool
    entire_endpoint_label: str | None
    endpoint_boundary: str


@dataclass(frozen=True)
class _ExactResolution:
    matches: tuple[IngestionSource, ...]
    target: IngestionSource | None
    source_action: str
    conflicting_source_ids: tuple[int, ...]
    duplicate_source_ids_to_inactivate: tuple[int, ...]
    blockers: tuple[SourceCreationMessage, ...]
    warnings: tuple[SourceCreationMessage, ...]


@dataclass(frozen=True)
class _PlanContext:
    probe: SourceIdentityProbeResponse | None
    fingerprint: FingerprintResult
    selected_endpoint: SourceEndpoint | None
    existing_source: IngestionSource | None
    safe_legacy_upgrade_endpoint_ids: frozenset[int]


@dataclass(frozen=True)
class _SourceReferenceSummary:
    provenance_count: int = 0
    ingestion_runs_count: int = 0
    source_intake_runs_count: int = 0
    asset_count: int = 0

    @property
    def has_protected_history(self) -> bool:
        return any(
            value > 0
            for value in (
                self.provenance_count,
                self.ingestion_runs_count,
                self.source_intake_runs_count,
                self.asset_count,
            )
        )


class SourceCreationService:
    """Recognize a path, then atomically confirm the selected Source action."""

    def __init__(
        self,
        db_session: Session,
        probe_service: SourceIdentityProbeService | None = None,
    ) -> None:
        self._db = db_session
        self._probe_service = probe_service or SourceIdentityProbeService()

    def plan(self, request: SourceCreationPlanRequest) -> SourceCreationPlanResponse:
        """Return a read-only recognition and creation plan."""
        plan, _ = self._build_plan(request)
        return plan

    def confirm(self, request: SourceCreationConfirmRequest) -> SourceCreationConfirmResponse:
        """Recompute the plan and apply all selected metadata writes atomically."""
        plan_request = SourceCreationPlanRequest(
            source_type=request.source_type,
            observed_path=request.observed_path,
            source_name=request.source_name,
            device_name=request.device_name,
            naming_action=request.naming_action,
            selected_existing_endpoint_id=request.selected_existing_endpoint_id,
            selected_canonical_source_id=request.selected_canonical_source_id,
            duplicate_source_ids_to_inactivate=request.duplicate_source_ids_to_inactivate,
            use_registered_source_type=request.use_registered_source_type,
            operator_review_acknowledged=request.operator_review_acknowledged,
        )
        plan, context = self._build_plan(plan_request)
        blockers = list(plan.blockers)
        if request.plan_fingerprint != plan.plan_fingerprint:
            blockers.append(
                _message(
                    "plan_fingerprint_mismatch",
                    "The reviewed Create Source plan changed. Identify the location again before confirming.",
                )
            )
        if not request.operator_confirmed:
            blockers.append(
                _message(
                    "operator_confirmation_required",
                    "Confirm the displayed Source action before saving metadata.",
                )
            )
        if plan.plan_status not in {"ready", "source_exists"}:
            blockers.append(
                _message(
                    "plan_not_ready",
                    "The Create Source plan is not ready to confirm.",
                )
            )
        blockers = _dedupe_messages(blockers)
        if blockers:
            return self._blocked_confirm_response(plan, blockers)

        try:
            return self._apply_confirm(plan, context)
        except Exception:
            self._db.rollback()
            raise

    def _build_plan(
        self,
        request: SourceCreationPlanRequest,
    ) -> tuple[SourceCreationPlanResponse, _PlanContext]:
        blockers: list[SourceCreationMessage] = []
        warnings: list[SourceCreationMessage] = []
        required_confirmations: list[SourceCreationMessage] = []

        requested_device_name = _normalize_device_name(request.device_name)
        observed_path = (request.observed_path or "").strip()
        shape_blocker = _path_shape_blocker(request.source_type, observed_path)
        if shape_blocker is not None:
            blockers.append(shape_blocker)

        probe: SourceIdentityProbeResponse | None = None
        technical_source_type = request.source_type
        if not blockers:
            probe_type = _initial_probe_source_type(request.source_type, observed_path)
            probe = self._run_probe(probe_type, observed_path, "drive_agnostic_source_creation")
            if request.source_type in {"local", "external"} and _probe_reports_mapped_nas(probe):
                probe = self._run_probe("nas", observed_path, "mapped_nas_source_creation")
            technical_source_type = _operator_source_type_from_probe(probe, request.source_type)
            blockers.extend(_probe_blockers(probe))
            warnings.extend(_probe_warnings(probe))
            if request.source_type in {"local", "external"} and _has_clear_removable_evidence(probe):
                blockers.append(
                    _message(
                        "removable_media_requires_supported_flow",
                        "This location is removable media. Use Removable Media when that source type becomes available.",
                    )
                )

        derived_root, derive_blocker = _derive_root(technical_source_type, observed_path, probe)
        if derive_blocker is not None:
            blockers.append(derive_blocker)
        if derived_root is None:
            derived_root = _DerivedRoot(
                canonical_source_root_path=observed_path,
                endpoint_relative_root="",
                entire_endpoint=False,
                entire_endpoint_label=None,
                endpoint_boundary="",
            )

        durable_identity = summarize_durable_identity(
            probe=probe,
            source_type=_persisted_source_type(technical_source_type),
        )
        fingerprint = (
            fingerprint_from_probe(probe)
            if probe is not None
            else FingerprintResult(None, "unavailable", None)
        )
        match_endpoint_types = _match_endpoint_types(probe, technical_source_type)
        strong_matches = self._find_matches(
            endpoint_source_types=match_endpoint_types,
            fingerprint_hash=fingerprint.hash_value if fingerprint.strength == "strong" else None,
            match_strength="strong",
        )
        strong_ids = {match.source_endpoint_id for match in strong_matches}
        legacy_matches: list[SourceCreationEndpointMatch] = []
        for legacy_hash in fingerprint.legacy_hashes:
            legacy_matches.extend(
                match
                for match in self._find_matches(
                    endpoint_source_types=match_endpoint_types,
                    fingerprint_hash=legacy_hash,
                    match_strength="legacy_review",
                )
                if match.source_endpoint_id not in strong_ids
            )
        safe_legacy_upgrade_endpoint_ids = {
            match.source_endpoint_id for match in legacy_matches
        }
        revalidated_legacy_matches = self._find_revalidated_legacy_matches(
            endpoint_source_types=match_endpoint_types,
            endpoint_boundary=derived_root.endpoint_boundary,
            fingerprint=fingerprint,
            excluded_endpoint_ids=strong_ids | safe_legacy_upgrade_endpoint_ids,
        )
        legacy_matches.extend(revalidated_legacy_matches)
        safe_legacy_upgrade_endpoint_ids.update(
            match.source_endpoint_id for match in revalidated_legacy_matches
        )
        possible_matches = _dedupe_matches(strong_matches if strong_matches else legacy_matches)
        match_by_id = {match.source_endpoint_id: match for match in possible_matches}

        selected_endpoint: SourceEndpoint | None = None
        selected_match: SourceCreationEndpointMatch | None = None
        if request.selected_existing_endpoint_id is not None:
            selected_match = match_by_id.get(request.selected_existing_endpoint_id)
            if selected_match is None:
                blockers.append(
                    _message(
                        "selected_endpoint_not_a_match",
                        "The selected existing device no longer matches the current identity evidence.",
                    )
                )
            else:
                selected_endpoint = self._db.get(SourceEndpoint, selected_match.source_endpoint_id)
        elif len(strong_matches) == 1:
            selected_match = strong_matches[0]
            selected_endpoint = self._db.get(SourceEndpoint, selected_match.source_endpoint_id)
        elif len(strong_matches) > 1:
            required_confirmations.append(
                _message(
                    "select_existing_endpoint",
                    "More than one registered device has this durable identity. Select one before continuing.",
                )
            )
        elif len(legacy_matches) == 1:
            selected_match = legacy_matches[0]
            selected_endpoint = self._db.get(SourceEndpoint, selected_match.source_endpoint_id)
        elif len(legacy_matches) > 1:
            required_confirmations.append(
                _message(
                    "select_legacy_endpoint",
                    "More than one legacy device identity may match. Select one for review.",
                )
            )

        if selected_endpoint is not None and selected_endpoint.status == "retired":
            blockers.append(_message("selected_endpoint_retired", "The selected device identity is retired."))

        registered_operator_type = (
            _operator_source_type_from_endpoint(selected_endpoint.source_type)
            if selected_endpoint is not None
            else None
        )
        if selected_endpoint is not None and registered_operator_type is None:
            blockers.append(
                _message(
                    "registered_source_type_unsupported",
                    "The registered device type is not supported by this Create Source flow.",
                )
            )
        recognized_source_type = registered_operator_type or technical_source_type
        source_type_mismatch = recognized_source_type != request.source_type
        if source_type_mismatch and not request.use_registered_source_type:
            type_label = _operator_source_type_label(recognized_source_type)
            required_confirmations.append(
                _message(
                    "source_type_mismatch_acknowledgment_required",
                    f"This location is recognized as {type_label}. Continue using {type_label} or cancel.",
                )
            )

        endpoint_action = "create_new_endpoint"
        if selected_endpoint is not None:
            endpoint_action = (
                "upgrade_legacy_endpoint"
                if selected_match is not None and selected_match.match_strength == "legacy_review"
                else "reuse_existing_endpoint"
            )
        elif possible_matches:
            endpoint_action = "none"

        if selected_match is not None and selected_match.match_strength == "legacy_review" and (
            not request.operator_review_acknowledged
        ):
            required_confirmations.append(
                _message(
                    "legacy_endpoint_upgrade_required",
                    "The recognized device uses a legacy fingerprint. Review and confirm its safe upgrade.",
                )
            )

        naming_action = request.naming_action
        canonical_device_name = ""
        name_decision_required = False
        will_rename_endpoint = False
        if selected_endpoint is None and possible_matches:
            name_decision_required = True
        elif selected_endpoint is None:
            if naming_action is None and requested_device_name:
                naming_action = "create_new"
            if naming_action == "cancel":
                blockers.append(_message("creation_cancelled", "Create Source was cancelled."))
            elif naming_action not in {None, "create_new"}:
                blockers.append(
                    _message("invalid_name_action", "Choose a valid Device Name action for the new device.")
                )
            canonical_device_name = requested_device_name
            name_error = _validate_device_name(requested_device_name)
            if name_error is not None:
                if requested_device_name or naming_action == "create_new":
                    blockers.append(name_error)
                else:
                    name_decision_required = True
                    required_confirmations.append(
                        _message("device_name_required", "Enter a Device Name for this new device.")
                    )
            elif self._alias_conflict(requested_device_name, exclude_endpoint_id=None) is not None:
                blockers.append(
                    _message(
                        "device_name_conflict",
                        "Device Name is already used by a different durable device identity.",
                    )
                )
        else:
            if naming_action is None:
                name_decision_required = True
                canonical_device_name = selected_endpoint.alias
                required_confirmations.append(
                    _message(
                        "device_name_decision_required",
                        "Choose Use Existing Name, Rename Device, or Cancel.",
                    )
                )
            elif naming_action == "cancel":
                canonical_device_name = selected_endpoint.alias
                blockers.append(_message("creation_cancelled", "Create Source was cancelled."))
            elif naming_action == "use_existing":
                canonical_device_name = selected_endpoint.alias
            elif naming_action == "rename_existing":
                canonical_device_name = requested_device_name
                name_error = _validate_device_name(requested_device_name)
                if name_error is not None:
                    blockers.append(name_error)
                elif requested_device_name == selected_endpoint.alias:
                    blockers.append(
                        _message(
                            "device_name_unchanged",
                            "Enter a different Device Name or choose Use Existing Name.",
                        )
                    )
                elif self._alias_conflict(
                    requested_device_name,
                    exclude_endpoint_id=selected_endpoint.id,
                ) is not None:
                    blockers.append(
                        _message(
                            "device_name_conflict",
                            "Device Name is already used by a different durable device identity.",
                        )
                    )
                else:
                    will_rename_endpoint = True
                    warnings.append(
                        _message(
                            "endpoint_alias_will_change",
                            "Renaming changes only this device display name. Durable identity, Sources, roots, and history stay unchanged.",
                        )
                    )
            else:
                canonical_device_name = selected_endpoint.alias
                blockers.append(
                    _message(
                        "invalid_name_action",
                        "Choose Use Existing Name, Rename Device, or Cancel for this recognized device.",
                    )
                )

        if will_rename_endpoint:
            endpoint_action = (
                "upgrade_and_rename_endpoint"
                if endpoint_action == "upgrade_legacy_endpoint"
                else "rename_existing_endpoint"
            )

        exact_sources = self._find_exact_sources(
            endpoint_id=selected_endpoint.id if selected_endpoint is not None else None,
            endpoint_relative_root=derived_root.endpoint_relative_root,
            canonical_source_root_path=derived_root.canonical_source_root_path,
        )
        reference_summaries = {
            source.id: self._source_reference_summary(source.id) for source in exact_sources
        }
        exact_resolution = self._resolve_exact_sources(
            exact_sources=exact_sources,
            selected_endpoint_id=selected_endpoint.id if selected_endpoint is not None else None,
            endpoint_relative_root=derived_root.endpoint_relative_root,
            selected_canonical_source_id=request.selected_canonical_source_id,
            duplicate_source_ids_to_inactivate=tuple(request.duplicate_source_ids_to_inactivate),
            reference_summaries=reference_summaries,
        )
        blockers.extend(exact_resolution.blockers)
        warnings.extend(exact_resolution.warnings)
        source_action = exact_resolution.source_action
        existing_source = exact_resolution.target

        if selected_endpoint is not None:
            warnings.extend(
                self._overlap_warnings(
                    endpoint_id=selected_endpoint.id,
                    endpoint_relative_root=derived_root.endpoint_relative_root,
                    exclude_source_ids={source.id for source in exact_sources},
                )
            )

        if durable_identity.status != "verified" and not blockers and not request.operator_review_acknowledged:
            required_confirmations.append(
                _message(
                    "durable_identity_not_verified",
                    "Durable device identity is not verified. Review the evidence before continuing.",
                )
            )

        if (
            recognized_source_type == "local"
            and derived_root.entire_endpoint
            and derived_root.endpoint_boundary[:2].casefold()
            == os.environ.get("SystemDrive", "C:").casefold()
        ):
            warnings.append(
                _message(
                    "entire_system_volume_selected",
                    "This source includes the whole system volume and may contain system or application folders.",
                )
            )

        display_device_name = (
            canonical_device_name
            or (selected_endpoint.alias if selected_endpoint is not None else "Device name required")
        )
        suggested_source_name, display_warning = self._source_display_name_for_plan(
            endpoint_relative_root=derived_root.endpoint_relative_root,
            source_type=recognized_source_type,
            selected_endpoint_id=selected_endpoint.id if selected_endpoint is not None else None,
        )
        requested_source_name = _normalize_source_name(request.source_name)
        source_name_suggested_alternative: str | None = None
        if existing_source is not None:
            source_display_name = existing_source.source_label
        else:
            source_display_name = requested_source_name or suggested_source_name
            if request.source_name is not None:
                source_name_error = _validate_source_name(requested_source_name)
                if source_name_error is not None:
                    blockers.append(source_name_error)
                elif self._source_display_name_exists_on_endpoint(
                    endpoint_id=selected_endpoint.id if selected_endpoint is not None else None,
                    display_name=requested_source_name,
                ) or self._source_display_name_conflicts_with_db_tuple(
                    display_name=requested_source_name,
                    persisted_source_type=_persisted_source_type(recognized_source_type),
                    canonical_source_root_path=derived_root.canonical_source_root_path,
                ):
                    source_name_suggested_alternative, _ = self._source_display_name_for_plan(
                        endpoint_relative_root=derived_root.endpoint_relative_root,
                        source_type=recognized_source_type,
                        selected_endpoint_id=selected_endpoint.id if selected_endpoint is not None else None,
                    )
                    blockers.append(
                        _message(
                            "source_name_conflict",
                            "Source Name is already used by another Source on this durable device.",
                        )
                    )
        if display_warning is not None:
            warnings.append(display_warning)

        blockers = _dedupe_messages(blockers)
        warnings = _dedupe_messages(warnings)
        required_confirmations = _dedupe_messages(required_confirmations)

        recognition_status, recognition_title, recognition_message = _recognition_summary(
            blockers=blockers,
            selected_endpoint=selected_endpoint,
            source_action=source_action,
            source_type_mismatch=source_type_mismatch,
            required_confirmations=required_confirmations,
        )
        if blockers:
            plan_status = "blocked"
        elif required_confirmations:
            plan_status = "needs_review"
        elif source_action == "reuse_existing_source":
            plan_status = "source_exists"
        else:
            plan_status = "ready"

        final_action_label = _final_action_label(
            source_action=source_action,
            endpoint_action=endpoint_action,
            selected_endpoint=selected_endpoint,
        )
        exact_source_matches: list[SourceCreationSourceMatch] = []
        for source in exact_sources:
            reference_summary = reference_summaries[source.id]
            selected_for_action = existing_source is not None and source.id == existing_source.id
            allowed_actions: list[str] = []
            recommended_action: str | None = None
            if selected_for_action:
                allowed_actions.append(source_action)
                recommended_action = source_action
            elif source.id in exact_resolution.duplicate_source_ids_to_inactivate:
                allowed_actions.append("mark_inactive")
                recommended_action = "mark_inactive"
            elif source.profile_status == "inactive":
                recommended_action = "leave_inactive"

            exact_source_matches.append(
                SourceCreationSourceMatch(
                    source_profile_id=source.id,
                    source_label=source.source_label,
                    source_type=source.source_type,
                    profile_status=source.profile_status,
                    source_root_path=source.source_root_path,
                    source_endpoint_id=source.endpoint_id,
                    endpoint_alias=(source.source_endpoint.alias if source.source_endpoint is not None else None),
                    endpoint_relative_root=source.endpoint_relative_root,
                    match_kind=(
                        "modern_exact"
                        if _is_modern_exact(
                            source,
                            selected_endpoint_id=selected_endpoint.id if selected_endpoint is not None else None,
                            endpoint_relative_root=derived_root.endpoint_relative_root,
                        )
                        else "legacy_exact"
                    ),
                    classification=_source_match_classification(
                        source,
                        selected_endpoint_id=selected_endpoint.id if selected_endpoint is not None else None,
                        endpoint_relative_root=derived_root.endpoint_relative_root,
                    ),
                    provenance_count=reference_summary.provenance_count,
                    ingestion_runs_count=reference_summary.ingestion_runs_count,
                    source_intake_runs_count=reference_summary.source_intake_runs_count,
                    asset_count=reference_summary.asset_count,
                    has_protected_history=reference_summary.has_protected_history,
                    recommended_action=recommended_action,
                    allowed_actions=allowed_actions,
                    selected_for_action=selected_for_action,
                    conflict_reason=(
                        "Inactive duplicate retained for management review."
                        if source.id in exact_resolution.conflicting_source_ids
                        else None
                    ),
                )
            )

        plan_fingerprint = stable_hash(
            {
                "source_type": request.source_type,
                "recognized_source_type": recognized_source_type,
                "canonical_device_name": canonical_device_name,
                "source_display_name": source_display_name,
                "requested_source_name": requested_source_name,
                "naming_action": naming_action,
                "use_registered_source_type": request.use_registered_source_type,
                "canonical_source_root_path": derived_root.canonical_source_root_path.casefold(),
                "endpoint_relative_root": derived_root.endpoint_relative_root.casefold(),
                "fingerprint_hash": fingerprint.hash_value,
                "fingerprint_version": fingerprint.version,
                "selected_endpoint": (
                    {
                        "id": selected_endpoint.id,
                        "alias": selected_endpoint.alias,
                        "type": selected_endpoint.source_type,
                        "status": selected_endpoint.status,
                        "fingerprint": selected_endpoint.identity_fingerprint_hash,
                    }
                    if selected_endpoint is not None
                    else None
                ),
                "endpoint_action": endpoint_action,
                "source_action": source_action,
                "exact_sources": [
                    {
                        "id": source.id,
                        "status": source.profile_status,
                        "endpoint_id": source.endpoint_id,
                        "relative_root": source.endpoint_relative_root,
                        "references": reference_summaries[source.id].__dict__,
                    }
                    for source in exact_sources
                ],
                "selected_canonical_source_id": request.selected_canonical_source_id,
                "duplicate_source_ids_to_inactivate": list(exact_resolution.duplicate_source_ids_to_inactivate),
                "existing_source_profile_id": existing_source.id if existing_source is not None else None,
                "blockers": [item.code for item in blockers],
                "required_confirmations": [item.code for item in required_confirmations],
            }
        )

        plan = SourceCreationPlanResponse(
            plan_status=plan_status,  # type: ignore[arg-type]
            plan_fingerprint=plan_fingerprint,
            recognition_status=recognition_status,  # type: ignore[arg-type]
            recognition_title=recognition_title,
            recognition_message=recognition_message,
            source_type=request.source_type,
            recognized_source_type=recognized_source_type,
            registered_endpoint_source_type=(
                selected_endpoint.source_type if selected_endpoint is not None else None
            ),
            source_type_mismatch=source_type_mismatch,
            persisted_source_type=_persisted_source_type(recognized_source_type),
            requested_device_name=requested_device_name,
            device_name=display_device_name,
            naming_action=naming_action,
            name_decision_required=name_decision_required,
            observed_path=observed_path,
            canonical_source_root_path=derived_root.canonical_source_root_path,
            endpoint_relative_root=derived_root.endpoint_relative_root,
            entire_endpoint=derived_root.entire_endpoint,
            entire_endpoint_label=derived_root.entire_endpoint_label,
                suggested_source_name=suggested_source_name,
                requested_source_name=requested_source_name or None,
                source_name_suggested_alternative=source_name_suggested_alternative,
            source_display_name=source_display_name,
            **durable_identity.response_fields(),
            endpoint_action=endpoint_action,  # type: ignore[arg-type]
            source_action=source_action,  # type: ignore[arg-type]
            selected_existing_endpoint_id=(selected_endpoint.id if selected_endpoint is not None else None),
                selected_canonical_source_id=(existing_source.id if existing_source is not None else None),
            existing_source_profile_id=existing_source.id if existing_source is not None else None,
            existing_source_status=(existing_source.profile_status if existing_source is not None else None),
                duplicate_source_ids_to_inactivate=list(exact_resolution.duplicate_source_ids_to_inactivate),
            possible_matches=possible_matches,
            exact_source_matches=exact_source_matches,
            conflicting_source_profile_ids=list(exact_resolution.conflicting_source_ids),
            final_action_label=final_action_label,
            blockers=blockers,
            warnings=warnings,
            required_confirmations=required_confirmations,
            advanced_details={
                "technical_source_type": technical_source_type,
                "endpoint_boundary": derived_root.endpoint_boundary,
                "fingerprint_hash": fingerprint.hash_value,
                "fingerprint_version": fingerprint.version,
                "fingerprint_strength": fingerprint.strength,
                "legacy_fingerprint_match_count": len(legacy_matches),
                "revalidated_legacy_match_count": len(revalidated_legacy_matches),
                "probe_status": probe.probe_status if probe is not None else None,
                "probe_provider": probe.provider_name if probe is not None else None,
                "filesystem_boundary_type": (
                    probe.source_root_candidate.filesystem_boundary_type if probe is not None else None
                ),
            },
        )
        return plan, _PlanContext(
            probe=probe,
            fingerprint=fingerprint,
            selected_endpoint=selected_endpoint,
            existing_source=existing_source,
            safe_legacy_upgrade_endpoint_ids=frozenset(safe_legacy_upgrade_endpoint_ids),
        )

    def _run_probe(
        self,
        probe_source_type: str,
        observed_path: str,
        intended_use: str,
    ) -> SourceIdentityProbeResponse:
        return self._probe_service.probe(
            SourceIdentityProbeRequest(
                source_type=probe_source_type,  # type: ignore[arg-type]
                observed_path=observed_path,
                probe_mode="setup_probe",
                intended_use=intended_use,
                os_family="windows",
            )
        )

    def _find_matches(
        self,
        *,
        endpoint_source_types: set[str],
        fingerprint_hash: str | None,
        match_strength: str,
    ) -> list[SourceCreationEndpointMatch]:
        if not fingerprint_hash:
            return []
        endpoints = self._db.scalars(
            select(SourceEndpoint).where(
                SourceEndpoint.source_type.in_(endpoint_source_types),
                SourceEndpoint.identity_fingerprint_hash == fingerprint_hash,
                SourceEndpoint.status != "retired",
            )
        ).all()
        reason = (
            "Full durable identity fingerprint matched across registered Local and External devices."
            if endpoint_source_types == _LOCAL_ENDPOINT_TYPES and match_strength == "strong"
            else "Same durable identity fingerprint and endpoint boundary."
            if match_strength == "strong"
            else "Legacy identity evidence may represent this device and requires review."
        )
        return [
            SourceCreationEndpointMatch(
                source_endpoint_id=endpoint.id,
                alias=endpoint.alias,
                source_type=endpoint.source_type,
                match_strength=match_strength,  # type: ignore[arg-type]
                match_reason=reason,
                identity_confidence=endpoint.identity_confidence,
            )
            for endpoint in endpoints
        ]

    def _find_revalidated_legacy_matches(
        self,
        *,
        endpoint_source_types: set[str],
        endpoint_boundary: str,
        fingerprint: FingerprintResult,
        excluded_endpoint_ids: set[int],
    ) -> list[SourceCreationEndpointMatch]:
        """Re-probe observed volume paths before accepting an old fingerprint."""
        if (
            not endpoint_source_types.issubset(_LOCAL_ENDPOINT_TYPES)
            or fingerprint.strength != "strong"
            or not fingerprint.hash_value
            or not fingerprint.version
        ):
            return []

        candidates = self._db.execute(
            select(SourceEndpoint, SourceEndpointObservedPath)
            .join(
                SourceEndpointObservedPath,
                SourceEndpointObservedPath.source_endpoint_id == SourceEndpoint.id,
            )
            .where(
                SourceEndpoint.source_type.in_(endpoint_source_types),
                SourceEndpoint.status != "retired",
                or_(
                    SourceEndpoint.identity_fingerprint_version.is_(None),
                    SourceEndpoint.identity_fingerprint_version != fingerprint.version,
                ),
            )
            .order_by(SourceEndpoint.id, SourceEndpointObservedPath.id)
        ).all()

        matches: list[SourceCreationEndpointMatch] = []
        checked_endpoint_ids: set[int] = set()
        for endpoint, observed in candidates:
            if endpoint.id in excluded_endpoint_ids or endpoint.id in checked_endpoint_ids:
                continue
            if _drive_boundary(observed.observed_path).casefold() != endpoint_boundary.casefold():
                continue
            checked_endpoint_ids.add(endpoint.id)
            try:
                observed_probe = self._run_probe(
                    endpoint.source_type,
                    observed.observed_path,
                    "legacy_endpoint_identity_revalidation",
                )
            except Exception:
                continue
            observed_fingerprint = fingerprint_from_probe(observed_probe)
            if (
                observed_fingerprint.strength != "strong"
                or observed_fingerprint.hash_value != fingerprint.hash_value
                or observed_fingerprint.version != fingerprint.version
            ):
                continue
            matches.append(
                SourceCreationEndpointMatch(
                    source_endpoint_id=endpoint.id,
                    alias=endpoint.alias,
                    source_type=endpoint.source_type,
                    match_strength="legacy_review",
                    match_reason=(
                        "A prior observed path was re-probed and matched the current full durable Volume GUID."
                    ),
                    identity_confidence=endpoint.identity_confidence,
                )
            )
        return matches

    def _find_exact_sources(
        self,
        *,
        endpoint_id: int | None,
        endpoint_relative_root: str,
        canonical_source_root_path: str,
    ) -> list[IngestionSource]:
        matches: dict[int, IngestionSource] = {}
        if endpoint_id is not None:
            modern = self._db.scalars(
                select(IngestionSource).where(
                    IngestionSource.endpoint_id == endpoint_id,
                    IngestionSource.endpoint_relative_root.is_not(None),
                    func.lower(IngestionSource.endpoint_relative_root)
                    == endpoint_relative_root.casefold(),
                )
            ).all()
            matches.update({source.id: source for source in modern})

        normalized_root = normalize_source_root_path(canonical_source_root_path)
        legacy = self._db.scalars(
            select(IngestionSource).where(
                IngestionSource.source_root_path_normalized == normalized_root,
                or_(
                    IngestionSource.endpoint_id.is_(None),
                    IngestionSource.endpoint_relative_root.is_(None),
                ),
            )
        ).all()
        matches.update({source.id: source for source in legacy})
        return [matches[source_id] for source_id in sorted(matches)]

    def _resolve_exact_sources(
        self,
        *,
        exact_sources: list[IngestionSource],
        selected_endpoint_id: int | None,
        endpoint_relative_root: str,
        selected_canonical_source_id: int | None,
        duplicate_source_ids_to_inactivate: tuple[int, ...],
        reference_summaries: dict[int, _SourceReferenceSummary],
    ) -> _ExactResolution:
        if not exact_sources:
            return _ExactResolution((), None, "create_new_source", (), (), (), ())

        blockers: list[SourceCreationMessage] = []
        warnings: list[SourceCreationMessage] = []
        foreign = [
            source
            for source in exact_sources
            if source.endpoint_id is not None and source.endpoint_id != selected_endpoint_id
        ]
        if foreign:
            blockers.append(
                _message(
                    "exact_source_endpoint_conflict",
                    "An exact-path Source is linked to a different durable device identity. Management review is required.",
                )
            )

        managed = [
            source for source in exact_sources if source.profile_status in _MANAGEMENT_REVIEW_STATUSES
        ]
        if managed:
            blockers.append(
                _message(
                    "exact_source_management_status",
                    "An exact Source is archived, test, or deprecated. Review it in Manage Sources before continuing.",
                )
            )

        active = [source for source in exact_sources if source.profile_status == "active"]
        inactive = [source for source in exact_sources if source.profile_status == "inactive"]
        if len(active) > 1 and selected_canonical_source_id is None:
            blockers.append(
                _message(
                    "multiple_active_exact_sources",
                    "Multiple active Sources match this exact location. Review is required before continuing.",
                )
            )

        target: IngestionSource | None = None
        source_action = "none"
        conflicting_source_ids: tuple[int, ...] = ()
        selected_canonical = (
            next((source for source in exact_sources if source.id == selected_canonical_source_id), None)
            if selected_canonical_source_id is not None
            else None
        )
        requested_inactivation_ids = tuple(dict.fromkeys(duplicate_source_ids_to_inactivate))

        if selected_canonical_source_id is not None and selected_canonical is None:
            blockers.append(
                _message(
                    "selected_canonical_source_not_exact",
                    "The selected canonical Source no longer matches this exact location.",
                )
            )

        if not blockers and selected_canonical is not None:
            target = selected_canonical
            source_action = _source_action_for_target(
                target,
                selected_endpoint_id=selected_endpoint_id,
                endpoint_relative_root=endpoint_relative_root,
                reactivate=target.profile_status == "inactive",
            )
            conflicting_source_ids = tuple(source.id for source in exact_sources if source.id != target.id)
        elif not blockers and len(active) == 1:
            candidate = active[0]
            if len(exact_sources) == 1:
                target = candidate
            elif _is_approved_active_legacy_conflict(
                active_source=candidate,
                exact_sources=exact_sources,
                selected_endpoint_id=selected_endpoint_id,
                endpoint_relative_root=endpoint_relative_root,
            ):
                target = candidate
                conflicting_source_ids = tuple(
                    source.id for source in exact_sources if source.id != candidate.id
                )
                warnings.append(
                    _message(
                        "inactive_modern_duplicate_retained",
                        "The active legacy Source can be used safely. The inactive exact duplicate will remain unchanged for management review.",
                    )
                )
            else:
                blockers.append(
                    _message(
                        "multiple_exact_sources",
                        "Multiple existing Sources match this exact location. Review is required before continuing.",
                    )
                )
            if target is not None:
                source_action = _source_action_for_target(
                    target,
                    selected_endpoint_id=selected_endpoint_id,
                    endpoint_relative_root=endpoint_relative_root,
                    reactivate=False,
                )
        elif not blockers and not active:
            if len(inactive) == 1 and len(exact_sources) == 1:
                target = inactive[0]
                source_action = _source_action_for_target(
                    target,
                    selected_endpoint_id=selected_endpoint_id,
                    endpoint_relative_root=endpoint_relative_root,
                    reactivate=True,
                )
            else:
                blockers.append(
                    _message(
                        "multiple_exact_sources",
                        "Multiple existing Sources match this exact location. Review is required before continuing.",
                    )
                )

        allowed_inactivation_ids: list[int] = []
        exact_source_ids = {source.id for source in exact_sources}
        for source_id in requested_inactivation_ids:
            source = next((item for item in exact_sources if item.id == source_id), None)
            if source is None or source_id not in exact_source_ids:
                blockers.append(
                    _message(
                        "duplicate_source_not_exact",
                        "A selected duplicate Source no longer matches this exact location.",
                    )
                )
                continue
            if target is not None and source.id == target.id:
                blockers.append(
                    _message(
                        "canonical_source_cannot_be_inactivated",
                        "The selected canonical Source cannot also be marked inactive.",
                    )
                )
                continue
            if source.profile_status != "active":
                blockers.append(
                    _message(
                        "duplicate_source_not_active",
                        "Only active no-history duplicate Sources can be marked inactive.",
                    )
                )
                continue
            if reference_summaries[source.id].has_protected_history:
                blockers.append(
                    _message(
                        "duplicate_source_has_history",
                        "A selected duplicate Source has protected history and cannot be marked inactive here.",
                    )
                )
                continue
            allowed_inactivation_ids.append(source.id)

        return _ExactResolution(
            matches=tuple(exact_sources),
            target=target,
            source_action=source_action,
            conflicting_source_ids=conflicting_source_ids,
            duplicate_source_ids_to_inactivate=tuple(allowed_inactivation_ids),
            blockers=tuple(blockers),
            warnings=tuple(warnings),
        )

    def _overlap_warnings(
        self,
        *,
        endpoint_id: int,
        endpoint_relative_root: str,
        exclude_source_ids: set[int],
    ) -> list[SourceCreationMessage]:
        sources = self._db.scalars(
            select(IngestionSource).where(
                IngestionSource.endpoint_id == endpoint_id,
                IngestionSource.endpoint_relative_root.is_not(None),
            )
        ).all()
        if any(
            source.id not in exclude_source_ids
            and source.endpoint_relative_root is not None
            and _roots_overlap(endpoint_relative_root, source.endpoint_relative_root)
            for source in sources
        ):
            return [
                _message(
                    "source_root_overlap",
                    "This root overlaps another Source on the same device. Files may be encountered by more than one intake source.",
                )
            ]
        return []

    def _source_display_name_for_plan(
        self,
        *,
        endpoint_relative_root: str,
        source_type: str,
        selected_endpoint_id: int | None,
    ) -> tuple[str, SourceCreationMessage | None]:
        warning: SourceCreationMessage | None = None
        display_name = "Source"
        for candidate in _source_display_name_candidates(endpoint_relative_root, source_type):
            display_name, candidate_warning = _fit_source_display_name(candidate)
            if candidate_warning is not None:
                warning = candidate_warning
            if not self._source_display_name_exists_on_endpoint(
                endpoint_id=selected_endpoint_id,
                display_name=display_name,
            ):
                return display_name, warning

        fallback_seed = endpoint_relative_root or source_type
        fallback_hash = stable_hash(fallback_seed)[:8]
        fallback, fallback_warning = _fit_source_display_name(f"{display_name} ({fallback_hash})")
        return fallback, fallback_warning or warning

    def _source_display_name_exists_on_endpoint(
        self,
        *,
        endpoint_id: int | None,
        display_name: str,
    ) -> bool:
        if endpoint_id is None:
            return False
        existing_id = self._db.scalar(
            select(IngestionSource.id)
            .where(
                IngestionSource.endpoint_id == endpoint_id,
                IngestionSource.source_label_normalized == normalize_source_label(display_name),
            )
            .limit(1)
        )
        return existing_id is not None

    def _source_display_name_conflicts_with_db_tuple(
        self,
        *,
        display_name: str,
        persisted_source_type: str,
        canonical_source_root_path: str,
    ) -> bool:
        existing_id = self._db.scalar(
            select(IngestionSource.id)
            .where(
                IngestionSource.source_label_normalized == normalize_source_label(display_name),
                IngestionSource.source_type == persisted_source_type,
                IngestionSource.source_root_path_normalized
                == normalize_source_root_path(canonical_source_root_path),
            )
            .limit(1)
        )
        return existing_id is not None

    def _source_reference_summary(self, source_id: int) -> _SourceReferenceSummary:
        table_names = set(inspect(self._db.connection()).get_table_names())

        def count_rows(table_name: str, column_name: str) -> int:
            if table_name not in table_names:
                return 0
            return int(
                self._db.execute(
                    text(f"SELECT COUNT(*) FROM {table_name} WHERE {column_name} = :source_id"),
                    {"source_id": source_id},
                ).scalar()
                or 0
            )

        asset_count = 0
        if "provenance" in table_names:
            asset_count = int(
                self._db.execute(
                    text(
                        "SELECT COUNT(DISTINCT asset_sha256) "
                        "FROM provenance WHERE ingestion_source_id = :source_id"
                    ),
                    {"source_id": source_id},
                ).scalar()
                or 0
            )

        return _SourceReferenceSummary(
            provenance_count=count_rows("provenance", "ingestion_source_id"),
            ingestion_runs_count=count_rows("ingestion_runs", "ingestion_source_id"),
            source_intake_runs_count=count_rows("source_intake_runs", "ingestion_source_id"),
            asset_count=asset_count,
        )

    def _alias_conflict(
        self,
        alias: str,
        *,
        exclude_endpoint_id: int | None,
    ) -> SourceEndpoint | None:
        statement = select(SourceEndpoint).where(
            SourceEndpoint.alias_normalized == alias.casefold()
        )
        if exclude_endpoint_id is not None:
            statement = statement.where(SourceEndpoint.id != exclude_endpoint_id)
        return self._db.scalar(statement)

    def _apply_confirm(
        self,
        plan: SourceCreationPlanResponse,
        context: _PlanContext,
    ) -> SourceCreationConfirmResponse:
        probe = context.probe
        if probe is None:
            return self._blocked_confirm_response(
                plan,
                [_message("probe_result_missing", "Source identity probe result is missing.")],
            )

        endpoint = context.selected_endpoint
        created_endpoint = False
        reused_endpoint = endpoint is not None
        upgraded_legacy_endpoint = False
        renamed_endpoint = False
        alias_event: SourceEndpointAliasEvent | None = None

        rename_requested = plan.endpoint_action in {
            "rename_existing_endpoint",
            "upgrade_and_rename_endpoint",
        }
        if endpoint is not None and rename_requested:
            conflict = self._alias_conflict(plan.device_name, exclude_endpoint_id=endpoint.id)
            if conflict is not None:
                return self._blocked_confirm_response(
                    plan,
                    [_message("device_name_conflict", "Device Name is already used by another endpoint.")],
                )

        upgrade_requested = plan.endpoint_action in {
            "upgrade_legacy_endpoint",
            "upgrade_and_rename_endpoint",
        }
        if endpoint is not None and upgrade_requested and (
            not context.fingerprint.hash_value
            or context.fingerprint.strength != "strong"
            or (
                endpoint.identity_fingerprint_hash not in context.fingerprint.legacy_hashes
                and endpoint.id not in context.safe_legacy_upgrade_endpoint_ids
            )
        ):
            return self._blocked_confirm_response(
                plan,
                [_message("legacy_upgrade_not_safe", "The legacy device identity could not be upgraded safely.")],
            )

        access_node, _ = self._get_or_create_access_node(probe)
        if endpoint is None:
            fingerprint_hash = (
                context.fingerprint.hash_value
                if context.fingerprint.strength == "strong" and plan.durable_identity_status == "verified"
                else None
            )
            fingerprint_version = context.fingerprint.version if fingerprint_hash else None
            endpoint = SourceEndpoint(
                source_type=_endpoint_source_type(plan.recognized_source_type),
                alias=plan.device_name,
                alias_normalized=plan.device_name.casefold(),
                status="active",
                identity_fingerprint_hash=fingerprint_hash,
                identity_fingerprint_version=fingerprint_version,
                identity_confidence=probe.confidence_tier,
                evidence_summary_json=_safe_json(
                    {
                        "durable_identity_status": plan.durable_identity_status,
                        "identifier_type": plan.durable_identity_identifier_type,
                        "identifier": plan.durable_identity_identifier,
                        "endpoint_boundary": plan.advanced_details.get("endpoint_boundary"),
                    }
                ),
                created_from_access_node=access_node,
            )
            self._db.add(endpoint)
            self._db.flush()
            created_endpoint = True
            reused_endpoint = False
        elif upgrade_requested:
            endpoint.identity_fingerprint_hash = context.fingerprint.hash_value
            endpoint.identity_fingerprint_version = context.fingerprint.version
            endpoint.identity_confidence = probe.confidence_tier
            endpoint.evidence_summary_json = _safe_json(
                {
                    "durable_identity_status": plan.durable_identity_status,
                    "identifier_type": plan.durable_identity_identifier_type,
                    "identifier": plan.durable_identity_identifier,
                    "legacy_fingerprint_upgraded": True,
                }
            )
            self._db.add(endpoint)
            self._db.flush()
            upgraded_legacy_endpoint = True

        if rename_requested:
            old_alias = endpoint.alias
            endpoint.alias = plan.device_name
            endpoint.alias_normalized = plan.device_name.casefold()
            alias_event = SourceEndpointAliasEvent(
                source_endpoint_id=endpoint.id,
                old_alias=old_alias,
                new_alias=plan.device_name,
                action_source="source_creation_confirm",
            )
            self._db.add_all([endpoint, alias_event])
            self._db.flush()
            renamed_endpoint = True

        observed_path, created_observed_path = self._get_or_create_observed_path(
            endpoint=endpoint,
            access_node=access_node,
            probe=probe,
            plan=plan,
        )

        source = context.existing_source
        created_source = False
        reused_source = source is not None
        reactivated_source = False
        adopted_legacy_source = False
        canonicalized_source = False
        if source is None:
            source = IngestionSource(
                source_label=plan.source_display_name,
                source_label_normalized=normalize_source_label(plan.source_display_name),
                source_type=plan.persisted_source_type,
                source_root_path=plan.canonical_source_root_path,
                source_root_path_normalized=normalize_source_root_path(plan.canonical_source_root_path),
                endpoint_relative_root=plan.endpoint_relative_root,
                profile_status="active",
                endpoint_id=endpoint.id,
            )
            self._db.add(source)
            self._db.flush()
            created_source = True
            reused_source = False
        else:
            if plan.source_action in {
                "adopt_legacy_source",
                "adopt_and_reactivate_source",
                "canonicalize_existing_source",
                "canonicalize_and_reactivate_source",
            }:
                if source.endpoint_id is None:
                    source.endpoint_id = endpoint.id
                source.endpoint_relative_root = plan.endpoint_relative_root
                adopted_legacy_source = plan.source_action in {
                    "adopt_legacy_source",
                    "adopt_and_reactivate_source",
                }
                canonicalized_source = plan.source_action in {
                    "canonicalize_existing_source",
                    "canonicalize_and_reactivate_source",
                }
            if plan.source_action in {
                "reactivate_existing_source",
                "adopt_and_reactivate_source",
                "canonicalize_and_reactivate_source",
            }:
                source.profile_status = "active"
                reactivated_source = True
            self._db.add(source)
            self._db.flush()

        inactivated_duplicate_source_ids: list[int] = []
        for duplicate_source_id in plan.duplicate_source_ids_to_inactivate:
            duplicate_source = self._db.get(IngestionSource, duplicate_source_id)
            if duplicate_source is None:
                return self._blocked_confirm_response(
                    plan,
                    [_message("duplicate_source_missing", "A selected duplicate Source no longer exists.")],
                )
            duplicate_source.profile_status = "inactive"
            self._db.add(duplicate_source)
            inactivated_duplicate_source_ids.append(duplicate_source.id)
        if inactivated_duplicate_source_ids:
            self._db.flush()

        self._db.commit()
        self._db.refresh(source)
        self._db.refresh(endpoint)
        if alias_event is not None:
            self._db.refresh(alias_event)

        return SourceCreationConfirmResponse(
            creation_status="completed",
            plan_fingerprint=plan.plan_fingerprint,
            source_profile_id=source.id,
            source_endpoint_id=endpoint.id,
            observed_path_id=observed_path.id,
            alias_event_id=alias_event.id if alias_event is not None else None,
            source_type=plan.source_type,
            recognized_source_type=plan.recognized_source_type,
            persisted_source_type=source.source_type,
            device_name=endpoint.alias,
            observed_path=plan.observed_path,
            canonical_source_root_path=source.source_root_path or plan.canonical_source_root_path,
            endpoint_relative_root=(
                source.endpoint_relative_root
                if source.endpoint_relative_root is not None
                else plan.endpoint_relative_root
            ),
            entire_endpoint=plan.entire_endpoint,
            entire_endpoint_label=plan.entire_endpoint_label,
            suggested_source_name=plan.suggested_source_name,
            requested_source_name=plan.requested_source_name,
            source_display_name=source.source_label,
            durable_identity_status=plan.durable_identity_status,
            durable_identity_reason=plan.durable_identity_reason,
            durable_identity_identifier_type=plan.durable_identity_identifier_type,
            durable_identity_identifier=plan.durable_identity_identifier,
            durable_identity_evidence=plan.durable_identity_evidence,
            endpoint_action=plan.endpoint_action,
            source_action=plan.source_action,
            created_endpoint=created_endpoint,
            reused_endpoint=reused_endpoint,
            upgraded_legacy_endpoint=upgraded_legacy_endpoint,
            renamed_endpoint=renamed_endpoint,
            created_source=created_source,
            reused_source=reused_source,
            reactivated_source=reactivated_source,
            adopted_legacy_source=adopted_legacy_source,
            canonicalized_source=canonicalized_source,
            inactivated_duplicate_source_ids=inactivated_duplicate_source_ids,
            created_observed_path=created_observed_path,
            warnings=plan.warnings,
            advanced_details={
                **plan.advanced_details,
                "source_endpoint_id": endpoint.id,
                "source_profile_id": source.id,
                "observed_path_id": observed_path.id,
                "alias_event_id": alias_event.id if alias_event is not None else None,
            },
        )

    def _get_or_create_access_node(
        self,
        probe: SourceIdentityProbeResponse,
    ) -> tuple[AccessNode, bool]:
        access_node_uuid = "access-node:" + hashlib.sha256(
            _safe_json(
                {
                    "label": probe.access_node_summary.label,
                    "os_family": probe.access_node_summary.os_family,
                    "provider_name": probe.provider_name,
                    "provider_version": probe.provider_version,
                }
            ).encode("utf-8")
        ).hexdigest()[:48]
        existing = self._db.scalar(
            select(AccessNode).where(AccessNode.access_node_uuid == access_node_uuid)
        )
        now = datetime.now(timezone.utc)
        if existing is not None:
            existing.last_seen_at = now
            self._db.add(existing)
            self._db.flush()
            return existing, False

        access_node = AccessNode(
            access_node_uuid=access_node_uuid,
            label=probe.access_node_summary.label,
            os_family=probe.access_node_summary.os_family,
            provider_name=probe.provider_name,
            provider_version=probe.provider_version,
            status="active",
            last_seen_at=now,
        )
        self._db.add(access_node)
        self._db.flush()
        return access_node, True

    def _get_or_create_observed_path(
        self,
        *,
        endpoint: SourceEndpoint,
        access_node: AccessNode,
        probe: SourceIdentityProbeResponse,
        plan: SourceCreationPlanResponse,
    ) -> tuple[SourceEndpointObservedPath, bool]:
        observed_path = probe.observed_path or plan.observed_path
        normalized_path = probe.normalized_observed_path or observed_path.replace("/", "\\").casefold()
        existing = self._db.scalar(
            select(SourceEndpointObservedPath).where(
                SourceEndpointObservedPath.source_endpoint_id == endpoint.id,
                SourceEndpointObservedPath.access_node_id == access_node.id,
                SourceEndpointObservedPath.normalized_observed_path == normalized_path,
            )
        )
        now = datetime.now(timezone.utc)
        if existing is not None:
            existing.last_seen_at = now
            existing.last_success_at = now
            self._db.add(existing)
            self._db.flush()
            return existing, False

        safe_to_run = probe.safe_to_run if isinstance(probe.safe_to_run, str) else str(probe.safe_to_run).lower()
        observed = SourceEndpointObservedPath(
            source_endpoint_id=endpoint.id,
            access_node_id=access_node.id,
            observed_path=observed_path,
            normalized_observed_path=normalized_path,
            filesystem_boundary_type=probe.source_root_candidate.filesystem_boundary_type,
            source_root_candidate_path=probe.source_root_candidate.path,
            is_valid_source_root_candidate=probe.source_root_candidate.is_valid_source_root_candidate,
            probe_provider_name=probe.provider_name,
            probe_provider_version=probe.provider_version,
            probe_status=probe.probe_status,
            confidence_tier=probe.confidence_tier,
            match_status="matched" if plan.endpoint_action != "create_new_endpoint" else "not_compared",
            safe_to_run=safe_to_run,
            blockers_json=_safe_json([item.model_dump(mode="json") for item in plan.blockers]),
            warnings_json=_safe_json([item.model_dump(mode="json") for item in plan.warnings]),
            evidence_summary_json=_safe_json(
                {
                    "canonical_source_root_path": plan.canonical_source_root_path,
                    "endpoint_relative_root": plan.endpoint_relative_root,
                    "durable_identity_status": plan.durable_identity_status,
                    "identifier_type": plan.durable_identity_identifier_type,
                    "identifier": plan.durable_identity_identifier,
                }
            ),
            last_seen_at=now,
            last_success_at=now,
        )
        self._db.add(observed)
        self._db.flush()
        return observed, True

    def _blocked_confirm_response(
        self,
        plan: SourceCreationPlanResponse,
        blockers: list[SourceCreationMessage],
    ) -> SourceCreationConfirmResponse:
        return SourceCreationConfirmResponse(
            creation_status="blocked",
            plan_fingerprint=plan.plan_fingerprint,
            source_type=plan.source_type,
            recognized_source_type=plan.recognized_source_type,
            persisted_source_type=plan.persisted_source_type,
            device_name=plan.device_name,
            observed_path=plan.observed_path,
            canonical_source_root_path=plan.canonical_source_root_path,
            endpoint_relative_root=plan.endpoint_relative_root,
            entire_endpoint=plan.entire_endpoint,
            entire_endpoint_label=plan.entire_endpoint_label,
            suggested_source_name=plan.suggested_source_name,
            requested_source_name=plan.requested_source_name,
            source_display_name=plan.source_display_name,
            durable_identity_status=plan.durable_identity_status,
            durable_identity_reason=plan.durable_identity_reason,
            durable_identity_identifier_type=plan.durable_identity_identifier_type,
            durable_identity_identifier=plan.durable_identity_identifier,
            durable_identity_evidence=plan.durable_identity_evidence,
            endpoint_action=plan.endpoint_action,
            source_action=plan.source_action,
            blockers=_dedupe_messages(blockers),
            warnings=plan.warnings,
            advanced_details=plan.advanced_details,
        )


def _initial_probe_source_type(source_type: str, observed_path: str) -> str:
    if observed_path.replace("/", "\\").startswith("\\\\"):
        return "nas"
    return _probe_source_type(source_type)


def _probe_source_type(source_type: str) -> str:
    return "external_device" if source_type == "external" else source_type


def _operator_source_type_from_probe(
    probe: SourceIdentityProbeResponse,
    selected_source_type: str,
) -> str:
    if probe.source_type == "nas":
        return "nas"
    if probe.source_type == "external_device":
        return "external"
    if probe.source_type == "local":
        return "local"
    return selected_source_type


def _operator_source_type_from_endpoint(source_type: str) -> str | None:
    if source_type == "local":
        return "local"
    if source_type == "external_device":
        return "external"
    if source_type == "nas":
        return "nas"
    return None


def _operator_source_type_label(source_type: str) -> str:
    return {"local": "Local", "external": "External", "nas": "NAS"}.get(source_type, source_type)


def _endpoint_source_type(source_type: str) -> str:
    return "external_device" if source_type == "external" else source_type


def _persisted_source_type(source_type: str) -> str:
    return "external_drive" if source_type == "external" else "local_folder"


def _match_endpoint_types(
    probe: SourceIdentityProbeResponse | None,
    technical_source_type: str,
) -> set[str]:
    if probe is not None and probe.source_type in {"local", "external_device"}:
        return set(_LOCAL_ENDPOINT_TYPES)
    return {_endpoint_source_type(technical_source_type)}


def _normalize_device_name(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _normalize_source_name(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _validate_device_name(value: str) -> SourceCreationMessage | None:
    if not value:
        return _message("device_name_required", "Device Name is required.")
    if len(value) > _ALIAS_MAX_LENGTH:
        return _message("device_name_too_long", "Device Name must be 255 characters or fewer.")
    if _CONTROL_CHARACTER_RE.search(value):
        return _message("device_name_invalid", "Device Name contains an unsupported control character.")
    return None


def _validate_source_name(value: str) -> SourceCreationMessage | None:
    if not value:
        return _message("source_name_required", "Source Name is required.")
    if len(value) > _SOURCE_LABEL_MAX_LENGTH:
        return _message("source_name_too_long", "Source Name must be 255 characters or fewer.")
    if _CONTROL_CHARACTER_RE.search(value):
        return _message("source_name_invalid", "Source Name contains an unsupported control character.")
    return None


def _path_shape_blocker(source_type: str, observed_path: str) -> SourceCreationMessage | None:
    normalized = observed_path.replace("/", "\\")
    if not normalized:
        return _message("source_path_required", "Root Path or Mount Point is required.")
    if source_type in {"local", "external"}:
        if normalized.startswith("\\\\"):
            return _message("network_path_requires_nas", "This is a network path. Choose NAS.")
        if not _DRIVE_PATH_RE.match(normalized):
            return _message("absolute_source_path_required", "Enter an absolute Windows drive path.")
    elif source_type == "nas":
        if not normalized.startswith("\\\\") and not _DRIVE_PATH_RE.match(normalized):
            return _message("nas_path_required", "Enter a UNC path or an existing mapped NAS drive path.")
    return None


def _probe_reports_mapped_nas(probe: SourceIdentityProbeResponse) -> bool:
    return any(
        item.code in {"mapped_network_path_requires_nas", "mapped_drive_unc_resolved"}
        for item in probe.evidence_items
    )


def _has_clear_removable_evidence(probe: SourceIdentityProbeResponse) -> bool:
    return any(
        item.category == "volume_evidence"
        and item.code == "drive_type_present"
        and item.status == "present"
        and (item.display_value or "").casefold() == "removable"
        for item in probe.evidence_items
    )


def _probe_blockers(probe: SourceIdentityProbeResponse) -> list[SourceCreationMessage]:
    blockers = [
        _message(item.code, item.message or "Source identity probe reported a blocker.")
        for item in probe.blockers
    ]
    if probe.probe_status not in _COMPLETED_PROBE_STATUSES:
        blockers.append(_message("probe_not_completed", "Source identity probe did not complete successfully."))
    if not probe.source_root_candidate.is_valid_source_root_candidate:
        blockers.append(_message("invalid_source_root", "The selected path is not a readable Source Root."))
    return _dedupe_messages(blockers)


def _probe_warnings(probe: SourceIdentityProbeResponse) -> list[SourceCreationMessage]:
    return _dedupe_messages(
        [_message(item.code, item.message or "Source identity probe reported a warning.") for item in probe.warnings]
    )


def _derive_root(
    source_type: str,
    observed_path: str,
    probe: SourceIdentityProbeResponse | None,
) -> tuple[_DerivedRoot | None, SourceCreationMessage | None]:
    if source_type in {"local", "external"}:
        normalized = ntpath.normpath(observed_path.replace("/", "\\"))
        drive, tail = ntpath.splitdrive(normalized)
        if len(drive) != 2 or not tail.startswith("\\"):
            return None, _message("drive_root_not_derived", "The selected drive root could not be derived.")
        drive = drive.upper()
        canonical = drive + tail
        endpoint_boundary = drive + "\\"
        relative = ntpath.relpath(canonical, endpoint_boundary)
        endpoint_relative_root = "" if relative == "." else relative.strip("\\")
        return (
            _DerivedRoot(
                canonical_source_root_path=canonical,
                endpoint_relative_root=endpoint_relative_root,
                entire_endpoint=endpoint_relative_root == "",
                entire_endpoint_label="Entire device" if endpoint_relative_root == "" else None,
                endpoint_boundary=endpoint_boundary,
            ),
            None,
        )

    canonical_candidate = probe.source_root_candidate.path if probe is not None else observed_path
    canonical = ntpath.normpath((canonical_candidate or "").replace("/", "\\"))
    server_share = parse_unc_server_share(canonical)
    if server_share is None:
        return None, _message(
            "nas_share_not_derived",
            "The NAS location could not be resolved to a specific UNC server/share.",
        )
    server, share = server_share
    endpoint_boundary = f"\\\\{server}\\{share}"
    relative = ntpath.relpath(canonical, endpoint_boundary)
    endpoint_relative_root = "" if relative == "." else relative.strip("\\")
    return (
        _DerivedRoot(
            canonical_source_root_path=canonical,
            endpoint_relative_root=endpoint_relative_root,
            entire_endpoint=endpoint_relative_root == "",
            entire_endpoint_label="Entire share" if endpoint_relative_root == "" else None,
            endpoint_boundary=endpoint_boundary,
        ),
        None,
    )


def _source_display_name_candidates(endpoint_relative_root: str, source_type: str) -> list[str]:
    if not endpoint_relative_root:
        return ["Entire share" if source_type == "nas" else "Entire device"]

    parts = [part.strip() for part in endpoint_relative_root.replace("/", "\\").split("\\") if part.strip()]
    if not parts:
        return ["Entire share" if source_type == "nas" else "Entire device"]

    candidates = [parts[-1]]
    if len(parts) >= 2:
        candidates.append(f"{parts[-2]} - {parts[-1]}")
    if len(parts) >= 3:
        candidates.append(f"{parts[-3]} - {parts[-2]} - {parts[-1]}")
    candidates.append(endpoint_relative_root)
    return list(dict.fromkeys(candidates))


def _fit_source_display_name(value: str) -> tuple[str, SourceCreationMessage | None]:
    cleaned = re.sub(r"\s+", " ", value.strip()) or "Source"
    if len(cleaned) <= _SOURCE_LABEL_MAX_LENGTH:
        return cleaned, None
    shortened = f"...{cleaned[-(_SOURCE_LABEL_MAX_LENGTH - 3):]}"
    return shortened[:_SOURCE_LABEL_MAX_LENGTH], _message(
        "source_display_name_shortened",
        "The Source display name was shortened; the complete endpoint-relative root remains stored.",
    )


def _is_modern_exact(
    source: IngestionSource,
    *,
    selected_endpoint_id: int | None,
    endpoint_relative_root: str,
) -> bool:
    return (
        selected_endpoint_id is not None
        and source.endpoint_id == selected_endpoint_id
        and source.endpoint_relative_root is not None
        and source.endpoint_relative_root.casefold() == endpoint_relative_root.casefold()
    )


def _is_legacy_root_model(source: IngestionSource) -> bool:
    return source.endpoint_id is None or source.endpoint_relative_root is None


def _source_action_for_target(
    source: IngestionSource,
    *,
    selected_endpoint_id: int | None,
    endpoint_relative_root: str,
    reactivate: bool,
) -> str:
    if _is_modern_exact(
        source,
        selected_endpoint_id=selected_endpoint_id,
        endpoint_relative_root=endpoint_relative_root,
    ):
        return "reactivate_existing_source" if reactivate else "reuse_existing_source"
    if source.endpoint_id == selected_endpoint_id and source.endpoint_relative_root is None:
        return "canonicalize_and_reactivate_source" if reactivate else "canonicalize_existing_source"
    return "adopt_and_reactivate_source" if reactivate else "adopt_legacy_source"


def _source_match_classification(
    source: IngestionSource,
    *,
    selected_endpoint_id: int | None,
    endpoint_relative_root: str,
) -> str:
    if _is_modern_exact(
        source,
        selected_endpoint_id=selected_endpoint_id,
        endpoint_relative_root=endpoint_relative_root,
    ):
        return f"{source.profile_status} modern linked Source"
    if source.endpoint_id is None:
        return f"{source.profile_status} unlinked legacy Source"
    if source.endpoint_relative_root is None:
        return f"{source.profile_status} linked legacy Source"
    return f"{source.profile_status} exact Source"


def _is_approved_active_legacy_conflict(
    *,
    active_source: IngestionSource,
    exact_sources: list[IngestionSource],
    selected_endpoint_id: int | None,
    endpoint_relative_root: str,
) -> bool:
    if len(exact_sources) != 2 or not _is_legacy_root_model(active_source):
        return False
    other = next(source for source in exact_sources if source.id != active_source.id)
    return (
        other.profile_status == "inactive"
        and (
            _is_modern_exact(
                other,
                selected_endpoint_id=selected_endpoint_id,
                endpoint_relative_root=endpoint_relative_root,
            )
            or _is_legacy_root_model(other)
        )
    )


def _recognition_summary(
    *,
    blockers: list[SourceCreationMessage],
    selected_endpoint: SourceEndpoint | None,
    source_action: str,
    source_type_mismatch: bool,
    required_confirmations: list[SourceCreationMessage],
) -> tuple[str, str, str]:
    blocker_codes = {item.code for item in blockers}
    if blocker_codes & _LOCATION_BLOCKER_CODES:
        return (
            "location_blocked",
            "Location blocked or unreadable",
            blockers[0].message,
        )
    if "exact_source_endpoint_conflict" in blocker_codes:
        return (
            "multiple_source_matches",
            "Source identity conflict",
            blockers[0].message,
        )
    if "multiple_active_exact_sources" in blocker_codes or "multiple_exact_sources" in blocker_codes:
        return (
            "multiple_source_matches",
            "Multiple conflicting Source matches",
            "More than one Source matches this exact location. No automatic choice was made.",
        )
    if blockers:
        return (
            "identity_needs_review",
            "Review required",
            blockers[0].message,
        )
    if source_action == "reuse_existing_source":
        return (
            "existing_source_active",
            "Existing exact Source found",
            "This active Source already represents the recognized device and exact root.",
        )
    if source_action == "reactivate_existing_source":
        return (
            "existing_source_inactive",
            "Existing inactive Source found",
            "The exact Source exists and can be reactivated without creating a duplicate.",
        )
    if source_action in {
        "adopt_legacy_source",
        "adopt_and_reactivate_source",
        "canonicalize_existing_source",
        "canonicalize_and_reactivate_source",
    }:
        return (
            "existing_legacy_source",
            "Existing legacy Source found",
            "The exact legacy Source can be used while retaining its Source Profile ID and history.",
        )
    if selected_endpoint is not None and source_type_mismatch:
        return (
            "existing_device_type_mismatch",
            "Existing device recognized with a different stored type",
            f"This device is registered as {_operator_source_type_label(_operator_source_type_from_endpoint(selected_endpoint.source_type) or selected_endpoint.source_type)}.",
        )
    if selected_endpoint is not None:
        return (
            "existing_device",
            "Existing device recognized",
            f"Durable identity matched the registered device {selected_endpoint.alias}.",
        )
    if required_confirmations and any(
        item.code in {"durable_identity_not_verified", "select_existing_endpoint", "select_legacy_endpoint"}
        for item in required_confirmations
    ):
        return (
            "identity_needs_review",
            "Device identity needs review",
            required_confirmations[0].message,
        )
    return (
        "new_device",
        "New device identified",
        "No registered durable endpoint matched this location.",
    )


def _final_action_label(
    *,
    source_action: str,
    endpoint_action: str,
    selected_endpoint: SourceEndpoint | None,
) -> str:
    labels = {
        "create_new_source": (
            "Create Source on Existing Device" if selected_endpoint is not None else "Create New Source"
        ),
        "reuse_existing_source": "Use Existing Source",
        "reactivate_existing_source": "Reactivate Existing Source",
        "adopt_legacy_source": "Adopt and Link Existing Source",
        "adopt_and_reactivate_source": "Adopt and Reactivate Existing Source",
        "canonicalize_existing_source": "Use and Canonicalize Existing Source",
        "canonicalize_and_reactivate_source": "Canonicalize and Reactivate Existing Source",
        "none": "Review Source Matches",
    }
    base = labels.get(source_action, "Create Source")
    if endpoint_action in {"rename_existing_endpoint", "upgrade_and_rename_endpoint"}:
        return f"Rename Device and {base}"
    return base


def _roots_overlap(left: str, right: str) -> bool:
    left_parts = [part.casefold() for part in left.replace("/", "\\").split("\\") if part]
    right_parts = [part.casefold() for part in right.replace("/", "\\").split("\\") if part]
    if not left_parts or not right_parts:
        return True
    shorter, longer = (
        (left_parts, right_parts) if len(left_parts) <= len(right_parts) else (right_parts, left_parts)
    )
    return longer[: len(shorter)] == shorter


def _drive_boundary(path: str) -> str:
    drive, _ = ntpath.splitdrive(ntpath.normpath(path.replace("/", "\\")))
    return drive.upper() + "\\" if len(drive) == 2 else ""


def _message(code: str, message: str) -> SourceCreationMessage:
    return SourceCreationMessage(code=code, message=message)


def _dedupe_messages(messages: list[SourceCreationMessage]) -> list[SourceCreationMessage]:
    seen: set[str] = set()
    result: list[SourceCreationMessage] = []
    for message in messages:
        if message.code in seen:
            continue
        seen.add(message.code)
        result.append(message)
    return result


def _dedupe_matches(matches: list[SourceCreationEndpointMatch]) -> list[SourceCreationEndpointMatch]:
    seen: set[int] = set()
    result: list[SourceCreationEndpointMatch] = []
    for match in matches:
        if match.source_endpoint_id in seen:
            continue
        seen.add(match.source_endpoint_id)
        result.append(match)
    return result


def _safe_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
