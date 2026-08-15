"""Backend adapter for the shared non-admin Windows identity collector."""

from __future__ import annotations

from app.services.source_identity.probe_schema import (
    AccessNodeSummary,
    IdentityFingerprintCandidate,
    SourceIdentityEvidenceItem,
    SourceIdentityProbeRequest,
    SourceIdentityProbeResponse,
    SourceIdentityProviderCapabilities,
    SourceRootCandidate,
)
from app.windows_helper_shared.identity.models import IdentityCollectionRequest, NormalizedIdentityEvidence
from app.windows_helper_shared.identity.windows import (
    DEFAULT_COMMAND_TIMEOUT_SECONDS,
    DEFAULT_OPTICAL_FINGERPRINT_TIMEOUT_SECONDS,
    PROVIDER_NAME,
    PROVIDER_VERSION,
    PathProbeStatus,
    WindowsCommandRunner,
    WindowsIdentityCollector,
    _OpticalManifestError,
    _OpticalManifestResult,
    _optical_metadata_command,
    mask_guid,
    mask_identifier,
    mask_path_usernames,
    resolve_mapped_drive_to_unc,
)


def _adapt_evidence(item: NormalizedIdentityEvidence) -> SourceIdentityEvidenceItem:
    """Map shared sanitized evidence into the established backend schema."""
    return SourceIdentityEvidenceItem(**item.model_dump())


class WindowsSourceIdentityProbeProvider:
    """Preserve the established backend provider contract around the shared collector."""

    provider_name = PROVIDER_NAME
    provider_version = PROVIDER_VERSION

    def __init__(
        self,
        *,
        command_runner=None,
        path_probe=None,
        mapped_drive_resolver=None,
        command_timeout_seconds: float = DEFAULT_COMMAND_TIMEOUT_SECONDS,
        optical_fingerprint_timeout_seconds: float = DEFAULT_OPTICAL_FINGERPRINT_TIMEOUT_SECONDS,
        optical_manifest_reader=None,
    ) -> None:
        self._collector = WindowsIdentityCollector(
            command_runner=command_runner,
            path_probe=path_probe,
            mapped_drive_resolver=mapped_drive_resolver,
            command_timeout_seconds=command_timeout_seconds,
            optical_fingerprint_timeout_seconds=optical_fingerprint_timeout_seconds,
            optical_manifest_reader=optical_manifest_reader,
        )

    def capabilities(self) -> SourceIdentityProviderCapabilities:
        """Return the unchanged backend capability schema."""
        return SourceIdentityProviderCapabilities(**self._collector.capabilities().model_dump())

    def probe(self, request: SourceIdentityProbeRequest) -> SourceIdentityProbeResponse:
        """Collect shared evidence and adapt it without changing external behavior."""
        result = self._collector.collect(
            IdentityCollectionRequest(
                source_type=request.source_type,
                observed_path=request.observed_path,
                probe_mode=request.probe_mode,
                access_node_id=request.access_node_id,
                access_node_hint=request.access_node_hint,
                comparison_requested=bool(request.expected_endpoint_evidence),
            )
        )
        evidence_items = [_adapt_evidence(item) for item in result.evidence_items]
        blockers = [_adapt_evidence(item) for item in result.blockers]
        warnings = [_adapt_evidence(item) for item in result.warnings]
        return SourceIdentityProbeResponse(
            probe_status=result.probe_status,
            source_type=result.source_type,
            os_family=result.os_family,
            provider_name=result.provider_name,
            provider_version=result.provider_version,
            access_node_summary=AccessNodeSummary(**result.access_node_summary.model_dump()),
            observed_path=result.observed_path,
            normalized_observed_path=result.normalized_observed_path,
            source_root_candidate=SourceRootCandidate(**result.source_root_candidate.model_dump()),
            evidence_summary=dict(result.evidence_summary),
            evidence_items=evidence_items,
            identity_fingerprint_candidate=IdentityFingerprintCandidate(
                **result.identity_fingerprint_candidate.model_dump()
            ),
            confidence_tier=result.confidence_tier,
            match_status=result.match_status,
            safe_to_run=result.safe_to_run,
            blockers=blockers,
            warnings=warnings,
            next_safe_actions=list(result.next_safe_actions),
            privacy_redaction_applied=result.privacy_redaction_applied,
            capabilities=SourceIdentityProviderCapabilities(**result.capabilities.model_dump()),
            raw_evidence_reference=None,
        )


__all__ = [
    "PathProbeStatus",
    "WindowsCommandRunner",
    "WindowsSourceIdentityProbeProvider",
    "_OpticalManifestError",
    "_OpticalManifestResult",
    "_optical_metadata_command",
    "mask_guid",
    "mask_identifier",
    "mask_path_usernames",
    "resolve_mapped_drive_to_unc",
]
