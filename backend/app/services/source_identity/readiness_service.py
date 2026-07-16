"""Read-only Source Profile readiness service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from sqlalchemy.orm import Session

from app.models.ingestion_source import IngestionSource
from app.models.source_endpoint import SourceEndpoint
from app.services.source_identity.identity_fingerprint import fingerprint_from_probe
from app.services.source_identity.probe_schema import (
    SourceIdentityProbeRequest,
    SourceIdentityProbeResponse,
    SourceIdentitySourceType,
)
from app.services.source_identity.probe_service import SourceIdentityProbeService
from app.services.source_identity.readiness_schema import (
    IdentityMatchStatus,
    ReadinessStatus,
    SourceProfileReadinessMessage,
    SourceProfileReadinessResponse,
)


_ProbeMapping = Literal["provider_specific", "unsupported"]
_COMPLETED_PROBE_STATUSES = {"completed", "completed_with_warnings"}
_PATH_UNAVAILABLE_CODES = {"access_denied", "path_not_found", "path_not_readable", "source_root_invalid"}


class SourceProfileReadinessService:
    """Evaluate whether the current runtime can safely use a Source Profile."""

    def __init__(
        self,
        db_session: Session,
        probe_service: SourceIdentityProbeService | None = None,
    ) -> None:
        self._db = db_session
        self._probe_service = probe_service or SourceIdentityProbeService()

    def check_readiness(self, source_profile_id: int) -> SourceProfileReadinessResponse:
        """Return a read-only readiness result for one Source Profile."""
        source = self._db.get(IngestionSource, source_profile_id)
        if source is None:
            raise LookupError("Source profile not found.")

        effective_path, path_kind = _effective_path(source)
        mapped_type = _map_source_type(source.source_type, effective_path)

        if mapped_type == "provider_specific":
            return self._provider_specific_response(source, effective_path=effective_path, path_kind=path_kind)

        if source.profile_status != "active":
            return self._blocked_without_probe(
                source,
                identity_match_status="unknown",
                code="profile_not_active",
                message="Only active Source Profiles can run Source Intake.",
                recommended_next_action="Set the Source Profile active before running intake.",
            )

        if mapped_type == "unsupported":
            return self._blocked_without_probe(
                source,
                identity_match_status="unsupported",
                code="unsupported_source_type",
                message="This Source Profile type is not supported by generic readiness.",
                recommended_next_action="Use a supported local, external, removable, or NAS Source Profile.",
            )

        if not effective_path:
            return self._blocked_without_probe(
                source,
                identity_match_status="unavailable",
                code="source_path_missing",
                message="This Source Profile does not have a source path configured.",
                recommended_next_action="Configure or reconnect the source path.",
            )

        probe = self._probe_service.probe(
            SourceIdentityProbeRequest(
                source_type=mapped_type,
                observed_path=effective_path,
                probe_mode="readiness_probe",
                intended_use="source_profile_readiness",
                os_family="windows",
            )
        )
        probe_block = _probe_blocker(probe)
        endpoint = self._load_endpoint(source)

        if probe_block is not None:
            status, identity_status, blocker = probe_block
            return self._response(
                source,
                endpoint=endpoint,
                probe=probe,
                readiness_status=status,
                identity_match_status=identity_status,
                can_run_source_intake=False,
                requires_operator_acknowledgment=False,
                hard_block=True,
                operator_message=blocker.message,
                recommended_next_action=_blocked_next_action(identity_status),
                blockers=[blocker],
                warnings=_probe_warning_messages(probe),
            )

        if source.endpoint_id is None:
            return self._path_only_response(source, probe)

        if endpoint is None:
            return self._response(
                source,
                endpoint=None,
                probe=probe,
                readiness_status="blocked",
                identity_match_status="mismatch",
                can_run_source_intake=False,
                hard_block=True,
                operator_message="Source Profile is linked to an endpoint that was not found.",
                recommended_next_action="Review or repair the Source Profile endpoint link.",
                blockers=[
                    _message(
                        "linked_endpoint_not_found",
                        "Source Profile is linked to an endpoint that was not found.",
                    )
                ],
                warnings=_probe_warning_messages(probe),
            )

        endpoint_blocker = _endpoint_blocker(endpoint=endpoint, probe=probe)
        if endpoint_blocker is not None:
            return self._response(
                source,
                endpoint=endpoint,
                probe=probe,
                readiness_status="blocked",
                identity_match_status="mismatch",
                can_run_source_intake=False,
                hard_block=True,
                operator_message=endpoint_blocker.message,
                recommended_next_action="Review the linked Source Endpoint before running intake.",
                blockers=[endpoint_blocker],
                warnings=_probe_warning_messages(probe),
            )

        fingerprint = fingerprint_from_probe(probe)
        fingerprint_match = (
            bool(endpoint.identity_fingerprint_hash)
            and bool(fingerprint.hash_value)
            and endpoint.identity_fingerprint_hash == fingerprint.hash_value
        )

        if (
            endpoint.identity_fingerprint_hash
            and fingerprint.hash_value
            and endpoint.identity_fingerprint_hash != fingerprint.hash_value
            and fingerprint.strength == "strong"
        ):
            return self._response(
                source,
                endpoint=endpoint,
                probe=probe,
                readiness_status="blocked",
                identity_match_status="mismatch",
                can_run_source_intake=False,
                hard_block=True,
                operator_message="Current source identity does not match the enrolled Source Endpoint.",
                recommended_next_action="Reconnect the correct source or review the Source Profile endpoint link.",
                blockers=[
                    _message(
                        "endpoint_identity_mismatch",
                        "Current source identity does not match the enrolled Source Endpoint.",
                    )
                ],
                warnings=_probe_warning_messages(probe),
                current_fingerprint_strength=fingerprint.strength,
                fingerprint_match=False,
            )

        if fingerprint_match and fingerprint.strength == "strong" and probe.safe_to_run is True:
            return self._response(
                source,
                endpoint=endpoint,
                probe=probe,
                readiness_status="ready",
                identity_match_status="matched",
                can_run_source_intake=True,
                requires_operator_acknowledgment=False,
                hard_block=False,
                operator_message="Source is ready. The current source matches the enrolled endpoint.",
                recommended_next_action="Run Intake",
                warnings=_probe_warning_messages(probe),
                current_fingerprint_strength=fingerprint.strength,
                fingerprint_match=True,
            )

        warning = _message(
            "identity_needs_review",
            "Source is readable, but endpoint identity evidence requires review before intake.",
        )
        return self._response(
            source,
            endpoint=endpoint,
            probe=probe,
            readiness_status="needs_review",
            identity_match_status="needs_review",
            can_run_source_intake=True,
            requires_operator_acknowledgment=True,
            hard_block=False,
            operator_message="Source can run after reviewing the endpoint identity warning.",
            recommended_next_action="Run Intake with acknowledgment",
            warnings=[*_probe_warning_messages(probe), warning],
            current_fingerprint_strength=fingerprint.strength,
            fingerprint_match=fingerprint_match,
        )

    def _path_only_response(
        self,
        source: IngestionSource,
        probe: SourceIdentityProbeResponse,
    ) -> SourceProfileReadinessResponse:
        warning = _message(
            "durable_source_identity_recommended",
            "Path-only source identity. Durable source identity enrollment is recommended.",
        )
        return self._response(
            source,
            endpoint=None,
            probe=probe,
            readiness_status="path_only",
            identity_match_status="not_enrolled",
            can_run_source_intake=True,
            requires_operator_acknowledgment=True,
            hard_block=False,
            operator_message="Source can run, but durable source identity enrollment is recommended.",
            recommended_next_action="Run Intake or enroll durable source identity.",
            warnings=[*_probe_warning_messages(probe), warning],
        )

    def _provider_specific_response(
        self,
        source: IngestionSource,
        *,
        effective_path: str | None,
        path_kind: str,
    ) -> SourceProfileReadinessResponse:
        message = (
            "iCloud readiness is handled by iCloud Intake."
            if source.cloud_provider == "icloud"
            else "Cloud readiness is handled by the provider-specific workflow."
        )
        return SourceProfileReadinessResponse(
            source_profile_id=source.id,
            source_label=source.source_label,
            source_type=source.source_type,
            profile_status=source.profile_status,
            cloud_provider=source.cloud_provider,
            endpoint_id=source.endpoint_id,
            readiness_status="provider_specific",
            identity_match_status="provider_specific",
            can_run_source_intake=False,
            requires_operator_acknowledgment=False,
            hard_block=False,
            operator_message=message,
            recommended_next_action="Use iCloud Intake" if source.cloud_provider == "icloud" else "Use provider-specific readiness.",
            observed_path_summary={
                "path": effective_path,
                "path_kind": path_kind,
            },
            checked_at=_utc_now(),
        )

    def _blocked_without_probe(
        self,
        source: IngestionSource,
        *,
        identity_match_status: IdentityMatchStatus,
        code: str,
        message: str,
        recommended_next_action: str,
    ) -> SourceProfileReadinessResponse:
        return self._response(
            source,
            endpoint=self._load_endpoint(source),
            probe=None,
            readiness_status="blocked",
            identity_match_status=identity_match_status,
            can_run_source_intake=False,
            requires_operator_acknowledgment=False,
            hard_block=True,
            operator_message=message,
            recommended_next_action=recommended_next_action,
            blockers=[_message(code, message)],
        )

    def _load_endpoint(self, source: IngestionSource) -> SourceEndpoint | None:
        if source.endpoint_id is None:
            return None
        return self._db.get(SourceEndpoint, source.endpoint_id)

    def _response(
        self,
        source: IngestionSource,
        *,
        endpoint: SourceEndpoint | None,
        probe: SourceIdentityProbeResponse | None,
        readiness_status: ReadinessStatus,
        identity_match_status: IdentityMatchStatus,
        can_run_source_intake: bool,
        operator_message: str,
        recommended_next_action: str,
        requires_operator_acknowledgment: bool = False,
        hard_block: bool = False,
        warnings: list[SourceProfileReadinessMessage] | None = None,
        blockers: list[SourceProfileReadinessMessage] | None = None,
        current_fingerprint_strength: str | None = None,
        fingerprint_match: bool | None = None,
    ) -> SourceProfileReadinessResponse:
        return SourceProfileReadinessResponse(
            source_profile_id=source.id,
            source_label=source.source_label,
            source_type=source.source_type,
            profile_status=source.profile_status,
            cloud_provider=source.cloud_provider,
            endpoint_id=source.endpoint_id,
            endpoint_alias=endpoint.alias if endpoint is not None else None,
            endpoint_source_type=endpoint.source_type if endpoint is not None else None,
            readiness_status=readiness_status,
            identity_match_status=identity_match_status,
            can_run_source_intake=can_run_source_intake,
            requires_operator_acknowledgment=requires_operator_acknowledgment,
            hard_block=hard_block,
            operator_message=operator_message,
            recommended_next_action=recommended_next_action,
            warnings=_dedupe_messages(warnings or []),
            blockers=_dedupe_messages(blockers or []),
            checked_at=_utc_now(),
            probe_summary=_probe_summary(probe),
            observed_path_summary=_observed_path_summary(probe),
            access_node_summary=_access_node_summary(probe),
            advanced_details=_advanced_details(
                endpoint=endpoint,
                probe=probe,
                current_fingerprint_strength=current_fingerprint_strength,
                fingerprint_match=fingerprint_match,
            ),
        )


def _map_source_type(source_type: str | None, path: str | None) -> SourceIdentitySourceType | _ProbeMapping:
    normalized = (source_type or "").strip().lower()
    if normalized in {"cloud_export", "cloud"}:
        return "provider_specific"
    if normalized in {"scan_batch", "other", ""}:
        return "unsupported"
    if normalized in {"local_folder", "local"}:
        return "nas" if _is_unc_path(path) else "local"
    if normalized in {"external_drive", "external_device"}:
        return "external_device"
    if normalized == "removable_media":
        return "removable_media"
    if normalized == "nas":
        return "nas"
    return "unsupported"


def _effective_path(source: IngestionSource) -> tuple[str | None, str]:
    if source.source_type == "cloud_export" and source.cloud_provider == "icloud" and source.managed_staging_path:
        return source.managed_staging_path, "managed_staging_path"
    if source.source_root_path:
        return source.source_root_path, "source_root_path"
    if source.managed_staging_path:
        return source.managed_staging_path, "managed_staging_path"
    return None, "none"


def _is_unc_path(path: str | None) -> bool:
    normalized = (path or "").strip().replace("/", "\\")
    return normalized.startswith("\\\\")


def _probe_blocker(
    probe: SourceIdentityProbeResponse,
) -> tuple[ReadinessStatus, IdentityMatchStatus, SourceProfileReadinessMessage] | None:
    boundary = probe.source_root_candidate.filesystem_boundary_type
    blocker_codes = {item.code for item in probe.blockers}

    if probe.match_status == "ambiguous":
        return (
            "blocked",
            "ambiguous",
            _message("ambiguous_source_identity", "Source identity evidence is ambiguous."),
        )
    if probe.probe_status == "unsupported_provider":
        return (
            "blocked",
            "unsupported",
            _message("unsupported_probe_provider", "The source identity probe provider is not supported."),
        )
    if boundary == "nas_server_only":
        return (
            "blocked",
            "unsupported",
            _message("nas_server_only_not_source_root", "A NAS server alone is not a runnable source root."),
        )
    if boundary in {"unknown", "cloud_profile_scope"} and not probe.source_root_candidate.is_valid_source_root_candidate:
        return (
            "blocked",
            "unsupported",
            _message("unsupported_source_root_boundary", "The observed path is not a supported source root."),
        )
    if blocker_codes & _PATH_UNAVAILABLE_CODES:
        first = next((item for item in probe.blockers if item.code in _PATH_UNAVAILABLE_CODES), None)
        code = first.code if first is not None else "source_unavailable"
        message = first.message if first is not None and first.message else "Source path is unavailable."
        return (
            "blocked",
            "unavailable",
            _message(code, message),
        )
    if probe.probe_status not in _COMPLETED_PROBE_STATUSES:
        return (
            "blocked",
            "unavailable",
            _message("probe_not_completed", "Readiness probe did not complete successfully."),
        )
    if not probe.source_root_candidate.is_valid_source_root_candidate:
        return (
            "blocked",
            "unavailable",
            _message("invalid_source_root_candidate", "The source path is not a readable source root."),
        )
    if probe.safe_to_run is False:
        return (
            "blocked",
            "unavailable",
            _message("not_safe_to_run", "The probe did not classify this source root as safe to run."),
        )
    return None


def _endpoint_blocker(endpoint: SourceEndpoint, probe: SourceIdentityProbeResponse) -> SourceProfileReadinessMessage | None:
    if endpoint.status == "retired":
        return _message("linked_endpoint_retired", "Linked Source Endpoint is retired.")
    if endpoint.source_type != probe.source_type:
        return _message("linked_endpoint_source_type_mismatch", "Linked Source Endpoint has a different source type.")
    return None


def _probe_warning_messages(probe: SourceIdentityProbeResponse) -> list[SourceProfileReadinessMessage]:
    warnings = [_message(item.code, item.message or "Probe reported a warning.") for item in probe.warnings]
    if probe.probe_status == "completed_with_warnings":
        warnings.append(_message("probe_completed_with_warnings", "Readiness probe completed with warnings."))
    if probe.safe_to_run == "needs_review":
        warnings.append(_message("safe_to_run_needs_review", "Probe result requires operator review."))
    return _dedupe_messages(warnings)


def _blocked_next_action(identity_match_status: IdentityMatchStatus) -> str:
    if identity_match_status == "unsupported":
        return "Use a supported source root or provider-specific workflow."
    if identity_match_status == "unavailable":
        return "Fix or reconnect the source path."
    if identity_match_status == "mismatch":
        return "Reconnect the correct source or review the Source Profile endpoint link."
    if identity_match_status == "ambiguous":
        return "Review the source identity evidence before running intake."
    return "Review Source Profile readiness details."


def _probe_summary(probe: SourceIdentityProbeResponse | None) -> dict[str, object]:
    if probe is None:
        return {}
    safe_to_run = probe.safe_to_run if isinstance(probe.safe_to_run, str) else str(probe.safe_to_run).lower()
    return {
        "probe_status": probe.probe_status,
        "source_type": probe.source_type,
        "provider_name": probe.provider_name,
        "provider_version": probe.provider_version,
        "confidence_tier": probe.confidence_tier,
        "match_status": probe.match_status,
        "safe_to_run": safe_to_run,
    }


def _observed_path_summary(probe: SourceIdentityProbeResponse | None) -> dict[str, object]:
    if probe is None:
        return {}
    return {
        "observed_path": probe.observed_path,
        "normalized_observed_path": probe.normalized_observed_path,
        "source_root_candidate_path": probe.source_root_candidate.path,
        "filesystem_boundary_type": probe.source_root_candidate.filesystem_boundary_type,
        "is_valid_source_root_candidate": probe.source_root_candidate.is_valid_source_root_candidate,
    }


def _access_node_summary(probe: SourceIdentityProbeResponse | None) -> dict[str, object]:
    if probe is None:
        return {}
    return probe.access_node_summary.model_dump(mode="json", exclude_none=True)


def _advanced_details(
    *,
    endpoint: SourceEndpoint | None,
    probe: SourceIdentityProbeResponse | None,
    current_fingerprint_strength: str | None,
    fingerprint_match: bool | None,
) -> dict[str, object]:
    details: dict[str, object] = {}
    if endpoint is not None:
        details["endpoint"] = {
            "status": endpoint.status,
            "identity_confidence": endpoint.identity_confidence,
            "identity_fingerprint_version": endpoint.identity_fingerprint_version,
        }
    if probe is not None:
        details["probe"] = {
            "blocker_codes": [item.code for item in probe.blockers],
            "warning_codes": [item.code for item in probe.warnings],
            "privacy_redaction_applied": probe.privacy_redaction_applied,
        }
    if current_fingerprint_strength is not None:
        details["current_identity_fingerprint_strength"] = current_fingerprint_strength
    if fingerprint_match is not None:
        details["fingerprint_match"] = fingerprint_match
    return details


def _message(code: str, message: str) -> SourceProfileReadinessMessage:
    return SourceProfileReadinessMessage(code=code, message=message)


def _dedupe_messages(messages: list[SourceProfileReadinessMessage]) -> list[SourceProfileReadinessMessage]:
    deduped: list[SourceProfileReadinessMessage] = []
    seen: set[str] = set()
    for message in messages:
        if message.code in seen:
            continue
        seen.add(message.code)
        deduped.append(message)
    return deduped


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
