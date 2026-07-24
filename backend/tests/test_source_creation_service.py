from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.ingestion_source import IngestionSource
from app.models.ingestion_run import IngestionRun
from app.models.source_endpoint import (
    AccessNode,
    SourceEndpoint,
    SourceEndpointAliasEvent,
    SourceEndpointObservedPath,
)
from app.services.ingestion.ingestion_context_service import normalize_source_root_path
from app.services.source_identity.creation_schema import (
    SourceCreationConfirmRequest,
    SourceCreationPlanRequest,
)
from app.services.source_identity.creation_service import SourceCreationService
from app.services.source_identity.identity_fingerprint import (
    fingerprint_from_probe,
    optical_media_fingerprint_v2,
    volume_guid_fingerprint,
)
from app.services.source_identity.probe_schema import (
    AccessNodeSummary,
    SourceIdentityEvidenceItem,
    SourceIdentityProbeRequest,
    SourceIdentityProbeResponse,
    SourceRootCandidate,
)


class _FakeProbeService:
    def __init__(self, responses: dict[str, SourceIdentityProbeResponse]) -> None:
        self.responses = responses
        self.requests: list[SourceIdentityProbeRequest] = []

    def probe(self, request: SourceIdentityProbeRequest) -> SourceIdentityProbeResponse:
        self.requests.append(request)
        return self.responses[request.observed_path or ""]


class SourceCreationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        AccessNode.__table__.create(self.engine)
        SourceEndpoint.__table__.create(self.engine)
        SourceEndpointAliasEvent.__table__.create(self.engine)
        IngestionSource.__table__.create(self.engine)
        IngestionRun.__table__.create(self.engine)
        SourceEndpointObservedPath.__table__.create(self.engine)
        self.db = Session(self.engine)

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_external_creation_persists_drive_agnostic_root_and_full_guid_hash(self) -> None:
        path = "E:\\Archive\\Family Photos"
        probe = _volume_probe("external_device", path, boundary="external_folder")
        service = self._service(probe)

        plan = service.plan(
            SourceCreationPlanRequest(
                source_type="external",
                device_name="External 1",
                observed_path=path,
            )
        )

        self.assertEqual(plan.plan_status, "ready")
        self.assertEqual(plan.endpoint_relative_root, "Archive\\Family Photos")
        self.assertNotIn("E:", plan.endpoint_relative_root)
        self.assertEqual(plan.source_display_name, "Family Photos")
        self.assertEqual(plan.durable_identity_status, "verified")
        self.assertEqual(self.db.scalar(select(func.count(IngestionSource.id))), 0)

        result = service.confirm(
            SourceCreationConfirmRequest(
                source_type="external",
                device_name="External 1",
                observed_path=path,
                plan_fingerprint=plan.plan_fingerprint,
                operator_confirmed=True,
            )
        )

        self.assertEqual(result.creation_status, "completed")
        self.assertTrue(result.created_endpoint)
        self.assertTrue(result.created_source)
        source = self.db.get(IngestionSource, result.source_profile_id)
        endpoint = self.db.get(SourceEndpoint, result.source_endpoint_id)
        observed = self.db.get(SourceEndpointObservedPath, result.observed_path_id)
        self.assertEqual(source.endpoint_relative_root, "Archive\\Family Photos")
        self.assertEqual(source.source_label, "Family Photos")
        self.assertEqual(source.source_root_path, path)
        self.assertEqual(endpoint.identity_fingerprint_version, "source_endpoint_volume_guid_v2")
        self.assertEqual(endpoint.identity_fingerprint_hash, fingerprint_from_probe(probe).hash_value)
        self.assertNotIn("12345678-90ab-cdef-1234-567890abcdef", endpoint.evidence_summary_json or "")
        self.assertEqual(observed.observed_path, path)

    def test_local_creation_derives_relative_root(self) -> None:
        path = "C:\\Users\\chhen\\Pictures\\Scans"
        service = self._service(_volume_probe("local", path, boundary="local_folder"))

        plan = service.plan(
            SourceCreationPlanRequest(
                source_type="local",
                device_name="Chuck PC",
                observed_path=path,
            )
        )

        self.assertEqual(plan.endpoint_relative_root, "Users\\chhen\\Pictures\\Scans")
        self.assertEqual(plan.source_display_name, "Scans")
        self.assertFalse(plan.entire_endpoint)
        result = service.confirm(
            SourceCreationConfirmRequest(
                source_type="local",
                device_name="Chuck PC",
                observed_path=path,
                plan_fingerprint=plan.plan_fingerprint,
                operator_confirmed=True,
            )
        )
        source = self.db.get(IngestionSource, result.source_profile_id)
        observed = self.db.get(SourceEndpointObservedPath, result.observed_path_id)
        self.assertEqual(source.endpoint_relative_root, "Users\\chhen\\Pictures\\Scans")
        self.assertEqual(observed.observed_path, path)

    def test_whole_device_uses_empty_relative_root(self) -> None:
        path = "E:\\"
        service = self._service(_volume_probe("external_device", path, boundary="external_volume_root"))

        plan = service.plan(
            SourceCreationPlanRequest(
                source_type="external",
                device_name="External 1",
                observed_path=path,
            )
        )

        self.assertEqual(plan.endpoint_relative_root, "")
        self.assertTrue(plan.entire_endpoint)
        self.assertEqual(plan.entire_endpoint_label, "Entire device")
        self.assertEqual(plan.source_display_name, "Entire device")

    def test_whole_removable_uses_empty_relative_root_and_entire_medium(self) -> None:
        path = "H:\\"
        service = self._service(
            _volume_probe(
                "removable_media",
                path,
                boundary="removable_media_root",
                drive_type="removable",
            )
        )

        plan = service.plan(
            SourceCreationPlanRequest(
                source_type="removable",
                device_name="Camera SD Card",
                observed_path=path,
            )
        )

        self.assertEqual(plan.endpoint_relative_root, "")
        self.assertTrue(plan.entire_endpoint)
        self.assertEqual(plan.entire_endpoint_label, "Entire medium")
        self.assertEqual(plan.source_display_name, "Entire medium")
        self.assertEqual(plan.persisted_source_type, "removable_media")

    def test_whole_optical_disc_uses_empty_relative_root_and_entire_disc(self) -> None:
        path = "E:\\"
        probe = _optical_probe(path, boundary="optical_media_root")
        service = self._service(probe)

        plan = service.plan(
            SourceCreationPlanRequest(
                source_type="optical",
                device_name="12.63.18.6 Validation CD-RW",
                observed_path=path,
            )
        )

        self.assertEqual(plan.plan_status, "ready")
        self.assertEqual(plan.endpoint_relative_root, "")
        self.assertTrue(plan.entire_endpoint)
        self.assertEqual(plan.entire_endpoint_label, "Entire disc")
        self.assertEqual(plan.source_display_name, "Entire disc")
        self.assertEqual(plan.persisted_source_type, "optical_media")
        self.assertEqual(plan.durable_identity_status, "verified")

        result = service.confirm(
            SourceCreationConfirmRequest(
                source_type="optical",
                device_name="12.63.18.6 Validation CD-RW",
                observed_path=path,
                plan_fingerprint=plan.plan_fingerprint,
                operator_confirmed=True,
            )
        )
        source = self.db.get(IngestionSource, result.source_profile_id)
        endpoint = self.db.get(SourceEndpoint, result.source_endpoint_id)

        self.assertEqual(result.creation_status, "completed")
        self.assertEqual(source.source_type, "optical_media")
        self.assertEqual(source.endpoint_relative_root, "")
        self.assertEqual(endpoint.source_type, "optical_media")
        self.assertEqual(endpoint.identity_fingerprint_hash, fingerprint_from_probe(probe).hash_value)
        self.assertEqual(endpoint.identity_fingerprint_version, "optical_media_fingerprint_v2")

    def test_optical_subfolder_reuses_disc_endpoint_and_exact_source(self) -> None:
        whole_path = "E:\\"
        folder_path = "E:\\New folder"
        service = SourceCreationService(
            self.db,
            _FakeProbeService(
                {
                    whole_path: _optical_probe(whole_path, boundary="optical_media_root"),
                    folder_path: _optical_probe(folder_path, boundary="optical_media_folder"),
                }
            ),
        )
        whole = self._confirm(service, "optical", "12.63.18.6 Validation CD-RW", whole_path)

        folder_plan = service.plan(
            SourceCreationPlanRequest(
                source_type="optical",
                observed_path=folder_path,
                naming_action="use_existing",
            )
        )
        self.assertEqual(folder_plan.plan_status, "ready")
        self.assertEqual(folder_plan.endpoint_relative_root, "New folder")
        self.assertEqual(folder_plan.source_display_name, "New folder")
        folder = service.confirm(
            SourceCreationConfirmRequest(
                source_type="optical",
                observed_path=folder_path,
                naming_action="use_existing",
                plan_fingerprint=folder_plan.plan_fingerprint,
                operator_confirmed=True,
            )
        )

        repeat = service.plan(
            SourceCreationPlanRequest(
                source_type="optical",
                observed_path=folder_path,
                naming_action="use_existing",
            )
        )

        self.assertEqual(folder.source_endpoint_id, whole.source_endpoint_id)
        self.assertNotEqual(folder.source_profile_id, whole.source_profile_id)
        self.assertEqual(repeat.plan_status, "source_exists")
        self.assertEqual(repeat.existing_source_profile_id, folder.source_profile_id)
        self.assertEqual(self.db.scalar(select(func.count(SourceEndpoint.id))), 1)
        self.assertEqual(self.db.scalar(select(func.count(IngestionSource.id))), 2)

    def test_nas_unc_folder_and_whole_share_are_derived(self) -> None:
        folder = "\\\\HENDERSON-NAS\\Photos\\Dad Files\\Scans"
        share = "\\\\HENDERSON-NAS\\Photos"
        service = SourceCreationService(
            self.db,
            _FakeProbeService(
                {
                    folder: _nas_probe(folder, canonical_path=folder, boundary="nas_share_folder"),
                    share: _nas_probe(share, canonical_path=share, boundary="nas_share_root"),
                }
            ),
        )

        folder_plan = service.plan(
            SourceCreationPlanRequest(source_type="nas", device_name="Henderson NAS", observed_path=folder)
        )
        share_plan = service.plan(
            SourceCreationPlanRequest(source_type="nas", device_name="Henderson NAS", observed_path=share)
        )

        self.assertEqual(folder_plan.endpoint_relative_root, "Dad Files\\Scans")
        self.assertEqual(folder_plan.advanced_details["endpoint_boundary"], "\\\\HENDERSON-NAS\\Photos")
        self.assertEqual(folder_plan.source_display_name, "Scans")
        self.assertEqual(folder_plan.durable_identity_status, "verified")
        self.assertEqual(share_plan.endpoint_relative_root, "")
        self.assertEqual(share_plan.entire_endpoint_label, "Entire share")
        self.assertEqual(share_plan.source_display_name, "Entire share")
        self.assertEqual(share_plan.durable_identity_status, "verified")

    def test_source_display_name_uses_final_folder_and_parent_context_on_collision(self) -> None:
        first_path = "E:\\Archive\\Photos"
        second_path = "E:\\Backup\\Photos"
        service = SourceCreationService(
            self.db,
            _FakeProbeService(
                {
                    first_path: _volume_probe("external_device", first_path, boundary="external_folder"),
                    second_path: _volume_probe("external_device", second_path, boundary="external_folder"),
                }
            ),
        )

        first = self._confirm(service, "external", "External 1", first_path)
        first_source = self.db.get(IngestionSource, first.source_profile_id)
        self.assertEqual(first_source.source_label, "Photos")

        second_plan = service.plan(
            SourceCreationPlanRequest(
                source_type="external",
                observed_path=second_path,
                naming_action="use_existing",
            )
        )

        self.assertEqual(second_plan.source_display_name, "Backup - Photos")
        second = service.confirm(
            SourceCreationConfirmRequest(
                source_type="external",
                observed_path=second_path,
                naming_action="use_existing",
                plan_fingerprint=second_plan.plan_fingerprint,
                operator_confirmed=True,
            )
        )
        second_source = self.db.get(IngestionSource, second.source_profile_id)
        self.assertEqual(second_source.source_label, "Backup - Photos")

    def test_long_technical_relative_root_uses_final_folder_name(self) -> None:
        path = (
            "E:\\WD Backup.swstor\\hende\\NzRjMzVjZTUwYThiNGJjZT\\"
            "Volume{0cba1e6c-5d1c-4b78-b5de-154078db4e3d}\\Users\\hende\\Pictures\\2019-03-13"
        )
        service = self._service(_volume_probe("external_device", path, boundary="external_folder"))

        plan = service.plan(
            SourceCreationPlanRequest(
                source_type="external",
                device_name="External 10",
                observed_path=path,
            )
        )

        self.assertEqual(plan.source_display_name, "2019-03-13")
        self.assertIn("WD Backup.swstor", plan.endpoint_relative_root)

    def test_operator_source_name_is_trimmed_and_persisted_without_identity_change(self) -> None:
        path = "E:\\Archive\\Family Photos"
        service = self._service(_volume_probe("external_device", path, boundary="external_folder"))

        plan = service.plan(
            SourceCreationPlanRequest(
                source_type="external",
                device_name="External 1",
                source_name="  2019 Vacation Photos  ",
                observed_path=path,
            )
        )

        self.assertEqual(plan.source_display_name, "2019 Vacation Photos")
        self.assertEqual(plan.suggested_source_name, "Family Photos")
        result = service.confirm(
            SourceCreationConfirmRequest(
                source_type="external",
                device_name="External 1",
                source_name="  2019 Vacation Photos  ",
                observed_path=path,
                plan_fingerprint=plan.plan_fingerprint,
                operator_confirmed=True,
            )
        )
        source = self.db.get(IngestionSource, result.source_profile_id)
        self.assertEqual(source.source_label, "2019 Vacation Photos")
        self.assertEqual(source.endpoint_relative_root, "Archive\\Family Photos")

    def test_blank_or_conflicting_source_name_is_blocked(self) -> None:
        first_path = "E:\\Archive\\Photos"
        second_path = "E:\\Backup\\Photos"
        service = SourceCreationService(
            self.db,
            _FakeProbeService(
                {
                    first_path: _volume_probe("external_device", first_path, boundary="external_folder"),
                    second_path: _volume_probe("external_device", second_path, boundary="external_folder"),
                }
            ),
        )
        self._confirm(service, "external", "External 1", first_path)

        blank = service.plan(
            SourceCreationPlanRequest(
                source_type="external",
                observed_path=second_path,
                source_name="   ",
                naming_action="use_existing",
            )
        )
        self.assertEqual(blank.plan_status, "blocked")
        self.assertIn("source_name_required", [item.code for item in blank.blockers])

        conflict = service.plan(
            SourceCreationPlanRequest(
                source_type="external",
                observed_path=second_path,
                source_name="Photos",
                naming_action="use_existing",
            )
        )
        self.assertEqual(conflict.plan_status, "blocked")
        self.assertIn("source_name_conflict", [item.code for item in conflict.blockers])
        self.assertEqual(conflict.source_name_suggested_alternative, "Backup - Photos")

    def test_mapped_nas_persists_canonical_unc_and_original_observed_path(self) -> None:
        mapped = "Z:\\Dad Files\\Scans"
        canonical = "\\\\HENDERSON-NAS\\Photos\\Dad Files\\Scans"
        service = self._service(
            _nas_probe(mapped, canonical_path=canonical, boundary="nas_share_folder")
        )
        plan = service.plan(
            SourceCreationPlanRequest(source_type="nas", device_name="Henderson NAS", observed_path=mapped)
        )
        result = service.confirm(
            SourceCreationConfirmRequest(
                source_type="nas",
                device_name="Henderson NAS",
                observed_path=mapped,
                plan_fingerprint=plan.plan_fingerprint,
                operator_confirmed=True,
            )
        )

        source = self.db.get(IngestionSource, result.source_profile_id)
        observed = self.db.get(SourceEndpointObservedPath, result.observed_path_id)
        self.assertEqual(source.source_root_path, canonical)
        self.assertEqual(source.endpoint_relative_root, "Dad Files\\Scans")
        self.assertEqual(observed.observed_path, mapped)
        self.assertEqual(observed.source_root_candidate_path, canonical)

    def test_unresolved_mapped_nas_creates_no_rows(self) -> None:
        mapped = "Z:\\Dad Files"
        blocker = SourceIdentityEvidenceItem(
            category="network_share_evidence",
            code="mapped_nas_unc_resolution_failed",
            status="blocked",
            source_types=["nas"],
            message="Enter the UNC path instead.",
        )
        probe = _nas_probe(
            mapped,
            canonical_path=mapped,
            boundary="unknown",
            valid=False,
            blockers=[blocker],
            probe_status="blocked",
        )
        service = self._service(probe)

        plan = service.plan(
            SourceCreationPlanRequest(source_type="nas", device_name="Henderson NAS", observed_path=mapped)
        )

        self.assertEqual(plan.plan_status, "blocked")
        self.assertEqual(self.db.scalar(select(func.count(SourceEndpoint.id))), 0)
        self.assertEqual(self.db.scalar(select(func.count(IngestionSource.id))), 0)

    def test_existing_endpoint_is_reused_and_different_root_creates_new_source(self) -> None:
        first_path = "E:\\Archive"
        second_path = "E:\\Family Photos"
        first_probe = _volume_probe("external_device", first_path, boundary="external_folder")
        second_probe = _volume_probe("external_device", second_path, boundary="external_folder")
        service = SourceCreationService(
            self.db,
            _FakeProbeService({first_path: first_probe, second_path: second_probe}),
        )
        first = self._confirm(service, "external", "External 1", first_path)

        recognition = service.plan(
            SourceCreationPlanRequest(
                source_type="external",
                observed_path=second_path,
            )
        )
        self.assertEqual(recognition.recognition_status, "existing_device")
        self.assertEqual(recognition.device_name, "External 1")
        self.assertEqual(recognition.plan_status, "needs_review")

        second_plan = service.plan(
            SourceCreationPlanRequest(
                source_type="external",
                observed_path=second_path,
                naming_action="use_existing",
            )
        )
        self.assertEqual(second_plan.endpoint_action, "reuse_existing_endpoint")
        self.assertEqual(second_plan.device_name, "External 1")
        self.assertEqual(second_plan.plan_status, "ready")
        second = service.confirm(
            SourceCreationConfirmRequest(
                source_type="external",
                observed_path=second_path,
                naming_action="use_existing",
                plan_fingerprint=second_plan.plan_fingerprint,
                operator_confirmed=True,
            )
        )

        self.assertEqual(second.source_endpoint_id, first.source_endpoint_id)
        self.assertNotEqual(second.source_profile_id, first.source_profile_id)
        self.assertTrue(second.created_source)
        self.assertEqual(self.db.scalar(select(func.count(SourceEndpoint.id))), 1)

    def test_same_endpoint_and_relative_root_reuses_existing_source(self) -> None:
        path = "E:\\Archive"
        service = self._service(_volume_probe("external_device", path, boundary="external_folder"))
        first = self._confirm(service, "external", "External 1", path)

        plan = service.plan(
            SourceCreationPlanRequest(
                source_type="external",
                observed_path=path,
                naming_action="use_existing",
            )
        )
        self.assertEqual(plan.plan_status, "source_exists")
        self.assertEqual(plan.existing_source_profile_id, first.source_profile_id)
        second = service.confirm(
            SourceCreationConfirmRequest(
                source_type="external",
                observed_path=path,
                naming_action="use_existing",
                plan_fingerprint=plan.plan_fingerprint,
                operator_confirmed=True,
            )
        )

        self.assertEqual(second.source_profile_id, first.source_profile_id)
        self.assertTrue(second.reused_source)
        self.assertFalse(second.created_source)
        self.assertEqual(self.db.scalar(select(func.count(IngestionSource.id))), 1)
        self.assertEqual(self.db.scalar(select(func.count(SourceEndpointObservedPath.id))), 1)

    def test_legacy_fingerprint_requires_review_then_upgrades_transactionally(self) -> None:
        path = "E:\\Archive"
        probe = _volume_probe("external_device", path, boundary="external_folder")
        fingerprint = fingerprint_from_probe(probe)
        legacy = SourceEndpoint(
            source_type="external_device",
            alias="Known External",
            alias_normalized="known external",
            status="active",
            identity_fingerprint_hash=fingerprint.legacy_hashes[0],
            identity_fingerprint_version="source_endpoint_identity_v1",
            identity_confidence="strong_match",
        )
        self.db.add(legacy)
        self.db.commit()
        self.db.refresh(legacy)
        service = self._service(probe)

        review = service.plan(
            SourceCreationPlanRequest(
                source_type="external",
                device_name="External 1",
                observed_path=path,
            )
        )
        self.assertEqual(review.plan_status, "needs_review")
        self.assertEqual(review.endpoint_action, "upgrade_legacy_endpoint")
        self.assertEqual(review.device_name, "Known External")

        ready = service.plan(
            SourceCreationPlanRequest(
                source_type="external",
                device_name="External 1",
                observed_path=path,
                selected_existing_endpoint_id=legacy.id,
                naming_action="use_existing",
                operator_review_acknowledged=True,
            )
        )
        result = service.confirm(
            SourceCreationConfirmRequest(
                source_type="external",
                device_name="External 1",
                observed_path=path,
                selected_existing_endpoint_id=legacy.id,
                naming_action="use_existing",
                operator_review_acknowledged=True,
                plan_fingerprint=ready.plan_fingerprint,
                operator_confirmed=True,
            )
        )

        self.db.refresh(legacy)
        self.assertTrue(result.upgraded_legacy_endpoint)
        self.assertEqual(legacy.identity_fingerprint_hash, fingerprint.hash_value)
        self.assertEqual(legacy.identity_fingerprint_version, "source_endpoint_volume_guid_v2")
        self.assertEqual(self.db.scalar(select(func.count(SourceEndpoint.id))), 1)

    def test_legacy_endpoint_can_be_safely_revalidated_from_observed_path(self) -> None:
        requested_path = "E:\\"
        prior_path = "E:\\Archive\\2017"
        requested_probe = _volume_probe(
            "external_device",
            requested_path,
            boundary="external_volume_root",
        )
        prior_probe = _volume_probe(
            "external_device",
            prior_path,
            boundary="external_folder",
        )
        access_node = AccessNode(
            access_node_uuid="legacy-access-node",
            label="Legacy Access Node",
            os_family="windows",
            provider_name="fake_probe",
            provider_version="1",
            status="active",
        )
        legacy = SourceEndpoint(
            source_type="external_device",
            alias="Known External",
            alias_normalized="known external",
            status="active",
            identity_fingerprint_hash="sha256:unreproducible-legacy-hash",
            identity_fingerprint_version=None,
            identity_confidence="medium_needs_review",
            created_from_access_node=access_node,
        )
        observed = SourceEndpointObservedPath(
            source_endpoint=legacy,
            access_node=access_node,
            observed_path=prior_path,
            normalized_observed_path=prior_path.casefold(),
            filesystem_boundary_type="external_folder",
            is_valid_source_root_candidate=True,
        )
        self.db.add_all([access_node, legacy, observed])
        self.db.commit()
        self.db.refresh(legacy)
        service = SourceCreationService(
            self.db,
            _FakeProbeService(
                {
                    requested_path: requested_probe,
                    prior_path: prior_probe,
                }
            ),
        )

        review = service.plan(
            SourceCreationPlanRequest(
                source_type="external",
                device_name="New Name",
                observed_path=requested_path,
            )
        )

        self.assertEqual(review.plan_status, "needs_review")
        self.assertEqual(review.endpoint_action, "upgrade_legacy_endpoint")
        self.assertEqual(review.selected_existing_endpoint_id, legacy.id)
        self.assertEqual(review.advanced_details["revalidated_legacy_match_count"], 1)

        ready = service.plan(
            SourceCreationPlanRequest(
                source_type="external",
                device_name="New Name",
                observed_path=requested_path,
                selected_existing_endpoint_id=legacy.id,
                naming_action="use_existing",
                operator_review_acknowledged=True,
            )
        )
        result = service.confirm(
            SourceCreationConfirmRequest(
                source_type="external",
                device_name="New Name",
                observed_path=requested_path,
                selected_existing_endpoint_id=legacy.id,
                naming_action="use_existing",
                operator_review_acknowledged=True,
                plan_fingerprint=ready.plan_fingerprint,
                operator_confirmed=True,
            )
        )

        self.db.refresh(legacy)
        self.assertEqual(result.creation_status, "completed")
        self.assertTrue(result.upgraded_legacy_endpoint)
        self.assertEqual(legacy.identity_fingerprint_hash, fingerprint_from_probe(requested_probe).hash_value)
        self.assertEqual(self.db.scalar(select(func.count(SourceEndpoint.id))), 1)

    def test_overlap_is_warning_not_blocker(self) -> None:
        root = "E:\\Archive"
        nested = "E:\\Archive\\Family"
        service = SourceCreationService(
            self.db,
            _FakeProbeService(
                {
                    root: _volume_probe("external_device", root, boundary="external_folder"),
                    nested: _volume_probe("external_device", nested, boundary="external_folder"),
                }
            ),
        )
        self._confirm(service, "external", "External 1", root)

        plan = service.plan(
            SourceCreationPlanRequest(
                source_type="external",
                observed_path=nested,
                naming_action="use_existing",
            )
        )

        self.assertEqual(plan.plan_status, "ready")
        self.assertIn("source_root_overlap", [item.code for item in plan.warnings])

    def test_path_first_identification_requires_name_only_after_recognition(self) -> None:
        path = "E:\\Archive"
        service = self._service(_volume_probe("external_device", path, boundary="external_folder"))

        plan = service.plan(SourceCreationPlanRequest(source_type="external", observed_path=path))

        self.assertEqual(plan.plan_status, "needs_review")
        self.assertEqual(plan.recognition_status, "new_device")
        self.assertTrue(plan.name_decision_required)
        self.assertIn("device_name_required", [item.code for item in plan.required_confirmations])
        self.assertEqual(self.db.scalar(select(func.count(SourceEndpoint.id))), 0)
        self.assertEqual(self.db.scalar(select(func.count(IngestionSource.id))), 0)

    def test_endpoint_rename_preserves_identity_sources_and_records_audit(self) -> None:
        first_path = "E:\\Archive"
        second_path = "E:\\Family"
        service = SourceCreationService(
            self.db,
            _FakeProbeService(
                {
                    first_path: _volume_probe("external_device", first_path, boundary="external_folder"),
                    second_path: _volume_probe("external_device", second_path, boundary="external_folder"),
                }
            ),
        )
        first = self._confirm(service, "external", "Old Device", first_path)
        endpoint = self.db.get(SourceEndpoint, first.source_endpoint_id)
        source = self.db.get(IngestionSource, first.source_profile_id)
        original_fingerprint = endpoint.identity_fingerprint_hash
        original_source_label = source.source_label
        original_source_root = source.source_root_path
        original_relative_root = source.endpoint_relative_root
        observed_ids = set(self.db.scalars(select(SourceEndpointObservedPath.id)).all())

        plan = service.plan(
            SourceCreationPlanRequest(
                source_type="external",
                observed_path=second_path,
                device_name="New Device",
                naming_action="rename_existing",
            )
        )
        result = service.confirm(
            SourceCreationConfirmRequest(
                source_type="external",
                observed_path=second_path,
                device_name="New Device",
                naming_action="rename_existing",
                plan_fingerprint=plan.plan_fingerprint,
                operator_confirmed=True,
            )
        )

        self.db.refresh(endpoint)
        self.db.refresh(source)
        event = self.db.scalar(select(SourceEndpointAliasEvent))
        self.assertEqual(result.source_endpoint_id, first.source_endpoint_id)
        self.assertTrue(result.renamed_endpoint)
        self.assertEqual(endpoint.alias, "New Device")
        self.assertEqual(endpoint.identity_fingerprint_hash, original_fingerprint)
        self.assertEqual(source.source_label, original_source_label)
        self.assertEqual(source.source_root_path, original_source_root)
        self.assertEqual(source.endpoint_relative_root, original_relative_root)
        self.assertTrue(observed_ids.issubset(set(self.db.scalars(select(SourceEndpointObservedPath.id)).all())))
        self.assertEqual(event.source_endpoint_id, endpoint.id)
        self.assertEqual(event.old_alias, "Old Device")
        self.assertEqual(event.new_alias, "New Device")

    def test_case_only_rename_is_allowed_but_other_endpoint_alias_collision_blocks(self) -> None:
        path = "E:\\Archive"
        service = self._service(_volume_probe("external_device", path, boundary="external_folder"))
        first = self._confirm(service, "external", "Photo Drive", path)
        collision = SourceEndpoint(
            source_type="local",
            alias="Taken Name",
            alias_normalized="taken name",
            identity_confidence="strong_match",
        )
        self.db.add(collision)
        self.db.commit()

        case_plan = service.plan(
            SourceCreationPlanRequest(
                source_type="external",
                observed_path=path,
                device_name="PHOTO DRIVE",
                naming_action="rename_existing",
            )
        )
        case_result = service.confirm(
            SourceCreationConfirmRequest(
                source_type="external",
                observed_path=path,
                device_name="PHOTO DRIVE",
                naming_action="rename_existing",
                plan_fingerprint=case_plan.plan_fingerprint,
                operator_confirmed=True,
            )
        )
        self.assertEqual(case_result.creation_status, "completed")
        self.assertEqual(case_result.source_endpoint_id, first.source_endpoint_id)

        collision_plan = service.plan(
            SourceCreationPlanRequest(
                source_type="external",
                observed_path=path,
                device_name="Taken Name",
                naming_action="rename_existing",
            )
        )
        self.assertEqual(collision_plan.plan_status, "blocked")
        self.assertIn("device_name_conflict", [item.code for item in collision_plan.blockers])

    def test_rename_rolls_back_when_later_confirm_step_fails(self) -> None:
        first_path = "E:\\Archive"
        second_path = "E:\\Family"
        service = SourceCreationService(
            self.db,
            _FakeProbeService(
                {
                    first_path: _volume_probe("external_device", first_path, boundary="external_folder"),
                    second_path: _volume_probe("external_device", second_path, boundary="external_folder"),
                }
            ),
        )
        first = self._confirm(service, "external", "Original", first_path)
        endpoint = self.db.get(SourceEndpoint, first.source_endpoint_id)
        plan = service.plan(
            SourceCreationPlanRequest(
                source_type="external",
                observed_path=second_path,
                device_name="Changed",
                naming_action="rename_existing",
            )
        )

        with patch.object(service, "_get_or_create_observed_path", side_effect=RuntimeError("test failure")):
            with self.assertRaises(RuntimeError):
                service.confirm(
                    SourceCreationConfirmRequest(
                        source_type="external",
                        observed_path=second_path,
                        device_name="Changed",
                        naming_action="rename_existing",
                        plan_fingerprint=plan.plan_fingerprint,
                        operator_confirmed=True,
                    )
                )

        self.db.expire_all()
        self.assertEqual(self.db.get(SourceEndpoint, endpoint.id).alias, "Original")
        self.assertEqual(self.db.scalar(select(func.count(SourceEndpointAliasEvent.id))), 0)
        self.assertEqual(self.db.scalar(select(func.count(IngestionSource.id))), 1)

    def test_volume_guid_matches_across_local_external_and_retains_registered_type(self) -> None:
        first_path = "E:\\Archive"
        second_path = "E:\\Family"
        service = SourceCreationService(
            self.db,
            _FakeProbeService(
                {
                    first_path: _volume_probe("external_device", first_path, boundary="external_folder"),
                    second_path: _volume_probe("local", second_path, boundary="local_folder"),
                }
            ),
        )
        first = self._confirm(service, "external", "External Device", first_path)

        recognition = service.plan(
            SourceCreationPlanRequest(source_type="local", observed_path=second_path)
        )
        self.assertEqual(recognition.selected_existing_endpoint_id, first.source_endpoint_id)
        self.assertTrue(recognition.source_type_mismatch)
        self.assertEqual(recognition.recognized_source_type, "external")
        self.assertEqual(recognition.plan_status, "needs_review")

        endpoint_count = self.db.scalar(select(func.count(SourceEndpoint.id)))
        source_count = self.db.scalar(select(func.count(IngestionSource.id)))
        cancelled = service.plan(
            SourceCreationPlanRequest(
                source_type="local",
                observed_path=second_path,
                naming_action="cancel",
                use_registered_source_type=True,
            )
        )
        self.assertEqual(cancelled.plan_status, "blocked")
        self.assertEqual(self.db.scalar(select(func.count(SourceEndpoint.id))), endpoint_count)
        self.assertEqual(self.db.scalar(select(func.count(IngestionSource.id))), source_count)

        ready = service.plan(
            SourceCreationPlanRequest(
                source_type="local",
                observed_path=second_path,
                naming_action="use_existing",
                use_registered_source_type=True,
            )
        )
        result = service.confirm(
            SourceCreationConfirmRequest(
                source_type="local",
                observed_path=second_path,
                naming_action="use_existing",
                use_registered_source_type=True,
                plan_fingerprint=ready.plan_fingerprint,
                operator_confirmed=True,
            )
        )
        endpoint = self.db.get(SourceEndpoint, first.source_endpoint_id)
        source = self.db.get(IngestionSource, result.source_profile_id)
        self.assertEqual(endpoint.source_type, "external_device")
        self.assertEqual(source.source_type, "external_drive")

    def test_strong_match_is_not_displaced_by_weaker_legacy_candidate(self) -> None:
        first_path = "E:\\Archive"
        second_path = "E:\\Family"
        first_probe = _volume_probe("external_device", first_path, boundary="external_folder")
        second_probe = _volume_probe("external_device", second_path, boundary="external_folder")
        service = SourceCreationService(
            self.db,
            _FakeProbeService({first_path: first_probe, second_path: second_probe}),
        )
        strong_result = self._confirm(service, "external", "Strong Device", first_path)
        fingerprint = fingerprint_from_probe(first_probe)
        legacy = SourceEndpoint(
            source_type="external_device",
            alias="Legacy Candidate",
            alias_normalized="legacy candidate",
            status="active",
            identity_fingerprint_hash=fingerprint.legacy_hashes[0],
            identity_fingerprint_version="source_endpoint_identity_v1",
            identity_confidence="medium_needs_review",
        )
        self.db.add(legacy)
        self.db.commit()

        plan = service.plan(
            SourceCreationPlanRequest(source_type="external", observed_path=second_path)
        )

        self.assertEqual(plan.selected_existing_endpoint_id, strong_result.source_endpoint_id)
        self.assertEqual(
            [match.source_endpoint_id for match in plan.possible_matches],
            [strong_result.source_endpoint_id],
        )

    def test_inactive_modern_source_reactivates_same_profile(self) -> None:
        path = "E:\\Archive"
        service = self._service(_volume_probe("external_device", path, boundary="external_folder"))
        first = self._confirm(service, "external", "External", path)
        source = self.db.get(IngestionSource, first.source_profile_id)
        source.profile_status = "inactive"
        self.db.commit()

        plan = service.plan(
            SourceCreationPlanRequest(
                source_type="external",
                observed_path=path,
                naming_action="use_existing",
            )
        )
        self.assertEqual(plan.source_action, "reactivate_existing_source")
        result = service.confirm(
            SourceCreationConfirmRequest(
                source_type="external",
                observed_path=path,
                naming_action="use_existing",
                plan_fingerprint=plan.plan_fingerprint,
                operator_confirmed=True,
            )
        )
        self.db.refresh(source)
        self.assertEqual(result.source_profile_id, first.source_profile_id)
        self.assertTrue(result.reactivated_source)
        self.assertEqual(source.profile_status, "active")
        self.assertEqual(self.db.scalar(select(func.count(IngestionSource.id))), 1)

    def test_active_unlinked_legacy_is_adopted_while_inactive_modern_conflict_remains(self) -> None:
        path = "E:\\Archive"
        service = self._service(_volume_probe("external_device", path, boundary="external_folder"))
        modern_result = self._confirm(service, "external", "Registered Device", path)
        modern = self.db.get(IngestionSource, modern_result.source_profile_id)
        modern.profile_status = "inactive"
        legacy = IngestionSource(
            source_label="Established Legacy Source",
            source_label_normalized="established legacy source",
            source_type="external_drive",
            source_root_path=path,
            source_root_path_normalized=normalize_source_root_path(path),
            endpoint_relative_root=None,
            profile_status="active",
            endpoint_id=None,
        )
        self.db.add(legacy)
        self.db.commit()
        self.db.refresh(legacy)

        plan = service.plan(
            SourceCreationPlanRequest(
                source_type="external",
                observed_path=path,
                naming_action="use_existing",
            )
        )
        self.assertEqual(plan.source_action, "adopt_legacy_source")
        self.assertEqual(plan.existing_source_profile_id, legacy.id)
        self.assertEqual(plan.conflicting_source_profile_ids, [modern.id])
        result = service.confirm(
            SourceCreationConfirmRequest(
                source_type="external",
                observed_path=path,
                naming_action="use_existing",
                plan_fingerprint=plan.plan_fingerprint,
                operator_confirmed=True,
            )
        )

        self.db.refresh(legacy)
        self.db.refresh(modern)
        self.assertEqual(result.source_profile_id, legacy.id)
        self.assertTrue(result.adopted_legacy_source)
        self.assertEqual(legacy.endpoint_id, modern_result.source_endpoint_id)
        self.assertEqual(legacy.endpoint_relative_root, "Archive")
        self.assertEqual(legacy.source_root_path, path)
        self.assertEqual(modern.profile_status, "inactive")
        self.assertEqual(self.db.scalar(select(func.count(IngestionSource.id))), 2)

    def test_linked_legacy_source_is_canonicalized_while_inactive_duplicate_remains(self) -> None:
        share = "\\\\HENDERSON-NAS\\Photos"
        folder = "\\\\HENDERSON-NAS\\Photos\\Camera imports"
        service = SourceCreationService(
            self.db,
            _FakeProbeService(
                {
                    share: _nas_probe(share, canonical_path=share, boundary="nas_share_root"),
                    folder: _nas_probe(folder, canonical_path=folder, boundary="nas_share_folder"),
                }
            ),
        )
        endpoint_result = self._confirm(service, "nas", "Henderson NAS", share)
        active_legacy = IngestionSource(
            source_label="Camera imports",
            source_label_normalized="camera imports",
            source_type="local_folder",
            source_root_path=folder,
            source_root_path_normalized=normalize_source_root_path(folder),
            endpoint_id=endpoint_result.source_endpoint_id,
            endpoint_relative_root=None,
            profile_status="active",
        )
        inactive_legacy = IngestionSource(
            source_label="Camera imports validation duplicate",
            source_label_normalized="camera imports validation duplicate",
            source_type="local_folder",
            source_root_path=folder,
            source_root_path_normalized=normalize_source_root_path(folder),
            endpoint_id=endpoint_result.source_endpoint_id,
            endpoint_relative_root=None,
            profile_status="inactive",
        )
        self.db.add_all([active_legacy, inactive_legacy])
        self.db.commit()
        self.db.refresh(active_legacy)
        self.db.refresh(inactive_legacy)

        plan = service.plan(
            SourceCreationPlanRequest(
                source_type="nas",
                observed_path=folder,
                naming_action="use_existing",
            )
        )

        self.assertEqual(plan.source_action, "canonicalize_existing_source")
        self.assertEqual(plan.final_action_label, "Use and Canonicalize Existing Source")
        self.assertEqual(plan.existing_source_profile_id, active_legacy.id)
        self.assertEqual(plan.conflicting_source_profile_ids, [inactive_legacy.id])
        result = service.confirm(
            SourceCreationConfirmRequest(
                source_type="nas",
                observed_path=folder,
                naming_action="use_existing",
                plan_fingerprint=plan.plan_fingerprint,
                operator_confirmed=True,
            )
        )

        self.db.refresh(active_legacy)
        self.db.refresh(inactive_legacy)
        self.assertEqual(result.source_profile_id, active_legacy.id)
        self.assertTrue(result.canonicalized_source)
        self.assertFalse(result.created_source)
        self.assertEqual(active_legacy.endpoint_relative_root, "Camera imports")
        self.assertEqual(active_legacy.profile_status, "active")
        self.assertEqual(inactive_legacy.endpoint_relative_root, None)
        self.assertEqual(inactive_legacy.profile_status, "inactive")

    def test_active_no_history_duplicate_can_be_explicitly_marked_inactive(self) -> None:
        path = "E:\\Archive"
        service = self._service(_volume_probe("external_device", path, boundary="external_folder"))
        canonical_result = self._confirm(service, "external", "External", path)
        duplicate = IngestionSource(
            source_label="Duplicate No History",
            source_label_normalized="duplicate no history",
            source_type="external_drive",
            source_root_path=path,
            source_root_path_normalized=normalize_source_root_path(path),
            profile_status="active",
        )
        self.db.add(duplicate)
        self.db.commit()
        self.db.refresh(duplicate)

        blocked = service.plan(
            SourceCreationPlanRequest(
                source_type="external",
                observed_path=path,
                naming_action="use_existing",
            )
        )
        self.assertEqual(blocked.plan_status, "blocked")

        plan = service.plan(
            SourceCreationPlanRequest(
                source_type="external",
                observed_path=path,
                naming_action="use_existing",
                selected_canonical_source_id=canonical_result.source_profile_id,
                duplicate_source_ids_to_inactivate=[duplicate.id],
            )
        )
        self.assertEqual(plan.plan_status, "source_exists")
        self.assertEqual(plan.duplicate_source_ids_to_inactivate, [duplicate.id])
        result = service.confirm(
            SourceCreationConfirmRequest(
                source_type="external",
                observed_path=path,
                naming_action="use_existing",
                selected_canonical_source_id=canonical_result.source_profile_id,
                duplicate_source_ids_to_inactivate=[duplicate.id],
                plan_fingerprint=plan.plan_fingerprint,
                operator_confirmed=True,
            )
        )
        self.db.refresh(duplicate)
        self.assertEqual(result.inactivated_duplicate_source_ids, [duplicate.id])
        self.assertEqual(duplicate.profile_status, "inactive")

    def test_history_bearing_duplicate_cannot_be_marked_inactive(self) -> None:
        path = "E:\\Archive"
        service = self._service(_volume_probe("external_device", path, boundary="external_folder"))
        canonical_result = self._confirm(service, "external", "External", path)
        duplicate = IngestionSource(
            source_label="Duplicate With History",
            source_label_normalized="duplicate with history",
            source_type="external_drive",
            source_root_path=path,
            source_root_path_normalized=normalize_source_root_path(path),
            profile_status="active",
        )
        self.db.add(duplicate)
        self.db.flush()
        self.db.add(IngestionRun(ingestion_source_id=duplicate.id, from_path=path))
        self.db.commit()
        self.db.refresh(duplicate)

        plan = service.plan(
            SourceCreationPlanRequest(
                source_type="external",
                observed_path=path,
                naming_action="use_existing",
                selected_canonical_source_id=canonical_result.source_profile_id,
                duplicate_source_ids_to_inactivate=[duplicate.id],
            )
        )

        self.assertEqual(plan.plan_status, "blocked")
        self.assertIn("duplicate_source_has_history", [item.code for item in plan.blockers])
        self.db.refresh(duplicate)
        self.assertEqual(duplicate.profile_status, "active")

    def test_inactive_unlinked_legacy_is_adopted_and_reactivated(self) -> None:
        registered_path = "E:\\Registered"
        legacy_path = "E:\\Legacy"
        service = SourceCreationService(
            self.db,
            _FakeProbeService(
                {
                    registered_path: _volume_probe("external_device", registered_path, boundary="external_folder"),
                    legacy_path: _volume_probe("external_device", legacy_path, boundary="external_folder"),
                }
            ),
        )
        endpoint_result = self._confirm(service, "external", "Registered", registered_path)
        legacy = IngestionSource(
            source_label="Inactive Legacy",
            source_label_normalized="inactive legacy",
            source_type="external_drive",
            source_root_path=legacy_path,
            source_root_path_normalized=normalize_source_root_path(legacy_path),
            endpoint_relative_root=None,
            profile_status="inactive",
            endpoint_id=None,
        )
        self.db.add(legacy)
        self.db.commit()
        self.db.refresh(legacy)

        plan = service.plan(
            SourceCreationPlanRequest(
                source_type="external",
                observed_path=legacy_path,
                naming_action="use_existing",
            )
        )
        self.assertEqual(plan.source_action, "adopt_and_reactivate_source")
        result = service.confirm(
            SourceCreationConfirmRequest(
                source_type="external",
                observed_path=legacy_path,
                naming_action="use_existing",
                plan_fingerprint=plan.plan_fingerprint,
                operator_confirmed=True,
            )
        )
        self.db.refresh(legacy)
        self.assertEqual(result.source_profile_id, legacy.id)
        self.assertEqual(legacy.endpoint_id, endpoint_result.source_endpoint_id)
        self.assertEqual(legacy.profile_status, "active")
        self.assertTrue(result.reactivated_source)
        self.assertTrue(result.adopted_legacy_source)

    def test_multiple_active_exact_sources_block_and_create_nothing(self) -> None:
        path = "E:\\Archive"
        service = self._service(_volume_probe("external_device", path, boundary="external_folder"))
        first = self._confirm(service, "external", "External", path)
        legacy = IngestionSource(
            source_label="Other Active",
            source_label_normalized="other active",
            source_type="external_drive",
            source_root_path=path,
            source_root_path_normalized=normalize_source_root_path(path),
            profile_status="active",
        )
        self.db.add(legacy)
        self.db.commit()

        plan = service.plan(
            SourceCreationPlanRequest(
                source_type="external",
                observed_path=path,
                naming_action="use_existing",
            )
        )
        self.assertEqual(plan.plan_status, "blocked")
        self.assertEqual(plan.recognition_status, "multiple_source_matches")
        blocked = service.confirm(
            SourceCreationConfirmRequest(
                source_type="external",
                observed_path=path,
                naming_action="use_existing",
                plan_fingerprint=plan.plan_fingerprint,
                operator_confirmed=True,
            )
        )
        self.assertEqual(blocked.creation_status, "blocked")
        self.assertEqual(self.db.scalar(select(func.count(IngestionSource.id))), 2)
        self.assertEqual(self.db.get(IngestionSource, first.source_profile_id).profile_status, "active")

    def test_archived_test_and_deprecated_exact_sources_require_management_review(self) -> None:
        path = "E:\\Archive"
        service = self._service(_volume_probe("external_device", path, boundary="external_folder"))
        first = self._confirm(service, "external", "External", path)
        source = self.db.get(IngestionSource, first.source_profile_id)

        for profile_status in ("archived", "test", "deprecated"):
            with self.subTest(profile_status=profile_status):
                source.profile_status = profile_status
                self.db.commit()
                plan = service.plan(
                    SourceCreationPlanRequest(
                        source_type="external",
                        observed_path=path,
                        naming_action="use_existing",
                    )
                )
                self.assertEqual(plan.plan_status, "blocked")
                self.assertIn(
                    "exact_source_management_status",
                    [item.code for item in plan.blockers],
                )
                self.assertEqual(source.profile_status, profile_status)

    def test_whole_device_exact_match_uses_empty_root_but_legacy_null_is_not_blindly_empty(self) -> None:
        folder_path = "E:\\Archive"
        whole_path = "E:\\"
        service = SourceCreationService(
            self.db,
            _FakeProbeService(
                {
                    folder_path: _volume_probe("external_device", folder_path, boundary="external_folder"),
                    whole_path: _volume_probe("external_device", whole_path, boundary="external_volume_root"),
                }
            ),
        )
        registered = self._confirm(service, "external", "External", folder_path)
        legacy_other_root = IngestionSource(
            source_label="Legacy Folder",
            source_label_normalized="legacy folder",
            source_type="external_drive",
            source_root_path=folder_path,
            source_root_path_normalized=normalize_source_root_path(folder_path),
            endpoint_id=registered.source_endpoint_id,
            endpoint_relative_root=None,
            profile_status="active",
        )
        self.db.add(legacy_other_root)
        self.db.commit()

        whole_plan = service.plan(
            SourceCreationPlanRequest(
                source_type="external",
                observed_path=whole_path,
                naming_action="use_existing",
            )
        )
        self.assertEqual(whole_plan.endpoint_relative_root, "")
        self.assertEqual(whole_plan.source_action, "create_new_source")
        self.assertNotIn(legacy_other_root.id, [item.source_profile_id for item in whole_plan.exact_source_matches])

        whole_result = service.confirm(
            SourceCreationConfirmRequest(
                source_type="external",
                observed_path=whole_path,
                naming_action="use_existing",
                plan_fingerprint=whole_plan.plan_fingerprint,
                operator_confirmed=True,
            )
        )
        repeat = service.plan(
            SourceCreationPlanRequest(
                source_type="external",
                observed_path=whole_path,
                naming_action="use_existing",
            )
        )
        self.assertEqual(repeat.source_action, "reuse_existing_source")
        self.assertEqual(repeat.existing_source_profile_id, whole_result.source_profile_id)

    def test_clear_removable_evidence_blocks_local_or_external_creation(self) -> None:
        path = "H:\\Photos"
        probe = _volume_probe(
            "external_device",
            path,
            boundary="external_folder",
            drive_type="removable",
        )
        service = self._service(probe)

        plan = service.plan(SourceCreationPlanRequest(source_type="external", observed_path=path))

        self.assertEqual(plan.plan_status, "blocked")
        self.assertIn(
            "removable_media_requires_supported_flow",
            [item.code for item in plan.blockers],
        )
        self.assertEqual(self.db.scalar(select(func.count(SourceEndpoint.id))), 0)
        self.assertEqual(self.db.scalar(select(func.count(IngestionSource.id))), 0)

    def test_removable_requires_acknowledgment_for_usb_guid_without_media_type(self) -> None:
        path = "D:\\Photos"
        probe = _volume_probe(
            "removable_media",
            path,
            boundary="removable_media_folder",
            bus_type="USB",
        )
        service = self._service(probe)

        plan = service.plan(SourceCreationPlanRequest(source_type="removable", observed_path=path))

        self.assertEqual(plan.plan_status, "needs_review")
        self.assertIn(
            "removable_classification_acknowledgment_required",
            [item.code for item in plan.required_confirmations],
        )

    def test_removable_blocks_usb_hdd_and_directs_to_external(self) -> None:
        path = "E:\\Photos"
        probe = _volume_probe(
            "removable_media",
            path,
            boundary="removable_media_folder",
            bus_type="USB",
            media_type="HDD",
        )
        service = self._service(probe)

        plan = service.plan(SourceCreationPlanRequest(source_type="removable", observed_path=path))

        self.assertEqual(plan.plan_status, "blocked")
        self.assertIn(
            "reliable_external_storage_detected",
            [item.code for item in plan.blockers],
        )

    def test_unreadable_location_takes_precedence_over_duplicate_classification(self) -> None:
        path = "\\\\HENDERSON-NAS\\Photos\\Camera imports"
        blocker = SourceIdentityEvidenceItem(
            category="path_evidence",
            code="access_denied",
            status="blocked",
            source_types=["nas"],
            message="Observed path exists but access was denied.",
        )
        probe = _nas_probe(
            path,
            canonical_path=path,
            boundary="nas_share_folder",
            valid=False,
            blockers=[blocker],
            probe_status="unavailable",
        )
        for index in range(2):
            self.db.add(
                IngestionSource(
                    source_label=f"NAS exact {index}",
                    source_label_normalized=f"nas exact {index}",
                    source_type="local_folder",
                    source_root_path=path,
                    source_root_path_normalized=normalize_source_root_path(path),
                    profile_status="active",
                )
            )
        self.db.commit()
        service = self._service(probe)

        plan = service.plan(SourceCreationPlanRequest(source_type="nas", observed_path=path))

        self.assertEqual(plan.plan_status, "blocked")
        self.assertEqual(plan.recognition_status, "location_blocked")
        self.assertEqual(plan.recognition_title, "Location blocked or unreadable")

    def test_whole_nas_share_exact_source_is_idempotent(self) -> None:
        share = "\\\\HENDERSON-NAS\\Photos"
        service = self._service(_nas_probe(share, canonical_path=share, boundary="nas_share_root"))
        first = self._confirm(service, "nas", "Henderson NAS", share)

        repeat = service.plan(
            SourceCreationPlanRequest(
                source_type="nas",
                observed_path=share,
                naming_action="use_existing",
            )
        )
        self.assertEqual(repeat.endpoint_relative_root, "")
        self.assertEqual(repeat.source_action, "reuse_existing_source")
        result = service.confirm(
            SourceCreationConfirmRequest(
                source_type="nas",
                observed_path=share,
                naming_action="use_existing",
                plan_fingerprint=repeat.plan_fingerprint,
                operator_confirmed=True,
            )
        )
        self.assertEqual(result.source_profile_id, first.source_profile_id)
        self.assertEqual(self.db.scalar(select(func.count(IngestionSource.id))), 1)

    def _service(self, probe: SourceIdentityProbeResponse) -> SourceCreationService:
        return SourceCreationService(
            self.db,
            _FakeProbeService({probe.observed_path or "": probe}),
        )

    def _confirm(
        self,
        service: SourceCreationService,
        source_type: str,
        device_name: str,
        path: str,
    ):
        plan = service.plan(
            SourceCreationPlanRequest(
                source_type=source_type,
                device_name=device_name,
                observed_path=path,
            )
        )
        return service.confirm(
            SourceCreationConfirmRequest(
                source_type=source_type,
                device_name=device_name,
                observed_path=path,
                plan_fingerprint=plan.plan_fingerprint,
                operator_confirmed=True,
            )
        )


def _volume_probe(
    source_type: str,
    path: str,
    *,
    boundary: str,
    drive_type: str | None = None,
    bus_type: str | None = None,
    media_type: str | None = None,
    system_volume: bool = False,
    card_reader_signal: bool = False,
) -> SourceIdentityProbeResponse:
    fingerprint_hash, fingerprint_version = volume_guid_fingerprint(
        "12345678-90AB-CDEF-1234-567890ABCDEF"
    )
    evidence = SourceIdentityEvidenceItem(
        category="volume_evidence",
        code="volume_guid_present",
        status="present",
        durability="durable",
        privacy_level="masked_only",
        source_types=[source_type],
        masked_value="{...cdef}",
        fingerprint_hash=fingerprint_hash,
        fingerprint_version=fingerprint_version,
        message="mountvol Volume GUID evidence is present and masked.",
        provider_name="fake_probe",
    )
    evidence_items = [evidence]
    if drive_type is not None:
        evidence_items.append(
            SourceIdentityEvidenceItem(
                category="volume_evidence",
                code="drive_type_present",
                status="present",
                durability="supporting",
                privacy_level="advanced_only",
                source_types=[source_type],
                display_value=drive_type,
                message="Drive type evidence is present.",
                provider_name="fake_probe",
            )
        )
    if bus_type is not None:
        evidence_items.append(
            SourceIdentityEvidenceItem(
                category="device_evidence",
                code="bus_type_present",
                status="present",
                durability="supporting",
                privacy_level="advanced_only",
                source_types=[source_type],
                display_value=bus_type,
                message="Windows bus/interface evidence is present.",
                provider_name="fake_probe",
            )
        )
    if media_type is not None:
        evidence_items.append(
            SourceIdentityEvidenceItem(
                category="device_evidence",
                code="media_type_present",
                status="present",
                durability="supporting",
                privacy_level="advanced_only",
                source_types=[source_type],
                display_value=media_type,
                message="Windows physical media-type evidence is present.",
                provider_name="fake_probe",
            )
        )
    if system_volume:
        evidence_items.append(
            SourceIdentityEvidenceItem(
                category="device_evidence",
                code="system_volume_present",
                status="present",
                durability="supporting",
                privacy_level="advanced_only",
                source_types=[source_type],
                display_value="system",
                message="Windows storage metadata indicates the active system volume.",
                provider_name="fake_probe",
            )
        )
    if card_reader_signal:
        evidence_items.append(
            SourceIdentityEvidenceItem(
                category="media_evidence",
                code="card_reader_media_present",
                status="present",
                durability="supporting",
                privacy_level="advanced_only",
                source_types=[source_type],
                display_value="card_reader",
                message="Windows storage metadata indicates SD, memory-card, or card-reader media.",
                provider_name="fake_probe",
            )
        )
    return _probe_response(
        source_type=source_type,
        observed_path=path,
        canonical_path=path,
        boundary=boundary,
        evidence=evidence_items,
    )


def _optical_probe(
    path: str,
    *,
    boundary: str,
    manifest_name: str = "ordinary.txt",
) -> SourceIdentityProbeResponse:
    fingerprint_hash, fingerprint_version = optical_media_fingerprint_v2(
        {
            "algorithm": "optical_media_fingerprint_v2",
            "disc_metadata": {
                "filesystem_type": "udf",
                "volume_label": None,
                "volume_serial": "7967c7ec",
                "total_size": 736960512,
            },
            "manifest": {
                "entries": [
                    {"relative_path": manifest_name, "entry_type": "file", "file_size": 42},
                ],
                "file_count": 1,
                "directory_count": 0,
            },
        }
    )
    evidence = [
        SourceIdentityEvidenceItem(
            category="media_evidence",
            code="optical_manifest_complete",
            status="present",
            durability="supporting",
            privacy_level="advanced_only",
            source_types=["optical_media"],
            display_value="files=1;directories=0;timestamps=excluded;elapsed_seconds=0.003",
            message="Complete metadata-only optical directory manifest was enumerated.",
            provider_name="fake_probe",
        ),
        SourceIdentityEvidenceItem(
            category="media_evidence",
            code="optical_media_fingerprint_present",
            status="present",
            durability="durable",
            privacy_level="masked_only",
            source_types=["optical_media"],
            masked_value=f"sha256:...{fingerprint_hash[-12:]}",
            fingerprint_hash=fingerprint_hash,
            fingerprint_version=fingerprint_version,
            message="Complete metadata-only inserted-disc fingerprint is present and masked.",
            provider_name="fake_probe",
        ),
    ]
    return _probe_response(
        source_type="optical_media",
        observed_path=path,
        canonical_path=path,
        boundary=boundary,
        evidence=evidence,
    )


def _nas_probe(
    observed_path: str,
    *,
    canonical_path: str,
    boundary: str,
    valid: bool = True,
    blockers: list[SourceIdentityEvidenceItem] | None = None,
    probe_status: str = "completed",
) -> SourceIdentityProbeResponse:
    return _probe_response(
        source_type="nas",
        observed_path=observed_path,
        canonical_path=canonical_path,
        boundary=boundary,
        evidence=[],
        valid=valid,
        blockers=blockers,
        probe_status=probe_status,
    )


def _probe_response(
    *,
    source_type: str,
    observed_path: str,
    canonical_path: str,
    boundary: str,
    evidence: list[SourceIdentityEvidenceItem],
    valid: bool = True,
    blockers: list[SourceIdentityEvidenceItem] | None = None,
    probe_status: str = "completed",
) -> SourceIdentityProbeResponse:
    blockers = blockers or []
    return SourceIdentityProbeResponse(
        probe_status=probe_status,
        source_type=source_type,
        os_family="windows",
        provider_name="fake_probe",
        provider_version="1",
        access_node_summary=AccessNodeSummary(
            access_node_id="node-test",
            label="Test Windows PC",
            os_family="windows",
            host_fingerprint_masked="host-1234",
        ),
        observed_path=observed_path,
        normalized_observed_path=observed_path.replace("/", "\\").casefold(),
        source_root_candidate=SourceRootCandidate(
            path=canonical_path,
            is_valid_source_root_candidate=valid,
            filesystem_boundary_type=boundary,
            root_reason="test",
        ),
        evidence_items=[*evidence, *blockers],
        confidence_tier="strong_match" if valid else "unavailable_not_connected",
        safe_to_run=True if valid else False,
        blockers=blockers,
    )


if __name__ == "__main__":
    unittest.main()
