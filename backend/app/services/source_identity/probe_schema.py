"""Schemas for read-only source identity probing."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


SourceIdentitySourceType = Literal["local", "external_device", "removable_media", "nas", "cloud"]
ProbeMode = Literal["setup_probe", "readiness_probe", "run_launch_verification", "diagnostic_probe"]
OsFamily = Literal["windows", "linux", "macos", "unknown"]
ProbeStatus = Literal[
    "completed",
    "completed_with_warnings",
    "blocked",
    "unavailable",
    "unsupported_provider",
    "provider_error",
]
ConfidenceTier = Literal[
    "strong_match",
    "medium_needs_review",
    "weak_manual_confirmation_required",
    "mismatch_block",
    "unavailable_not_connected",
    "not_compared",
]
MatchStatus = Literal["not_compared", "matched", "needs_review", "mismatch", "ambiguous", "unavailable"]
SafeToRun = bool | Literal["needs_review", "not_applicable"]
FilesystemBoundaryType = Literal[
    "local_volume_root",
    "local_folder",
    "external_volume_root",
    "external_folder",
    "removable_media_root",
    "removable_media_folder",
    "nas_server_only",
    "nas_share_root",
    "nas_share_folder",
    "cloud_profile_scope",
    "cloud_staging_path",
    "unknown",
]
EvidenceCategory = Literal[
    "host_evidence",
    "volume_evidence",
    "device_evidence",
    "media_evidence",
    "network_share_evidence",
    "cloud_profile_evidence",
    "path_evidence",
    "capability_evidence",
]
EvidenceDurability = Literal["durable", "supporting", "volatile", "weak", "unknown"]
PrivacyLevel = Literal[
    "public_ui",
    "normal_ui",
    "advanced_only",
    "masked_only",
    "hash_before_storage",
    "never_store",
]


class SourceIdentityProbeRequest(BaseModel):
    """Read-only source identity probe request."""

    source_type: SourceIdentitySourceType
    observed_path: str | None = None
    probe_mode: ProbeMode = "setup_probe"
    intended_use: str | None = None
    os_family: OsFamily = "unknown"
    access_node_id: str | None = None
    access_node_hint: str | None = None
    provider_name: str | None = None
    include_raw_evidence: bool = False
    redaction_level: str = "standard"
    expected_endpoint_evidence: dict[str, Any] | None = None
    expected_source_root: str | None = None


class AccessNodeSummary(BaseModel):
    """Sanitized summary of the access node performing the probe."""

    access_node_id: str | None = None
    label: str = "Current Access Node"
    os_family: OsFamily = "unknown"
    host_fingerprint_masked: str | None = None


class SourceRootCandidate(BaseModel):
    """Classification for the requested source root candidate."""

    path: str | None = None
    is_valid_source_root_candidate: bool = False
    filesystem_boundary_type: FilesystemBoundaryType = "unknown"
    root_reason: str = "Source root was not classified."


class SourceIdentityEvidenceItem(BaseModel):
    """One sanitized evidence item collected by a probe provider."""

    category: EvidenceCategory
    code: str
    status: Literal["present", "missing", "not_applicable", "warning", "blocked", "error"]
    durability: EvidenceDurability = "unknown"
    privacy_level: PrivacyLevel = "advanced_only"
    source_types: list[SourceIdentitySourceType] = Field(default_factory=list)
    display_value: str | None = None
    masked_value: str | None = None
    message: str | None = None
    provider_name: str | None = None
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class IdentityFingerprintCandidate(BaseModel):
    """Non-persistent future identity fingerprint summary."""

    algorithm: str = "future_versioned_hash"
    available: bool = False
    display: str = "identity-evidence-unavailable"


class SourceIdentityProviderCapabilities(BaseModel):
    """Provider capability flags safe for API/UI display."""

    path_exists_check: bool = False
    path_readable_check: bool = False
    volume_identity: bool = False
    volume_guid: bool = False
    volume_serial: bool = False
    device_pnp_evidence: bool = False
    drive_to_device_join: bool = False
    network_mapping: bool = False
    network_share_check: bool = False
    cloud_profile_check: bool = False
    limitations: list[str] = Field(default_factory=list)


class SourceIdentityProbeResponse(BaseModel):
    """Safe normalized result from a read-only source identity probe."""

    probe_status: ProbeStatus
    source_type: SourceIdentitySourceType
    os_family: OsFamily
    provider_name: str
    provider_version: str
    access_node_summary: AccessNodeSummary
    observed_path: str | None = None
    normalized_observed_path: str | None = None
    source_root_candidate: SourceRootCandidate
    evidence_summary: dict[str, str] = Field(default_factory=dict)
    evidence_items: list[SourceIdentityEvidenceItem] = Field(default_factory=list)
    identity_fingerprint_candidate: IdentityFingerprintCandidate = Field(default_factory=IdentityFingerprintCandidate)
    confidence_tier: ConfidenceTier
    match_status: MatchStatus = "not_compared"
    safe_to_run: SafeToRun = "not_applicable"
    blockers: list[SourceIdentityEvidenceItem] = Field(default_factory=list)
    warnings: list[SourceIdentityEvidenceItem] = Field(default_factory=list)
    next_safe_actions: list[str] = Field(default_factory=list)
    privacy_redaction_applied: bool = True
    capabilities: SourceIdentityProviderCapabilities = Field(default_factory=SourceIdentityProviderCapabilities)
    raw_evidence_reference: str | None = None


class SourceIdentityCapabilitiesResponse(BaseModel):
    """Read-only capability summary for source identity probing."""

    os_family: OsFamily
    supported_providers: list[str]
    default_provider: str | None = None
    capabilities: dict[str, SourceIdentityProviderCapabilities]
    limitations: list[str] = Field(default_factory=list)
