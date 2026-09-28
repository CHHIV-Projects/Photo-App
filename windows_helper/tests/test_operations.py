from __future__ import annotations

import json
import stat
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

from pydantic import ValidationError

from photo_organizer_windows_helper.operations import HelperOperationExecutor, WindowsInventoryCollector
from windows_helper_shared.channel import ClaimedObserveVolumesOperation
from windows_helper_shared.identity.fingerprints import volume_guid_fingerprint
from windows_helper_shared.identity.models import (
    CommandResult,
    IdentityFingerprintCandidate,
    NormalizedIdentityEvidence,
    ProviderNativeRootEvidence,
)
from windows_helper_shared.identity.windows import (
    MountedVolumeCandidate,
    MountedVolumeStorageEvidence,
    enumerate_windows_mounted_volume_candidates,
)
from windows_helper_shared.protocol import (
    MAX_INVENTORY_PAGE_SIZE,
    MAX_INVENTORY_RESULT_BYTES,
    HelperInventoryItem,
    HelperInventoryPageRequest,
    HelperObserveVolumesRequest,
    HelperObserveVolumesResponse,
    HelperProbeResponse,
    InventoryEntryKind,
    InventoryResultStatus,
    ProbeResultStatus,
    ProviderNativePath,
)


NODE_ID = UUID("aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee")
ROOT = "C:\\Controlled"
FINGERPRINT, FINGERPRINT_VERSION = volume_guid_fingerprint(
    "11111111-1111-1111-1111-111111111111"
)


def _path(relative: str = "") -> ProviderNativePath:
    full = ROOT if not relative else ROOT + "\\" + relative
    return ProviderNativePath(
        provider_native_root=ROOT,
        provider_native_relative_path=relative,
        provider_native_full_path=full,
    )


def _request(
    *,
    request_id: UUID | None = None,
    generation: UUID | None = None,
    cursor: str | None = None,
    page_size: int = 1,
    fingerprint: str = FINGERPRINT,
) -> HelperInventoryPageRequest:
    return HelperInventoryPageRequest(
        request_id=request_id or uuid4(),
        intended_access_node_id=NODE_ID,
        source_endpoint_id=7,
        source_profile_id=11,
        source_type="local",
        provider_native_path=_path(),
        expected_identity_fingerprint=fingerprint,
        inventory_generation=generation,
        cursor=cursor,
        page_size=page_size,
    )


def _probe(request: HelperInventoryPageRequest, fingerprint: str = FINGERPRINT) -> HelperProbeResponse:
    return HelperProbeResponse(
        request_id=request.request_id,
        result_status=ProbeResultStatus.SUCCESS,
        source_type=request.source_type,
        provider_native_path=request.provider_native_path,
        collector_name="windows_non_admin_probe_v1",
        collector_version="1",
        source_root_evidence=ProviderNativeRootEvidence(
            path=request.provider_native_path.provider_native_root,
            is_valid_source_root_candidate=True,
            filesystem_boundary_type="local_folder",
            root_reason="Synthetic exact root.",
        ),
        evidence_items=[
            NormalizedIdentityEvidence(
                category="volume_evidence",
                code="volume_guid_present",
                status="present",
                durability="durable",
                privacy_level="hash_before_storage",
                source_types=["local"],
                fingerprint_hash=fingerprint,
                fingerprint_version=FINGERPRINT_VERSION,
            )
        ],
        identity_fingerprint=IdentityFingerprintCandidate(
            algorithm=FINGERPRINT_VERSION,
            available=True,
            display="verified-volume",
        ),
    )


def _item(relative: str, kind: InventoryEntryKind = InventoryEntryKind.REGULAR_FILE) -> HelperInventoryItem:
    return HelperInventoryItem(
        candidate_reference=("candidate_" + relative.replace("\\", "_").replace(".", "_")),
        provider_native_path=_path(relative),
        filename=relative.rsplit("\\", 1)[-1],
        size_bytes=60 * 1024 if kind == InventoryEntryKind.REGULAR_FILE else None,
        modified_time_ns=123456789,
        entry_kind=kind,
        stable_file_id_digest="sha256:" + "a" * 64,
    )


class InventoryProtocolTests(unittest.TestCase):
    def test_page_bounds_pairing_and_traversal_are_strict(self) -> None:
        with self.assertRaises(ValidationError):
            _request(page_size=0)
        with self.assertRaises(ValidationError):
            _request(page_size=MAX_INVENTORY_PAGE_SIZE + 1)
        with self.assertRaises(ValidationError):
            _request(generation=uuid4(), cursor=None)
        with self.assertRaises(ValidationError):
            ProviderNativePath(
                provider_native_root=ROOT,
                provider_native_relative_path="..\\escape.jpg",
                provider_native_full_path="C:\\escape.jpg",
            )

    def test_metadata_contract_has_no_content_hash_or_transfer_authority(self) -> None:
        fields = set(HelperInventoryItem.model_fields)
        self.assertTrue(
            {"content", "content_hash", "sha256", "transfer", "upload", "destination"}.isdisjoint(fields)
        )
        payload = _item("family\\one.jpg").model_dump(mode="json")
        serialized = json.dumps(payload)
        self.assertNotIn("file_content", serialized)
        self.assertNotIn("transfer_destination", serialized)


class MountedVolumeObservationTests(unittest.TestCase):
    def test_non_admin_storage_collector_normalizes_live_classification_matrix(self) -> None:
        payloads = {
            "C": '{"QueryError":false,"PartitionCount":1,"DiskCount":1,"BusType":17,"IsBoot":true,"IsSystem":true,"IsOffline":false,"RemovalPolicy":1}',
            "G": '{"QueryError":false,"PartitionCount":0,"DiskCount":0,"BusType":0,"IsBoot":null,"IsSystem":null,"IsOffline":null,"RemovalPolicy":null}',
            "H": '{"QueryError":false,"PartitionCount":1,"DiskCount":1,"BusType":7,"IsBoot":false,"IsSystem":false,"IsOffline":false,"RemovalPolicy":3}',
            "X": '{"QueryError":false,"PartitionCount":1,"DiskCount":1,"BusType":7,"IsBoot":false,"IsSystem":false,"IsOffline":false,"RemovalPolicy":3}',
        }

        class _Runner:
            def run(self, args, *, timeout_seconds):
                if args[:3] == ["cmd", "/c", "mountvol"]:
                    return CommandResult(
                        args=tuple(args),
                        returncode=0,
                        stdout="\\\\?\\Volume{11111111-1111-1111-1111-111111111111}\\",
                    )
                script = args[-1]
                letter = next(key for key in payloads if f"DriveLetter = '{key}'" in script)
                return CommandResult(
                    args=tuple(args),
                    returncode=0,
                    stdout=payloads[letter],
                )

        with patch(
            "windows_helper_shared.identity.windows.platform.system",
            return_value="Windows",
        ):
            candidates = enumerate_windows_mounted_volume_candidates(
                command_runner=_Runner(),
                mounted_drive_provider=lambda: [
                    ("C:\\", "fixed"),
                    ("G:\\", "fixed"),
                    ("H:\\", "fixed"),
                    ("X:\\", "removable"),
                ],
            )

        evidence = {item.root_path: item.storage_evidence for item in candidates}
        self.assertEqual(evidence["C:\\"].storage_bus_type, "nvme")
        self.assertTrue(evidence["C:\\"].is_boot)
        self.assertEqual(evidence["G:\\"].backing_association, "none")
        self.assertEqual(evidence["H:\\"].storage_bus_type, "usb")
        self.assertEqual(evidence["H:\\"].external_connection, "usb")
        self.assertEqual(evidence["H:\\"].removal_policy, "surprise")
        self.assertEqual(evidence["H:\\"].operational_state, "online")
        self.assertEqual(evidence["X:\\"].storage_bus_type, "usb")

    def test_storage_collector_fails_closed_for_timeout_and_malformed_state(self) -> None:
        cases = [
            CommandResult(args=("powershell",), returncode=1, timed_out=True),
            CommandResult(args=("powershell",), returncode=0, stdout="not-json"),
            CommandResult(
                args=("powershell",),
                returncode=0,
                stdout=(
                    '{"QueryError":false,"PartitionCount":1,"DiskCount":1,'
                    '"BusType":7,"IsBoot":null,"IsSystem":false,'
                    '"IsOffline":false,"RemovalPolicy":3}'
                ),
            ),
        ]

        for collector_result in cases:
            with self.subTest(result=collector_result):
                runner = Mock()
                runner.run.side_effect = [
                    CommandResult(
                        args=("cmd", "/c", "mountvol", "H:", "/L"),
                        returncode=0,
                        stdout="\\\\?\\Volume{11111111-1111-1111-1111-111111111111}\\",
                    ),
                    collector_result,
                ]
                with patch(
                    "windows_helper_shared.identity.windows.platform.system",
                    return_value="Windows",
                ):
                    candidates = enumerate_windows_mounted_volume_candidates(
                        command_runner=runner,
                        mounted_drive_provider=lambda: [("H:\\", "fixed")],
                    )

                self.assertEqual(
                    candidates[0].storage_evidence.backing_association,
                    "error",
                )

    def test_observation_reuses_safe_volume_candidates_without_file_authority(self) -> None:
        request_id = uuid4()
        request = HelperObserveVolumesRequest(
            request_id=request_id,
            intended_access_node_id=NODE_ID,
            expected_collector_name="windows_non_admin_probe_v1",
            expected_collector_version="1",
        )
        executor = HelperOperationExecutor(
            mounted_volume_observer=lambda: [
                MountedVolumeCandidate(
                    root_path="E:\\",
                    identity_fingerprint_hash=FINGERPRINT,
                    identity_fingerprint_version=FINGERPRINT_VERSION,
                    drive_type="fixed",
                    identity_identifier_masked="{...1111}",
                    storage_evidence=MountedVolumeStorageEvidence(
                        backing_association="exact",
                        storage_bus_type="usb",
                        device_class="disk",
                        removal_policy="surprise",
                        external_connection="usb",
                        operational_state="online",
                        is_boot=False,
                        is_system=False,
                    ),
                )
            ]
        )
        result = executor.execute(
            ClaimedObserveVolumesOperation(
                operation_id=request_id,
                lease_expires_at=datetime.now(timezone.utc) + timedelta(minutes=1),
                request=request,
            )
        )

        self.assertIsInstance(result, HelperObserveVolumesResponse)
        self.assertEqual([item.provider_native_root for item in result.volumes], ["E:\\"])
        self.assertEqual(result.volumes[0].storage_evidence.storage_bus_type, "usb")
        self.assertEqual(result.volumes[0].storage_evidence.backing_association, "exact")
        payload = result.model_dump(mode="json")
        serialized = json.dumps(payload)
        self.assertTrue(
            {
                "content",
                "filename",
                "relative_path",
                "endpoint_id",
                "source_profile_id",
                "directory_entries",
            }.isdisjoint(type(result.volumes[0]).model_fields)
        )
        self.assertNotIn("11111111-1111-1111-1111-111111111111", serialized)

    def test_observation_rejects_duplicate_or_unsorted_roots(self) -> None:
        with self.assertRaises(ValidationError):
            HelperObserveVolumesResponse(
                request_id=uuid4(),
                collector_name="windows_non_admin_probe_v1",
                collector_version="1",
                volumes=[
                    {"provider_native_root": "E:\\"},
                    {"provider_native_root": "e:\\"},
                ],
            )
        with self.assertRaises(ValidationError):
            HelperObserveVolumesResponse(
                request_id=uuid4(),
                collector_name="windows_non_admin_probe_v1",
                collector_version="1",
                volumes=[
                    {"provider_native_root": "G:\\"},
                    {"provider_native_root": "E:\\"},
                ],
            )


class InventoryCollectorTests(unittest.TestCase):
    def test_pagination_is_exact_and_restart_invalidates_opaque_cursor(self) -> None:
        collector = WindowsInventoryCollector()
        ordered_items = [_item("A.jpg"), _item("family\\b.jpg")]
        collector._walk = lambda root, generation: iter(ordered_items)  # type: ignore[method-assign]

        def identity_probe(_collector, probe_request):
            inventory_request = probe_request.model_copy()
            return _probe(
                _request(request_id=inventory_request.request_id, page_size=1)
            )

        first_request = _request(page_size=1)
        with patch(
            "photo_organizer_windows_helper.operations.execute_probe",
            side_effect=identity_probe,
        ):
            first = collector.inventory_page(first_request)
        self.assertEqual(first.result_status, InventoryResultStatus.SUCCESS)
        self.assertEqual([item.filename for item in first.items], ["A.jpg"])
        self.assertIsNotNone(first.next_cursor)

        second_request = _request(
            generation=first.inventory_generation,
            cursor=first.next_cursor,
            page_size=1,
        )
        with patch(
            "photo_organizer_windows_helper.operations.execute_probe",
            side_effect=identity_probe,
        ):
            second = collector.inventory_page(second_request)
        self.assertEqual([item.filename for item in second.items], ["b.jpg"])
        self.assertIsNone(second.next_cursor)
        self.assertLessEqual(
            len(second.model_dump_json(exclude_none=True).encode("utf-8")),
            MAX_INVENTORY_RESULT_BYTES,
        )

        restarted = WindowsInventoryCollector()
        with patch(
            "photo_organizer_windows_helper.operations.execute_probe",
            side_effect=identity_probe,
        ):
            invalid = restarted.inventory_page(second_request)
        self.assertEqual(invalid.result_status, InventoryResultStatus.INVALID_CURSOR)
        self.assertEqual(invalid.items, [])

    def test_identity_change_stops_before_inventory_walk(self) -> None:
        collector = WindowsInventoryCollector()
        collector._walk = lambda *_: (_ for _ in ()).throw(AssertionError("walk must not run"))  # type: ignore[method-assign]
        request = _request()

        def changed_probe(_collector, probe_request):
            return _probe(
                _request(request_id=probe_request.request_id),
                fingerprint="sha256:" + "b" * 64,
            )

        with patch(
            "photo_organizer_windows_helper.operations.execute_probe",
            side_effect=changed_probe,
        ):
            response = collector.inventory_page(request)
        self.assertEqual(response.result_status, InventoryResultStatus.IDENTITY_CHANGED)
        self.assertEqual(response.items, [])

    def test_walk_is_deterministic_and_does_not_follow_reparse_or_special_entries(self) -> None:
        calls: list[tuple[str, bool]] = []

        class Entry:
            def __init__(self, name: str, mode: int, *, symlink: bool = False, denied: bool = False):
                self.name = name
                self.path = ROOT + "\\" + name
                self._mode = mode
                self._symlink = symlink
                self._denied = denied

            def stat(self, *, follow_symlinks: bool):
                calls.append((self.name, follow_symlinks))
                if self._denied:
                    raise PermissionError("denied")
                return SimpleNamespace(
                    st_mode=self._mode,
                    st_size=60 * 1024,
                    st_mtime_ns=123,
                    st_ino=42,
                    st_dev=7,
                    st_file_attributes=0,
                )

            def is_symlink(self) -> bool:
                return self._symlink

        entries = [
            Entry("z.jpg", stat.S_IFREG),
            Entry("Link", stat.S_IFDIR, symlink=True),
            Entry("pipe", stat.S_IFIFO),
            Entry("Denied.jpg", stat.S_IFREG, denied=True),
            Entry("Bdir", stat.S_IFDIR),
            Entry("A.jpg", stat.S_IFREG),
        ]
        child = Entry("child.jpg", stat.S_IFREG)
        child.path = ROOT + "\\Bdir\\child.jpg"
        collector = WindowsInventoryCollector()
        with patch(
            "photo_organizer_windows_helper.operations.os.scandir",
            side_effect=lambda directory: entries if directory == ROOT else [child],
        ):
            items = list(collector._walk(ROOT, uuid4()))

        self.assertEqual(
            [item.provider_native_path.provider_native_relative_path for item in items],
            ["A.jpg", "Bdir\\child.jpg", "Denied.jpg", "Link", "pipe", "z.jpg"],
        )
        self.assertEqual(
            [item.entry_kind for item in items],
            [
                InventoryEntryKind.REGULAR_FILE,
                InventoryEntryKind.REGULAR_FILE,
                InventoryEntryKind.INACCESSIBLE,
                InventoryEntryKind.REPARSE_POINT,
                InventoryEntryKind.SPECIAL,
                InventoryEntryKind.REGULAR_FILE,
            ],
        )
        self.assertTrue(all(follow is False for _, follow in calls))
        self.assertEqual([name for name, _ in calls].count("Link"), 1)


if __name__ == "__main__":
    unittest.main()
