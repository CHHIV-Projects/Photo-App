from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch
from uuid import UUID, uuid4

from photo_organizer_windows_helper.attestation import (
    ChildAttestationAuthority,
    ChildIdentityMismatch,
)
from windows_helper_shared.channel import ClaimedChildAttestationOperation
from windows_helper_shared.identity.models import (
    IdentityFingerprintCandidate,
    NormalizedIdentityEvidence,
    ProviderNativeRootEvidence,
)
from windows_helper_shared.protocol import (
    HelperAcquireItemRequest,
    HelperChildAttestationRequest,
    HelperProbeResponse,
    ProbeResultStatus,
    ProviderNativePath,
    SourceType,
)


NODE_ID = UUID("aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee")
FINGERPRINT = "sha256:" + "a" * 64
ROOT = "H:\\Photos"


def _claimed(*, lifetime: int = 900) -> ClaimedChildAttestationOperation:
    operation_id = uuid4()
    request = HelperChildAttestationRequest(
        request_id=operation_id,
        intended_access_node_id=NODE_ID,
        source_endpoint_id=2,
        source_profile_id=3,
        source_type=SourceType.EXTERNAL,
        provider_native_path=ProviderNativePath(
            provider_native_root=ROOT,
            provider_native_relative_path="",
            provider_native_full_path=ROOT,
        ),
        expected_identity_fingerprint=FINGERPRINT,
        parent_workflow_id=uuid4(),
        acquisition_run_id=uuid4(),
        attestation_lifetime_seconds=lifetime,
    )
    return ClaimedChildAttestationOperation(
        operation_id=operation_id,
        lease_expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        request=request,
    )


def _probe(operation: ClaimedChildAttestationOperation) -> HelperProbeResponse:
    request = operation.request
    return HelperProbeResponse(
        request_id=operation.operation_id,
        result_status=ProbeResultStatus.SUCCESS,
        source_type=request.source_type,
        provider_native_path=request.provider_native_path,
        collector_name="windows_non_admin_probe_v1",
        collector_version="1",
        source_root_evidence=ProviderNativeRootEvidence(
            path=ROOT,
            is_valid_source_root_candidate=True,
            filesystem_boundary_type="external_folder",
            root_reason="Synthetic exact root.",
        ),
        evidence_items=[
            NormalizedIdentityEvidence(
                category="volume_evidence",
                code="volume_guid_present",
                status="present",
                durability="durable",
                privacy_level="hash_before_storage",
                source_types=["external_device"],
                fingerprint_hash=FINGERPRINT,
                fingerprint_version="source_endpoint_volume_guid_v2",
            )
        ],
        identity_fingerprint=IdentityFingerprintCandidate(
            algorithm="source_endpoint_volume_guid_v2",
            available=True,
            display="verified-volume",
        ),
    )


def _acquire(operation: ClaimedChildAttestationOperation, token: str) -> HelperAcquireItemRequest:
    request = operation.request
    return HelperAcquireItemRequest(
        request_id=uuid4(),
        intended_access_node_id=request.intended_access_node_id,
        acquisition_run_id=request.acquisition_run_id,
        acquisition_item_id=uuid4(),
        source_endpoint_id=request.source_endpoint_id,
        source_profile_id=request.source_profile_id,
        source_type=request.source_type,
        provider_native_path=ProviderNativePath(
            provider_native_root=ROOT,
            provider_native_relative_path="one.jpg",
            provider_native_full_path=ROOT + "\\one.jpg",
        ),
        inventory_generation=uuid4(),
        candidate_reference="candidate_one",
        expected_identity_fingerprint=FINGERPRINT,
        expected_size_bytes=10,
        expected_modified_time_ns=1,
        parent_workflow_id=request.parent_workflow_id,
        child_attestation_token=token,
    )


class ChildAttestationTests(unittest.TestCase):
    def test_token_is_child_bound_short_lived_and_process_local(self) -> None:
        operation = _claimed(lifetime=60)
        authority = ChildAttestationAuthority(signing_key=b"a" * 32)
        issued = datetime(2026, 9, 30, tzinfo=timezone.utc)
        with patch(
            "photo_organizer_windows_helper.attestation.execute_probe",
            return_value=_probe(operation),
        ):
            response = authority.attest(operation, object(), now=issued)  # type: ignore[arg-type]
        request = _acquire(operation, response.attestation_token)
        self.assertEqual(authority.validate(request, now=issued + timedelta(seconds=59)), "valid")
        self.assertEqual(
            authority.validate(request, now=issued + timedelta(seconds=60)),
            "refresh_required",
        )
        self.assertEqual(
            ChildAttestationAuthority(signing_key=b"b" * 32).validate(request, now=issued),
            "refresh_required",
        )

    def test_valid_signature_with_wrong_child_binding_fails_closed(self) -> None:
        operation = _claimed()
        authority = ChildAttestationAuthority(signing_key=b"a" * 32)
        issued = datetime(2026, 9, 30, tzinfo=timezone.utc)
        with patch(
            "photo_organizer_windows_helper.attestation.execute_probe",
            return_value=_probe(operation),
        ):
            response = authority.attest(operation, object(), now=issued)  # type: ignore[arg-type]
        request = _acquire(operation, response.attestation_token)
        mismatches = {
            "child": {"acquisition_run_id": uuid4()},
            "access_node": {"intended_access_node_id": uuid4()},
            "endpoint": {"source_endpoint_id": 99},
            "profile": {"source_profile_id": 99},
            "fingerprint": {"expected_identity_fingerprint": "sha256:" + "b" * 64},
            "root": {
                "provider_native_path": ProviderNativePath(
                    provider_native_root="D:\\Photos",
                    provider_native_relative_path="one.jpg",
                    provider_native_full_path="D:\\Photos\\one.jpg",
                )
            },
            "parent": {"parent_workflow_id": uuid4()},
        }
        for name, change in mismatches.items():
            with self.subTest(name=name):
                self.assertEqual(
                    authority.validate(request.model_copy(update=change), now=issued),
                    "binding_mismatch",
                )

    def test_full_attestation_fingerprint_mismatch_fails_without_token(self) -> None:
        operation = _claimed()
        mismatched = _probe(operation)
        mismatched.evidence_items[0].fingerprint_hash = "sha256:" + "b" * 64
        with patch(
            "photo_organizer_windows_helper.attestation.execute_probe",
            return_value=mismatched,
        ), self.assertRaises(ChildIdentityMismatch):
            ChildAttestationAuthority().attest(operation, object())  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
