from __future__ import annotations

import json
import stat
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import UUID, uuid4

from pydantic import ValidationError

from photo_organizer_windows_helper.operations import WindowsInventoryCollector
from windows_helper_shared.identity.fingerprints import volume_guid_fingerprint
from windows_helper_shared.identity.models import (
    IdentityFingerprintCandidate,
    NormalizedIdentityEvidence,
    ProviderNativeRootEvidence,
)
from windows_helper_shared.protocol import (
    MAX_INVENTORY_PAGE_SIZE,
    MAX_INVENTORY_RESULT_BYTES,
    HelperInventoryItem,
    HelperInventoryPageRequest,
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
