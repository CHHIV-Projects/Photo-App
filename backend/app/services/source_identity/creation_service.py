"""Transactional, drive-agnostic filesystem Source creation."""

from __future__ import annotations

import hashlib
import json
import ntpath
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.ingestion_source import IngestionSource
from app.models.source_endpoint import AccessNode, SourceEndpoint, SourceEndpointObservedPath
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


@dataclass(frozen=True)
class _DerivedRoot:
    canonical_source_root_path: str
    endpoint_relative_root: str
    entire_endpoint: bool
    entire_endpoint_label: str | None
    endpoint_boundary: str


@dataclass(frozen=True)
class _PlanContext:
    probe: SourceIdentityProbeResponse | None
    fingerprint: FingerprintResult
    selected_endpoint: SourceEndpoint | None
    existing_source: IngestionSource | None
    safe_legacy_upgrade_endpoint_ids: frozenset[int]


class SourceCreationService:
    """Plan and atomically confirm filesystem Source creation."""

    def __init__(
        self,
        db_session: Session,
        probe_service: SourceIdentityProbeService | None = None,
    ) -> None:
        self._db = db_session
        self._probe_service = probe_service or SourceIdentityProbeService()

    def plan(self, request: SourceCreationPlanRequest) -> SourceCreationPlanResponse:
        """Return a read-only creation plan."""
        plan, _ = self._build_plan(request)
        return plan

    def confirm(self, request: SourceCreationConfirmRequest) -> SourceCreationConfirmResponse:
        """Recompute a plan and apply all creation writes in one transaction."""
        plan_request = SourceCreationPlanRequest(
            source_type=request.source_type,
            device_name=request.device_name,
            observed_path=request.observed_path,
            selected_existing_endpoint_id=request.selected_existing_endpoint_id,
            operator_review_acknowledged=request.operator_review_acknowledged,
        )
        plan, context = self._build_plan(plan_request)
        blockers = list(plan.blockers)
        if request.plan_fingerprint != plan.plan_fingerprint:
            blockers.append(
                _message(
                    "plan_fingerprint_mismatch",
                    "The reviewed Create Source plan changed. Refresh the plan before confirming.",
                )
            )
        if not request.operator_confirmed:
            blockers.append(
                _message(
                    "operator_confirmation_required",
                    "Confirm Create Source before saving the device and source root.",
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
        if not requested_device_name:
            blockers.append(_message("device_name_required", "Device Name is required."))
        elif len(requested_device_name) > _ALIAS_MAX_LENGTH:
            blockers.append(_message("device_name_too_long", "Device Name must be 255 characters or fewer."))
        elif _CONTROL_CHARACTER_RE.search(requested_device_name):
            blockers.append(
                _message("device_name_invalid", "Device Name contains an unsupported control character.")
            )

        observed_path = (request.observed_path or "").strip()
        shape_blocker = _path_shape_blocker(request.source_type, observed_path)
        if shape_blocker is not None:
            blockers.append(shape_blocker)

        probe: SourceIdentityProbeResponse | None = None
        if not blockers:
            probe = self._probe_service.probe(
                SourceIdentityProbeRequest(
                    source_type=_probe_source_type(request.source_type),
                    observed_path=observed_path,
                    probe_mode="setup_probe",
                    intended_use="drive_agnostic_source_creation",
                    os_family="windows",
                )
            )
            blockers.extend(_probe_blockers(probe))
            warnings.extend(_probe_warnings(probe))

        derived_root, derive_blocker = _derive_root(request.source_type, observed_path, probe)
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
            source_type=_persisted_source_type(request.source_type),
        )
        fingerprint = fingerprint_from_probe(probe) if probe is not None else FingerprintResult(None, "unavailable", None)
        endpoint_source_type = _endpoint_source_type(request.source_type)

        strong_matches = self._find_matches(
            endpoint_source_type=endpoint_source_type,
            fingerprint_hash=fingerprint.hash_value if fingerprint.strength == "strong" else None,
            match_strength="strong",
        )
        strong_ids = {match.source_endpoint_id for match in strong_matches}
        legacy_matches: list[SourceCreationEndpointMatch] = []
        for legacy_hash in fingerprint.legacy_hashes:
            legacy_matches.extend(
                match
                for match in self._find_matches(
                    endpoint_source_type=endpoint_source_type,
                    fingerprint_hash=legacy_hash,
                    match_strength="legacy_review",
                )
                if match.source_endpoint_id not in strong_ids
            )
        safe_legacy_upgrade_endpoint_ids = {
            match.source_endpoint_id for match in legacy_matches
        }
        revalidated_legacy_matches = self._find_revalidated_legacy_matches(
            endpoint_source_type=endpoint_source_type,
            endpoint_boundary=derived_root.endpoint_boundary,
            fingerprint=fingerprint,
            excluded_endpoint_ids=strong_ids | safe_legacy_upgrade_endpoint_ids,
        )
        legacy_matches.extend(revalidated_legacy_matches)
        safe_legacy_upgrade_endpoint_ids.update(
            match.source_endpoint_id for match in revalidated_legacy_matches
        )
        possible_matches = _dedupe_matches([*strong_matches, *legacy_matches])
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
                    "More than one matching device identity exists. Select the device to reuse.",
                )
            )
        elif legacy_matches:
            if len(legacy_matches) == 1:
                selected_match = legacy_matches[0]
                selected_endpoint = self._db.get(SourceEndpoint, selected_match.source_endpoint_id)
            else:
                required_confirmations.append(
                    _message(
                        "select_legacy_endpoint",
                        "More than one legacy device identity may match. Select the device to review.",
                    )
                )

        if selected_endpoint is not None and selected_endpoint.status == "retired":
            blockers.append(_message("selected_endpoint_retired", "The selected device identity is retired."))
        if selected_match is not None and selected_match.match_strength == "legacy_review":
            required_confirmations.append(
                _message(
                    "legacy_endpoint_upgrade_required",
                    "The known device uses a legacy masked-identifier fingerprint. Review and confirm its safe upgrade.",
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

        canonical_device_name = selected_endpoint.alias if selected_endpoint is not None else requested_device_name
        if selected_endpoint is not None and requested_device_name and requested_device_name != selected_endpoint.alias:
            warnings.append(
                _message(
                    "existing_device_name_reused",
                    f"Existing device identity found. This source will use the known device name: {selected_endpoint.alias}.",
                )
            )

        if endpoint_action == "create_new_endpoint" and requested_device_name:
            alias_conflict = self._db.scalar(
                select(SourceEndpoint).where(
                    SourceEndpoint.alias_normalized == requested_device_name.casefold(),
                    SourceEndpoint.status != "retired",
                )
            )
            if alias_conflict is not None:
                blockers.append(
                    _message(
                        "device_name_conflict",
                        "Device Name is already used by a different durable device identity.",
                    )
                )

        if durable_identity.status != "verified" and not blockers:
            required_confirmations.append(
                _message(
                    "durable_identity_not_verified",
                    "Durable device identity is not verified. Review the evidence before creating this source.",
                )
            )

        source_display_name, display_warning = _source_display_name(
            canonical_device_name or requested_device_name or "Unnamed Device",
            derived_root.endpoint_relative_root,
            request.source_type,
        )
        if display_warning is not None:
            warnings.append(display_warning)

        existing_source: IngestionSource | None = None
        if selected_endpoint is not None:
            existing_sources = self._find_existing_sources(
                endpoint_id=selected_endpoint.id,
                endpoint_relative_root=derived_root.endpoint_relative_root,
                canonical_source_root_path=derived_root.canonical_source_root_path,
            )
            if len(existing_sources) > 1:
                blockers.append(
                    _message(
                        "multiple_existing_sources",
                        "More than one existing Source Profile has this device and relative root.",
                    )
                )
            elif existing_sources:
                existing_source = existing_sources[0]
                source_display_name = existing_source.source_label

            warnings.extend(
                self._overlap_warnings(
                    endpoint_id=selected_endpoint.id,
                    endpoint_relative_root=derived_root.endpoint_relative_root,
                    exclude_source_id=existing_source.id if existing_source is not None else None,
                )
            )

        if (
            request.source_type == "local"
            and derived_root.entire_endpoint
            and derived_root.endpoint_boundary[:2].casefold() == os.environ.get("SystemDrive", "C:").casefold()
        ):
            warnings.append(
                _message(
                    "entire_system_volume_selected",
                    "This source includes the whole system volume and may contain system or application folders.",
                )
            )

        blockers = _dedupe_messages(blockers)
        warnings = _dedupe_messages(warnings)
        required_confirmations = _dedupe_messages(required_confirmations)

        source_action = "reuse_existing_source" if existing_source is not None else "create_new_source"
        if blockers:
            plan_status = "blocked"
        elif possible_matches and selected_endpoint is None:
            plan_status = "needs_review"
        elif required_confirmations and not request.operator_review_acknowledged:
            plan_status = "needs_review"
        elif existing_source is not None:
            plan_status = "source_exists"
        else:
            plan_status = "ready"

        plan_fingerprint = stable_hash(
            {
                "source_type": request.source_type,
                "canonical_device_name": canonical_device_name,
                "canonical_source_root_path": derived_root.canonical_source_root_path.casefold(),
                "endpoint_relative_root": derived_root.endpoint_relative_root.casefold(),
                "fingerprint_hash": fingerprint.hash_value,
                "fingerprint_version": fingerprint.version,
                "selected_existing_endpoint_id": selected_endpoint.id if selected_endpoint is not None else None,
                "endpoint_action": endpoint_action,
                "source_action": source_action,
                "existing_source_profile_id": existing_source.id if existing_source is not None else None,
                "blockers": [item.code for item in blockers],
                "required_confirmations": [item.code for item in required_confirmations],
            }
        )

        plan = SourceCreationPlanResponse(
            plan_status=plan_status,  # type: ignore[arg-type]
            plan_fingerprint=plan_fingerprint,
            source_type=request.source_type,
            persisted_source_type=_persisted_source_type(request.source_type),
            requested_device_name=requested_device_name,
            device_name=canonical_device_name or requested_device_name,
            observed_path=observed_path,
            canonical_source_root_path=derived_root.canonical_source_root_path,
            endpoint_relative_root=derived_root.endpoint_relative_root,
            entire_endpoint=derived_root.entire_endpoint,
            entire_endpoint_label=derived_root.entire_endpoint_label,
            source_display_name=source_display_name,
            **durable_identity.response_fields(),
            endpoint_action=endpoint_action,  # type: ignore[arg-type]
            source_action=source_action,  # type: ignore[arg-type]
            selected_existing_endpoint_id=selected_endpoint.id if selected_endpoint is not None else None,
            existing_source_profile_id=existing_source.id if existing_source is not None else None,
            possible_matches=possible_matches,
            blockers=blockers,
            warnings=warnings,
            required_confirmations=required_confirmations,
            advanced_details={
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

    def _find_matches(
        self,
        *,
        endpoint_source_type: str,
        fingerprint_hash: str | None,
        match_strength: str,
    ) -> list[SourceCreationEndpointMatch]:
        if not fingerprint_hash:
            return []
        endpoints = self._db.scalars(
            select(SourceEndpoint).where(
                SourceEndpoint.source_type == endpoint_source_type,
                SourceEndpoint.identity_fingerprint_hash == fingerprint_hash,
                SourceEndpoint.status != "retired",
            )
        ).all()
        reason = (
            "Same source type and full durable identity fingerprint."
            if match_strength == "strong"
            else "Legacy masked-identifier fingerprint may represent this device."
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
        endpoint_source_type: str,
        endpoint_boundary: str,
        fingerprint: FingerprintResult,
        excluded_endpoint_ids: set[int],
    ) -> list[SourceCreationEndpointMatch]:
        """Re-probe legacy observed paths before treating an old endpoint as a match."""
        if (
            endpoint_source_type not in {"local", "external_device"}
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
                SourceEndpoint.source_type == endpoint_source_type,
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
                observed_probe = self._probe_service.probe(
                    SourceIdentityProbeRequest(
                        source_type=endpoint_source_type,  # type: ignore[arg-type]
                        observed_path=observed.observed_path,
                        probe_mode="setup_probe",
                        intended_use="legacy_endpoint_identity_revalidation",
                        os_family="windows",
                    )
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
                        "A previously observed path was re-probed and matched the current full durable "
                        "Volume GUID."
                    ),
                    identity_confidence=endpoint.identity_confidence,
                )
            )
        return matches

    def _find_existing_sources(
        self,
        *,
        endpoint_id: int,
        endpoint_relative_root: str,
        canonical_source_root_path: str,
    ) -> list[IngestionSource]:
        normalized_relative = endpoint_relative_root.casefold()
        exact = self._db.scalars(
            select(IngestionSource).where(
                IngestionSource.endpoint_id == endpoint_id,
                IngestionSource.endpoint_relative_root.is_not(None),
                func.lower(IngestionSource.endpoint_relative_root) == normalized_relative,
            )
        ).all()
        if exact:
            return list(exact)

        normalized_root = normalize_source_root_path(canonical_source_root_path)
        return list(
            self._db.scalars(
                select(IngestionSource).where(
                    IngestionSource.endpoint_id == endpoint_id,
                    IngestionSource.endpoint_relative_root.is_(None),
                    IngestionSource.source_root_path_normalized == normalized_root,
                )
            ).all()
        )

    def _overlap_warnings(
        self,
        *,
        endpoint_id: int,
        endpoint_relative_root: str,
        exclude_source_id: int | None,
    ) -> list[SourceCreationMessage]:
        sources = self._db.scalars(
            select(IngestionSource).where(
                IngestionSource.endpoint_id == endpoint_id,
                IngestionSource.endpoint_relative_root.is_not(None),
            )
        ).all()
        if any(
            source.id != exclude_source_id
            and source.endpoint_relative_root is not None
            and _roots_overlap(endpoint_relative_root, source.endpoint_relative_root)
            for source in sources
        ):
            return [
                _message(
                    "source_root_overlap",
                    "This source overlaps another source on the same device. Files may be encountered by more than one intake source.",
                )
            ]
        return []

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

        if endpoint is not None and plan.endpoint_action == "upgrade_legacy_endpoint" and (
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
                source_type=_endpoint_source_type(plan.source_type),
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
        elif plan.endpoint_action == "upgrade_legacy_endpoint":
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

        observed_path, created_observed_path = self._get_or_create_observed_path(
            endpoint=endpoint,
            access_node=access_node,
            probe=probe,
            plan=plan,
        )

        source = context.existing_source
        created_source = False
        reused_source = source is not None
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

        self._db.commit()
        self._db.refresh(source)
        self._db.refresh(endpoint)

        return SourceCreationConfirmResponse(
            creation_status="completed",
            plan_fingerprint=plan.plan_fingerprint,
            source_profile_id=source.id,
            source_endpoint_id=endpoint.id,
            observed_path_id=observed_path.id,
            source_type=plan.source_type,
            persisted_source_type=plan.persisted_source_type,
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
            created_source=created_source,
            reused_source=reused_source,
            created_observed_path=created_observed_path,
            warnings=plan.warnings,
            advanced_details={
                **plan.advanced_details,
                "source_endpoint_id": endpoint.id,
                "source_profile_id": source.id,
                "observed_path_id": observed_path.id,
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
            persisted_source_type=plan.persisted_source_type,
            device_name=plan.device_name,
            observed_path=plan.observed_path,
            canonical_source_root_path=plan.canonical_source_root_path,
            endpoint_relative_root=plan.endpoint_relative_root,
            entire_endpoint=plan.entire_endpoint,
            entire_endpoint_label=plan.entire_endpoint_label,
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


def _probe_source_type(source_type: str) -> str:
    return "external_device" if source_type == "external" else source_type


def _endpoint_source_type(source_type: str) -> str:
    return "external_device" if source_type == "external" else source_type


def _persisted_source_type(source_type: str) -> str:
    return "external_drive" if source_type == "external" else "local_folder"


def _normalize_device_name(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _path_shape_blocker(source_type: str, observed_path: str) -> SourceCreationMessage | None:
    normalized = observed_path.replace("/", "\\")
    if not normalized:
        return _message("source_path_required", "Root Path or Mount Point is required.")
    if source_type in {"local", "external"}:
        if normalized.startswith("\\\\"):
            return _message("network_path_requires_nas", "This is a network path. Choose NAS.")
        if not _DRIVE_PATH_RE.match(normalized):
            return _message("absolute_drive_path_required", "Enter an absolute Windows drive path.")
    elif source_type == "nas":
        if not normalized.startswith("\\\\") and not _DRIVE_PATH_RE.match(normalized):
            return _message(
                "nas_path_required",
                "Enter a UNC path or an existing mapped NAS drive path.",
            )
    return None


def _probe_blockers(probe: SourceIdentityProbeResponse) -> list[SourceCreationMessage]:
    blockers = [_message(item.code, item.message or "Source identity probe reported a blocker.") for item in probe.blockers]
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


def _source_display_name(
    device_name: str,
    endpoint_relative_root: str,
    source_type: str,
) -> tuple[str, SourceCreationMessage | None]:
    suffix = endpoint_relative_root or ("Entire share" if source_type == "nas" else "Entire device")
    full_name = f"{device_name} - {suffix}"
    if len(full_name) <= _SOURCE_LABEL_MAX_LENGTH:
        return full_name, None
    available = max(12, _SOURCE_LABEL_MAX_LENGTH - len(device_name) - 6)
    shortened = f"{device_name} - ...{suffix[-available:]}"
    return shortened[:_SOURCE_LABEL_MAX_LENGTH], _message(
        "source_display_name_shortened",
        "The Source display name was shortened to fit; the complete endpoint-relative root remains stored.",
    )


def _roots_overlap(left: str, right: str) -> bool:
    left_parts = [part.casefold() for part in left.replace("/", "\\").split("\\") if part]
    right_parts = [part.casefold() for part in right.replace("/", "\\").split("\\") if part]
    if not left_parts or not right_parts:
        return True
    shorter, longer = (left_parts, right_parts) if len(left_parts) <= len(right_parts) else (right_parts, left_parts)
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
