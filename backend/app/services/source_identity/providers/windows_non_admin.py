"""Windows non-admin read-only source identity probe provider."""

from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
from app.services.source_identity.identity_fingerprint import optical_media_fingerprint, volume_guid_fingerprint
from app.services.source_identity.providers.base import CommandResult, CommandRunner


PROVIDER_NAME = "windows_non_admin_probe_v1"
PROVIDER_VERSION = "1"
DEFAULT_COMMAND_TIMEOUT_SECONDS = 10.0
DEFAULT_OPTICAL_FINGERPRINT_TIMEOUT_SECONDS = 300.0
_DRIVE_RE = re.compile(r"^[a-zA-Z]:")
_VOLUME_SERIAL_RE = re.compile(r"volume serial number is\s+([0-9a-fA-F-]+)", re.IGNORECASE)
_VOLUME_GUID_RE = re.compile(r"Volume\{([^}]+)\}", re.IGNORECASE)
_ERROR_MORE_DATA = 234
_UNIVERSAL_NAME_INFO_LEVEL = 1
_CARD_READER_HINT_RE = re.compile(r"\b(sd|mmc|micro\s*sd|card\s*reader|memory\s*card)\b", re.IGNORECASE)
_VIRTUAL_OPTICAL_HINT_RE = re.compile(
    r"\b(virtual|vbox|vmware|hyper-v|msft\s+virtual|daemon|dvdfab|elby|imdisk|iso|image)\b",
    re.IGNORECASE,
)
_MOVIE_ROOT_NAMES = {"VIDEO_TS", "BDMV", "AACS"}


@dataclass(frozen=True)
class PathProbeStatus:
    """Read-only path existence/readability result."""

    exists: bool
    is_dir: bool
    readable: bool
    access_denied: bool = False
    error: str | None = None


@dataclass(frozen=True)
class _OpticalMediaMetadata:
    drive_type: str | None = None
    filesystem_type: str | None = None
    volume_label: str | None = None
    volume_serial: str | None = None
    total_size: int | None = None
    free_space: int | None = None
    media_loaded: bool | None = None
    media_type: str | None = None
    drive_name: str | None = None
    pnp_device_id: str | None = None


@dataclass(frozen=True)
class _OpticalManifestResult:
    entries: tuple[dict[str, Any], ...]
    root_names: tuple[str, ...]
    file_count: int
    directory_count: int
    timestamps_included: bool
    elapsed_seconds: float


class _OpticalManifestError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        elapsed_seconds: float = 0.0,
        file_count: int = 0,
        directory_count: int = 0,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.elapsed_seconds = elapsed_seconds
        self.file_count = file_count
        self.directory_count = directory_count


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


def _drive_root_path(drive: str) -> str:
    return drive.rstrip(":\\/").upper() + ":\\"


def _optical_metadata_command(drive_letter: str) -> str:
    drive = drive_letter.rstrip(":\\/").upper()
    return (
        "$drive='" + drive + "';"
        "$logical=Get-CimInstance Win32_LogicalDisk -Filter \"DeviceID='" + drive + ":'\" -ErrorAction SilentlyContinue | "
        "Select-Object -First 1 DeviceID,DriveType,FileSystem,VolumeName,VolumeSerialNumber,Size,FreeSpace,MediaType;"
        "$cdrom=Get-CimInstance Win32_CDROMDrive -ErrorAction SilentlyContinue | Where-Object Drive -eq '" + drive + ":' | "
        "Select-Object -First 1 Drive,MediaLoaded,MediaType,Name,VolumeName,VolumeSerialNumber,Manufacturer,PNPDeviceID;"
        "[pscustomobject]@{LogicalDisk=$logical;CdRom=$cdrom} | ConvertTo-Json -Compress -Depth 4"
    )


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
    if source_type == "optical_media":
        return "optical_media_root" if is_root else "optical_media_folder"
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


def resolve_mapped_drive_to_unc(path: str | None) -> str | None:
    """Resolve a mapped Windows path through WNetGetUniversalNameW without changing mappings."""
    if os.name != "nt" or not path or _drive_root(path) is None:
        return None

    try:
        import ctypes
        from ctypes import wintypes

        class _UniversalNameInfo(ctypes.Structure):
            _fields_ = [("lpUniversalName", wintypes.LPWSTR)]

        get_universal_name = ctypes.WinDLL("mpr").WNetGetUniversalNameW
        get_universal_name.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.LPVOID,
            ctypes.POINTER(wintypes.DWORD),
        ]
        get_universal_name.restype = wintypes.DWORD

        buffer_size = wintypes.DWORD(0)
        result = get_universal_name(
            path,
            _UNIVERSAL_NAME_INFO_LEVEL,
            None,
            ctypes.byref(buffer_size),
        )
        if result != _ERROR_MORE_DATA or buffer_size.value <= 0:
            return None

        buffer = ctypes.create_string_buffer(buffer_size.value)
        result = get_universal_name(
            path,
            _UNIVERSAL_NAME_INFO_LEVEL,
            buffer,
            ctypes.byref(buffer_size),
        )
        if result != 0:
            return None

        info = ctypes.cast(buffer, ctypes.POINTER(_UniversalNameInfo)).contents
        resolved = (info.lpUniversalName or "").strip()
        return resolved if _is_unc_path(resolved) else None
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def _has_evidence_code(
    evidence: list[SourceIdentityEvidenceItem],
    *,
    category: str,
    code: str,
) -> bool:
    return any(item.category == category and item.code == code and item.status == "present" for item in evidence)


def _first_evidence_display_value(
    evidence: list[SourceIdentityEvidenceItem],
    *,
    category: str,
    code: str,
) -> str | None:
    for item in evidence:
        if item.category == category and item.code == code and item.status == "present":
            return item.display_value or item.masked_value
    return None


class WindowsSourceIdentityProbeProvider:
    """Read-only Windows provider based on non-admin evidence."""

    provider_name = PROVIDER_NAME
    provider_version = PROVIDER_VERSION

    def __init__(
        self,
        *,
        command_runner: CommandRunner | None = None,
        path_probe=None,
        mapped_drive_resolver=None,
        command_timeout_seconds: float = DEFAULT_COMMAND_TIMEOUT_SECONDS,
        optical_fingerprint_timeout_seconds: float = DEFAULT_OPTICAL_FINGERPRINT_TIMEOUT_SECONDS,
        optical_manifest_reader=None,
    ) -> None:
        self._command_runner = command_runner or WindowsCommandRunner()
        self._path_probe = path_probe or _default_path_probe
        self._mapped_drive_resolver = mapped_drive_resolver or resolve_mapped_drive_to_unc
        self._command_timeout_seconds = command_timeout_seconds
        self._optical_fingerprint_timeout_seconds = optical_fingerprint_timeout_seconds
        self._optical_manifest_reader = optical_manifest_reader or self._build_optical_manifest

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
                "Mapped NAS paths resolve only when the current Windows runtime can resolve the existing drive mapping.",
                "Cloud providers use provider-specific readiness and are not validated by this filesystem probe.",
                "Optical media identity uses a complete metadata-only logical-media fingerprint when Windows does not expose a proven inserted-disc identifier.",
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
        drive = _drive_root(observed_path)
        mapped_unc_path = self._mapped_drive_resolver(observed_path) if drive else None
        classification_path = mapped_unc_path if request.source_type == "nas" and mapped_unc_path else observed_path
        boundary = _classify_boundary(request.source_type, classification_path)

        if mapped_unc_path:
            parts = _unc_parts(mapped_unc_path)
            server_share = f"\\\\{parts[0]}\\{parts[1]}" if len(parts) >= 2 else None
            mapping_item = self._evidence(
                "network_share_evidence",
                "mapped_drive_unc_resolved",
                "present",
                source_types=[request.source_type],
                durability="supporting",
                privacy_level="normal_ui",
                display_value=server_share,
                message="The mapped drive was resolved read-only to a UNC server/share path.",
            )
            evidence.append(mapping_item)
            if request.source_type != "nas":
                boundary = "unknown"
                blocker = self._evidence(
                    "network_share_evidence",
                    "mapped_network_path_requires_nas",
                    "blocked",
                    source_types=[request.source_type],
                    message="This location is a mapped NAS path. Choose source type NAS.",
                )
                evidence.append(blocker)
                blockers.append(blocker)
        elif request.source_type == "nas" and drive:
            blocker = self._evidence(
                "network_share_evidence",
                "mapped_nas_unc_resolution_failed",
                "blocked",
                source_types=["nas"],
                message="Mapped NAS path detected, but the UNC share could not be resolved. Enter the UNC path instead.",
            )
            evidence.append(blocker)
            blockers.append(blocker)

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
        root_candidate = self._build_root_candidate(request.source_type, classification_path, boundary, path_status)
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

        if drive and not mapped_unc_path and request.source_type in {"local", "external_device", "removable_media"}:
            command_items, command_warnings = self._collect_drive_command_evidence(drive, request.source_type)
            evidence.extend(command_items)
            warnings.extend(command_warnings)
            if request.source_type != "local" or not _has_evidence_code(
                evidence,
                category="volume_evidence",
                code="volume_guid_present",
            ):
                storage_items, storage_warnings = self._collect_storage_metadata_evidence(drive, request.source_type)
                evidence.extend(storage_items)
                warnings.extend(storage_warnings)

        if drive and not mapped_unc_path and request.source_type == "optical_media":
            optical_items, optical_warnings, optical_blockers = self._collect_optical_media_evidence(
                drive=drive,
                observed_path=observed_path,
                path_status=path_status,
            )
            evidence.extend(optical_items)
            warnings.extend(optical_warnings)
            blockers.extend(optical_blockers)

        network_items, network_warnings = self._collect_network_mapping_evidence()
        evidence.extend(network_items)
        warnings.extend(network_warnings)

        if request.source_type in {"external_device", "removable_media"}:
            pnp_items, pnp_warnings = self._collect_pnp_evidence(request.source_type)
            evidence.extend(pnp_items)
            warnings.extend(pnp_warnings)

        storage_blockers = self._storage_metadata_blockers(
            request=request,
            drive=drive,
            path_status=path_status,
            evidence=evidence,
        )
        evidence.extend(storage_blockers)
        blockers.extend(storage_blockers)

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

    def _collect_storage_metadata_evidence(
        self,
        drive: str,
        source_type: SourceIdentitySourceType,
    ) -> tuple[list[SourceIdentityEvidenceItem], list[SourceIdentityEvidenceItem]]:
        drive_letter = drive.rstrip(":\\/")
        script = (
            "$drive='" + drive_letter + "';"
            "$volume=Get-Volume -DriveLetter $drive -ErrorAction SilentlyContinue | "
            "Select-Object -First 1 DriveLetter,DriveType,UniqueId,Path,FileSystemType,FileSystemLabel;"
            "$partition=Get-Partition -DriveLetter $drive -ErrorAction SilentlyContinue | "
            "Select-Object -First 1 DriveLetter,DiskNumber,PartitionNumber,Type;"
            "$disk=$null;$physical=$null;"
            "if($partition){"
            "$disk=Get-Disk -Number $partition.DiskNumber -ErrorAction SilentlyContinue | "
            "Select-Object -First 1 Number,FriendlyName,BusType,PartitionStyle,IsBoot,IsSystem,IsReadOnly,IsOffline;"
            "$physical=Get-PhysicalDisk -ErrorAction SilentlyContinue | Where-Object DeviceId -eq $partition.DiskNumber | "
            "Select-Object -First 1 DeviceId,FriendlyName,BusType,MediaType,HealthStatus;}"
            "[pscustomobject]@{Volume=$volume;Partition=$partition;Disk=$disk;PhysicalDisk=$physical} | ConvertTo-Json -Compress -Depth 4"
        )
        result = self._command_runner.run(
            ["powershell", "-NoProfile", "-Command", script],
            timeout_seconds=self._command_timeout_seconds,
        )
        evidence, warnings = self._command_result_to_evidence(result, source_type)
        if result.returncode != 0 or not result.combined_output:
            return evidence, warnings

        try:
            payload = json.loads(result.combined_output)
        except json.JSONDecodeError:
            item = self._evidence(
                "capability_evidence",
                "powershell_storage_metadata_unparsed",
                "warning",
                source_types=[source_type],
                message="Read-only Windows storage metadata could not be parsed.",
            )
            evidence.append(item)
            warnings.append(item)
            return evidence, warnings

        volume = payload.get("Volume") or {}
        disk = payload.get("Disk") or {}
        physical_disk = payload.get("PhysicalDisk") or {}
        partition = payload.get("Partition") or {}

        drive_type = str(volume.get("DriveType") or "").strip()
        if drive_type:
            evidence.append(
                self._evidence(
                    "volume_evidence",
                    "drive_type_present",
                    "present",
                    source_types=[source_type],
                    durability="supporting",
                    privacy_level="advanced_only",
                    display_value=drive_type.casefold(),
                    message="Windows volume drive type evidence is present.",
                )
            )

        unique_id = str(volume.get("UniqueId") or "").strip()
        if unique_id and not any(item.code == "volume_guid_present" for item in evidence):
            guid_match = _VOLUME_GUID_RE.search(unique_id)
            if guid_match:
                fingerprint_hash, fingerprint_version = volume_guid_fingerprint(guid_match.group(1))
                evidence.append(
                    self._evidence(
                        "volume_evidence",
                        "volume_guid_present",
                        "present",
                        source_types=[source_type],
                        durability="durable",
                        privacy_level="masked_only",
                        masked_value=mask_guid(unique_id),
                        fingerprint_hash=fingerprint_hash,
                        fingerprint_version=fingerprint_version,
                        message="Windows storage metadata confirmed the mounted volume GUID and masked it.",
                    )
                )

        bus_type = str(physical_disk.get("BusType") or disk.get("BusType") or "").strip()
        if bus_type:
            evidence.append(
                self._evidence(
                    "device_evidence",
                    "bus_type_present",
                    "present",
                    source_types=[source_type],
                    durability="supporting",
                    privacy_level="advanced_only",
                    display_value=bus_type.upper(),
                    message="Windows bus/interface evidence is present.",
                )
            )

        media_type = str(physical_disk.get("MediaType") or "").strip()
        if media_type:
            evidence.append(
                self._evidence(
                    "device_evidence",
                    "media_type_present",
                    "present",
                    source_types=[source_type],
                    durability="supporting",
                    privacy_level="advanced_only",
                    display_value=media_type.upper(),
                    message="Windows physical media-type evidence is present.",
                )
            )

        friendly_name = " ".join(
            value
            for value in [
                str(physical_disk.get("FriendlyName") or "").strip(),
                str(disk.get("FriendlyName") or "").strip(),
            ]
            if value
        )
        if friendly_name and _CARD_READER_HINT_RE.search(friendly_name):
            evidence.append(
                self._evidence(
                    "media_evidence",
                    "card_reader_media_present",
                    "present",
                    source_types=[source_type],
                    durability="supporting",
                    privacy_level="advanced_only",
                    display_value="card_reader",
                    message="Windows storage metadata indicates SD, memory-card, or card-reader media.",
                )
            )

        is_system = (
            bool(disk.get("IsSystem"))
            or bool(disk.get("IsBoot"))
            or drive_letter.casefold() == os.environ.get("SystemDrive", "C:").rstrip(":").casefold()
        )
        if is_system:
            evidence.append(
                self._evidence(
                    "device_evidence",
                    "system_volume_present",
                    "present",
                    source_types=[source_type],
                    durability="supporting",
                    privacy_level="advanced_only",
                    display_value="system",
                    message="Windows storage metadata indicates the active system volume.",
                )
            )

        if partition:
            evidence.append(
                self._evidence(
                    "device_evidence",
                    "partition_metadata_present",
                    "present",
                    source_types=[source_type],
                    durability="supporting",
                    privacy_level="advanced_only",
                    message="Windows partition metadata is present.",
                )
            )

        return evidence, warnings

    def _collect_optical_media_evidence(
        self,
        *,
        drive: str,
        observed_path: str,
        path_status: PathProbeStatus,
    ) -> tuple[list[SourceIdentityEvidenceItem], list[SourceIdentityEvidenceItem], list[SourceIdentityEvidenceItem]]:
        evidence: list[SourceIdentityEvidenceItem] = []
        warnings: list[SourceIdentityEvidenceItem] = []
        blockers: list[SourceIdentityEvidenceItem] = []
        metadata, metadata_items, metadata_warnings = self._collect_optical_metadata(drive)
        evidence.extend(metadata_items)
        warnings.extend(metadata_warnings)

        drive_type = (metadata.drive_type or "").casefold()
        if drive_type:
            evidence.append(
                self._evidence(
                    "volume_evidence",
                    "drive_type_present",
                    "present",
                    source_types=["optical_media"],
                    durability="supporting",
                    privacy_level="advanced_only",
                    display_value=drive_type,
                    message="Windows volume drive type evidence is present.",
                )
            )
        if metadata.filesystem_type:
            evidence.append(
                self._evidence(
                    "volume_evidence",
                    "filesystem_type_present",
                    "present",
                    source_types=["optical_media"],
                    durability="supporting",
                    privacy_level="advanced_only",
                    display_value=metadata.filesystem_type.casefold(),
                    message="Windows filesystem type evidence is present.",
                )
            )
        if metadata.volume_label:
            evidence.append(
                self._evidence(
                    "volume_evidence",
                    "volume_label_present",
                    "present",
                    source_types=["optical_media"],
                    durability="supporting",
                    privacy_level="normal_ui",
                    display_value=metadata.volume_label,
                    message="Optical volume label evidence is present.",
                )
            )
        if metadata.volume_serial:
            evidence.append(
                self._evidence(
                    "volume_evidence",
                    "volume_serial_present",
                    "present",
                    source_types=["optical_media"],
                    durability="supporting",
                    privacy_level="masked_only",
                    masked_value=mask_identifier(metadata.volume_serial),
                    message="Optical volume serial evidence is present and masked.",
                )
            )
        if metadata.total_size is not None:
            used_size = None
            if metadata.free_space is not None:
                used_size = max(metadata.total_size - metadata.free_space, 0)
            evidence.append(
                self._evidence(
                    "media_evidence",
                    "optical_media_capacity_present",
                    "present",
                    source_types=["optical_media"],
                    durability="supporting",
                    privacy_level="advanced_only",
                    display_value=f"total={metadata.total_size};used={used_size if used_size is not None else 'unknown'}",
                    message="Optical media capacity evidence is present.",
                )
            )
        if metadata.media_loaded is not None:
            evidence.append(
                self._evidence(
                    "media_evidence",
                    "optical_media_loaded_state_present",
                    "present",
                    source_types=["optical_media"],
                    durability="supporting",
                    privacy_level="advanced_only",
                    display_value="loaded" if metadata.media_loaded else "empty",
                    message="Windows optical drive media-loaded state is present.",
                )
            )
        if metadata.media_type:
            evidence.append(
                self._evidence(
                    "media_evidence",
                    "optical_media_type_present",
                    "present",
                    source_types=["optical_media"],
                    durability="supporting",
                    privacy_level="advanced_only",
                    display_value=metadata.media_type,
                    message="Windows optical media type evidence is present.",
                )
            )

        if drive_type and drive_type != "cd-rom":
            blocker = self._evidence(
                "volume_evidence",
                "non_optical_path_selected",
                "blocked",
                source_types=["optical_media"],
                message="The selected path is not an optical drive. Choose Optical only for readable data CDs, DVDs, or Blu-ray discs.",
            )
            evidence.append(blocker)
            blockers.append(blocker)
            return evidence, warnings, blockers
        if not drive_type:
            blocker = self._evidence(
                "volume_evidence",
                "optical_drive_unverified",
                "blocked",
                source_types=["optical_media"],
                message="Windows could not verify that the selected path is an optical drive.",
            )
            evidence.append(blocker)
            blockers.append(blocker)
            return evidence, warnings, blockers

        physical_status = _optical_physical_status(metadata)
        if physical_status == "virtual":
            blocker = self._evidence(
                "device_evidence",
                "virtual_optical_drive_not_supported",
                "blocked",
                source_types=["optical_media"],
                message="Virtual optical drives and mounted disc images are not supported in this milestone.",
            )
            evidence.append(blocker)
            blockers.append(blocker)
            return evidence, warnings, blockers
        if physical_status != "physical":
            blocker = self._evidence(
                "device_evidence",
                "optical_drive_unverified",
                "blocked",
                source_types=["optical_media"],
                message="Windows could not verify this as a supported physical optical drive.",
            )
            evidence.append(blocker)
            blockers.append(blocker)
            return evidence, warnings, blockers
        evidence.append(
            self._evidence(
                "device_evidence",
                "physical_optical_drive_verified",
                "present",
                source_types=["optical_media"],
                durability="supporting",
                privacy_level="advanced_only",
                display_value="physical",
                message="Windows optical drive evidence indicates a physical optical drive.",
            )
        )

        if metadata.media_loaded is False:
            blocker = self._evidence(
                "media_evidence",
                "no_readable_optical_media_inserted",
                "blocked",
                source_types=["optical_media"],
                message="No readable optical media is inserted.",
            )
            evidence.append(blocker)
            blockers.append(blocker)
            return evidence, warnings, blockers

        if not path_status.exists or not path_status.is_dir or not path_status.readable:
            blocker = self._optical_unreadable_blocker(metadata)
            evidence.append(blocker)
            blockers.append(blocker)
            return evidence, warnings, blockers

        try:
            manifest = self._optical_manifest_reader(
                _drive_root_path(drive),
                timeout_seconds=self._optical_fingerprint_timeout_seconds,
            )
        except _OpticalManifestError as exc:
            blocker = self._evidence(
                "media_evidence",
                exc.code,
                "blocked",
                source_types=["optical_media"],
                message=exc.message,
            )
            evidence.append(blocker)
            blockers.append(blocker)
            if exc.file_count or exc.directory_count or exc.elapsed_seconds:
                evidence.append(
                    self._evidence(
                        "media_evidence",
                        "optical_manifest_partial_summary",
                        "warning",
                        source_types=["optical_media"],
                        display_value=(
                            f"files={exc.file_count};directories={exc.directory_count};"
                            f"elapsed_seconds={exc.elapsed_seconds:.3f}"
                        ),
                        message="Partial optical manifest metadata was discarded and not fingerprinted.",
                    )
                )
            return evidence, warnings, blockers

        movie_blocker = self._movie_disc_blocker(manifest.root_names)
        if movie_blocker is not None:
            evidence.append(movie_blocker)
            blockers.append(movie_blocker)
            return evidence, warnings, blockers
        if not manifest.entries:
            blocker = self._evidence(
                "media_evidence",
                "blank_or_unreadable_optical_media",
                "blocked",
                source_types=["optical_media"],
                message="The optical disc appears blank or does not expose ordinary file entries.",
            )
            evidence.append(blocker)
            blockers.append(blocker)
            return evidence, warnings, blockers
        if not _optical_identity_evidence_is_sufficient(metadata, manifest):
            blocker = self._evidence(
                "media_evidence",
                "optical_identity_incomplete",
                "blocked",
                source_types=["optical_media"],
                message="The optical disc could not be identified from complete stable metadata.",
            )
            evidence.append(blocker)
            blockers.append(blocker)
            return evidence, warnings, blockers

        fingerprint_payload = _optical_fingerprint_payload(metadata, manifest)
        fingerprint_hash, fingerprint_version = optical_media_fingerprint(fingerprint_payload)
        evidence.append(
            self._evidence(
                "media_evidence",
                "optical_manifest_complete",
                "present",
                source_types=["optical_media"],
                durability="supporting",
                privacy_level="advanced_only",
                display_value=(
                    f"files={manifest.file_count};directories={manifest.directory_count};"
                    f"timestamps={'included' if manifest.timestamps_included else 'excluded'};"
                    f"elapsed_seconds={manifest.elapsed_seconds:.3f}"
                ),
                message="Complete metadata-only optical directory manifest was enumerated.",
            )
        )
        evidence.append(
            self._evidence(
                "media_evidence",
                "optical_media_fingerprint_present",
                "present",
                source_types=["optical_media"],
                durability="durable",
                privacy_level="masked_only",
                masked_value=_mask_hash(fingerprint_hash),
                fingerprint_hash=fingerprint_hash,
                fingerprint_version=fingerprint_version,
                message="Complete metadata-only inserted-disc fingerprint is present and masked.",
            )
        )
        return evidence, warnings, blockers

    def _collect_optical_metadata(
        self,
        drive: str,
    ) -> tuple[_OpticalMediaMetadata, list[SourceIdentityEvidenceItem], list[SourceIdentityEvidenceItem]]:
        drive_letter = drive.rstrip(":\\/")
        result = self._command_runner.run(
            ["powershell", "-NoProfile", "-Command", _optical_metadata_command(drive_letter)],
            timeout_seconds=self._command_timeout_seconds,
        )
        evidence, warnings = self._command_result_to_evidence(result, "optical_media")
        if result.returncode != 0 or not result.combined_output:
            return _OpticalMediaMetadata(), evidence, warnings
        try:
            payload = json.loads(result.combined_output)
        except json.JSONDecodeError:
            item = self._evidence(
                "capability_evidence",
                "optical_metadata_unparsed",
                "warning",
                source_types=["optical_media"],
                message="Read-only Windows optical metadata could not be parsed.",
            )
            evidence.append(item)
            warnings.append(item)
            return _OpticalMediaMetadata(), evidence, warnings
        return _optical_metadata_from_payload(payload), evidence, warnings

    def _optical_unreadable_blocker(self, metadata: _OpticalMediaMetadata) -> SourceIdentityEvidenceItem:
        if _looks_like_audio_cd(metadata):
            return self._evidence(
                "media_evidence",
                "audio_cd_not_supported",
                "blocked",
                source_types=["optical_media"],
                message="Audio CDs are not supported by Optical Source Creation.",
            )
        return self._evidence(
            "media_evidence",
            "blank_or_unreadable_optical_media",
            "blocked",
            source_types=["optical_media"],
            message="The optical disc is blank, unreadable, or does not expose a supported data filesystem.",
        )

    def _movie_disc_blocker(self, root_names: tuple[str, ...]) -> SourceIdentityEvidenceItem | None:
        normalized_names = {name.upper() for name in root_names}
        if normalized_names & _MOVIE_ROOT_NAMES:
            return self._evidence(
                "media_evidence",
                "unsupported_movie_optical_media",
                "blocked",
                source_types=["optical_media"],
                message="Movie-oriented DVD or Blu-ray media is not supported by Optical Source Creation.",
            )
        return None

    def _build_optical_manifest(self, root_path: str, *, timeout_seconds: float) -> _OpticalManifestResult:
        started_at = time.monotonic()
        deadline = started_at + timeout_seconds
        first_entries, root_names = _scan_optical_manifest_once(root_path, deadline=deadline)
        second_entries, _ = _scan_optical_manifest_once(root_path, deadline=deadline)
        elapsed = time.monotonic() - started_at
        first_without_timestamps = _strip_manifest_timestamps(first_entries)
        second_without_timestamps = _strip_manifest_timestamps(second_entries)
        if first_without_timestamps != second_without_timestamps:
            raise _OpticalManifestError(
                "optical_identity_incomplete",
                "The optical disc metadata changed while it was being identified. Try again without replacing or modifying the disc.",
                elapsed_seconds=elapsed,
                file_count=_manifest_file_count(first_without_timestamps),
                directory_count=_manifest_directory_count(first_without_timestamps),
            )
        timestamps_included = first_entries == second_entries and all(
            "last_write_time_ns" in entry for entry in first_entries
        )
        entries = tuple(first_entries if timestamps_included else first_without_timestamps)
        return _OpticalManifestResult(
            entries=entries,
            root_names=tuple(sorted(root_names)),
            file_count=_manifest_file_count(entries),
            directory_count=_manifest_directory_count(entries),
            timestamps_included=timestamps_included,
            elapsed_seconds=elapsed,
        )

    def _storage_metadata_blockers(
        self,
        *,
        request: SourceIdentityProbeRequest,
        drive: str | None,
        path_status: PathProbeStatus,
        evidence: list[SourceIdentityEvidenceItem],
    ) -> list[SourceIdentityEvidenceItem]:
        blockers: list[SourceIdentityEvidenceItem] = []
        drive_type = _first_evidence_display_value(evidence, category="volume_evidence", code="drive_type_present")
        has_volume_guid = any(item.category == "volume_evidence" and item.code == "volume_guid_present" for item in evidence)
        if request.source_type in {"local", "external_device", "removable_media"} and (drive_type or "").casefold() == "cd-rom":
            blockers.append(
                self._evidence(
                    "volume_evidence",
                    "optical_media_not_supported",
                    "blocked",
                    source_types=[request.source_type],
                    message="Optical media is not supported yet. Support for data CDs, DVDs, and Blu-ray discs will be added separately.",
                )
            )
        if request.source_type == "removable_media" and _has_evidence_code(evidence, category="device_evidence", code="system_volume_present"):
            blockers.append(
                self._evidence(
                    "device_evidence",
                    "system_volume_requires_local",
                    "blocked",
                    source_types=[request.source_type],
                    message="This location is the active Windows system volume. Use Local instead.",
                )
            )
        if (
            request.source_type == "removable_media"
            and drive is not None
            and not path_status.exists
            and not has_volume_guid
            and (drive_type or "").casefold() in {"removable", "cd-rom"}
        ):
            blockers.append(
                self._evidence(
                    "media_evidence",
                    "no_readable_media_inserted",
                    "blocked",
                    source_types=[request.source_type],
                    message="No readable media is inserted.",
                )
            )
        return blockers

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
                message="Optional read-only Windows metadata command timed out.",
            )
            evidence.append(item)
            return evidence, warnings
        if result.command_not_found:
            item = self._evidence(
                "capability_evidence",
                "command_unavailable",
                "warning",
                source_types=[source_type],
                message="Optional read-only Windows metadata command is unavailable.",
            )
            evidence.append(item)
            return evidence, warnings
        if result.error:
            item = self._evidence(
                "capability_evidence",
                "provider_error",
                "warning",
                source_types=[source_type],
                message="Optional read-only Windows metadata command could not run.",
            )
            evidence.append(item)
            return evidence, warnings
        if result.returncode not in (0, None):
            combined = result.combined_output.lower()
            code = "command_access_denied" if "access is denied" in combined or "error 5" in combined else "command_nonzero_exit"
            item = self._evidence(
                "capability_evidence",
                code,
                "warning",
                source_types=[source_type],
                message="Optional read-only Windows metadata command returned a non-zero status.",
            )
            evidence.append(item)
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
            fingerprint_hash, fingerprint_version = volume_guid_fingerprint(guid_match.group(1))
            evidence.append(
                self._evidence(
                    "volume_evidence",
                    "volume_guid_present",
                    "present",
                    source_types=[source_type],
                    durability="durable",
                    privacy_level="masked_only",
                    masked_value=mask_guid(f"Volume{{{guid_match.group(1)}}}"),
                    fingerprint_hash=fingerprint_hash,
                    fingerprint_version=fingerprint_version,
                    message="mountvol Volume GUID evidence is present and masked.",
                )
            )
        lowered = output.lower()
        if "removable" in lowered or "fixed" in lowered or "network" in lowered or "cd-rom" in lowered or "cdrom" in lowered:
            drive_type = (
                "cd-rom"
                if "cd-rom" in lowered or "cdrom" in lowered
                else "removable" if "removable" in lowered else "network" if "network" in lowered else "fixed"
            )
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
        if (
            request.source_type == "optical_media"
            and boundary in {"optical_media_root", "optical_media_folder"}
            and (not path_status.exists or not path_status.is_dir or not path_status.readable)
        ):
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
        if request.source_type == "optical_media" and path_status.exists and path_status.readable:
            has_fingerprint = any(
                item.category == "media_evidence"
                and item.code == "optical_media_fingerprint_present"
                and item.status == "present"
                for item in evidence
            )
            if has_fingerprint:
                return "strong_match", "not_compared", "not_applicable"
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
            item.category in {"volume_evidence", "device_evidence", "media_evidence", "network_share_evidence"}
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
        if source_type == "optical_media" and summary["media_evidence"] == "not_applicable":
            summary["media_evidence"] = "unavailable"
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
        if any(item.code == "mapped_nas_unc_resolution_failed" for item in blockers):
            return ["Enter the NAS location as a UNC path, such as \\\\HENDERSON-NAS\\Photos."]
        if any(item.code == "mapped_network_path_requires_nas" for item in blockers):
            return ["Choose source type NAS and check the mapped path again."]
        if any(item.code == "nas_server_not_runnable" for item in blockers):
            return ["Choose a NAS share or folder inside a share, such as \\\\HENDERSON-NAS\\Photos."]
        if any(item.code in {"path_not_found", "path_not_readable", "access_denied"} for item in blockers):
            return ["Confirm the source is connected and the selected path is readable, then probe again."]
        if source_type in {"external_device", "removable_media", "optical_media", "nas"} and not blockers:
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
        fingerprint_hash: str | None = None,
        fingerprint_version: str | None = None,
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
            fingerprint_hash=fingerprint_hash,
            fingerprint_version=fingerprint_version,
            message=message,
            provider_name=self.provider_name,
        )


def _optical_metadata_from_payload(payload: Any) -> _OpticalMediaMetadata:
    payload_dict = payload if isinstance(payload, dict) else {}
    volume = _metadata_dict(payload_dict.get("Volume"))
    logical = _metadata_dict(payload_dict.get("LogicalDisk"))
    cdrom = _metadata_dict(payload_dict.get("CdRom"))
    return _OpticalMediaMetadata(
        drive_type=_normalize_drive_type(_first_text(volume.get("DriveType"), logical.get("DriveType"))),
        filesystem_type=_normalize_filesystem_type(_first_text(logical.get("FileSystem"), volume.get("FileSystemType"))),
        volume_label=_normalize_optional_text(
            _first_text(logical.get("VolumeName"), volume.get("FileSystemLabel"), cdrom.get("VolumeName"))
        ),
        volume_serial=_normalize_optional_text(
            _first_text(logical.get("VolumeSerialNumber"), cdrom.get("VolumeSerialNumber"))
        ),
        total_size=_first_int(logical.get("Size"), volume.get("Size")),
        free_space=_first_int(logical.get("FreeSpace"), volume.get("SizeRemaining")),
        media_loaded=_bool_value(cdrom.get("MediaLoaded")),
        media_type=_normalize_optional_text(_first_text(cdrom.get("MediaType"), logical.get("MediaType"))),
        drive_name=_normalize_optional_text(_first_text(cdrom.get("Name"))),
        pnp_device_id=_normalize_optional_text(_first_text(cdrom.get("PNPDeviceID"))),
    )


def _metadata_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _first_text(*values: Any) -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _first_int(*values: Any) -> int | None:
    for value in values:
        if value is None or value == "":
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _bool_value(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().casefold()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def _normalize_optional_text(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    return cleaned or None


def _normalize_filesystem_type(value: str | None) -> str | None:
    cleaned = _normalize_optional_text(value)
    if cleaned is None or cleaned.casefold() == "unknown":
        return None
    return cleaned


def _normalize_drive_type(value: str | None) -> str | None:
    cleaned = _normalize_optional_text(value)
    if cleaned is None:
        return None
    lowered = cleaned.casefold()
    if lowered in {"5", "cdrom", "cd-rom", "cd-rom drive"} or "cd-rom" in lowered or "cdrom" in lowered:
        return "cd-rom"
    if lowered in {"2", "removable"} or "removable" in lowered:
        return "removable"
    if lowered in {"3", "fixed"} or "fixed" in lowered:
        return "fixed"
    if lowered in {"4", "network"} or "network" in lowered:
        return "network"
    return lowered


def _optical_physical_status(metadata: _OpticalMediaMetadata) -> str:
    combined = " ".join(
        value
        for value in [metadata.drive_name, metadata.media_type, metadata.pnp_device_id]
        if value
    )
    if _VIRTUAL_OPTICAL_HINT_RE.search(combined):
        return "virtual"
    pnp = (metadata.pnp_device_id or "").upper()
    if any(token in pnp for token in ("USBSTOR\\CDROM", "IDE\\CDROM", "SCSI\\CDROM")):
        return "physical"
    if metadata.drive_name and any(token in metadata.drive_name.upper() for token in ("DVD", "CD-ROM", "CDROM", "BLU-RAY", "BD-ROM")):
        return "physical"
    return "unverified"


def _looks_like_audio_cd(metadata: _OpticalMediaMetadata) -> bool:
    combined = " ".join(
        value
        for value in [metadata.volume_label, metadata.media_type, metadata.filesystem_type]
        if value
    ).casefold()
    return "audio cd" in combined or "cdda" in combined


def _optical_identity_evidence_is_sufficient(
    metadata: _OpticalMediaMetadata,
    manifest: _OpticalManifestResult,
) -> bool:
    has_stable_media_metadata = any(
        [
            metadata.filesystem_type,
            metadata.volume_serial,
            metadata.volume_label,
            metadata.total_size is not None,
        ]
    )
    return bool(manifest.entries) and has_stable_media_metadata


def _optical_fingerprint_payload(
    metadata: _OpticalMediaMetadata,
    manifest: _OpticalManifestResult,
) -> dict[str, Any]:
    used_size = None
    if metadata.total_size is not None and metadata.free_space is not None:
        used_size = max(metadata.total_size - metadata.free_space, 0)
    return {
        "algorithm": "optical_media_fingerprint_v1",
        "disc_metadata": {
            "filesystem_type": _normalized_payload_text(metadata.filesystem_type),
            "volume_label": _normalized_payload_text(metadata.volume_label),
            "volume_serial": _normalized_payload_text(metadata.volume_serial),
            "total_size": metadata.total_size,
            "used_size": used_size,
        },
        "manifest": {
            "entries": list(manifest.entries),
            "file_count": manifest.file_count,
            "directory_count": manifest.directory_count,
            "timestamps_included": manifest.timestamps_included,
        },
    }


def _normalized_payload_text(value: str | None) -> str | None:
    cleaned = _normalize_optional_text(value)
    return cleaned.casefold() if cleaned is not None else None


def _mask_hash(value: str) -> str:
    prefix = "sha256:"
    if value.startswith(prefix):
        return f"{prefix}...{value[-12:]}"
    return mask_identifier(value, keep=12) or "..."


def _scan_optical_manifest_once(root_path: str, *, deadline: float) -> tuple[tuple[dict[str, Any], ...], tuple[str, ...]]:
    entries: list[dict[str, Any]] = []
    root_names: list[str] = []
    stack: list[tuple[str, Path]] = [("", Path(root_path))]
    while stack:
        _raise_if_manifest_timeout(deadline, entries)
        relative_dir, current_path = stack.pop()
        try:
            directory_entries = list(os.scandir(current_path))
        except OSError as exc:
            raise _OpticalManifestError(
                "optical_identity_incomplete",
                f"The optical disc manifest could not be completely enumerated: {exc}",
                file_count=_manifest_file_count(tuple(entries)),
                directory_count=_manifest_directory_count(tuple(entries)),
            ) from exc
        child_directories: list[tuple[str, Path]] = []
        for directory_entry in directory_entries:
            _raise_if_manifest_timeout(deadline, entries)
            relative_path = f"{relative_dir}\\{directory_entry.name}" if relative_dir else directory_entry.name
            normalized_relative_path = relative_path.replace("/", "\\").strip("\\").casefold()
            try:
                is_directory = directory_entry.is_dir(follow_symlinks=False)
                is_file = directory_entry.is_file(follow_symlinks=False)
                stat_result = directory_entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise _OpticalManifestError(
                    "optical_identity_incomplete",
                    f"The optical disc manifest could not read metadata for {normalized_relative_path}.",
                    file_count=_manifest_file_count(tuple(entries)),
                    directory_count=_manifest_directory_count(tuple(entries)),
                ) from exc
            entry_type = "directory" if is_directory else "file" if is_file else "other"
            manifest_entry: dict[str, Any] = {
                "relative_path": normalized_relative_path,
                "entry_type": entry_type,
            }
            if is_file:
                manifest_entry["file_size"] = int(stat_result.st_size)
            if hasattr(stat_result, "st_mtime_ns"):
                manifest_entry["last_write_time_ns"] = int(stat_result.st_mtime_ns)
            entries.append(manifest_entry)
            if not relative_dir:
                root_names.append(directory_entry.name.upper())
            if is_directory:
                child_directories.append((normalized_relative_path, Path(directory_entry.path)))
        stack.extend(reversed(sorted(child_directories, key=lambda item: item[0])))
    return tuple(sorted(entries, key=lambda item: (item["relative_path"], item["entry_type"]))), tuple(sorted(root_names))


def _raise_if_manifest_timeout(deadline: float, entries: list[dict[str, Any]]) -> None:
    if time.monotonic() <= deadline:
        return
    raise _OpticalManifestError(
        "optical_identity_timeout",
        "The optical disc could not be completely identified within the allowed time. No partial fingerprint was saved.",
        file_count=_manifest_file_count(tuple(entries)),
        directory_count=_manifest_directory_count(tuple(entries)),
    )


def _strip_manifest_timestamps(entries: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
    stripped = []
    for entry in entries:
        stripped_entry = dict(entry)
        stripped_entry.pop("last_write_time_ns", None)
        stripped.append(stripped_entry)
    return tuple(sorted(stripped, key=lambda item: (item["relative_path"], item["entry_type"])))


def _manifest_file_count(entries: tuple[dict[str, Any], ...]) -> int:
    return sum(1 for entry in entries if entry.get("entry_type") == "file")


def _manifest_directory_count(entries: tuple[dict[str, Any], ...]) -> int:
    return sum(1 for entry in entries if entry.get("entry_type") == "directory")


__all__ = [
    "PathProbeStatus",
    "WindowsCommandRunner",
    "WindowsSourceIdentityProbeProvider",
    "mask_guid",
    "mask_identifier",
    "mask_path_usernames",
]
