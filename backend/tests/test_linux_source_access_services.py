"""Milestone 012 Linux creation, selection, and dispatch integration tests."""

from __future__ import annotations

import posixpath
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.ingestion_run import IngestionRun
from app.models.ingestion_source import IngestionSource
from app.models.nas_registration import NasApplianceRegistration, NasPendingRegistration, NasShareRegistration
from app.models.source_endpoint import AccessNode, SourceEndpoint, SourceEndpointAliasEvent, SourceEndpointObservedPath
from app.schemas.admin import RunIngestionDispatchRequest, RunIngestionFilesystemOptions
from app.services.admin.run_ingestion_dispatch_service import RunIngestionDispatchService
from app.services.source_identity.creation_schema import SourceCreationConfirmRequest, SourceCreationPlanRequest
from app.services.source_identity.creation_service import SourceCreationService
from app.services.source_identity.probe_schema import (
    AccessNodeSummary,
    SourceIdentityEvidenceItem,
    SourceIdentityProbeRequest,
    SourceIdentityProbeResponse,
    SourceRootCandidate,
)
from app.services.source_identity.source_selection_schema import SourceSelectionRequest
from app.services.source_identity.source_selection_service import SourceSelectionService


class LinuxProbeService:
    def __init__(self) -> None:
        self.requests: list[SourceIdentityProbeRequest] = []
        self.changed_fingerprint = False
        self.change_fingerprint_on_call: int | None = None

    def probe(self, request: SourceIdentityProbeRequest) -> SourceIdentityProbeResponse:
        self.requests.append(request)
        local = request.source_type == "local"
        host_slot = (
            "/mnt/photo-organizer-sources/local/server-photos"
            if local
            else "/mnt/photo-organizer-sources/nas/photo-organizer"
        )
        runtime_slot = "/app/sources/local/server-photos" if local else "/app/sources/nas/photo-organizer"
        relative = request.relative_root or ""
        host_path = posixpath.join(host_slot, relative) if relative else host_slot
        runtime_root = posixpath.join(runtime_slot, relative) if relative else runtime_slot
        fingerprint_changed = (
            self.changed_fingerprint
            or self.change_fingerprint_on_call == len(self.requests)
        )
        fingerprint = "sha256:changed" if fingerprint_changed else ("sha256:local" if local else "sha256:nas")
        evidence = SourceIdentityEvidenceItem(
            category="volume_evidence" if local else "network_share_evidence",
            code="linux_filesystem_uuid_present" if local else "linux_nas_canonical_share_present",
            status="present",
            durability="durable",
            privacy_level="masked_only" if local else "advanced_only",
            source_types=[request.source_type],
            masked_value="…334444" if local else None,
            display_value=None if local else "//192.168.1.171/PhotoOrganizer",
            fingerprint_hash=fingerprint,
            fingerprint_version="linux_filesystem_uuid_v1" if local else "source_endpoint_identity_v1",
            provider_name="linux_stable_mount_v1",
        )
        return SourceIdentityProbeResponse(
            probe_status="completed",
            source_type=request.source_type,
            os_family="linux",
            provider_name="linux_stable_mount_v1",
            provider_version="1",
            access_node_summary=AccessNodeSummary(
                access_node_id="linux-access-node:12345678901234567890123456789012345678901234",
                label="henderson-server1",
                os_family="linux",
                host_fingerprint_hash="sha256:host",
                host_fingerprint_masked="sha256:…host",
                capabilities={"stable_mount_local": True, "stable_mount_nas": True},
            ),
            observed_path=host_path,
            normalized_observed_path=host_path,
            source_root_candidate=SourceRootCandidate(
                path=host_path,
                is_valid_source_root_candidate=True,
                filesystem_boundary_type=(
                    "local_folder" if local and relative else
                    "local_volume_root" if local else
                    "nas_share_folder" if relative else "nas_share_root"
                ),
                root_reason="Verified Linux stable mount",
            ),
            evidence_items=[evidence],
            confidence_tier="strong_match",
            match_status="not_compared",
            safe_to_run=True,
            location_id=request.location_id,
            relative_root=relative,
            host_slot=host_slot,
            runtime_slot=runtime_slot,
            runtime_root=runtime_root,
        )


class LinuxSourceAccessServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        AccessNode.__table__.create(self.engine)
        SourceEndpoint.__table__.create(self.engine)
        SourceEndpointAliasEvent.__table__.create(self.engine)
        IngestionSource.__table__.create(self.engine)
        IngestionRun.__table__.create(self.engine)
        SourceEndpointObservedPath.__table__.create(self.engine)
        NasApplianceRegistration.__table__.create(self.engine)
        NasShareRegistration.__table__.create(self.engine)
        NasPendingRegistration.__table__.create(self.engine)
        self.db = Session(self.engine)
        self.probes = LinuxProbeService()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def _create(self, source_type: str) -> tuple[IngestionSource, SourceEndpoint]:
        location_id = "linux-local-server-photos" if source_type == "local" else "linux-nas-photo-organizer"
        service = SourceCreationService(self.db, self.probes)
        request = SourceCreationPlanRequest(
            source_type=source_type,
            location_id=location_id,
            relative_root="family",
            device_name="Linux Local" if source_type == "local" else "Linux NAS",
        )
        plan = service.plan(request)
        self.assertEqual(plan.plan_status, "ready")
        self.assertEqual(plan.endpoint_relative_root, "family")
        result = service.confirm(
            SourceCreationConfirmRequest(
                **request.model_dump(),
                plan_fingerprint=plan.plan_fingerprint,
                operator_confirmed=True,
            )
        )
        self.assertEqual(result.creation_status, "completed")
        source = self.db.get(IngestionSource, result.source_profile_id)
        endpoint = self.db.get(SourceEndpoint, result.source_endpoint_id)
        assert source and endpoint
        return source, endpoint

    def test_local_creation_persists_stable_access_node_host_path_and_relative_root(self) -> None:
        source, endpoint = self._create("local")
        observed = self.db.scalar(select(SourceEndpointObservedPath))
        node = self.db.scalar(select(AccessNode))
        self.assertEqual(source.source_root_path, "/mnt/photo-organizer-sources/local/server-photos/family")
        self.assertEqual(source.endpoint_relative_root, "family")
        self.assertEqual(endpoint.identity_fingerprint_hash, "sha256:local")
        self.assertEqual(observed.observed_path, source.source_root_path)
        self.assertIn('"location_id":"linux-local-server-photos"', observed.evidence_summary_json or "")
        self.assertEqual(node.access_node_uuid, "linux-access-node:12345678901234567890123456789012345678901234")
        self.assertEqual(node.host_fingerprint_hash, "sha256:host")

    def test_registered_nas_share_binds_to_created_endpoint_without_identity_rewrite(self) -> None:
        appliance = NasApplianceRegistration(
            registration_uuid="11111111-1111-4111-8111-111111111111",
            friendly_name="Registered NAS",
            server_guid_hash="sha256:" + "1" * 64,
            server_guid_masked="sha256:…111111111111",
            network_host="nas.example.test",
            network_host_normalized="nas.example.test",
        )
        self.db.add(appliance)
        self.db.flush()
        share = NasShareRegistration(
            registration_uuid="22222222-2222-4222-8222-222222222222",
            nas_appliance_id=appliance.id,
            location_id="linux-nas-photo-organizer",
            display_name="Registered Photos",
            share_name="PhotoOrganizer",
            share_name_normalized="photoorganizer",
            identity_fingerprint_hash="sha256:nas",
            identity_fingerprint_version="source_endpoint_identity_v1",
        )
        self.db.add(share)
        self.db.commit()
        service = SourceCreationService(self.db, self.probes)
        request = SourceCreationPlanRequest(
            source_type="nas",
            location_id="linux-nas-photo-organizer",
            relative_root="family",
        )
        plan = service.plan(request)
        self.assertEqual(plan.plan_status, "ready")
        self.assertEqual(plan.device_name, "Registered Photos")
        self.assertEqual(plan.naming_action, "create_new")
        self.assertFalse(plan.name_decision_required)
        conflicting_plan = service.plan(
            request.model_copy(update={"device_name": "Operator-supplied conflicting label"})
        )
        self.assertEqual(conflicting_plan.device_name, "Registered Photos")
        self.assertEqual(conflicting_plan.plan_fingerprint, plan.plan_fingerprint)
        result = service.confirm(
            SourceCreationConfirmRequest(
                **request.model_dump(),
                plan_fingerprint=plan.plan_fingerprint,
                operator_confirmed=True,
            )
        )
        source = self.db.get(IngestionSource, result.source_profile_id)
        endpoint = self.db.get(SourceEndpoint, result.source_endpoint_id)
        assert source and endpoint
        self.db.refresh(share)
        self.assertEqual(share.source_endpoint_id, endpoint.id)
        self.assertEqual(endpoint.identity_fingerprint_hash, "sha256:nas")
        self.assertEqual(endpoint.alias, "Registered Photos")
        self.assertEqual(source.endpoint_id, endpoint.id)

    def test_registered_nas_share_root_requires_explicit_acknowledgment(self) -> None:
        service = SourceCreationService(self.db, self.probes)
        unacknowledged = service.plan(
            SourceCreationPlanRequest(
                source_type="nas",
                location_id="linux-nas-photo-organizer",
                relative_root="",
            )
        )
        self.assertEqual(unacknowledged.plan_status, "blocked")
        self.assertIn(
            "nas_folder_or_entire_share_required",
            {item.code for item in unacknowledged.blockers},
        )

        acknowledged = service.plan(
            SourceCreationPlanRequest(
                source_type="nas",
                location_id="linux-nas-photo-organizer",
                relative_root="",
                entire_endpoint_acknowledged=True,
            )
        )
        self.assertEqual(acknowledged.plan_status, "needs_review")
        self.assertTrue(acknowledged.entire_endpoint)
        self.assertEqual(acknowledged.entire_endpoint_label, "Entire share")

        conflicting = service.plan(
            SourceCreationPlanRequest(
                source_type="nas",
                location_id="linux-nas-photo-organizer",
                relative_root="family",
                entire_endpoint_acknowledged=True,
            )
        )
        self.assertEqual(conflicting.plan_status, "blocked")
        self.assertIn("nas_source_scope_conflict", {item.code for item in conflicting.blockers})

    def test_registered_nas_share_preserves_existing_endpoint_alias(self) -> None:
        appliance = NasApplianceRegistration(
            registration_uuid="33333333-3333-4333-8333-333333333333",
            friendly_name="Registered NAS",
            server_guid_hash="sha256:" + "3" * 64,
            server_guid_masked="sha256:…333333333333",
            network_host="nas.example.test",
            network_host_normalized="nas.example.test",
        )
        endpoint = SourceEndpoint(
            source_type="nas",
            alias="Historical Accepted Name",
            alias_normalized="historical accepted name",
            status="active",
            identity_fingerprint_hash="sha256:nas",
            identity_fingerprint_version="source_endpoint_identity_v1",
            identity_confidence="strong_match",
        )
        self.db.add_all([appliance, endpoint])
        self.db.flush()
        share = NasShareRegistration(
            registration_uuid="44444444-4444-4444-8444-444444444444",
            nas_appliance_id=appliance.id,
            location_id="linux-nas-photo-organizer",
            display_name="Newer Location Display",
            share_name="PhotoOrganizer",
            share_name_normalized="photoorganizer",
            identity_fingerprint_hash="sha256:nas",
            identity_fingerprint_version="source_endpoint_identity_v1",
            source_endpoint_id=endpoint.id,
        )
        self.db.add(share)
        self.db.commit()

        plan = SourceCreationService(self.db, self.probes).plan(
            SourceCreationPlanRequest(
                source_type="nas",
                location_id="linux-nas-photo-organizer",
                relative_root="another-family",
                naming_action="use_existing",
            )
        )

        self.assertEqual(plan.plan_status, "ready")
        self.assertEqual(plan.device_name, "Historical Accepted Name")
        self.assertEqual(plan.selected_existing_endpoint_id, endpoint.id)

    def test_mounted_creation_does_not_adopt_or_relink_legacy_profile(self) -> None:
        legacy = IngestionSource(
            source_label="Legacy Root",
            source_label_normalized="legacy root",
            source_type="local_folder",
            source_root_path="/mnt/photo-organizer-sources/local/server-photos/family",
            source_root_path_normalized="/mnt/photo-organizer-sources/local/server-photos/family",
            endpoint_relative_root=None,
            profile_status="active",
            endpoint_id=None,
        )
        self.db.add(legacy)
        self.db.commit()
        request = SourceCreationPlanRequest(
            source_type="local",
            location_id="linux-local-server-photos",
            relative_root="family",
            device_name="Mounted Local",
        )

        plan = SourceCreationService(self.db, self.probes).plan(request)

        self.assertEqual(plan.plan_status, "blocked")
        self.assertIn("mounted_legacy_source_conflict", {item.code for item in plan.blockers})
        self.assertIsNone(legacy.endpoint_id)
        self.assertIsNone(legacy.endpoint_relative_root)

    def test_local_and_nas_selection_derive_only_container_runtime_root(self) -> None:
        for source_type, expected in (
            ("local", "/app/sources/local/server-photos/family"),
            ("nas", "/app/sources/nas/photo-organizer/family"),
        ):
            with self.subTest(source_type=source_type):
                source, _endpoint = self._create(source_type)
                selection = SourceSelectionService(self.db, self.probes).select_source(
                    SourceSelectionRequest(source_profile_id=source.id)
                )
                self.assertEqual(selection.result, "selected")
                self.assertEqual(selection.selected_source_context.resolved_source_root, expected)
                self.assertEqual(source.endpoint_relative_root, "family")
                self.db.rollback()
                self.db.query(SourceEndpointObservedPath).delete()
                self.db.query(IngestionSource).delete()
                self.db.query(SourceEndpoint).delete()
                self.db.query(AccessNode).delete()
                self.db.commit()

    def test_changed_identity_blocks_selection(self) -> None:
        source, _endpoint = self._create("nas")
        self.probes.changed_fingerprint = True
        selection = SourceSelectionService(self.db, self.probes).select_source(
            SourceSelectionRequest(source_profile_id=source.id)
        )
        self.assertEqual(selection.result, "not_selected")
        self.assertEqual(selection.availability, "needs_attention")

    def test_missing_linux_location_evidence_blocks_selection(self) -> None:
        source, _endpoint = self._create("local")
        self.db.query(SourceEndpointObservedPath).delete()
        self.db.commit()

        selection = SourceSelectionService(self.db, self.probes).select_source(
            SourceSelectionRequest(source_profile_id=source.id)
        )

        self.assertEqual(selection.result, "not_selected")
        self.assertEqual(selection.availability, "needs_attention")
        self.assertIn("evidence is missing", selection.message)

    def test_another_profile_cannot_supply_mounted_location_evidence(self) -> None:
        source, endpoint = self._create("local")
        other = IngestionSource(
            source_label="Other Mounted Root",
            source_label_normalized="other mounted root",
            source_type=source.source_type,
            source_root_path="/mnt/photo-organizer-sources/local/server-photos/other",
            source_root_path_normalized="/mnt/photo-organizer-sources/local/server-photos/other",
            endpoint_relative_root="other",
            profile_status="active",
            endpoint_id=endpoint.id,
        )
        self.db.add(other)
        self.db.commit()

        selection = SourceSelectionService(self.db, self.probes).select_source(
            SourceSelectionRequest(source_profile_id=other.id)
        )

        self.assertEqual(selection.result, "not_selected")
        self.assertEqual(selection.availability, "needs_attention")
        self.assertIn("evidence is missing for this Profile root", selection.message)

    def test_dispatch_revalidates_and_passes_verified_runtime_root_to_existing_seam(self) -> None:
        for source_type, expected in (
            ("local", "/app/sources/local/server-photos/family"),
            ("nas", "/app/sources/nas/photo-organizer/family"),
        ):
            with self.subTest(source_type=source_type):
                source, _endpoint = self._create(source_type)
                persisted_profile_root = source.source_root_path
                selection_service = SourceSelectionService(self.db, self.probes)
                service = RunIngestionDispatchService(
                    self.db,
                    source_selection_service=selection_service,
                    probe_service=self.probes,
                )
                with patch(
                    "app.services.admin.run_ingestion_dispatch_service.get_ingestion_operation_guardrail_snapshot",
                    return_value=SimpleNamespace(blocked=False),
                ), patch(
                    "app.services.admin.run_ingestion_dispatch_service.start_source_intake",
                    return_value=SimpleNamespace(run_id=1, status="running"),
                ) as start:
                    result = service.dispatch(
                        RunIngestionDispatchRequest(
                            source_profile_id=source.id,
                            filesystem_options=RunIngestionFilesystemOptions(),
                        )
                    )
                self.assertEqual(result.result, "started")
                self.assertEqual(start.call_args.kwargs["ingestion_source_id"], source.id)
                self.assertEqual(start.call_args.kwargs["runtime_source_root_path"], expected)
                self.assertTrue(start.call_args.kwargs["selection_verified_identity"])
                self.assertEqual(source.source_root_path, persisted_profile_root)
                self.db.rollback()
                self.db.query(SourceEndpointObservedPath).delete()
                self.db.query(IngestionSource).delete()
                self.db.query(SourceEndpoint).delete()
                self.db.query(AccessNode).delete()
                self.db.commit()

    def test_dispatch_blocks_identity_change_after_selection(self) -> None:
        source, _endpoint = self._create("nas")
        self.probes.change_fingerprint_on_call = len(self.probes.requests) + 2
        service = RunIngestionDispatchService(
            self.db,
            source_selection_service=SourceSelectionService(self.db, self.probes),
            probe_service=self.probes,
        )

        with patch(
            "app.services.admin.run_ingestion_dispatch_service.start_source_intake",
        ) as start:
            result = service.dispatch(
                RunIngestionDispatchRequest(
                    source_profile_id=source.id,
                    filesystem_options=RunIngestionFilesystemOptions(),
                )
            )

        self.assertEqual(result.result, "blocked")
        self.assertEqual(result.status, "linux_identity_not_matched")
        start.assert_not_called()

    def test_client_cannot_supply_runtime_root(self) -> None:
        with self.assertRaises(ValidationError):
            RunIngestionDispatchRequest(source_profile_id=1, runtime_root="/app/storage")
        with self.assertRaises(ValidationError):
            SourceCreationPlanRequest(
                source_type="local",
                location_id="linux-local-server-photos",
                runtime_root="/app/storage",
            )
        with self.assertRaises(ValidationError):
            SourceIdentityProbeRequest(
                source_type="local",
                os_family="linux",
                location_id="linux-local-server-photos",
                runtime_root="/app/storage",
            )


if __name__ == "__main__":
    unittest.main()
