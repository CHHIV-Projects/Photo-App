"""Shared durable source identity summary policy."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.services.source_identity.identity_fingerprint import parse_unc_server_share
from app.services.source_identity.probe_schema import (
    SourceIdentityEvidenceItem,
    SourceIdentityProbeResponse,
)


DurableIdentityStatus = Literal["verified", "not_verified", "provider_specific", "unknown"]

_COMPLETED_STATUSES = {"completed", "completed_with_warnings"}
_NAS_SHARE_BOUNDARIES = {"nas_share_root", "nas_share_folder"}


@dataclass(frozen=True)
class DurableIdentitySummary:
    """Operator-safe durable identity status shared by readiness and enrollment."""

    status: DurableIdentityStatus
    reason: str
    identifier_type: str | None = None
    identifier: str | None = None
    evidence: list[str] = field(default_factory=list)

    def response_fields(self) -> dict[str, object]:
        return {
            "durable_identity_status": self.status,
            "durable_identity_reason": self.reason,
            "durable_identity_identifier_type": self.identifier_type,
            "durable_identity_identifier": self.identifier,
            "durable_identity_evidence": list(self.evidence),
        }


def summarize_durable_identity(
    *,
    probe: SourceIdentityProbeResponse | None,
    source_type: str | None = None,
    cloud_provider: str | None = None,
) -> DurableIdentitySummary:
    """Return the normal-UI durable identity status without using endpoint ids as proof."""
    if _is_provider_specific(source_type=source_type, cloud_provider=cloud_provider, probe=probe):
        provider_label = "iCloud" if cloud_provider == "icloud" else "provider-specific"
        return DurableIdentitySummary(
            status="provider_specific",
            reason=f"Durable identity is handled by the {provider_label} workflow.",
            identifier_type="Provider workflow",
            identifier=provider_label,
            evidence=["Provider-specific identity is not evaluated by the generic filesystem policy."],
        )

    if probe is None:
        return DurableIdentitySummary(
            status="unknown",
            reason="Durable identity has not been checked.",
        )

    if probe.source_type == "nas":
        return _summarize_nas_identity(probe)
    if probe.source_type in {"local", "external_device", "removable_media"}:
        return _summarize_volume_identity(probe)
    if probe.source_type == "cloud":
        return DurableIdentitySummary(
            status="provider_specific",
            reason="Cloud durable identity is handled by the provider-specific workflow.",
            identifier_type="Provider workflow",
            identifier="cloud",
            evidence=["Cloud profile identity is not evaluated by the generic filesystem policy."],
        )

    return DurableIdentitySummary(
        status="unknown",
        reason="This source type is not covered by durable identity verification.",
    )


def _summarize_volume_identity(probe: SourceIdentityProbeResponse) -> DurableIdentitySummary:
    if not _has_readable_source_root(probe):
        return DurableIdentitySummary(
            status="not_verified",
            reason="The source root was not confirmed readable, so durable volume identity is not verified.",
            evidence=_safe_probe_evidence(probe),
        )

    volume_guid = _first_present_volume_guid(probe.evidence_items)
    if volume_guid is not None:
        identifier = volume_guid.masked_value or volume_guid.display_value
        return DurableIdentitySummary(
            status="verified",
            reason="A readable source root and mountvol Volume GUID were confirmed.",
            identifier_type="Volume GUID",
            identifier=identifier,
            evidence=[
                "Source root path is readable.",
                "mountvol Volume GUID evidence is present and masked.",
            ],
        )

    return DurableIdentitySummary(
        status="not_verified",
        reason="The source root is readable, but no strong durable volume identifier was confirmed.",
        evidence=_safe_probe_evidence(probe),
    )


def _summarize_nas_identity(probe: SourceIdentityProbeResponse) -> DurableIdentitySummary:
    boundary = probe.source_root_candidate.filesystem_boundary_type
    server_share = parse_unc_server_share(
        probe.source_root_candidate.path or probe.normalized_observed_path or probe.observed_path
    )
    if boundary == "nas_server_only":
        return DurableIdentitySummary(
            status="not_verified",
            reason="A NAS server alone is not a verified runnable source root.",
            evidence=_safe_probe_evidence(probe),
        )
    if server_share is not None and boundary in _NAS_SHARE_BOUNDARIES and _has_readable_source_root(probe):
        server, share = server_share
        return DurableIdentitySummary(
            status="verified",
            reason="A readable NAS share/root path and UNC server/share identity were confirmed.",
            identifier_type="NAS server/share",
            identifier=f"\\\\{server.casefold()}\\{share.casefold()}",
            evidence=[
                "UNC server/share parsed from the observed path.",
                "NAS share/root path is readable.",
            ],
        )
    if server_share is None:
        reason = "The NAS path did not include a clear server/share identity."
    elif boundary not in _NAS_SHARE_BOUNDARIES:
        reason = "The NAS path is not a supported share or folder boundary."
    else:
        reason = "The NAS share/root path was not confirmed readable."
    return DurableIdentitySummary(
        status="not_verified",
        reason=reason,
        evidence=_safe_probe_evidence(probe),
    )


def _is_provider_specific(
    *,
    source_type: str | None,
    cloud_provider: str | None,
    probe: SourceIdentityProbeResponse | None,
) -> bool:
    normalized = (source_type or "").strip().lower()
    if normalized in {"cloud", "cloud_export"}:
        return True
    if cloud_provider:
        return True
    return probe is not None and probe.source_type == "cloud"


def _has_readable_source_root(probe: SourceIdentityProbeResponse) -> bool:
    return (
        probe.probe_status in _COMPLETED_STATUSES
        and probe.source_root_candidate.is_valid_source_root_candidate
        and not probe.blockers
    )


def _first_present_volume_guid(
    evidence_items: list[SourceIdentityEvidenceItem],
) -> SourceIdentityEvidenceItem | None:
    for item in evidence_items:
        if (
            item.category == "volume_evidence"
            and item.code == "volume_guid_present"
            and item.status == "present"
            and item.durability == "durable"
        ):
            return item
    return None


def _safe_probe_evidence(probe: SourceIdentityProbeResponse) -> list[str]:
    evidence: list[str] = []
    if probe.source_root_candidate.is_valid_source_root_candidate:
        evidence.append("Source root path is readable.")
    else:
        evidence.append("Source root path was not confirmed readable.")
    for item in probe.evidence_items:
        if item.status != "present":
            continue
        if item.code == "volume_guid_present" and item.durability == "durable":
            evidence.append("mountvol Volume GUID evidence is present and masked.")
        elif item.code == "volume_serial_present":
            evidence.append("Volume serial evidence is present as supporting evidence.")
        elif item.code == "pnp_evidence_present":
            evidence.append("PnP/device evidence is present as supporting evidence.")
        elif item.code == "net_use_mapping_present":
            evidence.append("Network mapping evidence is present as supporting evidence.")
    return _dedupe(evidence)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped
