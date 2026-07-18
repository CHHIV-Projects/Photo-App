"""Windows non-admin read-only source identity probe provider."""

from __future__ import annotations

import os
import platform
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.services.source_identity.probe_schema import (
    AccessNodeSummary,
    EvidenceCategory,
    FilesystemBoundaryType,
    IdentityFingerprintCandidate,
    SourceIdentityEvidenceItem,
    SourceIdentityProbeRequest,
    SourceIdentityProbeResponse,
    SourceIdentityProviderCapabilities,
    SourceIdentitySourceType,
    SourceRootCandidate,
)
from app.services.source_identity.providers.base import CommandResult, CommandRunner


PROVIDER_NAME = "windows_non_admin_probe_v1"
PROVIDER_VERSION = "1"
DEFAULT_COMMAND_TIMEOUT_SECONDS = 3.0
_DRIVE_RE = re.compile(r"^[a-zA-Z]:")
_VOLUME_SERIAL_RE = re.compile(r"volume serial number is\s+([0-9a-fA-F-]+)", re.IGNORECASE)
_VOLUME_GUID_RE = re.compile(r"Volume\{([^}]+)\}", re.IGNORECASE)


@dataclass(frozen=True)
class PathProbeStatus:
    """Read-only path existence/readability result."""

    exists: bool
    is_dir: bool
    readable: bool
    access_denied: bool = False
    error: str | None = None


class WindowsCommandRunner:
    """Bounded shell-free command runner for read-only Windows commands."""

    def run(self, args: list[str], *, timeout_seconds: float = DEFAULT_COMMAND_TIMEOUT_SECONDS) -> CommandResult:
        try:
            completed = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                shell=False,
                check=False,
            )
        except FileNotFoundError as exc:
            return CommandResult(args=tuple(args), returncode=None, command_not_found=True, error=str(exc))
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr if isinstance(exc.stderr, str) else ""
            return CommandResult(args=tuple(args), returncode=None, stdout=stdout, stderr=stderr, timed_out=True)
        except OSError as exc:
            return CommandResult(args=tuple(args), returncode=None, error=str(exc))
        return CommandResult(
            args=tuple(args),
            returncode=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
        )


def mask_identifier(value: str | None, *, keep: int = 4) -> str | None:
    """Mask an identifier while preserving a short suffix for troubleshooting."""
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned:
        return None
    if len(cleaned) <= keep:
        return "..."
    return f"...{cleaned[-keep:]}"


def mask_guid(value: str | None) -> str | None:
    """Mask a GUID-like value."""
    if value is None:
        return None
    cleaned = value.strip().strip("\\")
    match = _VOLUME_GUID_RE.search(cleaned)
    if match:
        return f"{{...{match.group(1)[-4:].lower()}}}"
    return mask_identifier(cleaned.lower())


def mask_path_usernames(path: str | None) -> str | None:
    """Mask common Windows user-name path segments."""
    if path is None:
        return None
    return re.sub(r"(?i)([a-z]:\\users\\)[^\\]+", r"\1...", path)


def _normalize_observed_path(path: str | None) -> str | None:
    cleaned = (path or "").strip()
    return cleaned.lower() if cleaned else None


def _is_unc_path(path: str) -> bool:
    return path.startswith("\\\\") and not path.startswith("\\\\?\\")


def _unc_parts(path: str) -> list[str]:
    return [part for part in path.strip().strip("\\").split("\\") if part]


def _drive_root(path: str) -> str | None:
    cleaned = path.strip().replace("/", "\\")
    if not _DRIVE_RE.match(cleaned):
        return None
    return cleaned[:2]


def _is_drive_root(path: str) -> bool:
    cleaned = path.strip().replace("/", "\\")
    if not _DRIVE_RE.match(cleaned):
        return False
    remainder = cleaned[2:]
    return remainder == "" or set(remainder) <= {"\\"}


def _classify_boundary(source_type: SourceIdentitySourceType, observed_path: str | None) -> FilesystemBoundaryType:
    path = (observed_path or "").strip().replace("/", "\\")
    if source_type == "cloud":
        return "cloud_profile_scope"
    if not path:
        return "unknown"
    if source_type == "nas":
        if _is_unc_path(path):
            parts = _unc_parts(path)
            if len(parts) == 1:
                return "nas_server_only"
            if len(parts) == 2:
                return "nas_share_root"
            if len(parts) > 2:
                return "nas_share_folder"
        return "unknown"
    if _is_unc_path(path):
        return "unknown"
    is_root = _is_drive_root(path)
    if source_type == "local":
        return "local_volume_root" if is_root else "local_folder"
    if source_type == "external_device":
        return "external_volume_root" if is_root else "external_folder"
    if source_type == "removable_media":
        return "removable_media_root" if is_root else "removable_media_folder"
    return "unknown"


def _default_path_probe(path: str | None) -> PathProbeStatus:
    if not path:
        return PathProbeStatus(exists=False, is_dir=False, readable=False)
    try:
        path_obj = Path(path)
        exists = path_obj.exists()
        is_dir = path_obj.is_dir() if exists else False
        readable = False
        if exists and is_dir:
            try:
                with os.scandir(path_obj):
                    readable = True
            except PermissionError as exc:
                return PathProbeStatus(exists=True, is_dir=True, readable=False, access_denied=True, error=str(exc))
            except OSError:
                readable = os.access(path_obj, os.R_OK)
        elif exists:
            readable = os.access(path_obj, os.R_OK)
        return PathProbeStatus(exists=exists, is_dir=is_dir, readable=readable)
    except PermissionError as exc:
        return PathProbeStatus(exists=True, is_dir=False, readable=False, access_denied=True, error=str(exc))
    except OSError as exc:
        message = str(exc)
        return PathProbeStatus(
            exists=False,
            is_dir=False,
            readable=False,
            access_denied=("access is denied" in message.lower()),
            error=message,
        )


class WindowsSourceIdentityProbeProvider:
    """Read-only Windows provider based on non-admin evidence."""

    provider_name = PROVIDER_NAME
    provider_version = PROVIDER_VERSION

    def __init__(
        self,
        *,
        command_runner: CommandRunner | None = None,
        path_probe=None,
        command_timeout_seconds: float = DEFAULT_COMMAND_TIMEOUT_SECONDS,
    ) -> None:
        self._command_runner = command_runner or WindowsCommandRunner()
        self._path_probe = path_probe or _default_path_probe
        self._command_timeout_seconds = command_timeout_seconds

    def capabilities(self) -> SourceIdentityProviderCapabilities:
        return SourceIdentityProviderCapabilities(
            path_exists_check=True,
            path_readable_check=True,
            volume_identity=True,
            volume_guid=True,
            volume_serial=True,
            device_pnp_evidence=True,
            drive_to_device_join=False,
            network_mapping=True,
            network_share_check=True,
            cloud_profile_check=False,
            limitations=[
                "Drive-letter-to-device joins are partial in the non-admin Windows provider.",
                "Cloud providers use provider-specific readiness and are not validated by this filesystem probe.",
            ],
        )

    def probe(self, request: SourceIdentityProbeRequest) -> SourceIdentityProbeResponse:
        if request.source_type == "cloud":
            return self._cloud_response(request)

        evidence: list[SourceIdentityEvidenceItem] = []
        warnings: list[SourceIdentityEvidenceItem] = []
        blockers: list[SourceIdentityEvidenceItem] = []
        observed_path = (request.observed_path or "").strip()
        normalized_path = _normalize_observed_path(observed_path)
        boundary = _classify_boundary(request.source_type, observed_path)

        host_item = self._evidence(
            "host_evidence",
            "host_evidence_present",
            "present",
            source_types=[request.source_type],
            durability="supporting",
            privacy_level="masked_only",
            masked_value=mask_identifier(platform.node() or "windows-host"),
            message="Access node host evidence is present and masked.",
        )
        evidence.append(host_item)

        path_status = self._path_probe(observed_path if observed_path else None)
        root_candidate = self._build_root_candidate(request.source_type, observed_path, boundary, path_status)
        path_items, path_warnings, path_blockers = self._path_evidence(request, boundary, path_status)
        evidence.extend(path_items)
        warnings.extend(path_warnings)
        blockers.extend(path_blockers)

        if boundary == "nas_server_only":
            blocker = self._evidence(
                "network_share_evidence",
                "nas_server_not_runnable",
                "blocked",
                source_types=[request.source_type],
                message="NAS server-only paths are endpoint seeds, not runnable source roots.",
            )
            evidence.append(blocker)
            blockers.append(blocker)

        drive = _drive_root(observed_path)
        if drive and request.source_type in {"local", "external_device", "removable_media"}:
            command_items, command_warnings = self._collect_drive_command_evidence(drive, request.source_type)
            evidence.extend(command_items)
            warnings.extend(command_warnings)

        network_items, network_warnings = self._collect_network_mapping_evidence()
        evidence.extend(network_items)
        warnings.extend(network_warnings)

        if request.source_type in {"external_device", "removable_media"}:
            pnp_items, pnp_warnings = self._collect_pnp_evidence(request.source_type)
            evidence.extend(pnp_items)
            warnings.extend(pnp_warnings)

        confidence, match_status, safe_to_run = self._classify_safety(
            request=request,
            boundary=boundary,
            path_status=path_status,
            blockers=blockers,
            warnings=warnings,
            evidence=evidence,
        )
        probe_status = self._probe_status(blockers=blockers, warnings=warnings, path_status=path_status)
        next_actions = self._next_actions(request.source_type, blockers, warnings, boundary)

        return SourceIdentityProbeResponse(
            probe_status=probe_status,
            source_type=request.source_type,
            os_family="windows",
            provider_name=self.provider_name,
            provider_version=self.provider_version,
            access_node_summary=AccessNodeSummary(
                access_node_id=request.access_node_id,
                label=request.access_node_hint or "Current Windows PC",
                os_family="windows",
                host_fingerprint_masked=mask_identifier(platform.node() or "windows-host"),
            ),
            observed_path=observed_path or None,
            normalized_observed_path=normalized_path,
            source_root_candidate=root_candidate,
            evidence_summary=self._evidence_summary(request.source_type, evidence, blockers, warnings),
            evidence_items=evidence,
            identity_fingerprint_candidate=self._identity_fingerprint_candidate(evidence, blockers),
            confidence_tier=confidence,
            match_status=match_status,
            safe_to_run=safe_to_run,
            blockers=blockers,
            warnings=warnings,
            next_safe_actions=next_actions,
            privacy_redaction_applied=True,
            capabilities=self.capabilities(),
            raw_evidence_reference=None,
        )

    def _cloud_response(self, request: SourceIdentityProbeRequest) -> SourceIdentityProbeResponse:
        warning = self._evidence(
            "cloud_profile_evidence",
            "cloud_provider_not_probeable",
            "warning",
            source_types=["cloud"],
            message="Cloud sources use provider-specific readiness and are not validated by the generic filesystem probe.",
        )
        return SourceIdentityProbeResponse(
            probe_status="completed_with_warnings",
            source_type="cloud",
            os_family="windows",
            provider_name=self.provider_name,
            provider_version=self.provider_version,
            access_node_summary=AccessNodeSummary(
                access_node_id=request.access_node_id,
                label=request.access_node_hint or "Current Windows PC",
                os_family="windows",
                host_fingerprint_masked=mask_identifier(platform.node() or "windows-host"),
            ),
            observed_path=request.observed_path,
            normalized_observed_path=_normalize_observed_path(request.observed_path),
            source_root_candidate=SourceRootCandidate(
                path=request.observed_path,
                is_valid_source_root_candidate=False,
                filesystem_boundary_type="cloud_profile_scope",
                root_reason="Cloud sources require provider-specific readiness, not generic filesystem probing.",
            ),
            evidence_summary={
                "cloud_profile_evidence": "not_applicable",
                "path_evidence": "not_applicable",
            },
            evidence_items=[warning],
            confidence_tier="not_compared",
            match_status="not_compared",
            safe_to_run="not_applicable",
            warnings=[warning],
            next_safe_actions=["Use the cloud provider-specific readiness workflow."],
            capabilities=self.capabilities(),
        )

    def _collect_drive_command_evidence(
        self,
        drive: str,
        source_type: SourceIdentitySourceType,
    ) -> tuple[list[SourceIdentityEvidenceItem], list[SourceIdentityEvidenceItem]]:
        commands = [
            ["cmd", "/c", "vol", drive],
            ["cmd", "/c", "mountvol", drive, "/L"],
            ["cmd", "/c", "fsutil", "fsinfo", "drivetype", drive],
            ["cmd", "/c", "fsutil", "fsinfo", "volumeinfo", drive],
        ]
        evidence: list[SourceIdentityEvidenceItem] = []
        warnings: list[SourceIdentityEvidenceItem] = []
        for args in commands:
            result = self._command_runner.run(args, timeout_seconds=self._command_timeout_seconds)
            result_items, result_warnings = self._command_result_to_evidence(result, source_type)
            evidence.extend(result_items)
            warnings.extend(result_warnings)
            if result.returncode == 0:
                evidence.extend(self._parse_drive_command_output(result, source_type))
        return evidence, warnings

    def _collect_pnp_evidence(
        self,
        source_type: SourceIdentitySourceType,
    ) -> tuple[list[SourceIdentityEvidenceItem], list[SourceIdentityEvidenceItem]]:
        commands = [
            ["pnputil", "/enum-devices", "/connected", "/class", "DiskDrive"],
            ["pnputil", "/enum-devices", "/connected", "/class", "Volume"],
            ["pnputil", "/enum-devices", "/connected", "/class", "WPD"],
            ["pnputil", "/enum-devices", "/connected", "/class", "USB"],
        ]
        evidence: list[SourceIdentityEvidenceItem] = []
        warnings: list[SourceIdentityEvidenceItem] = []
        for args in commands:
            result = self._command_runner.run(args, timeout_seconds=self._command_timeout_seconds)
            result_items, result_warnings = self._command_result_to_evidence(result, source_type)
            evidence.extend(result_items)
            warnings.extend(result_warnings)
            if result.returncode == 0 and result.combined_output:
                evidence.append(
                    self._evidence(
                        "device_evidence",
                        "pnp_evidence_present",
                        "present",
                        source_types=[source_type],
                        durability="supporting",
                        privacy_level="masked_only",
                        message=f"{args[-1]} PnP evidence is present; raw output suppressed.",
                    )
                )
        return evidence, warnings

    def _collect_network_mapping_evidence(self) -> tuple[list[SourceIdentityEvidenceItem], list[SourceIdentityEvidenceItem]]:
        result = self._command_runner.run(["net", "use"], timeout_seconds=self._command_timeout_seconds)
        evidence, warnings = self._command_result_to_evidence(result, "nas")
        if result.returncode == 0:
            output = result.combined_output.lower()
            mapping_present = "\\\\" in result.combined_output and "no entries" not in output
            evidence.append(
                self._evidence(
                    "network_share_evidence",
                    "net_use_mapping_present" if mapping_present else "net_use_mapping_absent",
                    "present" if mapping_present else "missing",
                    source_types=["nas"],
                    durability="supporting",
                    privacy_level="advanced_only",
                    display_value="mapping_present" if mapping_present else "none",
                    message="Mapped network drive evidence summarized; raw output suppressed.",
                )
            )
        return evidence, warnings

    def _command_result_to_evidence(
        self,
        result: CommandResult,
        source_type: SourceIdentitySourceType,
    ) -> tuple[list[SourceIdentityEvidenceItem], list[SourceIdentityEvidenceItem]]:
        evidence: list[SourceIdentityEvidenceItem] = []
        warnings: list[SourceIdentityEvidenceItem] = []
        command_name = " ".join(result.args)
        if result.timed_out:
            item = self._evidence(
                "capability_evidence",
                "command_timeout",
                "warning",
                source_types=[source_type],
                message=f"Read-only command timed out: {command_name}",
            )
            evidence.append(item)
            warnings.append(item)
            return evidence, warnings
        if result.command_not_found:
            item = self._evidence(
                "capability_evidence",
                "command_unavailable",
                "warning",
                source_types=[source_type],
                message=f"Read-only command is unavailable: {command_name}",
            )
            evidence.append(item)
            warnings.append(item)
            return evidence, warnings
        if result.error:
            item = self._evidence(
                "capability_evidence",
                "provider_error",
                "warning",
                source_types=[source_type],
                message=f"Read-only command could not run: {command_name}",
            )
            evidence.append(item)
            warnings.append(item)
            return evidence, warnings
        if result.returncode not in (0, None):
            combined = result.combined_output.lower()
            code = "command_access_denied" if "access is denied" in combined or "error 5" in combined else "command_nonzero_exit"
            item = self._evidence(
                "capability_evidence",
                code,
                "warning",
                source_types=[source_type],
                message=f"Read-only command returned non-zero status: {command_name}",
            )
            evidence.append(item)
            warnings.append(item)
        return evidence, warnings

    def _parse_drive_command_output(
        self,
        result: CommandResult,
        source_type: SourceIdentitySourceType,
    ) -> list[SourceIdentityEvidenceItem]:
        output = result.combined_output
        evidence: list[SourceIdentityEvidenceItem] = []
        serial_match = _VOLUME_SERIAL_RE.search(output)
        if serial_match:
            evidence.append(
                self._evidence(
                    "volume_evidence",
                    "volume_serial_present",
                    "present",
                    source_types=[source_type],
                    durability="supporting",
                    privacy_level="masked_only",
                    masked_value=mask_identifier(serial_match.group(1)),
                    message="Volume serial evidence is present and masked.",
                )
            )
        guid_match = _VOLUME_GUID_RE.search(output)
        if guid_match:
            evidence.append(
                self._evidence(
                    "volume_evidence",
                    "volume_guid_present",
                    "present",
                    source_types=[source_type],
                    durability="durable",
                    privacy_level="masked_only",
                    masked_value=mask_guid(f"Volume{{{guid_match.group(1)}}}"),
                    message="mountvol Volume GUID evidence is present and masked.",
                )
            )
        lowered = output.lower()
        if "removable" in lowered or "fixed" in lowered or "network" in lowered:
            drive_type = "removable" if "removable" in lowered else "network" if "network" in lowered else "fixed"
            evidence.append(
                self._evidence(
                    "volume_evidence",
                    "drive_type_present",
                    "present",
                    source_types=[source_type],
                    durability="supporting",
                    privacy_level="advanced_only",
                    display_value=drive_type,
                    message="Drive type evidence is present.",
                )
            )
        return evidence

    def _build_root_candidate(
        self,
        source_type: SourceIdentitySourceType,
        observed_path: str,
        boundary: FilesystemBoundaryType,
        path_status: PathProbeStatus,
    ) -> SourceRootCandidate:
        if source_type == "cloud":
            return SourceRootCandidate(
                path=observed_path or None,
                is_valid_source_root_candidate=False,
                filesystem_boundary_type="cloud_profile_scope",
                root_reason="Cloud sources use provider-specific readiness.",
            )
        if boundary == "nas_server_only":
            return SourceRootCandidate(
                path=observed_path or None,
                is_valid_source_root_candidate=False,
                filesystem_boundary_type=boundary,
                root_reason="NAS server-only paths are not runnable source roots.",
            )
        if boundary == "unknown":
            return SourceRootCandidate(
                path=observed_path or None,
                is_valid_source_root_candidate=False,
                filesystem_boundary_type="unknown",
                root_reason="Observed path shape is not valid for this source type.",
            )
        if path_status.exists and path_status.is_dir and path_status.readable:
            return SourceRootCandidate(
                path=observed_path or None,
                is_valid_source_root_candidate=True,
                filesystem_boundary_type=boundary,
                root_reason="Path exists, is a directory, and appears readable.",
            )
        return SourceRootCandidate(
            path=observed_path or None,
            is_valid_source_root_candidate=False,
            filesystem_boundary_type=boundary,
            root_reason="Path is missing, not a directory, or not readable.",
        )

    def _path_evidence(
        self,
        request: SourceIdentityProbeRequest,
        boundary: FilesystemBoundaryType,
        path_status: PathProbeStatus,
    ) -> tuple[list[SourceIdentityEvidenceItem], list[SourceIdentityEvidenceItem], list[SourceIdentityEvidenceItem]]:
        evidence: list[SourceIdentityEvidenceItem] = []
        warnings: list[SourceIdentityEvidenceItem] = []
        blockers: list[SourceIdentityEvidenceItem] = []
        evidence.append(
            self._evidence(
                "path_evidence",
                "source_root_classified",
                "present" if boundary != "unknown" else "warning",
                source_types=[request.source_type],
                durability="supporting",
                privacy_level="normal_ui",
                display_value=boundary,
                message="Observed path was classified without returning raw command output.",
            )
        )
        if path_status.access_denied:
            item = self._evidence(
                "path_evidence",
                "access_denied",
                "blocked",
                source_types=[request.source_type],
                message="Observed path exists but access was denied.",
            )
            evidence.append(item)
            blockers.append(item)
            return evidence, warnings, blockers
        if not path_status.exists and boundary != "nas_server_only":
            item = self._evidence(
                "path_evidence",
                "path_not_found",
                "blocked",
                source_types=[request.source_type],
                message="Observed path was not found.",
            )
            evidence.append(item)
            blockers.append(item)
        elif path_status.exists and (not path_status.is_dir or not path_status.readable):
            code = "path_not_readable" if path_status.is_dir else "source_root_invalid"
            item = self._evidence(
                "path_evidence",
                code,
                "blocked",
                source_types=[request.source_type],
                message="Observed path is not a readable directory.",
            )
            evidence.append(item)
            blockers.append(item)
        elif path_status.exists:
            evidence.append(
                self._evidence(
                    "path_evidence",
                    "path_readable",
                    "present",
                    source_types=[request.source_type],
                    durability="supporting",
                    privacy_level="normal_ui",
                    masked_value=mask_path_usernames(request.observed_path),
                    message="Observed path exists and appears readable.",
                )
            )
        return evidence, warnings, blockers

    def _classify_safety(
        self,
        *,
        request: SourceIdentityProbeRequest,
        boundary: FilesystemBoundaryType,
        path_status: PathProbeStatus,
        blockers: list[SourceIdentityEvidenceItem],
        warnings: list[SourceIdentityEvidenceItem],
        evidence: list[SourceIdentityEvidenceItem],
    ):
        if blockers:
            return "unavailable_not_connected", "unavailable", False
        if boundary == "unknown":
            return "weak_manual_confirmation_required", "needs_review", "needs_review"
        if request.expected_endpoint_evidence:
            return "medium_needs_review", "needs_review", "needs_review"
        if request.source_type == "local" and path_status.exists and path_status.readable:
            if boundary == "local_volume_root":
                warnings.append(
                    self._evidence(
                        "path_evidence",
                        "broad_system_drive_scan_warning",
                        "warning",
                        source_types=["local"],
                        message="A volume root may be a broad source root; review before large intake.",
                    )
                )
            return "not_compared", "not_compared", "not_applicable"
        if request.source_type in {"external_device", "removable_media"} and path_status.exists and path_status.readable:
            has_volume = any(item.category == "volume_evidence" and item.status == "present" for item in evidence)
            has_device = any(item.category == "device_evidence" and item.status == "present" for item in evidence)
            if has_volume and has_device:
                return "medium_needs_review", "needs_review", "needs_review"
            if has_volume:
                return "medium_needs_review", "needs_review", "needs_review"
            return "weak_manual_confirmation_required", "needs_review", "needs_review"
        if request.source_type == "nas" and path_status.exists and path_status.readable:
            return "medium_needs_review", "needs_review", "needs_review"
        return "not_compared", "not_compared", "not_applicable"

    def _probe_status(
        self,
        *,
        blockers: list[SourceIdentityEvidenceItem],
        warnings: list[SourceIdentityEvidenceItem],
        path_status: PathProbeStatus,
    ) -> str:
        if blockers:
            if any(item.code in {"path_not_found", "path_not_readable", "access_denied"} for item in blockers):
                return "unavailable"
            return "blocked"
        if path_status.error and path_status.access_denied:
            return "unavailable"
        if warnings:
            return "completed_with_warnings"
        return "completed"

    def _identity_fingerprint_candidate(
        self,
        evidence: list[SourceIdentityEvidenceItem],
        blockers: list[SourceIdentityEvidenceItem],
    ) -> IdentityFingerprintCandidate:
        if blockers:
            return IdentityFingerprintCandidate(available=False, display="identity-evidence-blocked")
        has_identity = any(
            item.category in {"volume_evidence", "device_evidence", "network_share_evidence"}
            and item.status in {"present", "missing"}
            for item in evidence
        )
        return IdentityFingerprintCandidate(
            available=has_identity,
            display="source-identity-evidence-present" if has_identity else "identity-evidence-unavailable",
        )

    def _evidence_summary(
        self,
        source_type: SourceIdentitySourceType,
        evidence: list[SourceIdentityEvidenceItem],
        blockers: list[SourceIdentityEvidenceItem],
        warnings: list[SourceIdentityEvidenceItem],
    ) -> dict[str, str]:
        summary = {
            "host_evidence": "not_applicable",
            "volume_evidence": "not_applicable",
            "device_evidence": "not_applicable",
            "media_evidence": "not_applicable",
            "network_share_evidence": "not_applicable",
            "cloud_profile_evidence": "not_applicable",
            "path_evidence": "not_applicable",
            "capability_evidence": "not_applicable",
        }
        for item in evidence:
            if item.status == "present":
                summary[item.category] = "present"
            elif item.status == "blocked":
                summary[item.category] = "blocked"
            elif item.status == "warning" and summary[item.category] == "not_applicable":
                summary[item.category] = "warning"
            elif item.status == "missing" and summary[item.category] == "not_applicable":
                summary[item.category] = "missing"
        if source_type in {"external_device", "removable_media"} and summary["device_evidence"] == "not_applicable":
            summary["device_evidence"] = "unavailable"
        if source_type == "nas" and summary["network_share_evidence"] == "not_applicable":
            summary["network_share_evidence"] = "unavailable"
        if blockers:
            summary["path_evidence"] = "blocked"
        if warnings and summary["capability_evidence"] == "not_applicable":
            summary["capability_evidence"] = "warning"
        return summary

    def _next_actions(
        self,
        source_type: SourceIdentitySourceType,
        blockers: list[SourceIdentityEvidenceItem],
        warnings: list[SourceIdentityEvidenceItem],
        boundary: FilesystemBoundaryType,
    ) -> list[str]:
        if any(item.code == "nas_server_not_runnable" for item in blockers):
            return ["Choose a NAS share or folder inside a share, such as \\\\HENDERSON-NAS\\Photos."]
        if any(item.code in {"path_not_found", "path_not_readable", "access_denied"} for item in blockers):
            return ["Confirm the source is connected and the selected path is readable, then probe again."]
        if source_type in {"external_device", "removable_media", "nas"} and not blockers:
            return ["Review the evidence before using this path for endpoint enrollment or future intake."]
        if warnings:
            return ["Review probe warnings before proceeding."]
        if boundary == "unknown":
            return ["Select a valid source root for the chosen source type."]
        return []

    def _evidence(
        self,
        category: EvidenceCategory,
        code: str,
        status: str,
        *,
        source_types: list[SourceIdentitySourceType],
        durability: str = "unknown",
        privacy_level: str = "advanced_only",
        display_value: str | None = None,
        masked_value: str | None = None,
        message: str | None = None,
    ) -> SourceIdentityEvidenceItem:
        return SourceIdentityEvidenceItem(
            category=category,
            code=code,
            status=status,  # type: ignore[arg-type]
            durability=durability,  # type: ignore[arg-type]
            privacy_level=privacy_level,  # type: ignore[arg-type]
            source_types=source_types,
            display_value=display_value,
            masked_value=masked_value,
            message=message,
            provider_name=self.provider_name,
        )


__all__ = [
    "PathProbeStatus",
    "WindowsCommandRunner",
    "WindowsSourceIdentityProbeProvider",
    "mask_guid",
    "mask_identifier",
    "mask_path_usernames",
]
