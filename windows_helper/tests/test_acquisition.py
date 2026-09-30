from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import ntpath
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from uuid import UUID, uuid4

from pydantic import ValidationError

from photo_organizer_windows_helper.acquisition import _stable_file_id, execute_acquisition
from photo_organizer_windows_helper.client import HelperClientError
from photo_organizer_windows_helper.credential_store import StoredCredential
from windows_helper_shared.channel import (
    ClaimedAcquireOperation,
    HelperAcquisitionStatusResponse,
    HelperChunkCommitResponse,
)
from windows_helper_shared.identity.models import (
    IdentityFingerprintCandidate,
    NormalizedIdentityEvidence,
    ProviderNativeRootEvidence,
)
from windows_helper_shared.protocol import (
    AcquireResultStatus,
    HelperAcquireItemRequest,
    HelperProbeResponse,
    ProbeResultStatus,
    ProviderNativePath,
    SourceType,
)


NODE_ID = UUID("aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee")
ROOT = "C:\\Controlled"
FINGERPRINT = "sha256:" + "a" * 64


def _operation(path: Path, *, chunk_bytes: int = 4) -> ClaimedAcquireOperation:
    metadata = os.stat(path, follow_symlinks=False)
    operation_id = uuid4()
    request = HelperAcquireItemRequest(
        request_id=operation_id,
        intended_access_node_id=NODE_ID,
        acquisition_run_id=uuid4(),
        acquisition_item_id=uuid4(),
        source_endpoint_id=2,
        source_profile_id=3,
        source_type=SourceType.LOCAL,
        provider_native_path=ProviderNativePath(
            provider_native_root=ROOT,
            provider_native_relative_path="file.jpg",
            provider_native_full_path=ROOT + "\\file.jpg",
        ),
        inventory_generation=uuid4(),
        candidate_reference="candidate_file",
        expected_identity_fingerprint=FINGERPRINT,
        expected_size_bytes=metadata.st_size,
        expected_modified_time_ns=metadata.st_mtime_ns,
        expected_file_id_digest=_stable_file_id(metadata),
        normal_chunk_bytes=chunk_bytes,
    )
    return ClaimedAcquireOperation(
        operation_id=operation_id,
        lease_expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        request=request,
    )


def _probe(operation: ClaimedAcquireOperation, fingerprint: str = FINGERPRINT) -> HelperProbeResponse:
    request = operation.request
    root_path = ProviderNativePath(
        provider_native_root=ROOT,
        provider_native_relative_path="",
        provider_native_full_path=ROOT,
    )
    return HelperProbeResponse(
        request_id=operation.operation_id,
        result_status=ProbeResultStatus.SUCCESS,
        source_type=request.source_type,
        provider_native_path=root_path,
        collector_name="windows_non_admin_probe_v1",
        collector_version="1",
        source_root_evidence=ProviderNativeRootEvidence(
            path=ROOT,
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
                fingerprint_version="source_endpoint_volume_guid_v2",
            )
        ],
        identity_fingerprint=IdentityFingerprintCandidate(
            algorithm="source_endpoint_volume_guid_v2",
            available=True,
            display="verified-volume",
        ),
    )


class _Client:
    def __init__(self, operation: ClaimedAcquireOperation, initial: bytes = b"") -> None:
        self.operation = operation
        self.received = bytearray(initial)
        self.uploads: list[tuple[int, bytes]] = []
        self.mutate_after_upload = None
        self.lose_first_response = False

    def acquisition_status(self, credential, operation_id, run_id, item_id):
        del credential
        assert operation_id == self.operation.operation_id
        assert run_id == self.operation.request.acquisition_run_id
        assert item_id == self.operation.request.acquisition_item_id
        return HelperAcquisitionStatusResponse(
            acquisition_run_id=run_id,
            acquisition_item_id=item_id,
            state="transferring",
            committed_offset=len(self.received),
            expected_size_bytes=self.operation.request.expected_size_bytes,
            maximum_chunk_bytes=4 * 1024 * 1024,
        )

    def upload_chunk(self, credential, operation_id, run_id, item_id, *, offset, chunk, digest):
        del credential
        assert operation_id == self.operation.operation_id
        assert run_id == self.operation.request.acquisition_run_id
        assert item_id == self.operation.request.acquisition_item_id
        assert offset == len(self.received)
        assert digest == "sha256:" + hashlib.sha256(chunk).hexdigest()
        self.received.extend(chunk)
        self.uploads.append((offset, chunk))
        if self.mutate_after_upload is not None:
            callback, self.mutate_after_upload = self.mutate_after_upload, None
            callback()
        if self.lose_first_response:
            self.lose_first_response = False
            raise HelperClientError("synthetic lost response")
        return HelperChunkCommitResponse(
            acquisition_run_id=run_id,
            acquisition_item_id=item_id,
            accepted_offset=offset,
            committed_offset=len(self.received),
            bytes_committed=len(chunk),
        )


class WindowsAcquisitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "controlled.jpg"
        self.content = b"controlled-source-bytes"
        self.path.write_bytes(self.content)
        self.operation = _operation(self.path)
        self.credential = StoredCredential(
            access_node_id=str(NODE_ID),
            credential_id="c_public",
            credential_version=1,
            token="protected-token",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _execute(self, client: _Client, **overrides):
        defaults = {
            "stat_path": lambda _: os.stat(self.path, follow_symlinks=False),
            "open_file": lambda _: self.path.open("rb", buffering=0),
            "handle_path": lambda _: ntpath.normcase(self.operation.request.provider_native_path.provider_native_full_path),
        }
        defaults.update(overrides)
        with patch(
            "photo_organizer_windows_helper.acquisition.execute_probe",
            return_value=_probe(self.operation),
        ):
            return execute_acquisition(
                self.operation,
                client,
                self.credential,
                **defaults,
            )

    def test_exact_read_hashes_and_resumes_from_linux_offset(self) -> None:
        prefix = self.content[:7]
        client = _Client(self.operation, prefix)
        result = self._execute(client)
        self.assertEqual(result.result_status, AcquireResultStatus.SUCCESS)
        self.assertEqual(bytes(client.received), self.content)
        self.assertEqual(result.bytes_read, len(self.content))
        self.assertEqual(
            result.helper_source_sha256,
            "sha256:" + hashlib.sha256(self.content).hexdigest(),
        )
        self.assertEqual(client.uploads[0][0], len(prefix))
        self.assertTrue(all(len(chunk) <= 4 for _, chunk in client.uploads))

    def test_lost_chunk_response_recovers_from_linux_committed_offset(self) -> None:
        client = _Client(self.operation)
        client.lose_first_response = True
        result = self._execute(client)
        self.assertEqual(result.result_status, AcquireResultStatus.SUCCESS)
        self.assertEqual(bytes(client.received), self.content)

    def test_fingerprint_mismatch_stops_before_content_open(self) -> None:
        opened = False

        def forbidden_open(_):
            nonlocal opened
            opened = True
            raise AssertionError("content open is forbidden")

        client = _Client(self.operation)
        with patch(
            "photo_organizer_windows_helper.acquisition.execute_probe",
            return_value=_probe(self.operation, "sha256:" + "b" * 64),
        ):
            result = execute_acquisition(
                self.operation,
                client,
                self.credential,
                stat_path=lambda _: os.stat(self.path, follow_symlinks=False),
                open_file=forbidden_open,
            )
        self.assertEqual(result.result_status, AcquireResultStatus.SOURCE_CHANGED)
        self.assertFalse(opened)
        self.assertEqual(client.uploads, [])

    def test_offline_or_reparse_evidence_stops_before_content_open(self) -> None:
        metadata = os.stat(self.path, follow_symlinks=False)
        for attributes, expected_status in (
            (0x1000, AcquireResultStatus.PLACEHOLDER_UNAVAILABLE),
            (0x400, AcquireResultStatus.SOURCE_CHANGED),
        ):
            with self.subTest(attributes=attributes):
                observed = SimpleNamespace(
                    st_mode=metadata.st_mode,
                    st_size=metadata.st_size,
                    st_mtime_ns=metadata.st_mtime_ns,
                    st_dev=metadata.st_dev,
                    st_ino=metadata.st_ino,
                    st_file_attributes=attributes,
                )
                opened = False

                def forbidden_open(_):
                    nonlocal opened
                    opened = True
                    raise AssertionError("content open is forbidden")

                client = _Client(self.operation)
                result = self._execute(client, stat_path=lambda _, value=observed: value, open_file=forbidden_open)
                self.assertEqual(result.result_status, expected_status)
                self.assertFalse(opened)
                self.assertEqual(client.uploads, [])

    def test_handle_path_change_and_source_mutation_never_succeed(self) -> None:
        client = _Client(self.operation)
        changed_path = self._execute(client, handle_path=lambda _: ntpath.normcase("C:\\Other\\file.jpg"))
        self.assertEqual(changed_path.result_status, AcquireResultStatus.SOURCE_CHANGED)
        self.assertEqual(client.uploads, [])

        client = _Client(self.operation)
        client.mutate_after_upload = lambda: self.path.write_bytes(self.content + b"x")
        changed_source = self._execute(client)
        self.assertEqual(changed_source.result_status, AcquireResultStatus.SOURCE_CHANGED)

    def test_acquire_contract_rejects_destination_authority(self) -> None:
        payload = self.operation.request.model_dump(mode="json")
        payload["destination_path"] = "/tmp/arbitrary"
        with self.assertRaises(ValidationError):
            HelperAcquireItemRequest.model_validate(payload)


if __name__ == "__main__":
    unittest.main()
