from __future__ import annotations

import sys
import unittest
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.ingestion_source import IngestionSource
from app.models.source_endpoint import AccessNode, SourceEndpoint, SourceEndpointObservedPath
from app.services.source_identity.creation_schema import (
    SourceCreationConfirmRequest,
    SourceCreationPlanRequest,
)
from app.services.source_identity.creation_service import SourceCreationService
from app.services.source_identity.identity_fingerprint import (
    fingerprint_from_probe,
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
        IngestionSource.__table__.create(self.engine)
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
        self.assertEqual(plan.source_display_name, "External 1 - Archive\\Family Photos")
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
        self.assertEqual(plan.source_display_name, "Chuck PC - Users\\chhen\\Pictures\\Scans")
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
        self.assertEqual(plan.source_display_name, "External 1 - Entire device")

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
        self.assertEqual(share_plan.endpoint_relative_root, "")
        self.assertEqual(share_plan.entire_endpoint_label, "Entire share")

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

        second_plan = service.plan(
            SourceCreationPlanRequest(
                source_type="external",
                device_name="Different Name",
                observed_path=second_path,
            )
        )
        self.assertEqual(second_plan.endpoint_action, "reuse_existing_endpoint")
        self.assertEqual(second_plan.device_name, "External 1")
        self.assertIn("existing_device_name_reused", [item.code for item in second_plan.warnings])
        second = service.confirm(
            SourceCreationConfirmRequest(
                source_type="external",
                device_name="Different Name",
                observed_path=second_path,
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
                device_name="Conflicting Name",
                observed_path=path,
            )
        )
        self.assertEqual(plan.plan_status, "source_exists")
        self.assertEqual(plan.existing_source_profile_id, first.source_profile_id)
        second = service.confirm(
            SourceCreationConfirmRequest(
                source_type="external",
                device_name="Conflicting Name",
                observed_path=path,
                plan_fingerprint=plan.plan_fingerprint,
                operator_confirmed=True,
            )
        )

        self.assertEqual(second.source_profile_id, first.source_profile_id)
        self.assertTrue(second.reused_source)
        self.assertFalse(second.created_source)
        self.assertEqual(self.db.scalar(select(func.count(IngestionSource.id))), 1)

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
                operator_review_acknowledged=True,
            )
        )
        result = service.confirm(
            SourceCreationConfirmRequest(
                source_type="external",
                device_name="External 1",
                observed_path=path,
                selected_existing_endpoint_id=legacy.id,
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
                operator_review_acknowledged=True,
            )
        )
        result = service.confirm(
            SourceCreationConfirmRequest(
                source_type="external",
                device_name="New Name",
                observed_path=requested_path,
                selected_existing_endpoint_id=legacy.id,
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
            SourceCreationPlanRequest(source_type="external", device_name="External 1", observed_path=nested)
        )

        self.assertEqual(plan.plan_status, "ready")
        self.assertIn("source_root_overlap", [item.code for item in plan.warnings])

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
    return _probe_response(
        source_type=source_type,
        observed_path=path,
        canonical_path=path,
        boundary=boundary,
        evidence=[evidence],
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
