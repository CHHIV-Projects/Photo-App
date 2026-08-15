from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest
from uuid import UUID, uuid4

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.models.ingestion_source import IngestionSource
from app.models.source_endpoint import (
    AccessNode,
    SourceEndpoint,
    SourceEndpointAliasEvent,
    SourceEndpointObservedPath,
)
from app.schemas.windows_helper import (
    CreateWindowsHelperInventoryOperationRequest,
    CreateWindowsHelperProbeOperationRequest,
)
from app.services.source_identity.creation_schema import (
    SourceCreationConfirmRequest,
    SourceCreationPlanRequest,
)
from app.services.source_identity.creation_service import SourceCreationService
from app.services.source_identity.identity_fingerprint import volume_guid_fingerprint
from app.services.source_identity.readiness_service import SourceProfileReadinessService
from app.services.source_identity.source_selection_schema import SourceSelectionRequest
from app.services.source_identity.source_selection_service import SourceSelectionService
from app.services.windows_helper.operations import (
    claim_operation,
    complete_inventory_operation,
    complete_probe_operation,
    create_inventory_operation,
    create_probe_operation,
    get_operation_status,
)
from app.services.windows_helper.schema import ensure_windows_helper_schema
from app.services.windows_helper.service import (
    WindowsHelperServiceError,
    authenticate_credential,
    complete_pairing,
    create_pairing_authorization,
)
from app.windows_helper_shared.channel import PairingCompleteRequest
from app.windows_helper_shared.identity.models import (
    IdentityFingerprintCandidate,
    NormalizedIdentityEvidence,
    ProviderNativeRootEvidence,
)
from app.windows_helper_shared.protocol import (
    CapabilityVersion,
    CollectorCapability,
    HelperCapabilityIdentity,
    HelperInventoryItem,
    HelperInventoryPageResponse,
    HelperProbeResponse,
    InventoryEntryKind,
    InventoryResultStatus,
    MachineIssue,
    ProbeResultStatus,
    ProviderNativePath,
    SourceType,
)


ROOT = "C:\\Controlled"
VOLUME_ID = "11111111-1111-1111-1111-111111111111"
FINGERPRINT, FINGERPRINT_VERSION = volume_guid_fingerprint(VOLUME_ID)


class _ForbiddenLocalProbe:
    def probe(self, request):
        raise AssertionError("Windows Helper workflows must not use backend-local probing.")


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


def _native_path(root: str = ROOT, relative: str = "") -> ProviderNativePath:
    return ProviderNativePath(
        provider_native_root=root,
        provider_native_relative_path=relative,
        provider_native_full_path=root if not relative else root + "\\" + relative,
    )


def _probe(
    request_id: UUID,
    *,
    root: str = ROOT,
    fingerprint: str = FINGERPRINT,
    status: ProbeResultStatus = ProbeResultStatus.SUCCESS,
) -> HelperProbeResponse:
    success = status == ProbeResultStatus.SUCCESS
    blocker = (
        []
        if success
        else [
            MachineIssue(
                code="unavailable",
                evidence_code="path_not_found",
                redacted_detail="The exact Source root is unavailable.",
            )
        ]
    )
    return HelperProbeResponse(
        request_id=request_id,
        result_status=status,
        source_type=SourceType.LOCAL,
        provider_native_path=_native_path(root),
        collector_name="windows_non_admin_probe_v1",
        collector_version="1",
        source_root_evidence=ProviderNativeRootEvidence(
            path="C:\\",
            is_valid_source_root_candidate=success,
            filesystem_boundary_type="local_folder",
            root_reason="Synthetic volume boundary.",
        ),
        evidence_items=[
            NormalizedIdentityEvidence(
                category="path_evidence",
                code="path_not_found",
                status="blocked",
                durability="volatile",
                privacy_level="advanced_only",
                source_types=["local"],
            )
        ]
        if not success
        else [
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
            available=success,
            display="verified-volume" if success else "identity-evidence-unavailable",
        ),
        blockers=blocker,
    )


class WindowsHelperSourceWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        AccessNode.__table__.create(self.engine)
        SourceEndpoint.__table__.create(self.engine)
        SourceEndpointAliasEvent.__table__.create(self.engine)
        IngestionSource.__table__.create(self.engine)
        SourceEndpointObservedPath.__table__.create(self.engine)
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

    def _complete_probe(
        self,
        *,
        source_profile_id: int | None = None,
        root: str = ROOT,
        fingerprint: str = FINGERPRINT,
        status: ProbeResultStatus = ProbeResultStatus.SUCCESS,
    ):
        created = create_probe_operation(
            self.db,
            CreateWindowsHelperProbeOperationRequest(
                access_node_id=self.node_id,
                source_type=SourceType.LOCAL,
                provider_native_root=root,
                probe_mode=(
                    "readiness_probe" if source_profile_id is not None else "setup_probe"
                ),
                source_profile_id=source_profile_id,
            ),
        )
        claimed = claim_operation(self.db, self.credential)
        self.assertEqual(claimed.operation.operation_id, created.operation_id)
        complete_probe_operation(
            self.db,
            self.credential,
            created.operation_id,
            _probe(
                created.operation_id,
                root=root,
                fingerprint=fingerprint,
                status=status,
            ),
        )
        return created

    def _create_profile(self):
        setup = self._complete_probe()
        service = SourceCreationService(self.db, _ForbiddenLocalProbe())
        request = SourceCreationPlanRequest(
            source_type="local",
            observed_path=ROOT,
            device_name="Controlled Windows Device",
            source_name="Controlled Windows Local",
            helper_probe_operation_id=setup.operation_id,
        )
        plan = service.plan(request)
        self.assertEqual(plan.plan_status, "ready")
        self.assertEqual(
            plan.advanced_details["helper_probe_result_digest"],
            get_operation_status(self.db, setup.operation_id).result_digest,
        )
        result = service.confirm(
            SourceCreationConfirmRequest(
                **request.model_dump(),
                plan_fingerprint=plan.plan_fingerprint,
                operator_confirmed=True,
            )
        )
        self.assertEqual(result.creation_status, "completed")
        return setup, plan, result

    def test_creation_readiness_selection_and_inventory_happy_path(self) -> None:
        setup, plan, created = self._create_profile()
        self.assertEqual(created.endpoint_relative_root, "Controlled")
        self.assertEqual(created.canonical_source_root_path, ROOT)
        self.assertEqual(
            self.db.scalar(select(func.count(AccessNode.id))),
            1,
            "confirmation must retain the paired Helper AccessNode",
        )

        service = SourceCreationService(self.db, _ForbiddenLocalProbe())
        repeat_request = SourceCreationPlanRequest(
            source_type="local",
            observed_path=ROOT,
            device_name="Controlled Windows Device",
            source_name="Controlled Windows Local",
            naming_action="use_existing",
            helper_probe_operation_id=setup.operation_id,
        )
        repeat_plan = service.plan(repeat_request)
        self.assertEqual(repeat_plan.plan_status, "source_exists")
        repeat = service.confirm(
            SourceCreationConfirmRequest(
                **repeat_request.model_dump(),
                plan_fingerprint=repeat_plan.plan_fingerprint,
                operator_confirmed=True,
            )
        )
        self.assertTrue(repeat.reused_endpoint)
        self.assertTrue(repeat.reused_source)
        self.assertEqual(repeat.source_profile_id, created.source_profile_id)
        self.assertEqual(self.db.scalar(select(func.count(IngestionSource.id))), 1)

        with self.assertRaises(WindowsHelperServiceError):
            create_probe_operation(
                self.db,
                CreateWindowsHelperProbeOperationRequest(
                    access_node_id=self.node_id,
                    source_type=SourceType.LOCAL,
                    provider_native_root="C:\\Other",
                    probe_mode="readiness_probe",
                    source_profile_id=created.source_profile_id,
                ),
            )

        readiness_probe = self._complete_probe(source_profile_id=created.source_profile_id)
        readiness = SourceProfileReadinessService(
            self.db,
            _ForbiddenLocalProbe(),
        ).check_readiness(
            created.source_profile_id,
            readiness_probe.operation_id,
        )
        self.assertEqual(readiness.readiness_status, "ready")
        self.assertEqual(readiness.identity_match_status, "matched")
        self.assertTrue(readiness.provider_operation_ready)
        self.assertFalse(readiness.can_run_source_intake)

        selection = SourceSelectionService(
            self.db,
            _ForbiddenLocalProbe(),
        ).select_source(
            SourceSelectionRequest(
                source_profile_id=created.source_profile_id,
                helper_probe_operation_id=readiness_probe.operation_id,
            )
        )
        self.assertEqual(selection.result, "selected")
        self.assertEqual(selection.workflow_kind, "windows_helper_intake")
        context = selection.selected_source_context
        self.assertEqual(context.source_profile_id, created.source_profile_id)
        self.assertEqual(context.configured_source_root, ROOT)
        self.assertIsNone(context.resolved_source_root)
        self.assertIsNone(context.resolved_endpoint_path)
        self.assertFalse(context.provider_context["can_run_source_intake"])

        inventory = create_inventory_operation(
            self.db,
            CreateWindowsHelperInventoryOperationRequest(
                source_profile_id=created.source_profile_id,
                probe_operation_id=readiness_probe.operation_id,
                page_size=4,
            ),
        )
        claim = claim_operation(self.db, self.credential)
        request = claim.operation.request
        generation = uuid4()
        items = [
            HelperInventoryItem(
                candidate_reference="eligible_jpg",
                provider_native_path=_native_path(relative="eligible.jpg"),
                filename="eligible.jpg",
                size_bytes=60 * 1024,
                modified_time_ns=1,
                entry_kind=InventoryEntryKind.REGULAR_FILE,
            ),
            HelperInventoryItem(
                candidate_reference="small_jpg",
                provider_native_path=_native_path(relative="small.jpg"),
                filename="small.jpg",
                size_bytes=1024,
                modified_time_ns=2,
                entry_kind=InventoryEntryKind.REGULAR_FILE,
            ),
            HelperInventoryItem(
                candidate_reference="text_file",
                provider_native_path=_native_path(relative="notes.txt"),
                filename="notes.txt",
                size_bytes=60 * 1024,
                modified_time_ns=3,
                entry_kind=InventoryEntryKind.REGULAR_FILE,
            ),
            HelperInventoryItem(
                candidate_reference="junction",
                provider_native_path=_native_path(relative="junction"),
                filename="junction",
                modified_time_ns=4,
                entry_kind=InventoryEntryKind.REPARSE_POINT,
            ),
        ]
        items.sort(key=lambda item: item.provider_native_path.provider_native_relative_path.casefold())
        complete_inventory_operation(
            self.db,
            self.credential,
            inventory.operation_id,
            HelperInventoryPageResponse(
                request_id=inventory.operation_id,
                result_status=InventoryResultStatus.SUCCESS,
                source_endpoint_id=created.source_endpoint_id,
                source_profile_id=created.source_profile_id,
                source_type=SourceType.LOCAL,
                provider_native_path=request.provider_native_path,
                inventory_generation=generation,
                identity_probe=_probe(inventory.operation_id),
                items=items,
                next_cursor="opaque_cursor_1",
            ),
        )
        status = get_operation_status(self.db, inventory.operation_id)
        self.assertEqual(
            [item.eligibility for item in status.inventory_candidates],
            ["eligible", "rejected", "rejected", "rejected"],
        )
        self.assertEqual(
            [item.eligibility_reason for item in status.inventory_candidates],
            [
                "current_linux_media_policy",
                "reparse_point",
                "unsupported_extension",
                "below_minimum_size",
            ],
        )

        continuation = create_inventory_operation(
            self.db,
            CreateWindowsHelperInventoryOperationRequest(
                source_profile_id=created.source_profile_id,
                probe_operation_id=readiness_probe.operation_id,
                inventory_generation=generation,
                cursor="opaque_cursor_1",
                page_size=1,
            ),
        )
        self.assertEqual(continuation.operation_type, "inventory_page")
        with self.assertRaises(WindowsHelperServiceError):
            create_inventory_operation(
                self.db,
                CreateWindowsHelperInventoryOperationRequest(
                    source_profile_id=created.source_profile_id,
                    probe_operation_id=readiness_probe.operation_id,
                    inventory_generation=generation,
                    cursor="tampered_cursor",
                    page_size=1,
                ),
            )

    def test_readiness_fails_closed_for_offline_stale_unavailable_and_identity_change(self) -> None:
        _, _, created = self._create_profile()
        service = SourceProfileReadinessService(self.db, _ForbiddenLocalProbe())

        missing = service.check_readiness(created.source_profile_id)
        self.assertEqual(missing.readiness_status, "blocked")
        self.assertEqual(missing.blockers[0].code, "windows_helper_probe_required")

        node = self.db.scalar(
            select(AccessNode).where(AccessNode.access_node_uuid == str(self.node_id))
        )
        node.last_seen_at = datetime.now(timezone.utc) - timedelta(seconds=91)
        self.db.commit()
        offline = service.check_readiness(created.source_profile_id)
        self.assertEqual(offline.blockers[0].code, "windows_helper_offline")

        node.last_seen_at = datetime.now(timezone.utc)
        self.db.commit()
        unavailable_probe = self._complete_probe(
            source_profile_id=created.source_profile_id,
            status=ProbeResultStatus.UNAVAILABLE,
        )
        unavailable = service.check_readiness(
            created.source_profile_id,
            unavailable_probe.operation_id,
        )
        self.assertEqual(unavailable.readiness_status, "blocked")
        self.assertFalse(unavailable.provider_operation_ready)

        changed_probe = self._complete_probe(
            source_profile_id=created.source_profile_id,
            fingerprint="sha256:" + "b" * 64,
        )
        changed = service.check_readiness(
            created.source_profile_id,
            changed_probe.operation_id,
        )
        self.assertEqual(changed.identity_match_status, "mismatch")
        self.assertFalse(changed.can_run_source_intake)

        table = type(self.credential).metadata.tables["windows_helper_operations"]
        self.db.execute(
            table.update()
            .where(table.c.operation_uuid == str(changed_probe.operation_id))
            .values(completed_at=datetime.now(timezone.utc) - timedelta(minutes=6))
        )
        self.db.commit()
        stale = service.check_readiness(
            created.source_profile_id,
            changed_probe.operation_id,
        )
        self.assertEqual(stale.blockers[0].code, "probe_operation_stale")


if __name__ == "__main__":
    unittest.main()
