"""Read-only Source Selection orchestration."""

from __future__ import annotations

import ntpath
import json
import platform
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ingestion_source import IngestionSource
from app.models.source_endpoint import SourceEndpoint, SourceEndpointObservedPath
from app.schemas.admin import IcloudSourceReadinessResponse
from app.services.ingestion.ingestion_context_service import normalize_source_root_path
from app.services.source_identity.durable_identity import DurableIdentityStatus, summarize_durable_identity
from app.services.source_identity.identity_fingerprint import (
    OPTICAL_MEDIA_FINGERPRINT_VERSION,
    fingerprint_from_probe,
    parse_unc_server_share,
    stable_hash,
)
from app.services.source_identity.probe_schema import SourceIdentityProbeRequest, SourceIdentityProbeResponse
from app.services.source_identity.probe_service import (
    LINUX_DEVELOPMENT_FIXTURE_PROVIDER_NAME,
    SourceIdentityProbeService,
)
from app.services.source_identity.providers.linux_development_fixture import CONTROLLED_SOURCE_LABEL
from app.services.source_identity.source_selection_schema import (
    SelectedSourceContext,
    SourceSelectionRequest,
    SourceSelectionResponse,
)


_ACTIVE_PROFILE_STATUS = "active"
_PATH_UNAVAILABLE_CODES = {
    "access_denied",
    "blank_or_unreadable_optical_media",
    "no_readable_optical_media_inserted",
    "optical_drive_unverified",
    "path_not_found",
    "path_not_readable",
    "source_root_invalid",
}
_COMPLETED_PROBE_STATUSES = {"completed", "completed_with_warnings"}
_BENIGN_ICLOUD_WARNING_CODES = {"AUTH_UNKNOWN", "NO_RECENT_ACQUISITION", "STAGING_FOLDER_MISSING", "SOURCE_REGISTRATION_UNKNOWN"}
_VOLUME_GUID_RE = re.compile(r"Volume\{([^}]+)\}", re.IGNORECASE)
_MOUNTED_VOLUME_ENUMERATION_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class MountedVolumeCandidate:
    """Read-only mounted-volume evidence used to find a current endpoint path."""

    root_path: str
    identity_fingerprint_hash: str | None = None
    identity_fingerprint_version: str | None = None
    drive_type: str | None = None
    identity_identifier_masked: str | None = None


class SourceSelectionService:
    """Select and verify one Source Profile without mutating metadata."""

    def __init__(
        self,
        db_session: Session,
        probe_service: SourceIdentityProbeService | None = None,
        icloud_readiness_resolver: Callable[..., IcloudSourceReadinessResponse] | None = None,
        mounted_volume_resolver: Callable[[], list[MountedVolumeCandidate]] | None = None,
    ) -> None:
        self._db = db_session
        self._probe_service = probe_service or SourceIdentityProbeService()
        self._icloud_readiness_resolver = icloud_readiness_resolver
        self._mounted_volume_resolver = mounted_volume_resolver or enumerate_windows_mounted_volume_candidates

    def select_source(
        self,
        request: SourceSelectionRequest,
        *,
        operator_acknowledged: bool = False,
    ) -> SourceSelectionResponse:
        """Return a normalized, read-only Source Selection result."""
        source = self._db.get(IngestionSource, request.source_profile_id)
        if source is None:
            raise LookupError("Source profile not found.")

        endpoint = self._load_endpoint(source)
        friendly_type = _friendly_source_type(source, endpoint)

        if source.profile_status != _ACTIVE_PROFILE_STATUS:
            return self._not_selected(
                availability="needs_attention",
                message="Only active Sources can be selected in the normal workflow.",
                retry_guidance="Use Source management to review this Source status.",
                advanced_details=_base_advanced_details(source, endpoint, friendly_type),
            )

        if endpoint is not None and endpoint.status == "retired":
            return self._not_selected(
                availability="needs_attention",
                message="The linked Source Endpoint is retired and cannot be selected.",
                retry_guidance="Review this Source in Source management.",
                advanced_details=_base_advanced_details(source, endpoint, friendly_type),
            )

        if _is_icloud_source(source):
            return self._select_icloud(source, endpoint, friendly_type)

        if source.endpoint_id is not None and endpoint is None:
            return self._not_selected(
                availability="needs_attention",
                message="This Source is linked to an endpoint that no longer exists.",
                retry_guidance="Review or repair the Source endpoint link before selecting it.",
                advanced_details=_base_advanced_details(source, endpoint, friendly_type),
            )

        if endpoint is None:
            return self._select_legacy_path_only(
                source,
                friendly_type,
                operator_acknowledged=operator_acknowledged,
            )

        if source.endpoint_relative_root is None:
            return self._not_selected(
                availability="needs_attention",
                message="This linked legacy Source needs identity review before it can be selected.",
                retry_guidance="Use the future Source identity repair workflow before selecting this Source.",
                advanced_details={
                    **_base_advanced_details(source, endpoint, friendly_type),
                    "legacy_reason": "endpoint_relative_root is NULL on a linked Source.",
                },
            )

        return self._select_modern_filesystem(source, endpoint, friendly_type)

    def _select_modern_filesystem(
        self,
        source: IngestionSource,
        endpoint: SourceEndpoint,
        friendly_type: str,
    ) -> SourceSelectionResponse:
        probe_source_type = _probe_source_type_for_endpoint(endpoint.source_type, friendly_type)
        if probe_source_type is None:
            return self._not_selected(
                availability="needs_attention",
                message="This Source type is not supported by Source Selection yet.",
                retry_guidance="Use the existing management or provider-specific workflow for this Source.",
                advanced_details=_base_advanced_details(source, endpoint, friendly_type),
            )

        attempted_paths: list[str] = []
        saw_unavailable = False
        saw_mismatch = False
        saw_legacy_optical_v1 = False
        attention_reason: str | None = None

        for candidate_path in self._candidate_paths(source, endpoint):
            attempted_paths.append(candidate_path)
            probe = self._probe(probe_source_type, candidate_path)
            if _probe_path_unavailable(probe):
                saw_unavailable = True
                continue

            identity_status = _identity_match_status(endpoint, probe)
            if identity_status == "legacy_optical_v1":
                saw_legacy_optical_v1 = True
                continue
            if identity_status == "mismatch":
                saw_mismatch = True
                continue
            if identity_status != "matched":
                attention_reason = "Endpoint identity could not be verified automatically."
                continue

            endpoint_path = _endpoint_path_from_probe(probe, friendly_type) or _endpoint_path_from_path(candidate_path, friendly_type)
            if not endpoint_path:
                attention_reason = "Current endpoint path could not be resolved from probe evidence."
                continue

            resolved_root = _join_endpoint_root(endpoint_path, source.endpoint_relative_root or "")
            root_probe = probe if _same_path(candidate_path, resolved_root) else self._probe(probe_source_type, resolved_root)
            if root_probe is not probe:
                attempted_paths.append(resolved_root)

            root_identity_status = _identity_match_status(endpoint, root_probe)
            if root_identity_status == "legacy_optical_v1":
                saw_legacy_optical_v1 = True
                continue
            if root_identity_status == "mismatch":
                saw_mismatch = True
                continue
            if _probe_path_unavailable(root_probe):
                return self._not_selected(
                    availability="needs_attention",
                    message=f"{source.source_label} was recognized, but its Source Root is missing or unreadable.",
                    retry_guidance="Restore the configured Source Root on the connected device, then select the Source again.",
                    advanced_details={
                        **_base_advanced_details(source, endpoint, friendly_type),
                        "attempted_paths": _dedupe(attempted_paths),
                        "resolved_endpoint_path": endpoint_path,
                        "resolved_source_root": resolved_root,
                        "root_probe": _probe_details(root_probe),
                    },
                )
            if not _probe_is_usable(root_probe, allow_needs_review=True):
                attention_reason = "The Source Root exists, but the probe did not classify it as automatically selectable."
                continue

            durable_identity = summarize_durable_identity(probe=root_probe, source_type=source.source_type)
            context = self._context(
                source=source,
                endpoint=endpoint,
                friendly_type=friendly_type,
                device_label=endpoint.alias,
                resolved_source_root=resolved_root,
                resolved_endpoint_path=endpoint_path,
                durable_identity_status=durable_identity.status,
                identity_match_status="matched",
                workflow_kind="filesystem_source_intake",
            )
            return SourceSelectionResponse(
                result="selected",
                availability="available",
                workflow_kind="filesystem_source_intake",
                selected_source_context=context,
                message=f"{source.source_label} is available.",
                retry_guidance=None,
                advanced_details={
                    **_base_advanced_details(source, endpoint, friendly_type),
                    "attempted_paths": _dedupe(attempted_paths),
                    "resolved_endpoint_path": endpoint_path,
                    "probe": _probe_details(root_probe),
                    "durable_identity_reason": durable_identity.reason,
                    "durable_identity_identifier_type": durable_identity.identifier_type,
                    "durable_identity_identifier": durable_identity.identifier,
                },
            )

        if saw_legacy_optical_v1:
            return self._not_selected(
                availability="needs_attention",
                message="This Optical Source uses the earlier v1 identity format. Recreate the Optical Source to use the stable v2 identity.",
                retry_guidance="Use the current Optical workflow to recreate this disc Source.",
                advanced_details={
                    **_base_advanced_details(source, endpoint, friendly_type),
                    "attempted_paths": _dedupe(attempted_paths),
                    "legacy_reason": "optical_media_fingerprint_v1",
                },
            )
        if saw_mismatch:
            return self._not_selected(
                availability="unavailable",
                message=f"{_device_label_for_source(source, endpoint, friendly_type)} does not match the selected Source identity.",
                retry_guidance="Connect the correct device, media, disc, or share and select the Source again.",
                advanced_details={
                    **_base_advanced_details(source, endpoint, friendly_type),
                    "attempted_paths": _dedupe(attempted_paths),
                },
            )
        if saw_unavailable:
            return self._not_selected(
                availability="unavailable",
                message=f"{_device_label_for_source(source, endpoint, friendly_type)} is not currently available.",
                retry_guidance="Connect or make the Source available, then select it again.",
                advanced_details={
                    **_base_advanced_details(source, endpoint, friendly_type),
                    "attempted_paths": _dedupe(attempted_paths),
                },
            )
        return self._not_selected(
            availability="needs_attention",
            message=attention_reason or "This Source could not be selected automatically.",
            retry_guidance="Review the Source identity and path details before trying again.",
            advanced_details={
                **_base_advanced_details(source, endpoint, friendly_type),
                "attempted_paths": _dedupe(attempted_paths),
            },
        )

    def _select_legacy_path_only(
        self,
        source: IngestionSource,
        friendly_type: str,
        *,
        operator_acknowledged: bool,
    ) -> SourceSelectionResponse:
        if source.endpoint_relative_root is not None:
            return self._not_selected(
                availability="needs_attention",
                message="This legacy Source has inconsistent endpoint-relative-root metadata.",
                retry_guidance="Review this Source in the future identity repair workflow.",
                advanced_details={
                    **_base_advanced_details(source, None, friendly_type),
                    "legacy_reason": "endpoint_relative_root is populated without an endpoint link.",
                },
            )
        if not source.source_root_path:
            return self._not_selected(
                availability="needs_attention",
                message="This legacy Source does not have a configured Source Root.",
                retry_guidance="Review or recreate this Source before selecting it.",
                advanced_details=_base_advanced_details(source, None, friendly_type),
            )

        is_controlled_fixture = source.source_label == CONTROLLED_SOURCE_LABEL
        if is_controlled_fixture and source.source_type != "local_folder":
            return self._not_selected(
                availability="needs_attention",
                message="The controlled Development fixture Source must remain a local path-only Source.",
                retry_guidance="Review the controlled fixture Source without changing its identity shape.",
                advanced_details={
                    **_base_advanced_details(source, None, friendly_type),
                    "fixture_reason": "controlled fixture Source type is not local_folder.",
                },
            )
        if is_controlled_fixture and not operator_acknowledged:
            return self._not_selected(
                availability="needs_attention",
                message="Explicit acknowledgment is required before selecting the controlled Development fixture Source.",
                retry_guidance="Run ingestion with the explicit legacy/review acknowledgment.",
                advanced_details={
                    **_base_advanced_details(source, None, friendly_type),
                    "fixture_reason": "development fixture acknowledgment was not supplied.",
                },
            )

        probe_source_type = _probe_source_type_for_legacy(source, friendly_type)
        if probe_source_type is None:
            return self._not_selected(
                availability="needs_attention",
                message="This legacy Source type is not supported by Source Selection.",
                retry_guidance="Use Source management or create a modern Source.",
                advanced_details=_base_advanced_details(source, None, friendly_type),
            )

        probe = self._probe(
            probe_source_type,
            source.source_root_path,
            controlled_fixture=is_controlled_fixture,
        )
        if _probe_path_unavailable(probe):
            return self._not_selected(
                availability="unavailable",
                message="This legacy Source path is absent or unreadable.",
                retry_guidance="Make the stored path available, then select the Source again.",
                advanced_details={
                    **_base_advanced_details(source, None, friendly_type),
                    "probe": _probe_details(probe),
                    "legacy_reason": "path-only compatibility fallback failed because the path is unavailable.",
                },
            )
        if not _probe_is_usable(probe, allow_needs_review=is_controlled_fixture):
            return self._not_selected(
                availability="needs_attention",
                message="This legacy Source needs identity review before it can be selected.",
                retry_guidance="Create a modern Source or use the future identity repair workflow.",
                advanced_details={
                    **_base_advanced_details(source, None, friendly_type),
                    "probe": _probe_details(probe),
                    "legacy_reason": "probe did not complete as an automatically safe path-only selection.",
                },
            )
        if self._has_active_exact_conflict(source):
            return self._not_selected(
                availability="needs_attention",
                message="This legacy Source has an exact active conflict that needs review.",
                retry_guidance="Use Source management before selecting this legacy Source.",
                advanced_details={
                    **_base_advanced_details(source, None, friendly_type),
                    "legacy_reason": "another active Source has the same normalized Source Root.",
                },
            )
        if self._matches_registered_endpoint(probe):
            return self._not_selected(
                availability="needs_attention",
                message="This legacy Source appears to belong to a registered endpoint and needs identity review.",
                retry_guidance="Use the future identity repair workflow instead of selecting it as path-only.",
                advanced_details={
                    **_base_advanced_details(source, None, friendly_type),
                    "probe": _probe_details(probe),
                    "legacy_reason": "probe fingerprint matches an existing Source Endpoint.",
                },
            )

        context = self._context(
            source=source,
            endpoint=None,
            friendly_type=friendly_type,
            device_label="Development fixture path" if is_controlled_fixture else "Legacy source",
            resolved_source_root=source.source_root_path,
            resolved_endpoint_path=None,
            durable_identity_status="not_verified",
            identity_match_status=(
                "development_fixture_path_only"
                if is_controlled_fixture
                else "path_only_compatibility"
            ),
            workflow_kind="filesystem_source_intake",
            provider_context=(
                {
                    "provider_name": LINUX_DEVELOPMENT_FIXTURE_PROVIDER_NAME,
                    "identity_representation": "unverified_development_fixture_path_only",
                    "requires_operator_acknowledgment": True,
                }
                if is_controlled_fixture
                else None
            ),
        )
        return SourceSelectionResponse(
            result="selected",
            availability="available",
            workflow_kind="filesystem_source_intake",
            selected_source_context=context,
            message=(
                f"{source.source_label} is available as an acknowledged, unverified Development fixture path."
                if is_controlled_fixture
                else f"{source.source_label} is available through legacy path compatibility."
            ),
            retry_guidance=None,
            advanced_details={
                **_base_advanced_details(source, None, friendly_type),
                "probe": _probe_details(probe),
                "legacy_reason": (
                    "exact acknowledged Development fixture Source selected without durable identity."
                    if is_controlled_fixture
                    else "active path-only Source selected through strict compatibility fallback."
                ),
            },
        )

    def _select_icloud(
        self,
        source: IngestionSource,
        endpoint: SourceEndpoint | None,
        friendly_type: str,
    ) -> SourceSelectionResponse:
        readiness = self._resolve_icloud_readiness(source.id)
        provider_context = _safe_icloud_provider_context(readiness)
        advanced_details = {
            **_base_advanced_details(source, endpoint, friendly_type),
            "icloud_readiness": provider_context,
            "icloud_blocking_reasons": [reason.model_dump(mode="json") for reason in readiness.blocking_reasons],
            "icloud_warnings": [warning.model_dump(mode="json") for warning in readiness.warnings],
        }
        blocking_codes = {reason.code for reason in readiness.blocking_reasons}
        warning_codes = {warning.code for warning in readiness.warnings}
        has_operation_conflict = (
            readiness.operation_conflicts.icloud_acquisition_active
            or readiness.operation_conflicts.source_intake_active
            or readiness.operation_conflicts.icloud_cleanup_active
        )
        if readiness.readiness_status == "not_ready" or blocking_codes or readiness.auth_status == "action_required" or has_operation_conflict:
            message = readiness.blocking_reasons[0].message if readiness.blocking_reasons else readiness.recommended_action
            return self._not_selected(
                availability="needs_attention",
                message=message or "The iCloud session requires attention before this Source can be selected.",
                retry_guidance=readiness.recommended_action,
                advanced_details=advanced_details,
            )
        if readiness.readiness_status == "unknown" or (warning_codes - _BENIGN_ICLOUD_WARNING_CODES):
            return self._not_selected(
                availability="needs_attention",
                message=readiness.recommended_action or "The iCloud Source needs attention before it can be selected.",
                retry_guidance=readiness.recommended_action,
                advanced_details=advanced_details,
            )

        root_display = "Provider managed"
        if readiness.managed_staging_path:
            root_display = readiness.managed_staging_path
        context = self._context(
            source=source,
            endpoint=endpoint,
            friendly_type=friendly_type,
            device_label=_icloud_device_label(source, readiness),
            resolved_source_root=readiness.effective_path,
            resolved_endpoint_path=None,
            durable_identity_status="provider_specific",
            identity_match_status="provider_specific",
            workflow_kind="icloud_intake",
            provider_context=provider_context,
            root_display=root_display,
        )
        return SourceSelectionResponse(
            result="selected",
            availability="available",
            workflow_kind="icloud_intake",
            selected_source_context=context,
            message=f"{source.source_label} is available for iCloud Intake.",
            retry_guidance=None,
            advanced_details=advanced_details,
        )

    def _resolve_icloud_readiness(self, source_id: int) -> IcloudSourceReadinessResponse:
        if self._icloud_readiness_resolver is not None:
            return self._icloud_readiness_resolver(self._db, source_id=source_id, include_username=False)
        from app.services.admin.icloud_readiness_service import get_icloud_source_readiness

        return get_icloud_source_readiness(self._db, source_id=source_id, include_username=False)

    def _load_endpoint(self, source: IngestionSource) -> SourceEndpoint | None:
        if source.endpoint_id is None:
            return None
        return self._db.get(SourceEndpoint, source.endpoint_id)

    def _candidate_paths(self, source: IngestionSource, endpoint: SourceEndpoint) -> list[str]:
        candidates: list[str] = []
        friendly_type = _friendly_source_type(source, endpoint)
        if source.source_root_path:
            candidates.append(source.source_root_path)
            endpoint_path = _endpoint_path_from_path(source.source_root_path, friendly_type)
            if endpoint_path:
                candidates.append(endpoint_path)
        observed = self._db.scalars(
            select(SourceEndpointObservedPath)
            .where(SourceEndpointObservedPath.source_endpoint_id == endpoint.id)
            .order_by(SourceEndpointObservedPath.last_success_at.desc().nullslast(), SourceEndpointObservedPath.last_seen_at.desc())
        ).all()
        for item in observed:
            if item.observed_path:
                candidates.append(item.observed_path)
                observed_endpoint_path = _endpoint_path_from_path(item.observed_path, friendly_type)
                if observed_endpoint_path:
                    candidates.append(observed_endpoint_path)
            if item.source_root_candidate_path:
                candidates.append(item.source_root_candidate_path)
                candidate_endpoint_path = _endpoint_path_from_path(item.source_root_candidate_path, friendly_type)
                if candidate_endpoint_path:
                    candidates.append(candidate_endpoint_path)
        candidates.extend(self._mounted_volume_candidate_paths(source, endpoint, friendly_type))
        return _dedupe([candidate for candidate in candidates if candidate and candidate.strip()])

    def _mounted_volume_candidate_paths(
        self,
        source: IngestionSource,
        endpoint: SourceEndpoint,
        friendly_type: str,
    ) -> list[str]:
        if friendly_type not in {"Local", "External", "Removable"}:
            return []
        if not endpoint.identity_fingerprint_hash:
            return []
        paths: list[str] = []
        for mounted in self._mounted_volume_resolver():
            if mounted.identity_fingerprint_hash != endpoint.identity_fingerprint_hash:
                continue
            endpoint_root = _normalize_drive_root_path(mounted.root_path)
            if endpoint_root is None:
                continue
            paths.append(_join_endpoint_root(endpoint_root, source.endpoint_relative_root or ""))
        return paths

    def _probe(
        self,
        source_type: str,
        path: str,
        *,
        controlled_fixture: bool = False,
    ) -> SourceIdentityProbeResponse:
        return self._probe_service.probe(
            SourceIdentityProbeRequest(
                source_type=source_type,  # type: ignore[arg-type]
                observed_path=path,
                probe_mode="readiness_probe",
                intended_use=(
                    "m005_development_fixture_source_selection_acknowledged"
                    if controlled_fixture
                    else "source_selection"
                ),
                os_family="linux" if controlled_fixture else "unknown",
                provider_name=LINUX_DEVELOPMENT_FIXTURE_PROVIDER_NAME if controlled_fixture else None,
            )
        )

    def _has_active_exact_conflict(self, source: IngestionSource) -> bool:
        normalized_root = source.source_root_path_normalized or normalize_source_root_path(source.source_root_path)
        if not normalized_root:
            return False
        count = self._db.scalar(
            select(func.count(IngestionSource.id)).where(
                IngestionSource.id != source.id,
                IngestionSource.profile_status == _ACTIVE_PROFILE_STATUS,
                IngestionSource.source_root_path_normalized == normalized_root,
            )
        )
        return bool(count and count > 0)

    def _matches_registered_endpoint(self, probe: SourceIdentityProbeResponse) -> bool:
        fingerprint = fingerprint_from_probe(probe)
        hashes = [fingerprint.hash_value, *fingerprint.legacy_hashes]
        hashes = [value for value in hashes if value]
        if not hashes:
            return False
        existing = self._db.scalar(
            select(SourceEndpoint.id).where(SourceEndpoint.identity_fingerprint_hash.in_(hashes)).limit(1)
        )
        return existing is not None

    def _context(
        self,
        *,
        source: IngestionSource,
        endpoint: SourceEndpoint | None,
        friendly_type: str,
        device_label: str,
        resolved_source_root: str | None,
        resolved_endpoint_path: str | None,
        durable_identity_status: DurableIdentityStatus,
        identity_match_status: str,
        workflow_kind: str,
        provider_context: dict[str, Any] | None = None,
        root_display: str | None = None,
    ) -> SelectedSourceContext:
        selected_at = datetime.now(timezone.utc)
        safe_fingerprint_payload = {
            "source_profile_id": source.id,
            "source_endpoint_id": endpoint.id if endpoint is not None else None,
            "source_type": source.source_type,
            "profile_status": source.profile_status,
            "endpoint_relative_root": source.endpoint_relative_root,
            "resolved_source_root": resolved_source_root,
            "workflow_kind": workflow_kind,
        }
        return SelectedSourceContext(
            source_profile_id=source.id,
            source_endpoint_id=endpoint.id if endpoint is not None else None,
            source_type=source.source_type,
            friendly_source_type=friendly_type,
            device_label=device_label,
            source_name=source.source_label,
            profile_status=source.profile_status,
            endpoint_status=endpoint.status if endpoint is not None else None,
            endpoint_relative_root=source.endpoint_relative_root,
            configured_source_root=source.source_root_path,
            resolved_source_root=resolved_source_root,
            resolved_endpoint_path=resolved_endpoint_path,
            root_display=root_display or resolved_source_root or source.source_root_path or "Provider managed",
            durable_identity_status=durable_identity_status,
            identity_match_status=identity_match_status,
            availability="available",
            workflow_kind=workflow_kind,  # type: ignore[arg-type]
            provider_context=provider_context,
            selected_at=selected_at,
            selection_fingerprint=stable_hash(safe_fingerprint_payload),
        )

    def _not_selected(
        self,
        *,
        availability: str,
        message: str,
        retry_guidance: str | None,
        advanced_details: dict[str, Any],
    ) -> SourceSelectionResponse:
        return SourceSelectionResponse(
            result="not_selected",
            availability=availability,  # type: ignore[arg-type]
            workflow_kind=None,
            selected_source_context=None,
            message=message,
            retry_guidance=retry_guidance,
            advanced_details=advanced_details,
        )


def _is_icloud_source(source: IngestionSource) -> bool:
    return source.source_type == "cloud_export" and source.cloud_provider == "icloud"


def _friendly_source_type(source: IngestionSource, endpoint: SourceEndpoint | None) -> str:
    if _is_icloud_source(source):
        return "iCloud"
    endpoint_type = endpoint.source_type if endpoint is not None else None
    if endpoint_type == "nas":
        return "NAS"
    if endpoint_type == "external_device":
        return "External"
    if endpoint_type == "removable_media":
        return "Removable"
    if endpoint_type == "optical_media":
        return "Optical"
    if endpoint_type == "local":
        return "Local"
    if source.source_type == "external_drive":
        return "External"
    if source.source_type == "removable_media":
        return "Removable"
    if source.source_type == "optical_media":
        return "Optical"
    if source.source_type == "local_folder" and _is_unc_path(source.source_root_path):
        return "NAS"
    if source.source_type == "local_folder":
        return "Local"
    if source.source_type == "cloud_export":
        return "iCloud" if source.cloud_provider == "icloud" else "Cloud"
    return "Advanced / Legacy"


def _probe_source_type_for_endpoint(endpoint_type: str, friendly_type: str) -> str | None:
    if endpoint_type in {"local", "external_device", "removable_media", "optical_media", "nas"}:
        return endpoint_type
    return _probe_source_type_for_friendly(friendly_type)


def _probe_source_type_for_legacy(source: IngestionSource, friendly_type: str) -> str | None:
    if source.source_type == "external_drive":
        return "external_device"
    if source.source_type in {"removable_media", "optical_media"}:
        return source.source_type
    return _probe_source_type_for_friendly(friendly_type)


def _probe_source_type_for_friendly(friendly_type: str) -> str | None:
    return {
        "Local": "local",
        "External": "external_device",
        "Removable": "removable_media",
        "Optical": "optical_media",
        "NAS": "nas",
    }.get(friendly_type)


def enumerate_windows_mounted_volume_candidates() -> list[MountedVolumeCandidate]:
    """Return currently mounted Windows drive roots with durable identity evidence when available.

    This is deliberately bounded and read-only. It asks Windows for actual mounted
    logical volumes and never probes an A-Z drive-letter range.
    """

    if platform.system().strip().casefold() != "windows":
        return []
    script = (
        "Get-Volume -ErrorAction SilentlyContinue | "
        "Where-Object DriveLetter | "
        "Select-Object DriveLetter,DriveType,UniqueId,Path,FileSystemType,FileSystemLabel | "
        "ConvertTo-Json -Compress -Depth 3"
    )
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=_MOUNTED_VOLUME_ENUMERATION_TIMEOUT_SECONDS,
            shell=False,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return []
    if completed.returncode != 0 or not (completed.stdout or "").strip():
        return []
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return []
    rows = payload if isinstance(payload, list) else [payload]
    candidates: list[MountedVolumeCandidate] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        drive_letter = str(row.get("DriveLetter") or "").strip().rstrip(":\\/")
        if len(drive_letter) != 1:
            continue
        root_path = f"{drive_letter.upper()}:\\"
        unique_id = str(row.get("UniqueId") or row.get("Path") or "").strip()
        fingerprint_hash: str | None = None
        fingerprint_version: str | None = None
        masked_identifier: str | None = None
        match = _VOLUME_GUID_RE.search(unique_id)
        if match:
            from app.services.source_identity.identity_fingerprint import volume_guid_fingerprint

            fingerprint_hash, fingerprint_version = volume_guid_fingerprint(match.group(1))
            masked_identifier = f"{{...{match.group(1)[-4:].casefold()}}}"
        candidates.append(
            MountedVolumeCandidate(
                root_path=root_path,
                identity_fingerprint_hash=fingerprint_hash,
                identity_fingerprint_version=fingerprint_version,
                drive_type=str(row.get("DriveType") or "").strip() or None,
                identity_identifier_masked=masked_identifier,
            )
        )
    return candidates


def _identity_match_status(endpoint: SourceEndpoint, probe: SourceIdentityProbeResponse) -> str:
    fingerprint = fingerprint_from_probe(probe)
    if endpoint.source_type == "optical_media" and endpoint.identity_fingerprint_version == OPTICAL_MEDIA_FINGERPRINT_VERSION:
        return "legacy_optical_v1"
    if endpoint.identity_fingerprint_hash and fingerprint.hash_value == endpoint.identity_fingerprint_hash:
        return "matched"
    if endpoint.identity_fingerprint_hash and endpoint.identity_fingerprint_hash in fingerprint.legacy_hashes:
        return "needs_attention"
    if endpoint.identity_fingerprint_hash and fingerprint.hash_value and fingerprint.strength == "strong":
        return "mismatch"
    return "needs_attention"


def _probe_path_unavailable(probe: SourceIdentityProbeResponse) -> bool:
    blocker_codes = {item.code for item in probe.blockers}
    return probe.probe_status == "unavailable" or bool(blocker_codes & _PATH_UNAVAILABLE_CODES)


def _probe_is_usable(probe: SourceIdentityProbeResponse, *, allow_needs_review: bool = False) -> bool:
    safe_to_run_is_selectable = (
        probe.safe_to_run is True
        or probe.safe_to_run == "not_applicable"
        or (allow_needs_review and probe.safe_to_run == "needs_review")
    )
    return (
        probe.probe_status in _COMPLETED_PROBE_STATUSES
        and probe.source_root_candidate.is_valid_source_root_candidate
        and not probe.blockers
        and safe_to_run_is_selectable
    )


def _endpoint_path_from_probe(probe: SourceIdentityProbeResponse, friendly_type: str) -> str | None:
    path = probe.source_root_candidate.path or probe.observed_path
    return _endpoint_path_from_path(path, friendly_type)


def _endpoint_path_from_path(path: str | None, friendly_type: str) -> str | None:
    if not path:
        return None
    normalized = path.replace("/", "\\")
    if friendly_type == "NAS":
        server_share = parse_unc_server_share(normalized)
        if server_share is None:
            return None
        server, share = server_share
        return f"\\\\{server}\\{share}"
    drive, _tail = ntpath.splitdrive(normalized)
    if drive:
        return f"{drive}\\"
    return None


def _normalize_drive_root_path(path: str | None) -> str | None:
    if not path:
        return None
    drive, _tail = ntpath.splitdrive(path.replace("/", "\\"))
    if not drive:
        return None
    return f"{drive.upper()}\\"


def _join_endpoint_root(endpoint_path: str, endpoint_relative_root: str) -> str:
    if not endpoint_relative_root:
        return endpoint_path
    cleaned_endpoint_path = endpoint_path.rstrip("\\/")
    cleaned_relative_root = endpoint_relative_root.strip("\\/")
    return f"{cleaned_endpoint_path}\\{cleaned_relative_root}"


def _same_path(left: str, right: str) -> bool:
    return left.replace("/", "\\").rstrip("\\").casefold() == right.replace("/", "\\").rstrip("\\").casefold()


def _is_unc_path(path: str | None) -> bool:
    return (path or "").strip().replace("/", "\\").startswith("\\\\")


def _device_label_for_source(source: IngestionSource, endpoint: SourceEndpoint | None, friendly_type: str) -> str:
    if endpoint is not None:
        return endpoint.alias
    if friendly_type == "iCloud":
        return source.account_username or source.source_label
    return "Legacy source"


def _icloud_device_label(source: IngestionSource, readiness: IcloudSourceReadinessResponse) -> str:
    if readiness.account_username_masked:
        return f"iCloud {readiness.account_username_masked}"
    return source.source_label


def _safe_icloud_provider_context(readiness: IcloudSourceReadinessResponse) -> dict[str, Any]:
    return {
        "source_id": readiness.source_id,
        "is_icloud_profile": readiness.is_icloud_profile,
        "readiness_status": readiness.readiness_status,
        "profile_status": readiness.profile_status,
        "cloud_provider": readiness.cloud_provider,
        "account_username_masked": readiness.account_username_masked,
        "managed_staging_path": readiness.managed_staging_path,
        "expected_acquisition_path": readiness.expected_acquisition_path,
        "effective_path": readiness.effective_path,
        "approved_root_status": readiness.approved_root_status,
        "staging_folder_status": readiness.staging_folder_status,
        "path_alignment_status": readiness.path_alignment_status,
        "source_root_alignment_status": readiness.source_root_alignment_status,
        "source_registration_status": readiness.source_registration_status,
        "auth_status": readiness.auth_status,
        "operation_conflicts": readiness.operation_conflicts.model_dump(mode="json"),
        "blocking_reason_codes": [reason.code for reason in readiness.blocking_reasons],
        "warning_codes": [warning.code for warning in readiness.warnings],
        "recommended_action": readiness.recommended_action,
    }


def _base_advanced_details(
    source: IngestionSource,
    endpoint: SourceEndpoint | None,
    friendly_type: str,
) -> dict[str, Any]:
    return {
        "source_profile": {
            "id": source.id,
            "source_type": source.source_type,
            "profile_status": source.profile_status,
            "endpoint_relative_root": source.endpoint_relative_root,
            "configured_source_root": source.source_root_path,
            "cloud_provider": source.cloud_provider,
        },
        "endpoint": None if endpoint is None else {
            "id": endpoint.id,
            "source_type": endpoint.source_type,
            "status": endpoint.status,
            "identity_fingerprint_version": endpoint.identity_fingerprint_version,
            "identity_confidence": endpoint.identity_confidence,
        },
        "friendly_source_type": friendly_type,
    }


def _probe_details(probe: SourceIdentityProbeResponse) -> dict[str, Any]:
    return {
        "probe_status": probe.probe_status,
        "source_type": probe.source_type,
        "provider_name": probe.provider_name,
        "provider_version": probe.provider_version,
        "observed_path": probe.observed_path,
        "source_root_candidate_path": probe.source_root_candidate.path,
        "filesystem_boundary_type": probe.source_root_candidate.filesystem_boundary_type,
        "is_valid_source_root_candidate": probe.source_root_candidate.is_valid_source_root_candidate,
        "confidence_tier": probe.confidence_tier,
        "match_status": probe.match_status,
        "safe_to_run": probe.safe_to_run if isinstance(probe.safe_to_run, str) else str(probe.safe_to_run).lower(),
        "blocker_codes": [item.code for item in probe.blockers],
        "warning_codes": [item.code for item in probe.warnings],
    }


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.strip().replace("/", "\\").casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(value)
    return deduped
