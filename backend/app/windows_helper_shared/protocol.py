"""Transport-neutral Windows Helper protocol v1 foundation."""

from __future__ import annotations

import hashlib
import json
import ntpath
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .identity.models import (
    IdentityCollectionResult,
    IdentityFingerprintCandidate,
    NormalizedIdentityEvidence,
    ProviderNativeRootEvidence,
)
from .paths import validate_provider_native_path


PROTOCOL_VERSION = 1
CANONICAL_DIGEST_DOMAIN = "photo-organizer-windows-helper-protocol-v1"
MAX_PATH_LENGTH = 4096
MAX_EVIDENCE_ITEMS = 256


class ProtocolCompatibilityError(ValueError):
    """The peer requested an unsupported protocol/capability version."""


class SourceType(StrEnum):
    LOCAL = "local"
    EXTERNAL = "external_device"
    REMOVABLE = "removable_media"
    NAS = "nas"
    OPTICAL = "optical_media"


class ProbeMode(StrEnum):
    SETUP = "setup_probe"
    READINESS = "readiness_probe"
    RUN_LAUNCH = "run_launch_verification"
    DIAGNOSTIC = "diagnostic_probe"


class ProbeResultStatus(StrEnum):
    SUCCESS = "success"
    UNAVAILABLE = "unavailable"
    IDENTITY_AMBIGUOUS = "identity_ambiguous"
    IDENTITY_MISMATCH = "identity_mismatch"
    INVALID_ROOT = "invalid_root"
    UNSUPPORTED = "unsupported"
    PROBE_FAILED = "probe_failed"


class ErrorCode(StrEnum):
    UNAVAILABLE = "unavailable"
    IDENTITY_AMBIGUOUS = "identity_ambiguous"
    IDENTITY_MISMATCH = "identity_mismatch"
    INVALID_ROOT = "invalid_root"
    UNSUPPORTED = "unsupported"
    PROBE_FAILED = "probe_failed"
    PROTOCOL_UNSUPPORTED = "protocol_unsupported"
    CAPABILITY_UNSUPPORTED = "capability_unsupported"


class _StrictProtocolModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CapabilityVersion(_StrictProtocolModel):
    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    version: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class CollectorCapability(CapabilityVersion):
    supported_source_types: list[SourceType] = Field(min_length=1, max_length=5)

    @field_validator("supported_source_types")
    @classmethod
    def _unique_source_types(cls, value: list[SourceType]) -> list[SourceType]:
        if len(value) != len(set(value)):
            raise ValueError("supported_source_types must be unique")
        return value


class HelperCapabilityIdentity(_StrictProtocolModel):
    """Unauthenticated capability identity; authentication begins in 12.66.2."""

    protocol_version: int = PROTOCOL_VERSION
    helper_version: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    intended_access_node_id: UUID | None = None
    os_platform: Literal["windows"] = "windows"
    os_version: str | None = Field(default=None, max_length=128)
    supported_source_types: list[SourceType] = Field(min_length=1, max_length=5)
    collectors: list[CollectorCapability] = Field(min_length=1, max_length=16)
    capabilities: list[CapabilityVersion] = Field(default_factory=list, max_length=32)

    @model_validator(mode="after")
    def _validate_identity(self) -> "HelperCapabilityIdentity":
        require_protocol_version(self.protocol_version)
        _require_unique(self.supported_source_types, "supported_source_types")
        _require_unique([item.name for item in self.collectors], "collector names")
        _require_unique([item.name for item in self.capabilities], "capability names")
        advertised = set(self.supported_source_types)
        collected = {source_type for collector in self.collectors for source_type in collector.supported_source_types}
        if not advertised.issubset(collected):
            raise ValueError("every supported Source type requires a collector capability")
        return self


class ProviderNativePath(_StrictProtocolModel):
    """Exact Windows-native root/relative/full path triple."""

    provider_native_root: str = Field(min_length=3, max_length=MAX_PATH_LENGTH)
    provider_native_relative_path: str = Field(default="", max_length=MAX_PATH_LENGTH)
    provider_native_full_path: str = Field(min_length=3, max_length=MAX_PATH_LENGTH)

    @model_validator(mode="after")
    def _validate_windows_path(self) -> "ProviderNativePath":
        root, relative_path, full_path = validate_provider_native_path(
            self.provider_native_root,
            self.provider_native_relative_path,
            self.provider_native_full_path,
        )
        object.__setattr__(self, "provider_native_root", root)
        object.__setattr__(self, "provider_native_relative_path", relative_path)
        object.__setattr__(self, "provider_native_full_path", full_path)
        return self


class HelperProbeRequest(_StrictProtocolModel):
    protocol_version: int = PROTOCOL_VERSION
    request_id: UUID
    intended_access_node_id: UUID | None = None
    source_type: SourceType
    probe_mode: ProbeMode = ProbeMode.SETUP
    provider_native_path: ProviderNativePath
    expected_collector_name: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    expected_collector_version: str = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def _validate_version(self) -> "HelperProbeRequest":
        require_protocol_version(self.protocol_version)
        return self


class MachineIssue(_StrictProtocolModel):
    code: ErrorCode
    evidence_code: str | None = Field(default=None, max_length=128, pattern=r"^[a-z0-9_]+$")
    redacted_detail: str | None = Field(default=None, max_length=512)
    next_action: str | None = Field(default=None, max_length=512)


class HelperProbeResponse(_StrictProtocolModel):
    protocol_version: int = PROTOCOL_VERSION
    request_id: UUID
    result_status: ProbeResultStatus
    source_type: SourceType
    provider_native_path: ProviderNativePath
    collector_name: str = Field(min_length=1, max_length=64)
    collector_version: str = Field(min_length=1, max_length=32)
    source_root_evidence: ProviderNativeRootEvidence
    evidence_items: list[NormalizedIdentityEvidence] = Field(default_factory=list, max_length=MAX_EVIDENCE_ITEMS)
    identity_fingerprint: IdentityFingerprintCandidate = Field(default_factory=IdentityFingerprintCandidate)
    blockers: list[MachineIssue] = Field(default_factory=list, max_length=64)
    warnings: list[MachineIssue] = Field(default_factory=list, max_length=64)

    @model_validator(mode="after")
    def _validate_response(self) -> "HelperProbeResponse":
        require_protocol_version(self.protocol_version)
        if self.result_status == ProbeResultStatus.SUCCESS and self.blockers:
            raise ValueError("successful probe response must not contain blockers")
        if self.result_status != ProbeResultStatus.SUCCESS and not self.blockers:
            raise ValueError("non-success probe response requires a machine-readable blocker")
        return self


def require_protocol_version(version: int) -> None:
    if version != PROTOCOL_VERSION:
        raise ProtocolCompatibilityError(
            f"Unsupported Windows Helper protocol version {version}; required version is {PROTOCOL_VERSION}."
        )


def require_capability(capabilities: list[CapabilityVersion], name: str, version: str) -> None:
    matches = [item for item in capabilities if item.name == name]
    if len(matches) != 1 or matches[0].version != version:
        raise ProtocolCompatibilityError(f"Required capability is unavailable: {name} version {version}.")


def canonical_protocol_json(message: _StrictProtocolModel) -> str:
    """Serialize machine-authority fields deterministically with a versioned domain."""
    payload = {
        "domain": CANONICAL_DIGEST_DOMAIN,
        "message_type": type(message).__name__,
        "payload": _canonical_message_payload(message),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def canonical_protocol_digest(message: _StrictProtocolModel) -> str:
    return "sha256:" + hashlib.sha256(canonical_protocol_json(message).encode("utf-8")).hexdigest()


def probe_response_from_collection(
    *,
    request: HelperProbeRequest,
    result: IdentityCollectionResult,
) -> HelperProbeResponse:
    """Create the safe wire view of a normalized observational collector result."""
    blockers = [_issue_from_evidence(item) for item in result.blockers]
    warnings = [_issue_from_evidence(item) for item in result.warnings]
    status = _wire_status(result)
    if status != ProbeResultStatus.SUCCESS and not blockers:
        blockers = [MachineIssue(code=ErrorCode.PROBE_FAILED)]
    return HelperProbeResponse(
        request_id=request.request_id,
        result_status=status,
        source_type=request.source_type,
        provider_native_path=request.provider_native_path,
        collector_name=result.provider_name,
        collector_version=result.provider_version,
        source_root_evidence=result.source_root_candidate,
        evidence_items=result.evidence_items,
        identity_fingerprint=result.identity_fingerprint_candidate,
        blockers=blockers,
        warnings=warnings,
    )


def _wire_status(result: IdentityCollectionResult) -> ProbeResultStatus:
    if result.probe_status in {"completed", "completed_with_warnings"}:
        return ProbeResultStatus.SUCCESS
    blocker_codes = {item.code for item in result.blockers}
    if blocker_codes & {"path_not_found", "path_not_readable", "access_denied", "source_root_invalid"}:
        return ProbeResultStatus.INVALID_ROOT
    if result.match_status == "mismatch":
        return ProbeResultStatus.IDENTITY_MISMATCH
    if result.match_status == "ambiguous":
        return ProbeResultStatus.IDENTITY_AMBIGUOUS
    if result.probe_status == "unavailable":
        return ProbeResultStatus.UNAVAILABLE
    if result.probe_status == "unsupported_provider":
        return ProbeResultStatus.UNSUPPORTED
    return ProbeResultStatus.PROBE_FAILED


def _issue_from_evidence(item: NormalizedIdentityEvidence) -> MachineIssue:
    code = {
        "path_not_found": ErrorCode.INVALID_ROOT,
        "path_not_readable": ErrorCode.INVALID_ROOT,
        "access_denied": ErrorCode.UNAVAILABLE,
        "source_root_invalid": ErrorCode.INVALID_ROOT,
        "unsupported_source_type": ErrorCode.UNSUPPORTED,
    }.get(item.code, ErrorCode.PROBE_FAILED)
    return MachineIssue(code=code, evidence_code=item.code, redacted_detail=item.message)


def _canonical_message_payload(message: _StrictProtocolModel) -> Any:
    if isinstance(message, HelperCapabilityIdentity):
        return {
            "protocol_version": message.protocol_version,
            "helper_version": message.helper_version,
            "intended_access_node_id": (
                str(message.intended_access_node_id) if message.intended_access_node_id else None
            ),
            "os_platform": message.os_platform,
            "os_version": message.os_version,
            "supported_source_types": sorted(item.value for item in message.supported_source_types),
            "collectors": sorted(
                (
                    {
                        "name": item.name,
                        "version": item.version,
                        "supported_source_types": sorted(
                            source_type.value for source_type in item.supported_source_types
                        ),
                    }
                    for item in message.collectors
                ),
                key=lambda item: (item["name"], item["version"]),
            ),
            "capabilities": sorted(
                ((item.name, item.version) for item in message.capabilities),
                key=lambda item: (item[0], item[1]),
            ),
        }
    if isinstance(message, HelperProbeRequest):
        return {
            "protocol_version": message.protocol_version,
            "request_id": str(message.request_id),
            "intended_access_node_id": (
                str(message.intended_access_node_id) if message.intended_access_node_id else None
            ),
            "source_type": message.source_type.value,
            "probe_mode": message.probe_mode.value,
            "provider_native_path": _canonical_path_payload(message.provider_native_path),
            "expected_collector_name": message.expected_collector_name,
            "expected_collector_version": message.expected_collector_version,
        }
    if isinstance(message, HelperProbeResponse):
        return {
            "protocol_version": message.protocol_version,
            "request_id": str(message.request_id),
            "result_status": message.result_status.value,
            "source_type": message.source_type.value,
            "provider_native_path": _canonical_path_payload(message.provider_native_path),
            "collector_name": message.collector_name,
            "collector_version": message.collector_version,
            "source_root_evidence": {
                "path": (
                    ntpath.normcase(message.source_root_evidence.path)
                    if message.source_root_evidence.path
                    else None
                ),
                "is_valid_source_root_candidate": message.source_root_evidence.is_valid_source_root_candidate,
                "filesystem_boundary_type": message.source_root_evidence.filesystem_boundary_type,
            },
            "evidence_items": sorted(
                (
                    {
                        "category": item.category,
                        "code": item.code,
                        "status": item.status,
                        "durability": item.durability,
                        "source_types": sorted(item.source_types),
                        "fingerprint_hash": item.fingerprint_hash,
                        "fingerprint_version": item.fingerprint_version,
                    }
                    for item in message.evidence_items
                ),
                key=lambda item: (item["category"], item["code"], item["status"]),
            ),
            "identity_fingerprint": message.identity_fingerprint.model_dump(mode="json"),
            "blockers": sorted((item.code.value, item.evidence_code) for item in message.blockers),
            "warnings": sorted((item.code.value, item.evidence_code) for item in message.warnings),
        }
    return message.model_dump(mode="json")


def _canonical_path_payload(path: ProviderNativePath) -> dict[str, str]:
    return {
        "provider_native_root": ntpath.normcase(path.provider_native_root),
        "provider_native_relative_path": ntpath.normcase(path.provider_native_relative_path),
        "provider_native_full_path": ntpath.normcase(path.provider_native_full_path),
    }


def _require_unique(values: list[Any], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must be unique")


__all__ = [
    "CANONICAL_DIGEST_DOMAIN",
    "PROTOCOL_VERSION",
    "CapabilityVersion",
    "CollectorCapability",
    "ErrorCode",
    "HelperCapabilityIdentity",
    "HelperProbeRequest",
    "HelperProbeResponse",
    "MachineIssue",
    "ProbeMode",
    "ProbeResultStatus",
    "ProtocolCompatibilityError",
    "ProviderNativePath",
    "SourceType",
    "canonical_protocol_digest",
    "canonical_protocol_json",
    "probe_response_from_collection",
    "require_capability",
    "require_protocol_version",
]
