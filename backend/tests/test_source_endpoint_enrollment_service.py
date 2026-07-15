from __future__ import annotations

import sys
import unittest
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.ingestion_source import IngestionSource
from app.models.source_endpoint import AccessNode, SourceEndpoint, SourceEndpointObservedPath
from app.services.source_identity.enrollment_schema import (
    SourceEndpointEnrollmentConfirmRequest,
    SourceEndpointEnrollmentPlanRequest,
)
from app.services.source_identity.enrollment_service import SourceEndpointEnrollmentService
from app.services.source_identity.probe_schema import (
    AccessNodeSummary,
    SourceIdentityEvidenceItem,
    SourceIdentityProbeRequest,
    SourceIdentityProbeResponse,
    SourceRootCandidate,
)


class _FakeProbeService:
    def __init__(self, response: SourceIdentityProbeResponse) -> None:
        self.response = response
        self.requests: list[SourceIdentityProbeRequest] = []

    def probe(self, request: SourceIdentityProbeRequest) -> SourceIdentityProbeResponse:
        self.requests.append(request)
        return self.response


class SourceEndpointEnrollmentServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        self._create_enrollment_tables()
        self.db = Session(self.engine)
        self.source = IngestionSource(
            source_label="Camera Imports",
            source_label_normalized="camera imports",
            source_type="external_drive",
            source_root_path="E:\\Photos",
            source_root_path_normalized="e:\\photos",
            profile_status="active",
        )
        self.db.add(self.source)
        self.db.commit()
        self.db.refresh(self.source)

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def _create_enrollment_tables(self) -> None:
        AccessNode.__table__.create(self.engine)
        SourceEndpoint.__table__.create(self.engine)
        IngestionSource.__table__.create(self.engine)
        SourceEndpointObservedPath.__table__.create(self.engine)

    def test_plan_is_read_only_for_new_endpoint(self) -> None:
        service = self._service(_probe_response())

        plan = service.plan(
            SourceEndpointEnrollmentPlanRequest(
                source_profile_id=self.source.id,
                probe_request=_probe_request(),
                proposed_alias="Camera Archive",
            )
        )

        self.assertEqual(plan.plan_status, "ready")
        self.assertEqual(plan.endpoint_action, "create_new_endpoint")
        self.assertEqual(plan.alias_normalized, "camera archive")
        self.assertEqual(self.db.scalar(select(func.count(SourceEndpoint.id))), 0)
        self.assertEqual(self.db.scalar(select(func.count(SourceEndpointObservedPath.id))), 0)
        self.db.refresh(self.source)
        self.assertIsNone(self.source.endpoint_id)

    def test_confirm_creates_endpoint_observed_path_and_links_profile(self) -> None:
        service = self._service(_probe_response())
        plan = service.plan(
            SourceEndpointEnrollmentPlanRequest(
                source_profile_id=self.source.id,
                probe_request=_probe_request(),
                proposed_alias="Camera Archive",
            )
        )

        result = service.confirm(
            SourceEndpointEnrollmentConfirmRequest(
                source_profile_id=self.source.id,
                probe_request=_probe_request(),
                confirmed_alias="Camera Archive",
                plan_fingerprint=plan.plan_fingerprint,
                operator_confirmed=True,
            )
        )

        self.assertEqual(result.enrollment_status, "completed")
        self.assertTrue(result.created_endpoint)
        self.assertTrue(result.created_observed_path)
        self.db.refresh(self.source)
        self.assertEqual(self.source.endpoint_id, result.source_endpoint_id)
        endpoint = self.db.get(SourceEndpoint, result.source_endpoint_id)
        self.assertIsNotNone(endpoint)
        self.assertEqual(endpoint.alias, "Camera Archive")
        self.assertEqual(endpoint.alias_normalized, "camera archive")

    def test_confirm_retry_returns_already_linked_without_duplicate_observed_path(self) -> None:
        service = self._service(_probe_response())
        plan = service.plan(
            SourceEndpointEnrollmentPlanRequest(
                source_profile_id=self.source.id,
                probe_request=_probe_request(),
                proposed_alias="Camera Archive",
            )
        )
        request = SourceEndpointEnrollmentConfirmRequest(
            source_profile_id=self.source.id,
            probe_request=_probe_request(),
            confirmed_alias="Camera Archive",
            plan_fingerprint=plan.plan_fingerprint,
            operator_confirmed=True,
        )

        first = service.confirm(request)
        second = service.confirm(request)

        self.assertEqual(first.enrollment_status, "completed")
        self.assertEqual(second.enrollment_status, "completed")
        self.assertTrue(second.already_linked)
        self.assertFalse(second.created_endpoint)
        self.assertFalse(second.created_observed_path)
        self.assertEqual(self.db.scalar(select(func.count(SourceEndpointObservedPath.id))), 1)

    def test_strong_duplicate_requires_selection_then_links_existing_endpoint(self) -> None:
        service = self._service(_probe_response())
        fingerprint = service.plan(
            SourceEndpointEnrollmentPlanRequest(
                source_profile_id=self.source.id,
                probe_request=_probe_request(),
                proposed_alias="Temp Alias",
            )
        ).candidate.identity_fingerprint_hash
        existing = SourceEndpoint(
            source_type="external_device",
            alias="Existing Camera Archive",
            alias_normalized="existing camera archive",
            status="active",
            identity_fingerprint_hash=fingerprint,
            identity_fingerprint_version="source_endpoint_identity_v1",
            identity_confidence="strong_match",
        )
        self.db.add(existing)
        self.db.commit()
        self.db.refresh(existing)

        duplicate_plan = service.plan(
            SourceEndpointEnrollmentPlanRequest(
                source_profile_id=self.source.id,
                probe_request=_probe_request(),
            )
        )
        self.assertEqual(duplicate_plan.plan_status, "duplicate_match")
        self.assertEqual(duplicate_plan.endpoint_action, "link_existing_endpoint")
        self.assertEqual(duplicate_plan.possible_matches[0].source_endpoint_id, existing.id)

        blocked = service.confirm(
            SourceEndpointEnrollmentConfirmRequest(
                source_profile_id=self.source.id,
                probe_request=_probe_request(),
                operator_confirmed=True,
            )
        )
        self.assertEqual(blocked.enrollment_status, "blocked")

        linked = service.confirm(
            SourceEndpointEnrollmentConfirmRequest(
                source_profile_id=self.source.id,
                probe_request=_probe_request(),
                selected_existing_endpoint_id=existing.id,
                operator_confirmed=True,
            )
        )
        self.assertEqual(linked.enrollment_status, "completed")
        self.assertFalse(linked.created_endpoint)
        self.assertEqual(linked.source_endpoint_id, existing.id)

    def test_alias_conflict_blocks_new_endpoint(self) -> None:
        self.db.add(
            SourceEndpoint(
                source_type="external_device",
                alias="Camera Archive",
                alias_normalized="camera archive",
                status="active",
                identity_confidence="unknown",
            )
        )
        self.db.commit()
        service = self._service(_probe_response(masked_value="different-volume"))

        plan = service.plan(
            SourceEndpointEnrollmentPlanRequest(
                source_profile_id=self.source.id,
                probe_request=_probe_request(),
                proposed_alias="Camera Archive",
            )
        )

        self.assertEqual(plan.plan_status, "alias_conflict")
        self.assertIn("alias_conflict", [blocker.code for blocker in plan.blockers])

    def test_observed_path_only_fingerprint_does_not_create_strong_duplicate_match(self) -> None:
        weak_response = _probe_response(evidence_items=[])
        service = self._service(weak_response)
        weak_plan = service.plan(
            SourceEndpointEnrollmentPlanRequest(
                source_profile_id=self.source.id,
                probe_request=_probe_request(),
                proposed_alias="Weak Camera Archive",
            )
        )
        self.db.add(
            SourceEndpoint(
                source_type="external_device",
                alias="Path Only Endpoint",
                alias_normalized="path only endpoint",
                status="active",
                identity_fingerprint_hash=weak_plan.candidate.identity_fingerprint_hash,
                identity_fingerprint_version="source_endpoint_identity_v1",
                identity_confidence="weak_manual_confirmation_required",
            )
        )
        self.db.commit()

        plan = service.plan(
            SourceEndpointEnrollmentPlanRequest(
                source_profile_id=self.source.id,
                probe_request=_probe_request(),
                proposed_alias="Another Weak Camera Archive",
            )
        )

        self.assertEqual(plan.candidate.identity_fingerprint_strength, "weak")
        self.assertEqual(plan.possible_matches, [])
        self.assertNotEqual(plan.plan_status, "duplicate_match")

    def test_nas_fingerprint_uses_server_and_share_not_folder(self) -> None:
        first = self._service(
            _probe_response(
                source_type="nas",
                path=r"\\HENDERSON-NAS\Photos\Camera imports",
                boundary="nas_share_folder",
                evidence_items=[],
            )
        ).plan(
            SourceEndpointEnrollmentPlanRequest(
                source_profile_id=self.source.id,
                probe_request=_probe_request(source_type="nas", path=r"\\HENDERSON-NAS\Photos\Camera imports"),
                proposed_alias="NAS Photos",
            )
        )
        second = self._service(
            _probe_response(
                source_type="nas",
                path=r"\\HENDERSON-NAS\Photos\Other folder",
                boundary="nas_share_folder",
                evidence_items=[],
            )
        ).plan(
            SourceEndpointEnrollmentPlanRequest(
                source_profile_id=self.source.id,
                probe_request=_probe_request(source_type="nas", path=r"\\HENDERSON-NAS\Photos\Other folder"),
                proposed_alias="NAS Photos",
            )
        )

        self.assertEqual(first.candidate.identity_fingerprint_strength, "strong")
        self.assertEqual(first.candidate.identity_fingerprint_hash, second.candidate.identity_fingerprint_hash)

    def test_nas_server_only_is_blocked(self) -> None:
        service = self._service(
            _probe_response(
                source_type="nas",
                path=r"\\HENDERSON-NAS",
                boundary="nas_server_only",
                is_valid=False,
                evidence_items=[],
            )
        )

        plan = service.plan(
            SourceEndpointEnrollmentPlanRequest(
                source_profile_id=self.source.id,
                probe_request=_probe_request(source_type="nas", path=r"\\HENDERSON-NAS"),
                proposed_alias="NAS Server",
            )
        )

        self.assertEqual(plan.plan_status, "blocked")
        self.assertIn("nas_server_only_not_source_root", [blocker.code for blocker in plan.blockers])

    def _service(self, response: SourceIdentityProbeResponse) -> SourceEndpointEnrollmentService:
        return SourceEndpointEnrollmentService(
            db_session=self.db,
            probe_service=_FakeProbeService(response),
        )


def _probe_request(source_type: str = "external_device", path: str = "E:\\Photos") -> SourceIdentityProbeRequest:
    return SourceIdentityProbeRequest(
        source_type=source_type,
        observed_path=path,
        os_family="windows",
        probe_mode="setup_probe",
    )


def _probe_response(
    *,
    source_type: str = "external_device",
    path: str = "E:\\Photos",
    boundary: str = "external_folder",
    is_valid: bool = True,
    masked_value: str = "volume-guid-1234",
    evidence_items: list[SourceIdentityEvidenceItem] | None = None,
) -> SourceIdentityProbeResponse:
    if evidence_items is None:
        evidence_items = [
            SourceIdentityEvidenceItem(
                category="volume_evidence",
                code="volume_guid",
                status="present",
                durability="durable",
                privacy_level="masked_only",
                source_types=[source_type],
                masked_value=masked_value,
                message="Volume identity was available.",
                provider_name="fake_probe",
            )
        ]
    return SourceIdentityProbeResponse(
        probe_status="completed",
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
        observed_path=path,
        normalized_observed_path=path.replace("/", "\\").casefold(),
        source_root_candidate=SourceRootCandidate(
            path=path,
            is_valid_source_root_candidate=is_valid,
            filesystem_boundary_type=boundary,
            root_reason="test",
        ),
        evidence_items=evidence_items,
        evidence_summary={"path": "present"},
        confidence_tier="strong_match",
        safe_to_run=True,
    )


if __name__ == "__main__":
    unittest.main()
