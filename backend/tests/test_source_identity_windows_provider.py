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
) -> WindowsSourceIdentityProbeProvider:
    mapped_paths = mapped_paths or {}
    return WindowsSourceIdentityProbeProvider(
        command_runner=_FakeCommandRunner(results),
        path_probe=_path_probe(readable_paths or set(), access_denied_paths=access_denied_paths),
        mapped_drive_resolver=lambda path: mapped_paths.get(path),
        command_timeout_seconds=0.01,
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
