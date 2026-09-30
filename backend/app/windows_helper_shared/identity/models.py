"""Pure normalized models emitted by Windows identity collectors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


SourceType = Literal["local", "external_device", "removable_media", "optical_media", "nas", "cloud"]
ProbeMode = Literal["setup_probe", "readiness_probe", "run_launch_verification", "diagnostic_probe"]
FilesystemBoundaryType = Literal[
    "local_volume_root",
    "local_folder",
    "external_volume_root",
    "external_folder",
    "removable_media_root",
    "removable_media_folder",
    "optical_media_root",
    "optical_media_folder",
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
EvidenceStatus = Literal["present", "missing", "not_applicable", "warning", "blocked", "error"]
EvidenceDurability = Literal["durable", "supporting", "volatile", "weak", "unknown"]
PrivacyLevel = Literal[
    "public_ui",
    "normal_ui",
    "advanced_only",
    "masked_only",
    "hash_before_storage",
    "never_store",
]
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


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IdentityCollectionRequest(_StrictModel):
    """Observational input for one exact Windows-native Source root."""

    source_type: SourceType
    observed_path: str | None = Field(default=None, max_length=4096)
    probe_mode: ProbeMode = "setup_probe"
    access_node_id: str | None = Field(default=None, max_length=128)
    access_node_hint: str | None = Field(default=None, max_length=256)
    comparison_requested: bool = False


class AccessNodeEvidence(_StrictModel):
    access_node_id: str | None = Field(default=None, max_length=128)
    label: str = Field(default="Current Windows PC", max_length=256)
    os_family: Literal["windows"] = "windows"
    host_fingerprint_masked: str | None = Field(default=None, max_length=256)


class ProviderNativeRootEvidence(_StrictModel):
    path: str | None = Field(default=None, max_length=4096)
    is_valid_source_root_candidate: bool = False
    filesystem_boundary_type: FilesystemBoundaryType = "unknown"
    root_reason: str = Field(default="Source root was not classified.", max_length=1024)


class NormalizedIdentityEvidence(_StrictModel):
    """One sanitized machine-decision or display evidence item."""

    category: EvidenceCategory
    code: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9_]+$")
    status: EvidenceStatus
    durability: EvidenceDurability = "unknown"
    privacy_level: PrivacyLevel = "advanced_only"
    source_types: list[SourceType] = Field(default_factory=list, max_length=6)
    display_value: str | None = Field(default=None, max_length=1024)
    masked_value: str | None = Field(default=None, max_length=1024)
    fingerprint_hash: str | None = Field(default=None, max_length=128)
    fingerprint_version: str | None = Field(default=None, max_length=64)
    message: str | None = Field(default=None, max_length=2048)
    provider_name: str | None = Field(default=None, max_length=128)


class IdentityFingerprintCandidate(_StrictModel):
    algorithm: str = Field(default="future_versioned_hash", max_length=64)
    available: bool = False
    display: str = Field(default="identity-evidence-unavailable", max_length=128)


class IdentityCollectorCapabilities(_StrictModel):
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
    limitations: list[str] = Field(default_factory=list, max_length=16)


class IdentityCollectionResult(_StrictModel):
    """Backend-neutral result from the Windows-native collector."""

    probe_status: ProbeStatus
    source_type: SourceType
    os_family: Literal["windows"] = "windows"
    provider_name: str = Field(max_length=128)
    provider_version: str = Field(max_length=64)
    access_node_summary: AccessNodeEvidence
    observed_path: str | None = Field(default=None, max_length=4096)
    normalized_observed_path: str | None = Field(default=None, max_length=4096)
    source_root_candidate: ProviderNativeRootEvidence
    evidence_summary: dict[str, str] = Field(default_factory=dict)
    evidence_items: list[NormalizedIdentityEvidence] = Field(default_factory=list, max_length=256)
    identity_fingerprint_candidate: IdentityFingerprintCandidate = Field(default_factory=IdentityFingerprintCandidate)
    confidence_tier: ConfidenceTier
    match_status: MatchStatus = "not_compared"
    safe_to_run: SafeToRun = "not_applicable"
    blockers: list[NormalizedIdentityEvidence] = Field(default_factory=list, max_length=64)
    warnings: list[NormalizedIdentityEvidence] = Field(default_factory=list, max_length=64)
    next_safe_actions: list[str] = Field(default_factory=list, max_length=32)
    privacy_redaction_applied: bool = True
    capabilities: IdentityCollectorCapabilities = Field(default_factory=IdentityCollectorCapabilities)


@dataclass(frozen=True)
class CommandResult:
    """Sanitized result of one bounded shell-free collector command."""

    args: tuple[str, ...]
    returncode: int | None
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    command_not_found: bool = False
    error: str | None = None

    @property
    def combined_output(self) -> str:
        return f"{self.stdout}\n{self.stderr}".strip()


class CommandRunner(Protocol):
    def run(self, args: list[str], *, timeout_seconds: float) -> CommandResult:
        """Run one bounded read-only command."""
