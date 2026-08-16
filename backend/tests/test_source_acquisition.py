from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import UUID, uuid4

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings as application_settings
from app.models.asset import Asset
from app.models.ingestion_run import IngestionRun
from app.models.ingestion_source import IngestionSource
from app.models.provenance import Provenance
from app.models.source_acquisition import SourceAcquisitionItem, SourceAcquisitionRun
from app.models.source_endpoint import AccessNode, SourceEndpoint, SourceEndpointObservedPath
from app.models.source_intake_run import SourceIntakeRun
from app.models.windows_helper import WindowsHelperCredential, WindowsHelperOperation
from app.schemas.source_acquisition import CreateSourceAcquisitionPlanRequest
from app.services.source_acquisition.receiving import (
    acquisition_status,
    cleanup_failed_partials,
    commit_chunk,
)
from app.services.source_acquisition.schema import ensure_source_acquisition_schema
from app.services.source_acquisition.service import (
    activate_run,
    create_planned_run,
    execute_acquisition_bridge,
    plan_acquisition_bridge,
)
from app.services.windows_helper.operations import (
    complete_acquire_operation,
    create_acquire_operation,
)
from app.services.windows_helper.schema import ensure_windows_helper_schema
from app.services.windows_helper.service import WindowsHelperServiceError
from app.windows_helper_shared.identity.models import (
    IdentityFingerprintCandidate,
    NormalizedIdentityEvidence,
    ProviderNativeRootEvidence,
)
from app.windows_helper_shared.protocol import (
    HelperAcquireItemRequest,
    HelperAcquireItemResponse,
    HelperInventoryItem,
    HelperInventoryPageRequest,
    HelperInventoryPageResponse,
    HelperProbeResponse,
    InventoryEntryKind,
    InventoryResultStatus,
    MAX_ACQUISITION_CHUNK_BYTES,
    ProbeResultStatus,
    ProviderNativePath,
    SourceFileEvidence,
    canonical_protocol_digest,
)


ROOT = "C:\\Controlled"
FINGERPRINT = "sha256:" + "a" * 64
FILE_ID = "sha256:" + "b" * 64
NODE_UUID = UUID("aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee")


def _digest(body: bytes) -> str:
    return "sha256:" + hashlib.sha256(body).hexdigest()


def _native_path(relative: str = "") -> ProviderNativePath:
    return ProviderNativePath(
        provider_native_root=ROOT,
        provider_native_relative_path=relative,
        provider_native_full_path=ROOT if not relative else ROOT + "\\" + relative,
    )


def _probe(request_id: UUID) -> HelperProbeResponse:
    return HelperProbeResponse(
        request_id=request_id,
        result_status=ProbeResultStatus.SUCCESS,
        source_type="local",
        provider_native_path=_native_path(),
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


class SourceAcquisitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.receiving_base = Path(self.temporary.name) / "acquisition"
        self.test_settings = replace(
            application_settings,
            acquisition_receiving_path=str(self.receiving_base),
            acquisition_disk_reserve_bytes=0,
            drop_zone_path=str(Path(self.temporary.name) / "drop-zone"),
            vault_path=str(Path(self.temporary.name) / "vault"),
            quarantine_path=str(Path(self.temporary.name) / "quarantine"),
            ingest_failures_path=str(Path(self.temporary.name) / "ingest-failures"),
        )
        self.settings_patches = [
            patch("app.services.source_acquisition.service.settings", self.test_settings),
            patch("app.services.source_acquisition.receiving.settings", self.test_settings),
        ]
        for active_patch in self.settings_patches:
            active_patch.start()

        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        AccessNode.__table__.create(self.engine)
        SourceEndpoint.__table__.create(self.engine)
        IngestionSource.__table__.create(self.engine)
        IngestionRun.__table__.create(self.engine)
        SourceIntakeRun.__table__.create(self.engine)
        Asset.__table__.create(self.engine)
        Provenance.__table__.create(self.engine)
        SourceEndpointObservedPath.__table__.create(self.engine)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.db = self.session_factory()
        for runtime_path in (
            self.test_settings.drop_zone_path,
            self.test_settings.vault_path,
            self.test_settings.quarantine_path,
            self.test_settings.ingest_failures_path,
        ):
            Path(runtime_path).mkdir(parents=True, exist_ok=True)
        ensure_windows_helper_schema(self.db)
        ensure_source_acquisition_schema(self.db)

        self.node = AccessNode(
            access_node_uuid=str(NODE_UUID),
            label="Controlled Windows Helper",
            os_family="windows",
            provider_name="windows_helper_v1",
            provider_version="1",
            capabilities_json=json.dumps(
                {
                    "protocol_version": 1,
                    "helper_version": "0.4.0",
                    "intended_access_node_id": str(NODE_UUID),
                    "os_platform": "windows",
                    "supported_source_types": ["local"],
                    "collectors": [
                        {
                            "name": "windows_non_admin_probe_v1",
                            "version": "1",
                            "supported_source_types": ["local"],
                        }
                    ],
                    "capabilities": [
                        {"name": "durable_acquisition", "version": "1"},
                        {"name": "verified_receiving", "version": "1"},
                    ],
                }
            ),
            status="active",
            last_seen_at=datetime.now(timezone.utc),
        )
        self.db.add(self.node)
        self.db.flush()
        self.endpoint = SourceEndpoint(
            source_type="local",
            alias="Controlled Windows Local",
            alias_normalized="controlled windows local",
            status="active",
            identity_fingerprint_hash=FINGERPRINT,
            identity_fingerprint_version="source_endpoint_volume_guid_v2",
            identity_confidence="strong_match",
            created_from_access_node_id=self.node.id,
        )
        self.db.add(self.endpoint)
        self.db.flush()
        self.profile = IngestionSource(
            source_label="Controlled Profile",
            source_label_normalized="controlled profile",
            source_type="local",
            source_root_path=ROOT,
            source_root_path_normalized=ROOT.casefold(),
            endpoint_relative_root="",
            profile_status="active",
            endpoint_id=self.endpoint.id,
        )
        self.db.add(self.profile)
        self.observed = SourceEndpointObservedPath(
            source_endpoint_id=self.endpoint.id,
            access_node_id=self.node.id,
            observed_path=ROOT,
            normalized_observed_path=ROOT.casefold(),
            filesystem_boundary_type="local_folder",
            source_root_candidate_path=ROOT,
            is_valid_source_root_candidate=True,
            probe_provider_name="windows_non_admin_probe_v1",
            probe_provider_version="1",
            probe_status="completed",
            confidence_tier="strong_match",
            match_status="match",
            safe_to_run="true",
        )
        self.credential = WindowsHelperCredential(
            public_id="c_" + "c" * 32,
            access_node_id=self.node.id,
            credential_version=1,
            token_digest="d" * 64,
            status="active",
        )
        self.db.add_all([self.observed, self.credential])
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()
        for active_patch in reversed(self.settings_patches):
            active_patch.stop()
        self.temporary.cleanup()

    def _inventory_operation(self, *, candidate_reference: str = "candidate_001") -> WindowsHelperOperation:
        operation_id = uuid4()
        generation = uuid4()
        request = HelperInventoryPageRequest(
            request_id=operation_id,
            intended_access_node_id=NODE_UUID,
            source_endpoint_id=self.endpoint.id,
            source_profile_id=self.profile.id,
            source_type="local",
            provider_native_path=_native_path(),
            expected_identity_fingerprint=FINGERPRINT,
            page_size=25,
        )
        response = HelperInventoryPageResponse(
            request_id=operation_id,
            result_status=InventoryResultStatus.SUCCESS,
            source_endpoint_id=self.endpoint.id,
            source_profile_id=self.profile.id,
            source_type="local",
            provider_native_path=_native_path(),
            inventory_generation=generation,
            identity_probe=_probe(operation_id),
            items=[
                HelperInventoryItem(
                    candidate_reference=candidate_reference,
                    provider_native_path=_native_path("family\\controlled.jpg"),
                    filename="controlled.jpg",
                    size_bytes=60 * 1024,
                    modified_time_ns=123456789,
                    entry_kind=InventoryEntryKind.REGULAR_FILE,
                    stable_file_id_digest=FILE_ID,
                    windows_file_attributes=0,
                    local_residency="resident",
                )
            ],
        )
        operation = WindowsHelperOperation(
            operation_uuid=str(operation_id),
            access_node_id=self.node.id,
            source_endpoint_id=self.endpoint.id,
            source_profile_id=self.profile.id,
            operation_type="inventory_page",
            request_json=request.model_dump_json(),
            request_digest=canonical_protocol_digest(request),
            state="completed",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            completed_at=datetime.now(timezone.utc),
            result_json=response.model_dump_json(),
            result_digest=canonical_protocol_digest(response),
        )
        self.db.add(operation)
        self.db.commit()
        return operation

    def test_planned_run_copies_exact_inventory_evidence_without_creating_content_paths(self) -> None:
        operation = self._inventory_operation()
        request = CreateSourceAcquisitionPlanRequest(
            idempotency_key=uuid4(),
            source_profile_id=self.profile.id,
            inventory_operation_ids=[UUID(operation.operation_uuid)],
            candidate_references=["candidate_001"],
        )
        response = create_planned_run(self.db, request)
        self.assertEqual(response.state, "planned")
        self.assertFalse(response.can_run_source_intake)
        self.assertEqual(response.selected_item_count, 1)
        self.assertEqual(response.expected_byte_count, 60 * 1024)
        self.assertFalse(Path(response.receiving_root).exists())
        item = response.items[0]
        self.assertEqual(item.provider_native_relative_path, "family\\controlled.jpg")
        self.assertEqual(item.local_residency, "resident")

        replay = create_planned_run(self.db, request)
        self.assertEqual(replay.acquisition_run_id, response.acquisition_run_id)
        with self.assertRaises(WindowsHelperServiceError):
            create_planned_run(
                self.db,
                request.model_copy(update={"candidate_references": ["candidate_substitution"]}),
            )

    def test_inventory_binding_and_duplicate_selection_fail_closed(self) -> None:
        operation = self._inventory_operation()
        request = CreateSourceAcquisitionPlanRequest(
            idempotency_key=uuid4(),
            source_profile_id=self.profile.id,
            inventory_operation_ids=[UUID(operation.operation_uuid)],
            candidate_references=["candidate_001", "candidate_001"],
        )
        with self.assertRaises(WindowsHelperServiceError):
            create_planned_run(self.db, request)

        operation.access_node_id = self.node.id + 100
        self.db.commit()
        with self.assertRaises(WindowsHelperServiceError):
            create_planned_run(
                self.db,
                request.model_copy(
                    update={
                        "idempotency_key": uuid4(),
                        "candidate_references": ["candidate_001"],
                    }
                ),
            )

    def test_pre_byte_approval_gate_blocks_operations_and_revalidates_identity(self) -> None:
        operation = self._inventory_operation()
        planned = create_planned_run(
            self.db,
            CreateSourceAcquisitionPlanRequest(
                idempotency_key=uuid4(),
                source_profile_id=self.profile.id,
                inventory_operation_ids=[UUID(operation.operation_uuid)],
                candidate_references=["candidate_001"],
            ),
        )
        item_id = planned.items[0].acquisition_item_id
        with self.assertRaises(WindowsHelperServiceError):
            create_acquire_operation(self.db, item_id)
        with self.assertRaises(WindowsHelperServiceError):
            activate_run(self.db, planned.acquisition_run_id, "sha256:" + "0" * 64)
        self.assertFalse(Path(planned.receiving_root).exists())

        self.endpoint.identity_fingerprint_hash = "sha256:" + "f" * 64
        self.db.commit()
        with self.assertRaises(WindowsHelperServiceError):
            activate_run(self.db, planned.acquisition_run_id, planned.proposal_digest)
        self.assertFalse(Path(planned.receiving_root).exists())

        self.endpoint.identity_fingerprint_hash = FINGERPRINT
        self.db.commit()
        active = activate_run(self.db, planned.acquisition_run_id, planned.proposal_digest)
        self.assertEqual(active.state, "active")
        self.assertTrue((Path(active.receiving_root) / "partial").is_dir())
        self.assertTrue((Path(active.receiving_root) / "ready").is_dir())
        self.assertEqual(list((Path(active.receiving_root) / "partial").iterdir()), [])

    def _active_item(self, content: bytes) -> tuple[SourceAcquisitionRun, SourceAcquisitionItem, WindowsHelperOperation]:
        self.receiving_base.mkdir(parents=True, mode=0o700, exist_ok=True)
        run_uuid = uuid4()
        item_uuid = uuid4()
        run_root = self.receiving_base / str(run_uuid)
        (run_root / "partial").mkdir(parents=True, mode=0o700)
        (run_root / "ready").mkdir(mode=0o700)
        run = SourceAcquisitionRun(
            run_uuid=str(run_uuid),
            idempotency_key=str(uuid4()),
            provider="windows_helper",
            access_node_id=self.node.id,
            source_endpoint_id=self.endpoint.id,
            source_profile_id=self.profile.id,
            inventory_generation=str(uuid4()),
            inventory_chain_digest="sha256:" + "1" * 64,
            proposal_digest=_digest(str(run_uuid).encode("ascii")),
            source_fingerprint=FINGERPRINT,
            provider_native_root=ROOT,
            receiving_root=str(run_root),
            state="active",
            selected_item_count=1,
            expected_byte_count=len(content),
            committed_byte_count=0,
            ready_item_count=0,
            failed_item_count=0,
            disk_free_bytes_at_plan=10**12,
            disk_reserve_bytes=0,
            activated_at=datetime.now(timezone.utc),
        )
        self.db.add(run)
        self.db.flush()
        item = SourceAcquisitionItem(
            item_uuid=str(item_uuid),
            run_id=run.id,
            ordinal=1,
            candidate_reference="candidate_receive",
            inventory_generation=run.inventory_generation,
            provider_native_root=ROOT,
            provider_native_relative_path="family\\controlled.jpg",
            provider_native_relative_path_normalized="family\\controlled.jpg",
            provider_native_relative_path_normalized_digest="sha256:" + "3" * 64,
            provider_native_full_path=ROOT + "\\family\\controlled.jpg",
            filename="controlled.jpg",
            safe_extension=".jpg",
            expected_size_bytes=len(content),
            expected_modified_time_ns=123456789,
            expected_file_id_digest=FILE_ID,
            source_fingerprint=FINGERPRINT,
            windows_file_attributes=0,
            local_residency="resident",
            eligibility_reason="current_linux_media_policy",
            state="transferring",
            partial_relative_path=f"partial/{item_uuid}.part",
            ready_relative_path=f"ready/{item_uuid}.jpg",
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(item)
        self.db.flush()
        operation_id = uuid4()
        request = HelperAcquireItemRequest(
            request_id=operation_id,
            intended_access_node_id=NODE_UUID,
            acquisition_run_id=run_uuid,
            acquisition_item_id=item_uuid,
            source_endpoint_id=self.endpoint.id,
            source_profile_id=self.profile.id,
            source_type="local",
            provider_native_path=_native_path("family\\controlled.jpg"),
            inventory_generation=UUID(run.inventory_generation),
            candidate_reference=item.candidate_reference,
            expected_identity_fingerprint=FINGERPRINT,
            expected_size_bytes=len(content),
            expected_modified_time_ns=item.expected_modified_time_ns,
            expected_file_id_digest=FILE_ID,
        )
        operation = WindowsHelperOperation(
            operation_uuid=str(operation_id),
            access_node_id=self.node.id,
            source_endpoint_id=self.endpoint.id,
            source_profile_id=self.profile.id,
            operation_type="acquire_item",
            request_json=request.model_dump_json(),
            request_digest=canonical_protocol_digest(request),
            state="claimed",
            attempt_count=1,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            claimed_at=datetime.now(timezone.utc),
            lease_expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        self.db.add(operation)
        self.db.commit()
        return run, item, operation

    def _result(
        self,
        run: SourceAcquisitionRun,
        item: SourceAcquisitionItem,
        operation: WindowsHelperOperation,
        content: bytes,
        *,
        helper_digest: str | None = None,
        modified_time_ns: int | None = None,
        bytes_read: int | None = None,
    ) -> HelperAcquireItemResponse:
        evidence = SourceFileEvidence(
            size_bytes=item.expected_size_bytes,
            modified_time_ns=modified_time_ns or item.expected_modified_time_ns,
            stable_file_id_digest=item.expected_file_id_digest,
            windows_file_attributes=0,
            local_residency="resident",
        )
        return HelperAcquireItemResponse(
            request_id=UUID(operation.operation_uuid),
            result_status="success",
            acquisition_run_id=UUID(run.run_uuid),
            acquisition_item_id=UUID(item.item_uuid),
            source_endpoint_id=self.endpoint.id,
            source_profile_id=self.profile.id,
            source_type="local",
            provider_native_path=_native_path("family\\controlled.jpg"),
            pre_read_evidence=evidence,
            post_read_evidence=evidence,
            bytes_read=item.expected_size_bytes if bytes_read is None else bytes_read,
            helper_source_sha256=helper_digest or _digest(content),
        )

    def test_chunk_integrity_offset_bounds_resume_and_idempotency(self) -> None:
        content = b"abcdefghijk"
        run, item, operation = self._active_item(content)
        with self.assertRaises(WindowsHelperServiceError):
            commit_chunk(
                self.db,
                self.credential,
                UUID(operation.operation_uuid),
                UUID(run.run_uuid),
                UUID(item.item_uuid),
                offset=0,
                supplied_digest=_digest(b"wrong"),
                body=content[:4],
            )
        self.assertEqual(item.committed_offset, 0)
        partial = Path(run.receiving_root) / item.partial_relative_path
        self.assertFalse(partial.exists())

        first = content[:4]
        committed = commit_chunk(
            self.db,
            self.credential,
            UUID(operation.operation_uuid),
            UUID(run.run_uuid),
            UUID(item.item_uuid),
            offset=0,
            supplied_digest=_digest(first),
            body=first,
        )
        self.assertEqual(committed.committed_offset, 4)
        self.assertEqual(acquisition_status(
            self.db, self.credential, UUID(operation.operation_uuid), UUID(run.run_uuid), UUID(item.item_uuid)
        ).committed_offset, 4)

        replay = commit_chunk(
            self.db,
            self.credential,
            UUID(operation.operation_uuid),
            UUID(run.run_uuid),
            UUID(item.item_uuid),
            offset=0,
            supplied_digest=_digest(first),
            body=first,
        )
        self.assertTrue(replay.idempotent_replay)
        with self.assertRaises(WindowsHelperServiceError):
            commit_chunk(
                self.db,
                self.credential,
                UUID(operation.operation_uuid),
                UUID(run.run_uuid),
                UUID(item.item_uuid),
                offset=0,
                supplied_digest=_digest(b"WXYZ"),
                body=b"WXYZ",
            )
        with self.assertRaises(WindowsHelperServiceError):
            commit_chunk(
                self.db,
                self.credential,
                UUID(operation.operation_uuid),
                UUID(run.run_uuid),
                UUID(item.item_uuid),
                offset=2,
                supplied_digest=_digest(content[2:6]),
                body=content[2:6],
            )
        with self.assertRaises(WindowsHelperServiceError):
            commit_chunk(
                self.db,
                self.credential,
                UUID(operation.operation_uuid),
                UUID(run.run_uuid),
                UUID(item.item_uuid),
                offset=6,
                supplied_digest=_digest(content[6:8]),
                body=content[6:8],
            )

    def test_chunk_maximum_wrong_binding_and_filesystem_ahead_reconcile(self) -> None:
        content = b"abcdefghijk"
        run, item, operation = self._active_item(content)
        with self.assertRaises(WindowsHelperServiceError):
            commit_chunk(
                self.db,
                self.credential,
                UUID(operation.operation_uuid),
                uuid4(),
                UUID(item.item_uuid),
                offset=0,
                supplied_digest=_digest(b"a"),
                body=b"a",
            )
        oversized = b"x" * (MAX_ACQUISITION_CHUNK_BYTES + 1)
        with self.assertRaises(WindowsHelperServiceError):
            commit_chunk(
                self.db,
                self.credential,
                UUID(operation.operation_uuid),
                UUID(run.run_uuid),
                UUID(item.item_uuid),
                offset=0,
                supplied_digest=_digest(oversized),
                body=oversized,
            )
        with self.assertRaises(WindowsHelperServiceError):
            commit_chunk(
                self.db,
                self.credential,
                UUID(operation.operation_uuid),
                UUID(run.run_uuid),
                UUID(item.item_uuid),
                offset=8,
                supplied_digest=_digest(b"more"),
                body=b"more",
            )

        first, second = content[:4], content[4:8]
        commit_chunk(
            self.db,
            self.credential,
            UUID(operation.operation_uuid),
            UUID(run.run_uuid),
            UUID(item.item_uuid),
            offset=0,
            supplied_digest=_digest(first),
            body=first,
        )
        partial = Path(run.receiving_root) / item.partial_relative_path
        with partial.open("ab", buffering=0) as receiving:
            receiving.write(second)
            os.fsync(receiving.fileno())
        recovered = commit_chunk(
            self.db,
            self.credential,
            UUID(operation.operation_uuid),
            UUID(run.run_uuid),
            UUID(item.item_uuid),
            offset=4,
            supplied_digest=_digest(second),
            body=second,
        )
        self.assertEqual(recovered.committed_offset, 8)
        self.assertEqual(item.committed_offset, 8)

    def test_successful_finalize_is_atomic_verified_and_idempotent(self) -> None:
        content = b"verified-content"
        run, item, operation = self._active_item(content)
        commit_chunk(
            self.db,
            self.credential,
            UUID(operation.operation_uuid),
            UUID(run.run_uuid),
            UUID(item.item_uuid),
            offset=0,
            supplied_digest=_digest(content),
            body=content,
        )
        result = self._result(run, item, operation, content)
        completed = complete_acquire_operation(
            self.db, self.credential, UUID(operation.operation_uuid), result
        )
        self.assertFalse(completed.idempotent_replay)
        self.assertEqual(item.state, "ready")
        self.assertEqual(run.state, "completed")
        partial = Path(run.receiving_root) / item.partial_relative_path
        ready = Path(run.receiving_root) / item.ready_relative_path
        self.assertFalse(partial.exists())
        self.assertEqual(ready.read_bytes(), content)
        self.assertNotIn(item.filename, str(ready))
        self.assertEqual(item.linux_verified_sha256, _digest(content))
        self.assertEqual(os.stat(ready).st_mode & 0o777, 0o600)

        ready_replay = commit_chunk(
            self.db,
            self.credential,
            UUID(operation.operation_uuid),
            UUID(run.run_uuid),
            UUID(item.item_uuid),
            offset=0,
            supplied_digest=_digest(content),
            body=content,
        )
        self.assertTrue(ready_replay.idempotent_replay)
        self.assertEqual(ready_replay.bytes_committed, 0)

        replay = complete_acquire_operation(
            self.db, self.credential, UUID(operation.operation_uuid), result
        )
        self.assertTrue(replay.idempotent_replay)
        ready.unlink()
        with self.assertRaises(WindowsHelperServiceError):
            complete_acquire_operation(
                self.db, self.credential, UUID(operation.operation_uuid), result
            )

    def test_mismatched_final_hash_mutation_and_conflicting_ready_never_publish(self) -> None:
        content = b"verified-content"
        run, item, operation = self._active_item(content)
        commit_chunk(
            self.db,
            self.credential,
            UUID(operation.operation_uuid),
            UUID(run.run_uuid),
            UUID(item.item_uuid),
            offset=0,
            supplied_digest=_digest(content),
            body=content,
        )
        with self.assertRaises(WindowsHelperServiceError):
            complete_acquire_operation(
                self.db,
                self.credential,
                UUID(operation.operation_uuid),
                self._result(run, item, operation, content, helper_digest=_digest(b"different")),
            )
        self.assertEqual(item.state, "failed")
        self.assertFalse((Path(run.receiving_root) / item.ready_relative_path).exists())

        run, item, operation = self._active_item(content)
        commit_chunk(
            self.db,
            self.credential,
            UUID(operation.operation_uuid),
            UUID(run.run_uuid),
            UUID(item.item_uuid),
            offset=0,
            supplied_digest=_digest(content),
            body=content,
        )
        with self.assertRaises(WindowsHelperServiceError):
            complete_acquire_operation(
                self.db,
                self.credential,
                UUID(operation.operation_uuid),
                self._result(run, item, operation, content, modified_time_ns=item.expected_modified_time_ns + 1),
            )
        self.assertEqual(item.state, "failed")

        run, item, operation = self._active_item(content)
        commit_chunk(
            self.db,
            self.credential,
            UUID(operation.operation_uuid),
            UUID(run.run_uuid),
            UUID(item.item_uuid),
            offset=0,
            supplied_digest=_digest(content),
            body=content,
        )
        ready = Path(run.receiving_root) / item.ready_relative_path
        ready.write_bytes(b"conflict")
        with self.assertRaises(WindowsHelperServiceError):
            complete_acquire_operation(
                self.db,
                self.credential,
                UUID(operation.operation_uuid),
                self._result(run, item, operation, content),
            )
        self.assertEqual(item.state, "verifying")
        self.assertEqual(ready.read_bytes(), b"conflict")

    def test_expired_operation_replacement_preserves_item_and_offset(self) -> None:
        content = b"resume-content"
        run, item, operation = self._active_item(content)
        first = content[:4]
        commit_chunk(
            self.db,
            self.credential,
            UUID(operation.operation_uuid),
            UUID(run.run_uuid),
            UUID(item.item_uuid),
            offset=0,
            supplied_digest=_digest(first),
            body=first,
        )
        operation.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        self.db.commit()
        with self.assertRaises(WindowsHelperServiceError):
            acquisition_status(
                self.db, self.credential, UUID(operation.operation_uuid), UUID(run.run_uuid), UUID(item.item_uuid)
            )
        replacement = create_acquire_operation(self.db, UUID(item.item_uuid))
        self.assertNotEqual(replacement.operation_id, UUID(operation.operation_uuid))
        self.assertEqual(operation.state, "expired")
        self.assertEqual(item.committed_offset, len(first))
        self.assertEqual(item.state, "transferring")

    def test_receiving_path_substitution_and_active_cleanup_fail_closed(self) -> None:
        content = b"safe-content"
        run, item, operation = self._active_item(content)
        original_root = run.receiving_root
        run.receiving_root = str(Path(self.temporary.name) / "outside")
        self.db.commit()
        with self.assertRaises(WindowsHelperServiceError):
            commit_chunk(
                self.db,
                self.credential,
                UUID(operation.operation_uuid),
                UUID(run.run_uuid),
                UUID(item.item_uuid),
                offset=0,
                supplied_digest=_digest(content),
                body=content,
            )
        run.receiving_root = original_root
        run.state = "failed"
        self.db.commit()
        with self.assertRaises(WindowsHelperServiceError):
            cleanup_failed_partials(self.db, UUID(run.run_uuid))

    def test_guarded_cleanup_removes_only_failed_partial_and_preserves_ready(self) -> None:
        content = b"ready-content"
        run, item, operation = self._active_item(content)
        commit_chunk(
            self.db,
            self.credential,
            UUID(operation.operation_uuid),
            UUID(run.run_uuid),
            UUID(item.item_uuid),
            offset=0,
            supplied_digest=_digest(content),
            body=content,
        )
        complete_acquire_operation(
            self.db,
            self.credential,
            UUID(operation.operation_uuid),
            self._result(run, item, operation, content),
        )
        second_uuid = uuid4()
        second = SourceAcquisitionItem(
            item_uuid=str(second_uuid),
            run_id=run.id,
            ordinal=2,
            candidate_reference="candidate_failed",
            inventory_generation=run.inventory_generation,
            provider_native_root=ROOT,
            provider_native_relative_path="family\\failed.jpg",
            provider_native_relative_path_normalized="family\\failed.jpg",
            provider_native_relative_path_normalized_digest="sha256:" + "4" * 64,
            provider_native_full_path=ROOT + "\\family\\failed.jpg",
            filename="failed.jpg",
            safe_extension=".jpg",
            expected_size_bytes=4,
            expected_modified_time_ns=1,
            expected_file_id_digest=None,
            source_fingerprint=FINGERPRINT,
            windows_file_attributes=0,
            local_residency="resident",
            eligibility_reason="current_linux_media_policy",
            state="failed",
            partial_relative_path=f"partial/{second_uuid}.part",
            ready_relative_path=f"ready/{second_uuid}.jpg",
            failure_code="synthetic_failure",
        )
        run.state = "failed"
        run.selected_item_count = 2
        run.failed_item_count = 1
        self.db.add_all([run, second])
        self.db.commit()
        failed_partial = Path(run.receiving_root) / second.partial_relative_path
        failed_partial.write_bytes(b"part")
        ready = Path(run.receiving_root) / item.ready_relative_path
        removed, preserved = cleanup_failed_partials(self.db, UUID(run.run_uuid))
        self.assertEqual((removed, preserved), (1, 1))
        self.assertFalse(failed_partial.exists())
        self.assertEqual(ready.read_bytes(), content)


    def _completed_bridge_run(self) -> tuple[SourceAcquisitionRun, list[SourceAcquisitionItem], list[bytes]]:
        self.receiving_base.mkdir(parents=True, mode=0o700, exist_ok=True)
        run_uuid = uuid4()
        run_root = self.receiving_base / str(run_uuid)
        (run_root / "partial").mkdir(parents=True, mode=0o700)
        (run_root / "ready").mkdir(mode=0o700)
        contents = [b"unique-a", b"duplicate-b", b"duplicate-b", b"duplicate-c", b"duplicate-c"]
        names = ["IMG_1.JPG", "IMG_2 (1).JPG", "IMG_2.JPG", "IMG_3 (1).JPG", "IMG_3.JPG"]
        run = SourceAcquisitionRun(
            run_uuid=str(run_uuid),
            idempotency_key=str(uuid4()),
            provider="windows_helper",
            access_node_id=self.node.id,
            source_endpoint_id=self.endpoint.id,
            source_profile_id=self.profile.id,
            inventory_generation=str(uuid4()),
            inventory_chain_digest="sha256:" + "1" * 64,
            proposal_digest=_digest(str(run_uuid).encode()),
            source_fingerprint=FINGERPRINT,
            provider_native_root=ROOT,
            receiving_root=str(run_root),
            state="completed",
            selected_item_count=5,
            expected_byte_count=sum(len(content) for content in contents),
            committed_byte_count=sum(len(content) for content in contents),
            ready_item_count=5,
            failed_item_count=0,
            disk_free_bytes_at_plan=10**12,
            disk_reserve_bytes=0,
            completed_at=datetime.now(timezone.utc),
        )
        self.db.add(run)
        self.db.flush()
        items: list[SourceAcquisitionItem] = []
        for ordinal, (content, name) in enumerate(zip(contents, names, strict=True), start=1):
            item_uuid = uuid4()
            digest = _digest(content)
            item = SourceAcquisitionItem(
                item_uuid=str(item_uuid),
                run_id=run.id,
                ordinal=ordinal,
                candidate_reference=f"candidate_{ordinal}",
                inventory_generation=run.inventory_generation,
                provider_native_root=ROOT,
                provider_native_relative_path=name,
                provider_native_relative_path_normalized=name.casefold(),
                provider_native_relative_path_normalized_digest=_digest(name.casefold().encode()),
                provider_native_full_path=ROOT + "\\" + name,
                filename=name,
                safe_extension=".jpg",
                expected_size_bytes=len(content),
                expected_modified_time_ns=ordinal,
                expected_file_id_digest=None,
                source_fingerprint=FINGERPRINT,
                windows_file_attributes=0,
                local_residency="resident",
                eligibility_reason="current_linux_media_policy",
                state="ready",
                committed_offset=len(content),
                verified_byte_count=len(content),
                helper_source_sha256=digest,
                linux_verified_sha256=digest,
                partial_relative_path=f"partial/{item_uuid}.part",
                ready_relative_path=f"ready/{item_uuid}.jpg",
                completed_at=datetime.now(timezone.utc),
            )
            ready = run_root / item.ready_relative_path
            ready.write_bytes(content)
            ready.chmod(0o600)
            self.db.add(item)
            items.append(item)
        self.db.commit()
        return run, items, contents

    def _establish_completed_bridge_links(
        self,
        run: SourceAcquisitionRun,
        items: list[SourceAcquisitionItem],
    ) -> None:
        ready_root = (Path(run.receiving_root) / "ready").resolve()
        ingestion = IngestionRun(
            ingestion_source_id=run.source_profile_id,
            from_path=str(ready_root),
        )
        self.db.add(ingestion)
        self.db.flush()
        intake = SourceIntakeRun(
            status="completed",
            ingestion_source_id=run.source_profile_id,
            ingestion_run_id=ingestion.id,
            source_label=self.profile.source_label,
            source_type=self.profile.source_type,
            source_root_path=str(ready_root),
            intake_mode="acquisition_bridge",
            source_intake_limit=len(items),
            ingest_batch_size=len(items),
            files_scanned=len(items),
            selected=len(items),
            staged=len(items),
            failed_or_rejected=0,
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            created_by="source_acquisition_bridge",
        )
        self.db.add(intake)
        self.db.flush()
        for item in items:
            ready_path = (ready_root / Path(item.ready_relative_path).name).resolve()
            sha256 = item.linux_verified_sha256.removeprefix("sha256:")
            asset = self.db.get(Asset, sha256)
            if asset is None:
                vault = Path(self.test_settings.vault_path) / sha256[:2] / f"{sha256}.jpg"
                vault.parent.mkdir(parents=True, exist_ok=True)
                vault.write_bytes(ready_path.read_bytes())
                asset = Asset(
                    sha256=sha256,
                    vault_path=str(vault),
                    original_filename=item.filename,
                    original_source_path=item.provider_native_full_path,
                    extension=item.safe_extension,
                    size_bytes=item.expected_size_bytes,
                    modified_timestamp_utc=datetime.now(timezone.utc),
                )
                self.db.add(asset)
                self.db.flush()
            provenance = Provenance(
                asset_sha256=sha256,
                source_path=str(ready_path),
                ingestion_source_id=run.source_profile_id,
                ingestion_run_id=ingestion.id,
                source_label=self.profile.source_label,
                source_type=self.profile.source_type,
                source_root_path=str(ready_root),
                source_relative_path=ready_path.name,
            )
            self.db.add(provenance)
            self.db.flush()
            item.bridged_asset_sha256 = sha256
            item.bridged_provenance_id = provenance.id
        run.bridge_state = "completed"
        run.bridge_source_intake_run_id = intake.id
        run.bridge_ingestion_run_id = ingestion.id
        run.bridge_started_at = datetime.now(timezone.utc)
        run.bridge_completed_at = datetime.now(timezone.utc)
        self.db.commit()

    def test_bridge_plan_reverifies_exact_ready_set_and_predicts_three_content_results(self) -> None:
        run, items, _ = self._completed_bridge_run()
        plan = plan_acquisition_bridge(self.db, UUID(run.run_uuid))
        self.assertEqual(plan.bridge_state, "not_started")
        self.assertEqual(plan.item_count, 5)
        self.assertEqual(plan.unique_content_count, 3)
        self.assertEqual(plan.expected_asset_delta, 3)
        self.assertEqual(plan.expected_vault_delta, 3)
        self.assertEqual(plan.expected_provenance_delta, 5)
        self.assertEqual([item.ordinal for item in plan.items], [1, 2, 3, 4, 5])
        self.assertEqual({item.classification for item in plan.classifications}, {"new_content"})
        self.assertTrue(all(item.runtime_relative_path.endswith(".jpg") for item in plan.items))

        known_content = Path(run.receiving_root, items[0].ready_relative_path).read_bytes()
        known_sha256 = hashlib.sha256(known_content).hexdigest()
        known_vault = (
            Path(self.test_settings.vault_path) / known_sha256[:2] / f"{known_sha256}.jpg"
        )
        known_vault.parent.mkdir(parents=True, exist_ok=True)
        known_vault.write_bytes(known_content)
        self.db.add(
            Asset(
                sha256=known_sha256,
                vault_path=str(known_vault),
                original_filename="existing.jpg",
                original_source_path="existing/original.jpg",
                extension=".jpg",
                size_bytes=len(known_content),
                modified_timestamp_utc=datetime.now(timezone.utc),
            )
        )
        self.db.commit()
        exact_known_plan = plan_acquisition_bridge(self.db, UUID(run.run_uuid))
        self.assertEqual(exact_known_plan.expected_asset_delta, 2)
        self.assertEqual(exact_known_plan.expected_vault_delta, 2)
        self.assertEqual(
            [item.classification for item in exact_known_plan.classifications].count(
                "exact_known"
            ),
            1,
        )

        ready = Path(run.receiving_root) / items[0].ready_relative_path
        original = ready.read_bytes()
        ready.unlink()
        ready.symlink_to(Path(run.receiving_root) / items[1].ready_relative_path)
        with self.assertRaises(WindowsHelperServiceError):
            plan_acquisition_bridge(self.db, UUID(run.run_uuid))
        ready.unlink()
        ready.write_bytes(original)
        ready.chmod(0o600)

        ready.write_bytes(b"changed!")
        with self.assertRaises(WindowsHelperServiceError):
            plan_acquisition_bridge(self.db, UUID(run.run_uuid))

    def test_bridge_execute_links_five_items_and_repeat_is_zero_delta(self) -> None:
        run, items, _ = self._completed_bridge_run()
        plan = plan_acquisition_bridge(self.db, UUID(run.run_uuid))

        def fake_start(db_session, **kwargs):
            root = Path(kwargs["runtime_source_root_path"]).resolve()
            self.assertEqual(
                [record.explicit_order for record in kwargs["explicit_source_records"]],
                [1, 2, 3, 4, 5],
            )
            ingestion = IngestionRun(
                ingestion_source_id=kwargs["ingestion_source_id"], from_path=str(root)
            )
            db_session.add(ingestion)
            db_session.flush()
            intake = SourceIntakeRun(
                status="running",
                ingestion_source_id=kwargs["ingestion_source_id"],
                ingestion_run_id=None,
                source_label=self.profile.source_label,
                source_type=self.profile.source_type,
                source_root_path=str(root),
                intake_mode="acquisition_bridge",
                source_intake_limit=5,
                ingest_batch_size=5,
                started_at=datetime.now(timezone.utc),
                created_by="source_acquisition_bridge",
            )
            db_session.add(intake)
            db_session.commit()
            kwargs["on_created"](intake.id)

            first_by_hash: dict[str, str] = {}
            for record in kwargs["explicit_source_records"]:
                digest = hashlib.sha256(Path(record.full_path).read_bytes()).hexdigest()
                asset = db_session.get(Asset, digest)
                if asset is None:
                    first_by_hash[digest] = record.asset_original_source_path or ""
                    vault = Path(self.test_settings.vault_path) / digest[:2] / f"{digest}.jpg"
                    vault.parent.mkdir(parents=True, exist_ok=True)
                    vault.write_bytes(Path(record.full_path).read_bytes())
                    asset = Asset(
                        sha256=digest,
                        vault_path=str(vault),
                        original_filename=record.original_filename,
                        original_source_path=first_by_hash[digest],
                        extension=record.extension,
                        size_bytes=record.size_bytes,
                        modified_timestamp_utc=datetime.now(timezone.utc),
                    )
                    db_session.add(asset)
                    db_session.flush()
                db_session.add(
                    Provenance(
                        asset_sha256=digest,
                        source_path=record.original_source_path,
                        ingestion_source_id=kwargs["ingestion_source_id"],
                        ingestion_run_id=ingestion.id,
                        source_label=self.profile.source_label,
                        source_type=self.profile.source_type,
                        source_root_path=str(root),
                        source_relative_path=Path(record.original_source_path).name,
                    )
                )
            db_session.flush()
            intake.status = "completed"
            intake.ingestion_run_id = ingestion.id
            intake.files_scanned = 5
            intake.selected = 5
            intake.staged = 5
            intake.finished_at = datetime.now(timezone.utc)
            db_session.commit()
            kwargs["on_finished"](intake.id)

        with (
            patch("app.services.source_acquisition.service.SessionLocal", self.session_factory),
            patch(
                "app.services.source_acquisition.service.start_explicit_source_intake",
                side_effect=fake_start,
            ) as start,
        ):
            completed = execute_acquisition_bridge(
                self.db, UUID(run.run_uuid), plan.bridge_plan_digest
            )
            self.assertEqual(completed.bridge_state, "completed")
            self.assertEqual(start.call_count, 1)
            before = (
                self.db.scalar(select(func.count(SourceIntakeRun.id))),
                self.db.scalar(select(func.count(IngestionRun.id))),
                self.db.scalar(select(func.count(Asset.sha256))),
                self.db.scalar(select(func.count(Provenance.id))),
            )
            repeated = execute_acquisition_bridge(
                self.db, UUID(run.run_uuid), plan.bridge_plan_digest
            )
            after = (
                self.db.scalar(select(func.count(SourceIntakeRun.id))),
                self.db.scalar(select(func.count(IngestionRun.id))),
                self.db.scalar(select(func.count(Asset.sha256))),
                self.db.scalar(select(func.count(Provenance.id))),
            )
        self.assertEqual(repeated.bridge_state, "completed")
        self.assertEqual(start.call_count, 1)
        self.assertEqual(before, after)
        self.assertEqual(before, (1, 1, 3, 5))
        self.db.expire_all()
        linked_items = list(
            self.db.scalars(
                select(SourceAcquisitionItem)
                .where(SourceAcquisitionItem.run_id == run.id)
                .order_by(SourceAcquisitionItem.ordinal)
            )
        )
        self.assertTrue(all(item.bridged_asset_sha256 for item in linked_items))
        self.assertEqual(len({item.bridged_provenance_id for item in linked_items}), 5)
        self.assertEqual(linked_items[1].bridged_asset_sha256, linked_items[2].bridged_asset_sha256)
        self.assertEqual(linked_items[3].bridged_asset_sha256, linked_items[4].bridged_asset_sha256)


    def test_cross_acquisition_unchanged_observations_reuse_without_common_intake(self) -> None:
        prior_run, prior_items, _ = self._completed_bridge_run()
        self._establish_completed_bridge_links(prior_run, prior_items)
        repeat_run, repeat_items, _ = self._completed_bridge_run()

        plan = plan_acquisition_bridge(self.db, UUID(repeat_run.run_uuid))
        self.assertEqual(plan.expected_asset_delta, 0)
        self.assertEqual(plan.expected_vault_delta, 0)
        self.assertEqual(plan.expected_provenance_delta, 0)
        self.assertTrue(
            all(item.observation_classification == "reuse_prior_observation" for item in plan.items)
        )
        before = (
            self.db.scalar(select(func.count(SourceIntakeRun.id))),
            self.db.scalar(select(func.count(IngestionRun.id))),
            self.db.scalar(select(func.count(Asset.sha256))),
            self.db.scalar(select(func.count(Provenance.id))),
        )
        with patch(
            "app.services.source_acquisition.service.start_explicit_source_intake",
            side_effect=AssertionError("Fully reused bridge must not start common intake."),
        ) as start:
            completed = execute_acquisition_bridge(
                self.db, UUID(repeat_run.run_uuid), plan.bridge_plan_digest
            )
        after = (
            self.db.scalar(select(func.count(SourceIntakeRun.id))),
            self.db.scalar(select(func.count(IngestionRun.id))),
            self.db.scalar(select(func.count(Asset.sha256))),
            self.db.scalar(select(func.count(Provenance.id))),
        )
        self.assertEqual(completed.bridge_state, "completed")
        self.assertEqual(before, after)
        start.assert_not_called()
        self.db.expire_all()
        refreshed_run = self.db.get(SourceAcquisitionRun, repeat_run.id)
        refreshed_items = list(
            self.db.scalars(
                select(SourceAcquisitionItem)
                .where(SourceAcquisitionItem.run_id == repeat_run.id)
                .order_by(SourceAcquisitionItem.ordinal)
            )
        )
        self.assertIsNone(refreshed_run.bridge_source_intake_run_id)
        self.assertIsNone(refreshed_run.bridge_ingestion_run_id)
        self.assertEqual(
            [(item.bridged_asset_sha256, item.bridged_provenance_id) for item in refreshed_items],
            [(item.bridged_asset_sha256, item.bridged_provenance_id) for item in prior_items],
        )

    def test_cross_acquisition_same_hash_different_path_requires_new_provenance(self) -> None:
        prior_run, prior_items, _ = self._completed_bridge_run()
        self._establish_completed_bridge_links(prior_run, prior_items)
        repeat_run, repeat_items, _ = self._completed_bridge_run()
        changed = repeat_items[0]
        changed.provider_native_relative_path = "different\\IMG_1.JPG"
        changed.provider_native_relative_path_normalized = "different\\img_1.jpg"
        changed.provider_native_relative_path_normalized_digest = _digest(
            changed.provider_native_relative_path_normalized.encode()
        )
        changed.provider_native_full_path = ROOT + "\\different\\IMG_1.JPG"
        self.db.commit()

        plan = plan_acquisition_bridge(self.db, UUID(repeat_run.run_uuid))
        self.assertEqual(plan.expected_asset_delta, 0)
        self.assertEqual(plan.expected_provenance_delta, 1)
        self.assertEqual(plan.items[0].observation_classification, "common_intake")
        self.assertTrue(
            all(
                item.observation_classification == "reuse_prior_observation"
                for item in plan.items[1:]
            )
        )

    def test_cross_acquisition_mixed_run_sends_only_unmatched_item_to_common_intake(self) -> None:
        prior_run, prior_items, _ = self._completed_bridge_run()
        self._establish_completed_bridge_links(prior_run, prior_items)
        repeat_run, repeat_items, _ = self._completed_bridge_run()
        changed = repeat_items[0]
        changed.provider_native_relative_path = "different\\IMG_1.JPG"
        changed.provider_native_relative_path_normalized = "different\\img_1.jpg"
        changed.provider_native_relative_path_normalized_digest = _digest(
            changed.provider_native_relative_path_normalized.encode()
        )
        changed.provider_native_full_path = ROOT + "\\different\\IMG_1.JPG"
        self.db.commit()
        plan = plan_acquisition_bridge(self.db, UUID(repeat_run.run_uuid))
        before = (
            self.db.scalar(select(func.count(SourceIntakeRun.id))),
            self.db.scalar(select(func.count(IngestionRun.id))),
            self.db.scalar(select(func.count(Asset.sha256))),
            self.db.scalar(select(func.count(Provenance.id))),
        )

        def fake_start(db_session, **kwargs):
            records = kwargs["explicit_source_records"]
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].explicit_order, 1)
            root = Path(kwargs["runtime_source_root_path"]).resolve()
            ingestion = IngestionRun(
                ingestion_source_id=kwargs["ingestion_source_id"], from_path=str(root)
            )
            db_session.add(ingestion)
            db_session.flush()
            intake = SourceIntakeRun(
                status="running",
                ingestion_source_id=kwargs["ingestion_source_id"],
                source_label=self.profile.source_label,
                source_type=self.profile.source_type,
                source_root_path=str(root),
                intake_mode="acquisition_bridge",
                source_intake_limit=1,
                ingest_batch_size=1,
                started_at=datetime.now(timezone.utc),
                created_by="source_acquisition_bridge",
            )
            db_session.add(intake)
            db_session.commit()
            kwargs["on_created"](intake.id)
            record = records[0]
            sha256 = hashlib.sha256(Path(record.full_path).read_bytes()).hexdigest()
            provenance = Provenance(
                asset_sha256=sha256,
                source_path=record.original_source_path,
                ingestion_source_id=kwargs["ingestion_source_id"],
                ingestion_run_id=ingestion.id,
                source_label=self.profile.source_label,
                source_type=self.profile.source_type,
                source_root_path=str(root),
                source_relative_path=Path(record.original_source_path).name,
            )
            db_session.add(provenance)
            intake.status = "completed"
            intake.ingestion_run_id = ingestion.id
            intake.files_scanned = 1
            intake.selected = 1
            intake.staged = 1
            intake.failed_or_rejected = 0
            intake.finished_at = datetime.now(timezone.utc)
            db_session.commit()
            kwargs["on_finished"](intake.id)

        with (
            patch("app.services.source_acquisition.service.SessionLocal", self.session_factory),
            patch(
                "app.services.source_acquisition.service.start_explicit_source_intake",
                side_effect=fake_start,
            ) as start,
        ):
            completed = execute_acquisition_bridge(
                self.db, UUID(repeat_run.run_uuid), plan.bridge_plan_digest
            )
        after = (
            self.db.scalar(select(func.count(SourceIntakeRun.id))),
            self.db.scalar(select(func.count(IngestionRun.id))),
            self.db.scalar(select(func.count(Asset.sha256))),
            self.db.scalar(select(func.count(Provenance.id))),
        )
        self.assertEqual(completed.bridge_state, "completed")
        self.assertEqual(start.call_count, 1)
        self.assertEqual(
            tuple(after_value - before_value for before_value, after_value in zip(before, after)),
            (1, 1, 0, 1),
        )
        self.db.expire_all()
        linked = list(
            self.db.scalars(
                select(SourceAcquisitionItem)
                .where(SourceAcquisitionItem.run_id == repeat_run.id)
                .order_by(SourceAcquisitionItem.ordinal)
            )
        )
        self.assertNotEqual(linked[0].bridged_provenance_id, prior_items[0].bridged_provenance_id)
        self.assertEqual(
            [item.bridged_provenance_id for item in linked[1:]],
            [item.bridged_provenance_id for item in prior_items[1:]],
        )

    def test_cross_acquisition_ambiguous_prior_observation_fails_closed(self) -> None:
        first_run, first_items, _ = self._completed_bridge_run()
        self._establish_completed_bridge_links(first_run, first_items)
        second_run, second_items, _ = self._completed_bridge_run()
        self._establish_completed_bridge_links(second_run, second_items)
        repeat_run, _, _ = self._completed_bridge_run()

        with self.assertRaises(WindowsHelperServiceError) as raised:
            plan_acquisition_bridge(self.db, UUID(repeat_run.run_uuid))
        self.assertEqual(raised.exception.code, "bridge_prior_observation_ambiguous")

    def test_cross_acquisition_same_path_changed_content_common_intake(self) -> None:
        prior_run, prior_items, _ = self._completed_bridge_run()
        self._establish_completed_bridge_links(prior_run, prior_items)
        repeat_run, repeat_items, _ = self._completed_bridge_run()
        changed = repeat_items[0]
        changed_content = b"changed!"
        ready_path = Path(repeat_run.receiving_root) / changed.ready_relative_path
        ready_path.write_bytes(changed_content)
        changed.expected_size_bytes = len(changed_content)
        changed.verified_byte_count = len(changed_content)
        changed.committed_offset = len(changed_content)
        changed.helper_source_sha256 = _digest(changed_content)
        changed.linux_verified_sha256 = _digest(changed_content)
        repeat_run.expected_byte_count = sum(item.expected_size_bytes for item in repeat_items)
        repeat_run.committed_byte_count = repeat_run.expected_byte_count
        self.db.commit()

        plan = plan_acquisition_bridge(self.db, UUID(repeat_run.run_uuid))
        self.assertEqual(plan.expected_asset_delta, 1)
        self.assertEqual(plan.expected_provenance_delta, 1)
        self.assertEqual(plan.items[0].observation_classification, "common_intake")



if __name__ == "__main__":
    unittest.main()
