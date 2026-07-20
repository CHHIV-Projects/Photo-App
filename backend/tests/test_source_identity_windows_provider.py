from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.source_identity.probe_schema import SourceIdentityProbeRequest
from app.services.source_identity.durable_identity import summarize_durable_identity
from app.services.source_identity.identity_fingerprint import fingerprint_from_probe
from app.services.source_identity.providers.base import CommandResult
from app.services.source_identity.providers.windows_non_admin import (
    _OpticalManifestError,
    _OpticalManifestResult,
    _optical_metadata_command,
    PathProbeStatus,
    WindowsSourceIdentityProbeProvider,
    mask_guid,
    mask_identifier,
)


class _FakeCommandRunner:
    def __init__(self, results: dict[tuple[str, ...], CommandResult] | None = None) -> None:
        self.results = results or {}
        self.calls: list[tuple[str, ...]] = []

    def run(self, args: list[str], *, timeout_seconds: float) -> CommandResult:
        key = tuple(args)
        self.calls.append(key)
        return self.results.get(key, CommandResult(args=key, returncode=0, stdout=""))


def _path_probe(readable_paths: set[str], *, access_denied_paths: set[str] | None = None):
    access_denied_paths = access_denied_paths or set()

    def _probe(path: str | None) -> PathProbeStatus:
        if path in access_denied_paths:
            return PathProbeStatus(exists=True, is_dir=True, readable=False, access_denied=True)
        if path in readable_paths:
            return PathProbeStatus(exists=True, is_dir=True, readable=True)
        return PathProbeStatus(exists=False, is_dir=False, readable=False)

    return _probe


def _provider(
    *,
    readable_paths: set[str] | None = None,
    access_denied_paths: set[str] | None = None,
    results: dict[tuple[str, ...], CommandResult] | None = None,
    mapped_paths: dict[str, str] | None = None,
    optical_manifest_reader=None,
) -> WindowsSourceIdentityProbeProvider:
    mapped_paths = mapped_paths or {}
    return WindowsSourceIdentityProbeProvider(
        command_runner=_FakeCommandRunner(results),
        path_probe=_path_probe(readable_paths or set(), access_denied_paths=access_denied_paths),
        mapped_drive_resolver=lambda path: mapped_paths.get(path),
        command_timeout_seconds=0.01,
        optical_manifest_reader=optical_manifest_reader,
    )


def _optical_metadata_results(
    drive: str = "E",
    *,
    filesystem: str | None = "UDF",
    volume_label: str = "",
    volume_serial: str = "7967C7EC",
    media_loaded: bool = True,
    media_type: str = "DVD Writer",
    drive_name: str = "Slimtype DVD A DS8A5S USB Device",
    pnp_device_id: str = "USBSTOR\\CDROM&VEN_SLIMTYPE&PROD_DVD_A__DS8A5S&REV_WP56\\FFFFFFFE0D103110198982&0",
    total_size: int = 736960512,
    free_space: int = 706088960,
) -> dict[tuple[str, ...], CommandResult]:
    script = _optical_metadata_command(drive)
    payload = json.dumps(
        {
            "Volume": {
                "DriveLetter": drive,
                "DriveType": "CD-ROM",
                "FileSystemType": "Unknown",
                "FileSystemLabel": volume_label,
                "Size": total_size,
                "SizeRemaining": free_space,
            },
            "LogicalDisk": {
                "DeviceID": f"{drive}:",
                "DriveType": 5,
                "FileSystem": filesystem,
                "VolumeName": volume_label,
                "VolumeSerialNumber": volume_serial,
                "Size": total_size,
                "FreeSpace": free_space,
                "MediaType": 11,
            },
            "CdRom": {
                "Drive": f"{drive}:",
                "MediaLoaded": media_loaded,
                "MediaType": media_type,
                "Name": drive_name,
                "VolumeName": volume_label,
                "VolumeSerialNumber": volume_serial,
                "PNPDeviceID": pnp_device_id,
            },
        }
    )
    return {
        ("powershell", "-NoProfile", "-Command", script): CommandResult(
            args=("powershell", "-NoProfile", "-Command", script),
            returncode=0,
            stdout=payload,
        )
    }


def _optical_manifest(
    entries: tuple[dict[str, object], ...] | None = None,
    *,
    root_names: tuple[str, ...] = ("ordinary.txt",),
) -> _OpticalManifestResult:
    manifest_entries = entries or (
        {"relative_path": "ordinary.txt", "entry_type": "file", "file_size": 42},
    )
    return _OpticalManifestResult(
        entries=manifest_entries,
        root_names=root_names,
        file_count=sum(1 for item in manifest_entries if item.get("entry_type") == "file"),
        directory_count=sum(1 for item in manifest_entries if item.get("entry_type") == "directory"),
        timestamps_included=False,
        elapsed_seconds=0.003,
    )


class WindowsSourceIdentityProbeProviderTests(unittest.TestCase):
    def test_source_root_classification_by_source_type(self) -> None:
        cases = [
            ("local", "C:\\", "local_volume_root"),
            ("local", "C:\\Photos", "local_folder"),
            ("external_device", "F:\\", "external_volume_root"),
            ("external_device", "F:\\Photos", "external_folder"),
            ("removable_media", "H:\\", "removable_media_root"),
            ("removable_media", "H:\\DCIM", "removable_media_folder"),
            ("nas", "\\\\HENDERSON-NAS", "nas_server_only"),
            ("nas", "\\\\HENDERSON-NAS\\Photos", "nas_share_root"),
            ("nas", "\\\\HENDERSON-NAS\\Photos\\Family Archive", "nas_share_folder"),
        ]
        readable_paths = {path for _, path, boundary in cases if boundary != "nas_server_only"}
        provider = _provider(readable_paths=readable_paths)

        for source_type, path, boundary in cases:
            with self.subTest(source_type=source_type, path=path):
                response = provider.probe(SourceIdentityProbeRequest(source_type=source_type, observed_path=path))
                self.assertEqual(response.source_root_candidate.filesystem_boundary_type, boundary)

    def test_nas_server_only_blocks_as_not_runnable(self) -> None:
        provider = _provider()

        response = provider.probe(
            SourceIdentityProbeRequest(source_type="nas", observed_path="\\\\HENDERSON-NAS")
        )

        self.assertEqual(response.source_root_candidate.filesystem_boundary_type, "nas_server_only")
        self.assertFalse(response.source_root_candidate.is_valid_source_root_candidate)
        self.assertFalse(response.safe_to_run)
        self.assertIn("nas_server_not_runnable", [item.code for item in response.blockers])

    def test_nas_share_and_folder_are_valid_when_readable(self) -> None:
        paths = {"\\\\HENDERSON-NAS\\Photos", "\\\\HENDERSON-NAS\\Photos\\Family Archive"}
        provider = _provider(readable_paths=paths)

        share_response = provider.probe(
            SourceIdentityProbeRequest(source_type="nas", observed_path="\\\\HENDERSON-NAS\\Photos")
        )
        folder_response = provider.probe(
            SourceIdentityProbeRequest(source_type="nas", observed_path="\\\\HENDERSON-NAS\\Photos\\Family Archive")
        )

        self.assertEqual(share_response.source_root_candidate.filesystem_boundary_type, "nas_share_root")
        self.assertTrue(share_response.source_root_candidate.is_valid_source_root_candidate)
        self.assertEqual(folder_response.source_root_candidate.filesystem_boundary_type, "nas_share_folder")
        self.assertTrue(folder_response.source_root_candidate.is_valid_source_root_candidate)

    def test_mapped_nas_path_resolves_to_canonical_unc_identity(self) -> None:
        mapped_path = "Z:\\Dad Files"
        canonical_path = "\\\\HENDERSON-NAS\\Photos\\Dad Files"
        provider = _provider(
            readable_paths={mapped_path},
            mapped_paths={mapped_path: canonical_path},
        )

        response = provider.probe(
            SourceIdentityProbeRequest(source_type="nas", observed_path=mapped_path)
        )
        durable_identity = summarize_durable_identity(probe=response, source_type="local_folder")
        fingerprint = fingerprint_from_probe(response)

        self.assertEqual(response.observed_path, mapped_path)
        self.assertEqual(response.normalized_observed_path, mapped_path.lower())
        self.assertEqual(response.source_root_candidate.path, canonical_path)
        self.assertEqual(response.source_root_candidate.filesystem_boundary_type, "nas_share_folder")
        self.assertTrue(response.source_root_candidate.is_valid_source_root_candidate)
        self.assertIn("mapped_drive_unc_resolved", [item.code for item in response.evidence_items])
        self.assertEqual(durable_identity.status, "verified")
        self.assertEqual(durable_identity.identifier, "\\\\henderson-nas\\photos")
        self.assertEqual(fingerprint.strength, "strong")

    def test_unresolved_mapped_nas_path_blocks_and_requests_unc(self) -> None:
        mapped_path = "Z:\\Dad Files"
        provider = _provider(readable_paths={mapped_path})

        response = provider.probe(
            SourceIdentityProbeRequest(source_type="nas", observed_path=mapped_path)
        )

        self.assertEqual(response.probe_status, "blocked")
        self.assertFalse(response.source_root_candidate.is_valid_source_root_candidate)
        self.assertIn("mapped_nas_unc_resolution_failed", [item.code for item in response.blockers])
        self.assertIn("Enter the NAS location as a UNC path", response.next_safe_actions[0])

    def test_mapped_network_path_is_not_accepted_as_local(self) -> None:
        mapped_path = "Z:\\Dad Files"
        provider = _provider(
            readable_paths={mapped_path},
            mapped_paths={mapped_path: "\\\\HENDERSON-NAS\\Photos\\Dad Files"},
        )

        response = provider.probe(
            SourceIdentityProbeRequest(source_type="local", observed_path=mapped_path)
        )

        self.assertEqual(response.probe_status, "blocked")
        self.assertFalse(response.source_root_candidate.is_valid_source_root_candidate)
        self.assertIn("mapped_network_path_requires_nas", [item.code for item in response.blockers])

    def test_unreadable_nas_path_returns_access_blocker(self) -> None:
        path = "\\\\HENDERSON-NAS\\Photos"
        provider = _provider(access_denied_paths={path})

        response = provider.probe(SourceIdentityProbeRequest(source_type="nas", observed_path=path))

        self.assertFalse(response.safe_to_run)
        self.assertIn("access_denied", [item.code for item in response.blockers])

    def test_external_partial_evidence_needs_review_and_masks_raw_values(self) -> None:
        results = {
            ("cmd", "/c", "vol", "E:"): CommandResult(
                args=("cmd", "/c", "vol", "E:"),
                returncode=0,
                stdout="Volume Serial Number is 1234-ABCD",
            ),
            ("cmd", "/c", "mountvol", "E:", "/L"): CommandResult(
                args=("cmd", "/c", "mountvol", "E:", "/L"),
                returncode=0,
                stdout="\\\\?\\Volume{12345678-90AB-CDEF-1234-567890ABCDEF}\\",
            ),
            ("cmd", "/c", "fsutil", "fsinfo", "drivetype", "E:"): CommandResult(
                args=("cmd", "/c", "fsutil", "fsinfo", "drivetype", "E:"),
                returncode=0,
                stdout="E: - Fixed Drive",
            ),
        }
        provider = _provider(readable_paths={"E:\\Photos"}, results=results)

        response = provider.probe(
            SourceIdentityProbeRequest(source_type="external_device", observed_path="E:\\Photos")
        )
        payload = response.model_dump_json()

        self.assertEqual(response.safe_to_run, "needs_review")
        self.assertIn(response.confidence_tier, {"medium_needs_review", "weak_manual_confirmation_required"})
        self.assertNotIn("1234-ABCD", payload)
        self.assertNotIn("12345678-90AB-CDEF-1234-567890ABCDEF", payload)
        self.assertIn("volume_serial_present", [item.code for item in response.evidence_items])
        self.assertIn("volume_guid_present", [item.code for item in response.evidence_items])
        volume_guid = next(item for item in response.evidence_items if item.code == "volume_guid_present")
        self.assertEqual(volume_guid.durability, "durable")
        self.assertIn("mountvol", volume_guid.message or "")
        self.assertTrue(volume_guid.fingerprint_hash.startswith("sha256:"))
        self.assertEqual(volume_guid.fingerprint_version, "source_endpoint_volume_guid_v2")
        fingerprint = fingerprint_from_probe(response)
        self.assertEqual(fingerprint.hash_value, volume_guid.fingerprint_hash)
        self.assertEqual(fingerprint.version, "source_endpoint_volume_guid_v2")
        self.assertEqual(fingerprint.strength, "strong")
        self.assertEqual(len(fingerprint.legacy_hashes), 1)

    def test_powershell_storage_metadata_adds_usb_and_media_type_evidence(self) -> None:
        payload = json.dumps(
            {
                "Volume": {
                    "DriveLetter": "D",
                    "DriveType": "Removable",
                    "UniqueId": "\\\\?\\Volume{9cd1fa08-fccc-11ee-98fb-70d82340c017}\\",
                },
                "Partition": {"DriveLetter": "D", "DiskNumber": 3},
                "Disk": {
                    "Number": 3,
                    "FriendlyName": "Generic Flash Disk",
                    "BusType": "USB",
                    "IsBoot": False,
                    "IsSystem": False,
                },
                "PhysicalDisk": {
                    "DeviceId": 3,
                    "FriendlyName": "Generic Flash Disk",
                    "BusType": "USB",
                    "MediaType": "Unspecified",
                },
            }
        )
        results = {
            ("powershell", "-NoProfile", "-Command", "$drive='D';$volume=Get-Volume -DriveLetter $drive -ErrorAction SilentlyContinue | Select-Object -First 1 DriveLetter,DriveType,UniqueId,Path,FileSystemType,FileSystemLabel;$partition=Get-Partition -DriveLetter $drive -ErrorAction SilentlyContinue | Select-Object -First 1 DriveLetter,DiskNumber,PartitionNumber,Type;$disk=$null;$physical=$null;if($partition){$disk=Get-Disk -Number $partition.DiskNumber -ErrorAction SilentlyContinue | Select-Object -First 1 Number,FriendlyName,BusType,PartitionStyle,IsBoot,IsSystem,IsReadOnly,IsOffline;$physical=Get-PhysicalDisk -ErrorAction SilentlyContinue | Where-Object DeviceId -eq $partition.DiskNumber | Select-Object -First 1 DeviceId,FriendlyName,BusType,MediaType,HealthStatus;}[pscustomobject]@{Volume=$volume;Partition=$partition;Disk=$disk;PhysicalDisk=$physical} | ConvertTo-Json -Compress -Depth 4"): CommandResult(
                args=("powershell", "-NoProfile", "-Command", "$drive='D';$volume=Get-Volume -DriveLetter $drive -ErrorAction SilentlyContinue | Select-Object -First 1 DriveLetter,DriveType,UniqueId,Path,FileSystemType,FileSystemLabel;$partition=Get-Partition -DriveLetter $drive -ErrorAction SilentlyContinue | Select-Object -First 1 DriveLetter,DiskNumber,PartitionNumber,Type;$disk=$null;$physical=$null;if($partition){$disk=Get-Disk -Number $partition.DiskNumber -ErrorAction SilentlyContinue | Select-Object -First 1 Number,FriendlyName,BusType,PartitionStyle,IsBoot,IsSystem,IsReadOnly,IsOffline;$physical=Get-PhysicalDisk -ErrorAction SilentlyContinue | Where-Object DeviceId -eq $partition.DiskNumber | Select-Object -First 1 DeviceId,FriendlyName,BusType,MediaType,HealthStatus;}[pscustomobject]@{Volume=$volume;Partition=$partition;Disk=$disk;PhysicalDisk=$physical} | ConvertTo-Json -Compress -Depth 4"),
                returncode=0,
                stdout=payload,
            ),
        }
        provider = _provider(readable_paths={"D:\\Photos"}, results=results)

        response = provider.probe(
            SourceIdentityProbeRequest(source_type="removable_media", observed_path="D:\\Photos")
        )

        self.assertIn("bus_type_present", [item.code for item in response.evidence_items])
        self.assertIn("media_type_present", [item.code for item in response.evidence_items])

    def test_removable_empty_slot_blocks_with_no_media_message(self) -> None:
        results = {
            ("cmd", "/c", "fsutil", "fsinfo", "drivetype", "H:"): CommandResult(
                args=("cmd", "/c", "fsutil", "fsinfo", "drivetype", "H:"),
                returncode=0,
                stdout="H: - Removable Drive",
            ),
            ("powershell", "-NoProfile", "-Command", "$drive='H';$volume=Get-Volume -DriveLetter $drive -ErrorAction SilentlyContinue | Select-Object -First 1 DriveLetter,DriveType,UniqueId,Path,FileSystemType,FileSystemLabel;$partition=Get-Partition -DriveLetter $drive -ErrorAction SilentlyContinue | Select-Object -First 1 DriveLetter,DiskNumber,PartitionNumber,Type;$disk=$null;$physical=$null;if($partition){$disk=Get-Disk -Number $partition.DiskNumber -ErrorAction SilentlyContinue | Select-Object -First 1 Number,FriendlyName,BusType,PartitionStyle,IsBoot,IsSystem,IsReadOnly,IsOffline;$physical=Get-PhysicalDisk -ErrorAction SilentlyContinue | Where-Object DeviceId -eq $partition.DiskNumber | Select-Object -First 1 DeviceId,FriendlyName,BusType,MediaType,HealthStatus;}[pscustomobject]@{Volume=$volume;Partition=$partition;Disk=$disk;PhysicalDisk=$physical} | ConvertTo-Json -Compress -Depth 4"): CommandResult(
                args=("powershell", "-NoProfile", "-Command", "$drive='H';$volume=Get-Volume -DriveLetter $drive -ErrorAction SilentlyContinue | Select-Object -First 1 DriveLetter,DriveType,UniqueId,Path,FileSystemType,FileSystemLabel;$partition=Get-Partition -DriveLetter $drive -ErrorAction SilentlyContinue | Select-Object -First 1 DriveLetter,DiskNumber,PartitionNumber,Type;$disk=$null;$physical=$null;if($partition){$disk=Get-Disk -Number $partition.DiskNumber -ErrorAction SilentlyContinue | Select-Object -First 1 Number,FriendlyName,BusType,PartitionStyle,IsBoot,IsSystem,IsReadOnly,IsOffline;$physical=Get-PhysicalDisk -ErrorAction SilentlyContinue | Where-Object DeviceId -eq $partition.DiskNumber | Select-Object -First 1 DeviceId,FriendlyName,BusType,MediaType,HealthStatus;}[pscustomobject]@{Volume=$volume;Partition=$partition;Disk=$disk;PhysicalDisk=$physical} | ConvertTo-Json -Compress -Depth 4"),
                returncode=0,
                stdout="{}",
            ),
        }
        provider = _provider(results=results)

        response = provider.probe(
            SourceIdentityProbeRequest(source_type="removable_media", observed_path="H:\\")
        )

        self.assertIn("no_readable_media_inserted", [item.code for item in response.blockers])

    def test_optical_data_disc_uses_complete_manifest_fingerprint(self) -> None:
        provider = _provider(
            readable_paths={"E:\\"},
            results=_optical_metadata_results(),
            optical_manifest_reader=lambda root_path, *, timeout_seconds: _optical_manifest(),
        )

        response = provider.probe(SourceIdentityProbeRequest(source_type="optical_media", observed_path="E:\\"))
        fingerprint = fingerprint_from_probe(response)
        durable_identity = summarize_durable_identity(probe=response, source_type="optical_media")
        codes = [item.code for item in response.evidence_items]

        self.assertEqual(response.probe_status, "completed")
        self.assertEqual(response.source_root_candidate.filesystem_boundary_type, "optical_media_root")
        self.assertFalse(response.blockers)
        self.assertIn("filesystem_type_present", codes)
        self.assertIn("optical_manifest_complete", codes)
        self.assertIn("optical_media_fingerprint_present", codes)
        self.assertEqual(fingerprint.strength, "strong")
        self.assertEqual(fingerprint.version, "optical_media_fingerprint_v1")
        self.assertEqual(durable_identity.status, "verified")
        self.assertEqual(durable_identity.identifier_type, "Optical media fingerprint")
        self.assertNotIn("ordinary.txt", response.model_dump_json())

    def test_optical_fingerprint_excludes_drive_letter_and_reader_hardware(self) -> None:
        manifest_reader = lambda root_path, *, timeout_seconds: _optical_manifest()
        e_provider = _provider(
            readable_paths={"E:\\"},
            results=_optical_metadata_results("E"),
            optical_manifest_reader=manifest_reader,
        )
        f_provider = _provider(
            readable_paths={"F:\\"},
            results=_optical_metadata_results("F", drive_name="Different Physical DVD Drive"),
            optical_manifest_reader=manifest_reader,
        )

        e_response = e_provider.probe(SourceIdentityProbeRequest(source_type="optical_media", observed_path="E:\\"))
        f_response = f_provider.probe(SourceIdentityProbeRequest(source_type="optical_media", observed_path="F:\\"))

        self.assertEqual(fingerprint_from_probe(e_response).hash_value, fingerprint_from_probe(f_response).hash_value)

    def test_different_optical_manifest_changes_fingerprint(self) -> None:
        first_provider = _provider(
            readable_paths={"E:\\"},
            results=_optical_metadata_results(),
            optical_manifest_reader=lambda root_path, *, timeout_seconds: _optical_manifest(),
        )
        second_provider = _provider(
            readable_paths={"E:\\"},
            results=_optical_metadata_results(),
            optical_manifest_reader=lambda root_path, *, timeout_seconds: _optical_manifest(
                ({"relative_path": "different.txt", "entry_type": "file", "file_size": 42},),
                root_names=("different.txt",),
            ),
        )

        first = first_provider.probe(SourceIdentityProbeRequest(source_type="optical_media", observed_path="E:\\"))
        second = second_provider.probe(SourceIdentityProbeRequest(source_type="optical_media", observed_path="E:\\"))

        self.assertNotEqual(fingerprint_from_probe(first).hash_value, fingerprint_from_probe(second).hash_value)

    def test_optical_empty_drive_blocks_with_specific_message(self) -> None:
        provider = _provider(
            results=_optical_metadata_results(media_loaded=False),
            optical_manifest_reader=lambda root_path, *, timeout_seconds: _optical_manifest(),
        )

        response = provider.probe(SourceIdentityProbeRequest(source_type="optical_media", observed_path="E:\\"))
        blocker_codes = [item.code for item in response.blockers]

        self.assertIn("no_readable_optical_media_inserted", blocker_codes)
        self.assertNotIn("path_not_found", blocker_codes)
        self.assertEqual(response.blockers[0].message, "No readable optical media is inserted.")

    def test_optical_audio_cd_blocks_only_when_no_data_filesystem_is_exposed(self) -> None:
        provider = _provider(
            results=_optical_metadata_results(filesystem=None, volume_label="Audio CD", media_type="Audio CD"),
            optical_manifest_reader=lambda root_path, *, timeout_seconds: _optical_manifest(),
        )

        response = provider.probe(SourceIdentityProbeRequest(source_type="optical_media", observed_path="E:\\"))

        self.assertIn("audio_cd_not_supported", [item.code for item in response.blockers])
        self.assertNotIn("optical_media_fingerprint_present", [item.code for item in response.evidence_items])

    def test_optical_movie_disc_blocks_from_root_level_names(self) -> None:
        provider = _provider(
            readable_paths={"E:\\"},
            results=_optical_metadata_results(),
            optical_manifest_reader=lambda root_path, *, timeout_seconds: _optical_manifest(
                (
                    {"relative_path": "bdmv", "entry_type": "directory"},
                    {"relative_path": "certificate", "entry_type": "directory"},
                ),
                root_names=("BDMV", "CERTIFICATE"),
            ),
        )

        response = provider.probe(SourceIdentityProbeRequest(source_type="optical_media", observed_path="E:\\"))

        self.assertIn("unsupported_movie_optical_media", [item.code for item in response.blockers])
        self.assertNotIn("optical_media_fingerprint_present", [item.code for item in response.evidence_items])

    def test_virtual_optical_drive_blocks(self) -> None:
        provider = _provider(
            readable_paths={"E:\\"},
            results=_optical_metadata_results(
                drive_name="Microsoft Virtual DVD-ROM",
                pnp_device_id="SCSI\\CDROM&VEN_MSFT&PROD_VIRTUAL_DVD-ROM\\1",
            ),
            optical_manifest_reader=lambda root_path, *, timeout_seconds: _optical_manifest(),
        )

        response = provider.probe(SourceIdentityProbeRequest(source_type="optical_media", observed_path="E:\\"))

        self.assertIn("virtual_optical_drive_not_supported", [item.code for item in response.blockers])
        self.assertNotIn("optical_media_fingerprint_present", [item.code for item in response.evidence_items])

    def test_optical_manifest_timeout_blocks_without_partial_fingerprint(self) -> None:
        def _timeout_reader(root_path: str, *, timeout_seconds: float) -> _OpticalManifestResult:
            raise _OpticalManifestError(
                "optical_identity_timeout",
                "The optical disc could not be completely identified within the allowed time. No partial fingerprint was saved.",
                elapsed_seconds=300.0,
                file_count=1,
                directory_count=0,
            )

        provider = _provider(
            readable_paths={"E:\\"},
            results=_optical_metadata_results(),
            optical_manifest_reader=_timeout_reader,
        )

        response = provider.probe(SourceIdentityProbeRequest(source_type="optical_media", observed_path="E:\\"))

        self.assertIn("optical_identity_timeout", [item.code for item in response.blockers])
        self.assertIn("optical_manifest_partial_summary", [item.code for item in response.evidence_items])
        self.assertNotIn("optical_media_fingerprint_present", [item.code for item in response.evidence_items])

    def test_command_failures_are_summarized_not_crashes(self) -> None:
        results = {
            ("cmd", "/c", "vol", "C:"): CommandResult(
                args=("cmd", "/c", "vol", "C:"),
                returncode=1,
                stderr="Access is denied.",
            ),
            ("cmd", "/c", "mountvol", "C:", "/L"): CommandResult(
                args=("cmd", "/c", "mountvol", "C:", "/L"),
                returncode=None,
                command_not_found=True,
            ),
            ("cmd", "/c", "fsutil", "fsinfo", "drivetype", "C:"): CommandResult(
                args=("cmd", "/c", "fsutil", "fsinfo", "drivetype", "C:"),
                returncode=None,
                timed_out=True,
            ),
            ("cmd", "/c", "fsutil", "fsinfo", "volumeinfo", "C:"): CommandResult(
                args=("cmd", "/c", "fsutil", "fsinfo", "volumeinfo", "C:"),
                returncode=2,
                stderr="Unexpected non-zero exit.",
            ),
        }
        provider = _provider(readable_paths={"C:\\Photos"}, results=results)

        response = provider.probe(SourceIdentityProbeRequest(source_type="local", observed_path="C:\\Photos"))
        warning_codes = {item.code for item in response.warnings}

        self.assertIn("command_access_denied", warning_codes)
        self.assertIn("command_unavailable", warning_codes)
        self.assertIn("command_timeout", warning_codes)
        self.assertIn("command_nonzero_exit", warning_codes)
        warning_messages = [item.message or "" for item in response.warnings]
        self.assertTrue(any("cmd /c fsutil fsinfo drivetype C:" in message for message in warning_messages))
        self.assertTrue(any("cmd /c fsutil fsinfo volumeinfo C:" in message for message in warning_messages))
        self.assertIn(response.probe_status, {"completed_with_warnings", "completed"})

    def test_cloud_probe_does_not_probe_provider_credentials(self) -> None:
        runner = _FakeCommandRunner()
        provider = WindowsSourceIdentityProbeProvider(
            command_runner=runner,
            path_probe=_path_probe(set()),
            command_timeout_seconds=0.01,
        )

        response = provider.probe(SourceIdentityProbeRequest(source_type="cloud", observed_path=None))

        self.assertEqual(response.safe_to_run, "not_applicable")
        self.assertIn("cloud_provider_not_probeable", [item.code for item in response.warnings])
        self.assertEqual(runner.calls, [])

    def test_mask_helpers_do_not_return_full_identifiers(self) -> None:
        self.assertEqual(mask_identifier("ABCDEFG123456"), "...3456")
        self.assertEqual(mask_guid("Volume{12345678-90AB-CDEF-1234-567890ABCDEF}"), "{...cdef}")


if __name__ == "__main__":
    unittest.main()
