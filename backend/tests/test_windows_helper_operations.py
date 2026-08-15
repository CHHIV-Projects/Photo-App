from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.source_endpoint import AccessNode
from app.models.windows_helper import WindowsHelperOperation
from app.schemas.windows_helper import CreateWindowsHelperProbeOperationRequest
from app.services.source_identity.identity_fingerprint import volume_guid_fingerprint
from app.services.windows_helper.operations import (
    claim_operation,
    complete_probe_operation,
    create_probe_operation,
    fail_operation,
)
from app.services.windows_helper.schema import ensure_windows_helper_schema
from app.services.windows_helper.service import (
    WindowsHelperServiceError,
    authenticate_credential,
    complete_pairing,
    create_pairing_authorization,
)
from app.windows_helper_shared.channel import (
    HelperOperationFailureRequest,
    PairingCompleteRequest,
)
from app.windows_helper_shared.identity.models import (
    IdentityFingerprintCandidate,
    NormalizedIdentityEvidence,
    ProviderNativeRootEvidence,
)
from app.windows_helper_shared.protocol import (
    CapabilityVersion,
    CollectorCapability,
    HelperCapabilityIdentity,
    HelperProbeResponse,
    MachineIssue,
    ProbeResultStatus,
    ProviderNativePath,
    SourceType,
)


def _capability(access_node_id: UUID) -> HelperCapabilityIdentity:
    return HelperCapabilityIdentity(
        helper_version="0.3.0",
        intended_access_node_id=access_node_id,
        supported_source_types=[SourceType.LOCAL],
        collectors=[
            CollectorCapability(
                name="windows_non_admin_probe_v1",
                version="1",
                supported_source_types=[SourceType.LOCAL],
            )
        ],
        capabilities=[
            CapabilityVersion(name="authenticated_channel", version="1"),
            CapabilityVersion(name="remote_operations", version="1"),
            CapabilityVersion(name="bounded_inventory", version="1"),
        ],
    )


def _probe_result(operation_id: UUID, path: str) -> HelperProbeResponse:
    fingerprint_hash, fingerprint_version = volume_guid_fingerprint(
        "11111111-1111-1111-1111-111111111111"
    )
    native_path = ProviderNativePath(
        provider_native_root=path,
        provider_native_relative_path="",
        provider_native_full_path=path,
    )
    return HelperProbeResponse(
        request_id=operation_id,
        result_status=ProbeResultStatus.SUCCESS,
        source_type=SourceType.LOCAL,
        provider_native_path=native_path,
        collector_name="windows_non_admin_probe_v1",
        collector_version="1",
        source_root_evidence=ProviderNativeRootEvidence(
            path=path,
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
                fingerprint_hash=fingerprint_hash,
                fingerprint_version=fingerprint_version,
            )
        ],
        identity_fingerprint=IdentityFingerprintCandidate(
            algorithm=fingerprint_version,
            available=True,
            display="verified-volume",
        ),
    )


class WindowsHelperOperationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        AccessNode.__table__.create(self.engine)
        self.db = Session(self.engine, expire_on_commit=False)
        ensure_windows_helper_schema(self.db)
        authorization = create_pairing_authorization(self.db)
        paired = complete_pairing(
            self.db,
            PairingCompleteRequest(
                pairing_code=authorization.pairing_code,
                access_node_id=authorization.access_node_id,
                capability_identity=_capability(authorization.access_node_id),
            ),
        )
        self.node_id = paired.access_node_id
        self.credential = authenticate_credential(
            self.db,
            f"PhotoOrganizerHelper {paired.credential_id}.{paired.credential_token}",
        )

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def _operation(self):
        return create_probe_operation(
            self.db,
            CreateWindowsHelperProbeOperationRequest(
                access_node_id=self.node_id,
                source_type=SourceType.LOCAL,
                provider_native_root="C:\\Controlled",
            ),
        )

    def test_exact_helper_claims_and_completes_immutable_probe(self) -> None:
        created = self._operation()
        claim = claim_operation(self.db, self.credential)
        self.assertEqual(claim.operation.operation_id, created.operation_id)
        self.assertEqual(claim.operation.operation_type, "probe_source")
        completed = complete_probe_operation(
            self.db,
            self.credential,
            created.operation_id,
            _probe_result(created.operation_id, "C:\\Controlled"),
        )
        self.assertEqual(completed.state, "completed")
        self.assertFalse(completed.idempotent_replay)

        replay = complete_probe_operation(
            self.db,
            self.credential,
            created.operation_id,
            _probe_result(created.operation_id, "C:\\Controlled"),
        )
        self.assertTrue(replay.idempotent_replay)

        changed = _probe_result(created.operation_id, "C:\\Controlled")
        changed.warnings.append(
            MachineIssue(code="probe_failed", evidence_code="synthetic_warning")
        )
        with self.assertRaises(WindowsHelperServiceError):
            complete_probe_operation(
                self.db,
                self.credential,
                created.operation_id,
                changed,
            )

    def test_wrong_helper_cannot_claim_and_expired_operation_fails_safe(self) -> None:
        created = self._operation()
        other_node = AccessNode(
            access_node_uuid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            label="Other Helper",
            os_family="windows",
            provider_name="windows_helper_v1",
            provider_version="1",
            status="active",
        )
        self.db.add(other_node)
        self.db.flush()
        from app.models.windows_helper import WindowsHelperCredential

        other_credential = WindowsHelperCredential(
            public_id="c_" + "a" * 32,
            access_node_id=other_node.id,
            credential_version=1,
            token_digest="0" * 64,
            status="active",
        )
        self.db.add(other_credential)
        self.db.commit()
        self.assertIsNone(claim_operation(self.db, other_credential).operation)

        operation = self.db.scalar(
            select(WindowsHelperOperation).where(
                WindowsHelperOperation.operation_uuid == str(created.operation_id)
            )
        )
        operation.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        self.db.commit()
        self.assertIsNone(claim_operation(self.db, self.credential).operation)
        self.assertEqual(operation.state, "expired")

    def test_failure_requires_a_live_claim_lease(self) -> None:
        created = self._operation()
        failure = HelperOperationFailureRequest(error_code="operation_failed")
        with self.assertRaises(WindowsHelperServiceError):
            fail_operation(self.db, self.credential, created.operation_id, failure)

        claim_operation(self.db, self.credential)
        operation = self.db.scalar(
            select(WindowsHelperOperation).where(
                WindowsHelperOperation.operation_uuid == str(created.operation_id)
            )
        )
        operation.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        self.db.commit()
        with self.assertRaises(WindowsHelperServiceError):
            fail_operation(self.db, self.credential, created.operation_id, failure)
        self.assertEqual(operation.state, "expired")
        self.assertEqual(operation.error_code, "operation_expired")

    def test_unknown_operation_and_arbitrary_payload_fail_closed(self) -> None:
        with self.assertRaises(ValidationError):
            CreateWindowsHelperProbeOperationRequest.model_validate(
                {
                    "access_node_id": str(self.node_id),
                    "source_type": "local",
                    "provider_native_root": "C:\\Controlled",
                    "command": "dir C:\\",
                }
            )

        unknown = WindowsHelperOperation(
            operation_uuid="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            access_node_id=self.credential.access_node_id,
            operation_type="shell_command",
            request_json="{}",
            request_digest="sha256:" + "0" * 64,
            state="pending",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=1),
        )
        self.db.add(unknown)
        self.db.commit()
        with self.assertRaises(WindowsHelperServiceError):
            claim_operation(self.db, self.credential)
        self.assertEqual(unknown.state, "failed")
        self.assertEqual(unknown.error_code, "operation_unsupported")


if __name__ == "__main__":
    unittest.main()

