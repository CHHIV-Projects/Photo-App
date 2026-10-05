from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

from photo_organizer_windows_helper.attestation import InventoryAttestationAuthority
from photo_organizer_windows_helper.known_source import KnownSourceVerification, verify_known_source
from photo_organizer_windows_helper.operations import WindowsInventoryCollector
from windows_helper_shared.channel import ClaimedInventoryAttestationOperation
from windows_helper_shared.identity.fingerprints import volume_guid_fingerprint
from windows_helper_shared.protocol import (
    HelperInventoryPageRequest,
    HelperInventoryItem,
    HelperKnownSourceAttestationRequest,
    InventoryResultStatus,
    InventoryEntryKind,
    ProviderNativePath,
    SourceType,
)


NODE = UUID("aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee")
GUID = "11111111-1111-1111-1111-111111111111"
FINGERPRINT = volume_guid_fingerprint(GUID)[0]


def _operation(*, root: str = "H:\\Photos", workflow: UUID | None = None, generation: UUID | None = None):
    operation_id = uuid4()
    request = HelperKnownSourceAttestationRequest(
        request_id=operation_id,
        intended_access_node_id=NODE,
        source_endpoint_id=2,
        source_profile_id=3,
        source_type=SourceType.EXTERNAL,
        configured_source_root=root,
        endpoint_relative_root="Photos",
        expected_identity_fingerprint=FINGERPRINT,
        parent_workflow_id=workflow or uuid4(),
        inventory_generation=generation or uuid4(),
        attestation_lifetime_seconds=60,
    )
    return ClaimedInventoryAttestationOperation(
        operation_id=operation_id,
        lease_expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        request=request,
    )


def _page(operation, token: str, *, root: str | None = None, workflow: UUID | None = None):
    request = operation.request
    runtime_root = root or request.configured_source_root
    return HelperInventoryPageRequest(
        request_id=uuid4(),
        intended_access_node_id=NODE,
        source_endpoint_id=request.source_endpoint_id,
        source_profile_id=request.source_profile_id,
        source_type=request.source_type,
        provider_native_path=ProviderNativePath(
            provider_native_root=runtime_root,
            provider_native_relative_path="",
            provider_native_full_path=runtime_root,
        ),
        expected_identity_fingerprint=FINGERPRINT,
        inventory_generation=request.inventory_generation,
        parent_workflow_id=workflow or request.parent_workflow_id,
        inventory_attestation_token=token,
        page_size=1,
    )


class KnownSourceVerificationTests(unittest.TestCase):
    def test_same_volume_at_changed_drive_letter_is_accepted(self) -> None:
        request = _operation().request
        evidence = verify_known_source(
            request,
            handle_paths=lambda path: (path.casefold(), GUID) if path.startswith("J:") else (_ for _ in ()).throw(OSError()),
            volume_roots=lambda: [("J:\\", GUID)],
        )
        self.assertEqual(evidence.status, "success")
        self.assertEqual(evidence.runtime_source_root, "J:\\Photos")

    def test_wrong_device_and_ambiguous_route_fail_closed(self) -> None:
        request = _operation().request
        wrong = verify_known_source(
            request,
            handle_paths=lambda path: (path.casefold(), "22222222-2222-2222-2222-222222222222"),
            volume_roots=lambda: [],
        )
        self.assertEqual(wrong.status, "identity_changed")
        ambiguous = verify_known_source(
            request,
            handle_paths=lambda path: (path.casefold(), GUID),
            volume_roots=lambda: [("H:\\", GUID), ("J:\\", GUID)],
        )
        self.assertEqual(ambiguous.status, "ambiguous")


class InventoryAttestationTests(unittest.TestCase):
    def test_token_is_generation_workflow_root_bound_expiring_and_process_local(self) -> None:
        operation = _operation()
        authority = InventoryAttestationAuthority(signing_key=b"a" * 32)
        issued = datetime(2026, 10, 1, tzinfo=timezone.utc)
        response = authority.attest(
            operation,
            verifier=lambda request: KnownSourceVerification(
                "success", request.configured_source_root, request.expected_identity_fingerprint
            ),
            now=issued,
        )
        token = response.inventory_attestation_token or ""
        request = _page(operation, token)
        self.assertEqual(authority.validate(request, now=issued + timedelta(seconds=59)), "valid")
        self.assertEqual(authority.validate(request, now=issued + timedelta(seconds=60)), "refresh_required")
        self.assertEqual(
            authority.validate(request.model_copy(update={"parent_workflow_id": uuid4()}), now=issued),
            "binding_mismatch",
        )
        self.assertEqual(
            InventoryAttestationAuthority(signing_key=b"b" * 32).validate(request, now=issued),
            "refresh_required",
        )

    def test_multi_page_inventory_does_not_run_full_probe(self) -> None:
        operation = _operation()
        authority = InventoryAttestationAuthority(signing_key=b"a" * 32)
        response = authority.attest(
            operation,
            verifier=lambda request: KnownSourceVerification(
                "success", request.configured_source_root, request.expected_identity_fingerprint
            ),
        )
        token = response.inventory_attestation_token or ""
        first_request = _page(operation, token)
        collector = WindowsInventoryCollector(identity_collector=Mock())
        items = iter(
            HelperInventoryItem(
                candidate_reference=f"candidate_{index}",
                provider_native_path=ProviderNativePath(
                    provider_native_root="H:\\Photos",
                    provider_native_relative_path=f"{index}.jpg",
                    provider_native_full_path=f"H:\\Photos\\{index}.jpg",
                ),
                filename=f"{index}.jpg",
                size_bytes=1,
                modified_time_ns=index,
                entry_kind=InventoryEntryKind.REGULAR_FILE,
                local_residency="resident",
            )
            for index in (1, 2)
        )
        with (
            patch.object(collector, "_walk", return_value=items),
            patch(
                "photo_organizer_windows_helper.operations.verify_runtime_root",
                return_value=KnownSourceVerification("success", "H:\\Photos", FINGERPRINT),
            ),
        ):
            first = collector.inventory_page(first_request, attestation_authority=authority)
            second = collector.inventory_page(
                first_request.model_copy(
                    update={"request_id": uuid4(), "cursor": first.next_cursor}
                ),
                attestation_authority=authority,
            )
        self.assertEqual(first.result_status, InventoryResultStatus.SUCCESS)
        self.assertEqual(second.result_status, InventoryResultStatus.SUCCESS)
        self.assertIsNone(first.identity_probe)
        self.assertIsNotNone(first.root_continuity)
        self.assertIsNone(second.next_cursor)


if __name__ == "__main__":
    unittest.main()
