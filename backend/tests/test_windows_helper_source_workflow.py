from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch
from tempfile import TemporaryDirectory
from types import SimpleNamespace
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
from app.models.windows_source_workflow import (
    WindowsSourceWorkflow,
    WindowsSourceWorkflowCandidate,
    WindowsSourceWorkflowPage,
)
from app.schemas.windows_helper import (
    CreateWindowsHelperPairingRequest,
    CreateWindowsHelperInventoryOperationRequest,
    CreateWindowsHelperProbeOperationRequest,
)
from app.schemas.windows_source_ui import (
    WindowsSourceUiCreateProbeRequest,
    WindowsSourceUiCreatePlanRequest,
    WindowsSourceUiPortableDiscoveryRequest,
    WindowsSourceUiPortableDiscoveryResolveRequest,
    WindowsSourceUiRouteResolveRequest,
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
from app.services.source_acquisition.schema import ensure_source_acquisition_schema
from app.services.windows_helper.operations import (
    claim_operation,
    complete_inventory_operation,
    complete_inventory_attestation_operation,
    complete_probe_operation,
    complete_volume_observation_operation,
    create_inventory_operation,
    create_probe_operation,
    create_resolved_profile_probe_operation,
    create_volume_observation_operation,
    get_operation_status,
)
from app.services.windows_helper.schema import ensure_windows_helper_schema
from app.services.windows_helper.service import (
    WindowsHelperServiceError,
    authenticate_credential,
    complete_pairing,
    create_pairing_authorization,
)
from app.services.windows_helper.ui_facade import (
    begin_profile_route_check,
    begin_portable_discovery,
    create_computer_pairing,
    create_creation_probe,
    creation_plan,
    list_computers,
    resolve_profile_route,
    resolve_portable_discovery,
)
from app.services.windows_helper.source_workflow import (
    _advance_inventory,
    approve_or_resume_workflow,
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
    HelperKnownSourceAttestationResponse,
    HelperObserveVolumesResponse,
    HelperProbeResponse,
    InventoryEntryKind,
    InventoryResultStatus,
    KnownSourceAttestationResultStatus,
    MachineIssue,
    MountedVolumeObservation,
    MountedVolumeStorageEvidence,
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


def _capability(
    access_node_id: UUID,
    *,
    mounted_volume_version: str = "1",
    inventory_attestation: bool = False,
) -> HelperCapabilityIdentity:
    return HelperCapabilityIdentity(
        helper_version=(
            "0.5.2" if mounted_volume_version == "2" else "0.5.1"
        ),
        intended_access_node_id=access_node_id,
        supported_source_types=[SourceType.LOCAL, SourceType.EXTERNAL, SourceType.REMOVABLE],
        collectors=[
            CollectorCapability(
                name="windows_non_admin_probe_v1",
                version="1",
                supported_source_types=[SourceType.LOCAL, SourceType.EXTERNAL, SourceType.REMOVABLE],
            )
        ],
        capabilities=[
            CapabilityVersion(name="authenticated_channel", version="1"),
            CapabilityVersion(name="remote_operations", version="1"),
            CapabilityVersion(name="bounded_inventory", version="1"),
            CapabilityVersion(
                name="mounted_volume_observation",
                version=mounted_volume_version,
            ),
        ] + (
            [CapabilityVersion(name="known_source_inventory_attestation", version="1")]
            if inventory_attestation
            else []
        ),
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
    source_type: SourceType = SourceType.LOCAL,
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
        source_type=source_type,
        provider_native_path=_native_path(root),
        collector_name="windows_non_admin_probe_v1",
        collector_version="1",
        source_root_evidence=ProviderNativeRootEvidence(
            path="C:\\",
            is_valid_source_root_candidate=success,
            filesystem_boundary_type=(
                "external_folder"
                if source_type == SourceType.EXTERNAL
                else "removable_media_folder"
                if source_type == SourceType.REMOVABLE
                else "local_folder"
            ),
            root_reason="Synthetic volume boundary.",
        ),
        evidence_items=[
            NormalizedIdentityEvidence(
                category="path_evidence",
                code="path_not_found",
                status="blocked",
                durability="volatile",
                privacy_level="advanced_only",
                source_types=[source_type.value],
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
                source_types=[source_type.value],
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
        ensure_source_acquisition_schema(self.db)

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

    def _set_mounted_volume_capability(self, version: str) -> AccessNode:
        node = self.db.scalar(
            select(AccessNode).where(AccessNode.access_node_uuid == str(self.node_id))
        )
        node.capabilities_json = _capability(
            self.node_id,
            mounted_volume_version=version,
        ).model_dump_json()
        node.last_seen_at = datetime.now(timezone.utc)
        self.db.commit()
        return node

    def _enable_inventory_attestation(self) -> AccessNode:
        node = self.db.scalar(
            select(AccessNode).where(AccessNode.access_node_uuid == str(self.node_id))
        )
        node.capabilities_json = _capability(
            self.node_id,
            mounted_volume_version="2",
            inventory_attestation=True,
        ).model_dump_json()
        node.last_seen_at = datetime.now(timezone.utc)
        self.db.commit()
        return node

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

    def test_computer_projection_preserves_legacy_endpoint_display_without_rewriting_node(self) -> None:
        _, _, result = self._create_profile()
        endpoint = self.db.get(SourceEndpoint, result.source_endpoint_id)
        node = self.db.scalar(
            select(AccessNode).where(AccessNode.access_node_uuid == str(self.node_id))
        )
        original_node_label = node.label

        projection = list_computers(self.db)

        self.assertEqual(len(projection.computers), 1)
        self.assertEqual(projection.computers[0].computer_alias, endpoint.alias)
        self.assertEqual(projection.computers[0].source_device_aliases, [endpoint.alias])
        self.assertEqual(node.label, original_node_label)
        with self.assertRaisesRegex(WindowsHelperServiceError, "already paired"):
            create_computer_pairing(
                self.db,
                CreateWindowsHelperPairingRequest(computer_alias=endpoint.alias.lower()),
            )
        self.assertEqual(self.db.query(AccessNode).count(), 1)

    def test_external_creation_rejects_the_retired_browser_composed_root_contract(self) -> None:
        with self.assertRaisesRegex(ValueError, "discovery candidate token"):
            WindowsSourceUiCreateProbeRequest(
                access_node_id=self.node_id,
                source_type="external",
                device_alias="Travel Drive",
                windows_root="H:\\Pictures",
                profile_name="Travel photos",
            )

    def _create_external_profile(self) -> tuple[SourceEndpoint, IngestionSource]:
        node = self.db.scalar(
            select(AccessNode).where(AccessNode.access_node_uuid == str(self.node_id))
        )
        node.last_seen_at = datetime.now(timezone.utc)
        endpoint = SourceEndpoint(
            source_type="external_device",
            alias="Controlled External",
            alias_normalized="controlled external",
            status="active",
            identity_fingerprint_hash=FINGERPRINT,
            identity_fingerprint_version=FINGERPRINT_VERSION,
            identity_confidence="strong_match",
            created_from_access_node_id=node.id,
        )
        self.db.add(endpoint)
        self.db.flush()
        source = IngestionSource(
            source_label="Controlled External Photos",
            source_label_normalized="controlled external photos",
            source_type="external_drive",
            source_root_path="F:\\Pictures",
            source_root_path_normalized="f:\\pictures",
            endpoint_relative_root="Pictures",
            endpoint_id=endpoint.id,
            profile_status="active",
        )
        self.db.add(source)
        self.db.flush()
        self.db.add(
            SourceEndpointObservedPath(
                source_endpoint_id=endpoint.id,
                access_node_id=node.id,
                observed_path="F:\\Pictures",
                normalized_observed_path="f:\\pictures",
                filesystem_boundary_type="external_folder",
                source_root_candidate_path="F:\\Pictures",
                is_valid_source_root_candidate=True,
                probe_provider_name="windows_non_admin_probe_v1",
                probe_provider_version="1",
                probe_status="completed",
                confidence_tier="strong_match",
                match_status="matched",
                safe_to_run="true",
            )
        )
        self.db.commit()
        return endpoint, source

    def _complete_volume_observation(
        self,
        source_profile_id: int,
        volumes: list[MountedVolumeObservation],
    ):
        created = create_volume_observation_operation(self.db, source_profile_id)
        claim = claim_operation(self.db, self.credential)
        self.assertEqual(claim.operation.operation_type, "observe_volumes")
        complete_volume_observation_operation(
            self.db,
            self.credential,
            created.operation_id,
            HelperObserveVolumesResponse(
                request_id=created.operation_id,
                collector_name="windows_non_admin_probe_v1",
                collector_version="1",
                volumes=volumes,
            ),
        )
        return created

    def test_external_helper_resolves_changed_letter_without_profile_rewrite(self) -> None:
        endpoint, source = self._create_external_profile()
        counts_before = (
            self.db.scalar(select(func.count(SourceEndpoint.id))),
            self.db.scalar(select(func.count(IngestionSource.id))),
            self.db.scalar(select(func.count(SourceEndpointObservedPath.id))),
        )
        observation = self._complete_volume_observation(
            source.id,
            [
                MountedVolumeObservation(
                    provider_native_root="E:\\",
                    identity_fingerprint_hash=FINGERPRINT,
                    identity_fingerprint_version=FINGERPRINT_VERSION,
                    drive_type="fixed",
                    identity_identifier_masked="{...1111}",
                )
            ],
        )

        probe_id = create_resolved_profile_probe_operation(self.db, observation.operation_id)
        self.assertEqual(
            probe_id,
            create_resolved_profile_probe_operation(self.db, observation.operation_id),
        )
        claim = claim_operation(self.db, self.credential)
        self.assertEqual(claim.operation.operation_type, "probe_source")
        self.assertEqual(claim.operation.request.provider_native_path.provider_native_root, "E:\\Pictures")
        self.assertEqual(claim.operation.request.source_type, SourceType.EXTERNAL)
        complete_probe_operation(
            self.db,
            self.credential,
            probe_id,
            _probe(probe_id, root="E:\\Pictures", source_type=SourceType.EXTERNAL),
        )

        readiness = SourceProfileReadinessService(
            self.db,
            _ForbiddenLocalProbe(),
        ).check_readiness(source.id, probe_id)
        self.assertEqual(readiness.readiness_status, "ready")
        self.assertEqual(readiness.observed_path_summary["observed_path"], "E:\\Pictures")
        self.db.refresh(source)
        self.db.refresh(endpoint)
        self.assertEqual(source.source_root_path, "F:\\Pictures")
        self.assertEqual(source.endpoint_relative_root, "Pictures")
        self.assertEqual(endpoint.identity_fingerprint_hash, FINGERPRINT)
        self.assertEqual(
            counts_before,
            (
                self.db.scalar(select(func.count(SourceEndpoint.id))),
                self.db.scalar(select(func.count(IngestionSource.id))),
                self.db.scalar(select(func.count(SourceEndpointObservedPath.id))),
            ),
        )

    def test_external_volume_resolution_fails_closed_for_zero_multiple_and_wrong_letter(self) -> None:
        _endpoint, source = self._create_external_profile()

        missing = self._complete_volume_observation(source.id, [])
        with self.assertRaisesRegex(WindowsHelperServiceError, "not connected"):
            create_resolved_profile_probe_operation(self.db, missing.operation_id)

        duplicate = self._complete_volume_observation(
            source.id,
            [
                MountedVolumeObservation(
                    provider_native_root=root,
                    identity_fingerprint_hash=FINGERPRINT,
                    identity_fingerprint_version=FINGERPRINT_VERSION,
                )
                for root in ["E:\\", "G:\\"]
            ],
        )
        with self.assertRaisesRegex(WindowsHelperServiceError, "More than one"):
            create_resolved_profile_probe_operation(self.db, duplicate.operation_id)

        other_fingerprint, other_version = volume_guid_fingerprint(
            "22222222-2222-2222-2222-222222222222"
        )
        wrong = self._complete_volume_observation(
            source.id,
            [
                MountedVolumeObservation(
                    provider_native_root="F:\\",
                    identity_fingerprint_hash=other_fingerprint,
                    identity_fingerprint_version=other_version,
                )
            ],
        )
        with self.assertRaisesRegex(WindowsHelperServiceError, "different Windows volume"):
            create_resolved_profile_probe_operation(self.db, wrong.operation_id)

    def test_portable_routes_require_fresh_observation_and_fail_closed_on_multiple(self) -> None:
        endpoint, source = self._create_external_profile()
        second_authorization = create_pairing_authorization(self.db, "Family Laptop")
        second_paired = complete_pairing(
            self.db,
            PairingCompleteRequest(
                pairing_code=second_authorization.pairing_code,
                access_node_id=second_authorization.access_node_id,
                capability_identity=_capability(second_authorization.access_node_id),
            ),
        )
        second_credential = authenticate_credential(
            self.db,
            f"PhotoOrganizerHelper {second_paired.credential_id}.{second_paired.credential_token}",
        )
        second_node = self.db.scalar(
            select(AccessNode).where(
                AccessNode.access_node_uuid == str(second_paired.access_node_id)
            )
        )
        second_node.last_seen_at = datetime.now(timezone.utc)
        self.db.commit()

        started = begin_profile_route_check(self.db, source.id)
        self.assertEqual(started.stage, "checking_routes")
        self.assertEqual(len(started.observation_tokens), 2)
        for credential, root in [(self.credential, "E:\\"), (second_credential, "H:\\")]:
            claimed = claim_operation(self.db, credential)
            complete_volume_observation_operation(
                self.db,
                credential,
                claimed.operation.operation_id,
                HelperObserveVolumesResponse(
                    request_id=claimed.operation.operation_id,
                    collector_name="windows_non_admin_probe_v1",
                    collector_version="1",
                    volumes=[
                        MountedVolumeObservation(
                            provider_native_root=root,
                            identity_fingerprint_hash=FINGERPRINT,
                            identity_fingerprint_version=FINGERPRINT_VERSION,
                            drive_type="fixed",
                        )
                    ],
                ),
            )

        ambiguous = resolve_profile_route(
            self.db,
            source.id,
            WindowsSourceUiRouteResolveRequest(
                observation_tokens=started.observation_tokens,
            ),
        )
        self.assertEqual(ambiguous.stage, "ambiguous")
        self.assertEqual(len(ambiguous.routes), 2)
        selected = resolve_profile_route(
            self.db,
            source.id,
            WindowsSourceUiRouteResolveRequest(
                observation_tokens=started.observation_tokens,
                selected_access_node_id=second_paired.access_node_id,
            ),
        )
        self.assertEqual(selected.stage, "checking_source")
        self.assertIsNotNone(selected.probe_operation_token)

        second_node.last_seen_at = datetime.now(timezone.utc) - timedelta(seconds=91)
        self.db.commit()
        single = begin_profile_route_check(self.db, source.id)
        self.assertEqual(len(single.observation_tokens), 1)

    def test_known_external_route_uses_targeted_inventory_attestation(self) -> None:
        endpoint, source = self._create_external_profile()
        self._enable_inventory_attestation()
        started = begin_profile_route_check(self.db, source.id)
        self.assertEqual(started.stage, "checking_routes")
        self.assertEqual(len(started.observation_tokens), 1)

        claimed = claim_operation(self.db, self.credential)
        self.assertEqual(claimed.operation.operation_type, "attest_inventory")
        request = claimed.operation.request
        issued = datetime.now(timezone.utc)
        complete_inventory_attestation_operation(
            self.db,
            self.credential,
            claimed.operation.operation_id,
            HelperKnownSourceAttestationResponse(
                request_id=claimed.operation.operation_id,
                result_status=KnownSourceAttestationResultStatus.SUCCESS,
                intended_access_node_id=request.intended_access_node_id,
                source_endpoint_id=endpoint.id,
                source_profile_id=source.id,
                source_type=SourceType.EXTERNAL,
                expected_identity_fingerprint=FINGERPRINT,
                parent_workflow_id=request.parent_workflow_id,
                inventory_generation=request.inventory_generation,
                runtime_source_root=request.configured_source_root,
                issued_at=issued,
                expires_at=issued + timedelta(minutes=5),
                inventory_attestation_token="a" * 64,
            ),
        )
        readiness = SourceProfileReadinessService(self.db, _ForbiddenLocalProbe()).check_readiness(
            source.id,
            claimed.operation.operation_id,
        )
        self.assertEqual(readiness.readiness_status, "ready")
        self.assertEqual(readiness.identity_match_status, "matched")
        selection = SourceSelectionService(self.db, _ForbiddenLocalProbe()).select_source(
            SourceSelectionRequest(
                source_profile_id=source.id,
                helper_probe_operation_id=claimed.operation.operation_id,
            )
        )
        self.assertEqual(selection.result, "selected")
        resolved = resolve_profile_route(
            self.db,
            source.id,
            WindowsSourceUiRouteResolveRequest(
                observation_tokens=started.observation_tokens,
            ),
        )
        self.assertEqual(resolved.probe_operation_token, claimed.operation.operation_id)
        inventory = create_inventory_operation(
            self.db,
            CreateWindowsHelperInventoryOperationRequest(
                source_profile_id=source.id,
                probe_operation_id=claimed.operation.operation_id,
                page_size=100,
            ),
        )
        inventory_claim = claim_operation(self.db, self.credential)
        self.assertEqual(inventory_claim.operation.operation_id, inventory.operation_id)
        self.assertEqual(
            inventory_claim.operation.request.inventory_attestation_token,
            "a" * 64,
        )
        self.assertEqual(
            inventory_claim.operation.request.inventory_generation,
            request.inventory_generation,
        )

    def test_portable_discovery_recognizes_known_fingerprint_without_exposing_it(self) -> None:
        endpoint, _source = self._create_external_profile()
        started = begin_portable_discovery(
            self.db,
            WindowsSourceUiPortableDiscoveryRequest(source_type="external"),
        )
        self.assertEqual(started.stage, "checking_devices")
        claimed = claim_operation(self.db, self.credential)
        complete_volume_observation_operation(
            self.db,
            self.credential,
            claimed.operation.operation_id,
            HelperObserveVolumesResponse(
                request_id=claimed.operation.operation_id,
                collector_name="windows_non_admin_probe_v1",
                collector_version="1",
                volumes=[
                    MountedVolumeObservation(
                        provider_native_root="D:\\",
                        identity_fingerprint_hash="sha256:" + "d" * 64,
                        identity_fingerprint_version=FINGERPRINT_VERSION,
                        drive_type="cd-rom",
                    ),
                    MountedVolumeObservation(
                        provider_native_root="G:\\",
                        identity_fingerprint_hash="sha256:" + "e" * 64,
                        identity_fingerprint_version=FINGERPRINT_VERSION,
                        drive_type="fixed",
                    ),
                    MountedVolumeObservation(
                        provider_native_root="H:\\",
                        identity_fingerprint_hash=FINGERPRINT,
                        identity_fingerprint_version=FINGERPRINT_VERSION,
                        drive_type="fixed",
                    )
                ],
            ),
        )
        resolved = resolve_portable_discovery(
            self.db,
            WindowsSourceUiPortableDiscoveryResolveRequest(
                source_type="external",
                observation_tokens=started.observation_tokens,
            ),
        )
        self.assertEqual(resolved.stage, "ready")
        self.assertEqual(len(resolved.candidates), 1)
        self.assertTrue(resolved.candidates[0].known_device)
        self.assertEqual(resolved.candidates[0].device_alias, endpoint.alias)
        self.assertEqual(resolved.candidates[0].current_root, "H:\\")
        self.assertNotIn(FINGERPRINT, resolved.model_dump_json())

    def test_v2_verified_unknown_external_is_discoverable_and_can_start_existing_probe_path(self) -> None:
        self._set_mounted_volume_capability("2")
        started = begin_portable_discovery(
            self.db,
            WindowsSourceUiPortableDiscoveryRequest(source_type="external"),
        )
        claimed = claim_operation(self.db, self.credential)
        complete_volume_observation_operation(
            self.db,
            self.credential,
            claimed.operation.operation_id,
            HelperObserveVolumesResponse(
                request_id=claimed.operation.operation_id,
                collector_name="windows_non_admin_probe_v1",
                collector_version="1",
                volumes=[
                    MountedVolumeObservation(
                        provider_native_root="H:\\",
                        identity_fingerprint_hash="sha256:" + "9" * 64,
                        identity_fingerprint_version=FINGERPRINT_VERSION,
                        drive_type="fixed",
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
                ],
            ),
        )

        resolved = resolve_portable_discovery(
            self.db,
            WindowsSourceUiPortableDiscoveryResolveRequest(
                source_type="external",
                observation_tokens=started.observation_tokens,
            ),
        )
        self.assertEqual(resolved.stage, "ready")
        self.assertEqual(len(resolved.candidates), 1)
        self.assertFalse(resolved.candidates[0].known_device)
        self.assertIsNone(resolved.candidates[0].device_alias)

        created = create_creation_probe(
            self.db,
            WindowsSourceUiCreateProbeRequest(
                discovery_candidate_token=resolved.candidates[0].candidate_token,
                source_type="external",
                device_alias="New USB Archive",
                endpoint_relative_root="Pictures",
                profile_name="New USB Photos",
            ),
        )
        probe_claim = claim_operation(self.db, self.credential)
        self.assertEqual(created.operation_token, probe_claim.operation.operation_id)
        self.assertEqual(probe_claim.operation.request.source_type, SourceType.EXTERNAL)
        self.assertEqual(
            probe_claim.operation.request.provider_native_path.provider_native_root,
            "H:\\Pictures",
        )
        self.assertEqual(self.db.scalar(select(func.count(SourceEndpoint.id))), 0)

    def test_v2_contradictory_virtual_evidence_blocks_known_external_route(self) -> None:
        endpoint, _source = self._create_external_profile()
        self._set_mounted_volume_capability("2")
        started = begin_portable_discovery(
            self.db,
            WindowsSourceUiPortableDiscoveryRequest(source_type="external"),
        )
        claimed = claim_operation(self.db, self.credential)
        complete_volume_observation_operation(
            self.db,
            self.credential,
            claimed.operation.operation_id,
            HelperObserveVolumesResponse(
                request_id=claimed.operation.operation_id,
                collector_name="windows_non_admin_probe_v1",
                collector_version="1",
                volumes=[
                    MountedVolumeObservation(
                        provider_native_root="H:\\",
                        identity_fingerprint_hash=endpoint.identity_fingerprint_hash,
                        identity_fingerprint_version=endpoint.identity_fingerprint_version,
                        drive_type="fixed",
                        storage_evidence=MountedVolumeStorageEvidence(
                            backing_association="exact",
                            storage_bus_type="file_backed_virtual",
                            device_class="virtual",
                            external_connection="none",
                            is_boot=False,
                            is_system=False,
                        ),
                    )
                ],
            ),
        )

        resolved = resolve_portable_discovery(
            self.db,
            WindowsSourceUiPortableDiscoveryResolveRequest(
                source_type="external",
                observation_tokens=started.observation_tokens,
            ),
        )
        self.assertEqual(resolved.stage, "unavailable")
        self.assertEqual(resolved.candidates, [])
        self.assertEqual(self.db.get(SourceEndpoint, endpoint.id).alias, "Controlled External")

    def test_v2_result_missing_storage_evidence_is_rejected(self) -> None:
        self._set_mounted_volume_capability("2")
        started = begin_portable_discovery(
            self.db,
            WindowsSourceUiPortableDiscoveryRequest(source_type="external"),
        )
        claimed = claim_operation(self.db, self.credential)

        with self.assertRaisesRegex(WindowsHelperServiceError, "omitted required"):
            complete_volume_observation_operation(
                self.db,
                self.credential,
                claimed.operation.operation_id,
                HelperObserveVolumesResponse(
                    request_id=claimed.operation.operation_id,
                    collector_name="windows_non_admin_probe_v1",
                    collector_version="1",
                    volumes=[
                        MountedVolumeObservation(
                            provider_native_root="H:\\",
                            identity_fingerprint_hash="sha256:" + "8" * 64,
                            identity_fingerprint_version=FINGERPRINT_VERSION,
                            drive_type="fixed",
                        )
                    ],
                ),
            )
        self.assertEqual(len(started.observation_tokens), 1)

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

    def test_parent_inventory_preserves_helper_dfs_order_and_creates_bounded_children(self) -> None:
        _setup, _plan, created = self._create_profile()
        readiness_probe = self._complete_probe(source_profile_id=created.source_profile_id)
        first = create_inventory_operation(
            self.db,
            CreateWindowsHelperInventoryOperationRequest(
                source_profile_id=created.source_profile_id,
                probe_operation_id=readiness_probe.operation_id,
                page_size=100,
            ),
        )
        first_claim = claim_operation(self.db, self.credential)
        generation = uuid4()
        first_items = [
            HelperInventoryItem(
                candidate_reference=f"candidate_{index}",
                provider_native_path=_native_path(relative=("z.jpg" if index == 0 else f"folder\\{index:03}.jpg")),
                filename="z.jpg" if index == 0 else f"{index:03}.jpg",
                size_bytes=60 * 1024,
                modified_time_ns=index + 1,
                entry_kind=InventoryEntryKind.REGULAR_FILE,
                local_residency="resident",
            )
            for index in range(100)
        ]
        complete_inventory_operation(
            self.db,
            self.credential,
            first.operation_id,
            HelperInventoryPageResponse(
                request_id=first.operation_id,
                result_status=InventoryResultStatus.SUCCESS,
                source_endpoint_id=created.source_endpoint_id,
                source_profile_id=created.source_profile_id,
                source_type=SourceType.LOCAL,
                provider_native_path=first_claim.operation.request.provider_native_path,
                inventory_generation=generation,
                identity_probe=_probe(first.operation_id),
                items=first_items,
                next_cursor="opaque_cursor_100",
            ),
        )
        node = self.db.scalar(select(AccessNode).where(AccessNode.access_node_uuid == str(self.node_id)))
        parent = WindowsSourceWorkflow(
            source_profile_id=created.source_profile_id,
            source_endpoint_id=created.source_endpoint_id,
            access_node_id=node.id,
            probe_operation_uuid=str(readiness_probe.operation_id),
            state="inventorying",
            source_fingerprint=FINGERPRINT,
            provider_native_root=ROOT,
            max_observed_entries=100_000,
        )
        self.db.add(parent)
        self.db.flush()
        self.db.add(WindowsSourceWorkflowPage(workflow_id=parent.id, page_index=1, operation_uuid=str(first.operation_id)))
        self.db.commit()

        with TemporaryDirectory() as receiving:
            with patch(
                "app.services.windows_helper.source_workflow.settings",
                SimpleNamespace(
                    acquisition_receiving_path=receiving,
                    acquisition_disk_reserve_bytes=0,
                ),
            ):
                self.assertFalse(_advance_inventory(self.db, parent))
        second_claim = claim_operation(self.db, self.credential)
        second_item = HelperInventoryItem(
            candidate_reference="candidate_100",
            provider_native_path=_native_path(relative="a\\nested.jpg"),
            filename="nested.jpg",
            size_bytes=60 * 1024,
            modified_time_ns=101,
            entry_kind=InventoryEntryKind.REGULAR_FILE,
            local_residency="resident",
        )
        complete_inventory_operation(
            self.db,
            self.credential,
            second_claim.operation.operation_id,
            HelperInventoryPageResponse(
                request_id=second_claim.operation.operation_id,
                result_status=InventoryResultStatus.SUCCESS,
                source_endpoint_id=created.source_endpoint_id,
                source_profile_id=created.source_profile_id,
                source_type=SourceType.LOCAL,
                provider_native_path=second_claim.operation.request.provider_native_path,
                inventory_generation=generation,
                identity_probe=_probe(second_claim.operation.operation_id),
                items=[second_item],
                next_cursor=None,
            ),
        )
        with TemporaryDirectory() as receiving:
            with patch(
                "app.services.windows_helper.source_workflow.settings",
                SimpleNamespace(
                    acquisition_receiving_path=receiving,
                    acquisition_disk_reserve_bytes=0,
                ),
            ):
                self.assertFalse(_advance_inventory(self.db, parent))
        self.db.refresh(parent)
        self.assertEqual(parent.state, "awaiting_confirmation")
        self.assertEqual(parent.observed_item_count, 101)
        self.assertEqual(parent.eligible_item_count, 101)
        ordered = list(self.db.scalars(select(WindowsSourceWorkflowCandidate).where(WindowsSourceWorkflowCandidate.workflow_id == parent.id).order_by(WindowsSourceWorkflowCandidate.ordinal)))
        self.assertEqual(ordered[0].relative_path, "z.jpg")
        self.assertEqual(ordered[-1].relative_path, "a\\nested.jpg")
        with patch("app.services.windows_helper.source_workflow.start_or_resume_worker"):
            approved = approve_or_resume_workflow(self.db, UUID(parent.workflow_uuid), confirm=True)
        self.assertEqual(approved.files_total, 101)
        self.assertEqual(approved.source_profile_id, created.source_profile_id)
        self.assertEqual(approved.source_label, "Controlled Windows Local")
        self.assertIsNotNone(approved.started_at)
        self.assertIsNone(approved.finished_at)
        self.assertEqual(parent.child_count, 2)

    def test_local_v1_invariant_reuses_same_volume_and_blocks_different_or_ambiguous(self) -> None:
        setup, _plan, created = self._create_profile()
        same = creation_plan(
            self.db,
            WindowsSourceUiCreatePlanRequest(
                access_node_id=self.node_id,
                source_type="local",
                device_alias="ignored presentation alias",
                windows_root=ROOT,
                profile_name="Controlled Windows Local",
                probe_operation_token=setup.operation_id,
            ),
        )
        self.assertEqual(same.plan_status, "source_exists")
        self.assertEqual(same.device_alias, "Controlled Windows Device")

        other_fingerprint, _ = volume_guid_fingerprint(
            "33333333-3333-3333-3333-333333333333"
        )
        different = self._complete_probe(
            root="D:\\Pictures",
            fingerprint=other_fingerprint,
        )
        with self.assertRaisesRegex(WindowsHelperServiceError, "Additional local volumes"):
            creation_plan(
                self.db,
                WindowsSourceUiCreatePlanRequest(
                    access_node_id=self.node_id,
                    source_type="local",
                    device_alias="ignored",
                    windows_root="D:\\Pictures",
                    profile_name="Other Local",
                    probe_operation_token=different.operation_id,
                ),
            )

        node = self.db.scalar(
            select(AccessNode).where(AccessNode.access_node_uuid == str(self.node_id))
        )
        second = SourceEndpoint(
            source_type="local",
            alias="Historical second local",
            alias_normalized="historical second local",
            status="active",
            identity_fingerprint_hash=other_fingerprint,
            identity_fingerprint_version=FINGERPRINT_VERSION,
            identity_confidence="strong_match",
        )
        self.db.add(second)
        self.db.flush()
        self.db.add(
            SourceEndpointObservedPath(
                source_endpoint_id=second.id,
                access_node_id=node.id,
                observed_path="D:\\",
                normalized_observed_path="d:\\",
                filesystem_boundary_type="local_folder",
                is_valid_source_root_candidate=True,
                safe_to_run="true",
            )
        )
        self.db.commit()
        with self.assertRaisesRegex(WindowsHelperServiceError, "operator review"):
            creation_plan(
                self.db,
                WindowsSourceUiCreatePlanRequest(
                    access_node_id=self.node_id,
                    source_type="local",
                    device_alias="ignored",
                    windows_root=ROOT,
                    profile_name="Controlled Windows Local",
                    probe_operation_token=setup.operation_id,
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
