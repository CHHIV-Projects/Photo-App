from __future__ import annotations

import sys
import unittest
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.ingestion_run import IngestionRun
from app.models.ingestion_source import IngestionSource
from app.models.source_endpoint import AccessNode, SourceEndpoint, SourceEndpointObservedPath
from app.models.source_intake_run import SourceIntakeRun
from app.services.source_identity.identity_fingerprint import fingerprint_from_probe
from app.services.source_identity.probe_schema import (
    AccessNodeSummary,
    SourceIdentityEvidenceItem,
    SourceIdentityProbeRequest,
    SourceIdentityProbeResponse,
    SourceRootCandidate,
)
from app.services.source_identity.readiness_service import SourceProfileReadinessService


class _FakeProbeService:
    def __init__(self, response: SourceIdentityProbeResponse) -> None:
        self.response = response
        self.requests: list[SourceIdentityProbeRequest] = []

    def probe(self, request: SourceIdentityProbeRequest) -> SourceIdentityProbeResponse:
        self.requests.append(request)
        return self.response


class _FailingProbeService:
    def probe(self, request: SourceIdentityProbeRequest) -> SourceIdentityProbeResponse:
        raise AssertionError("Probe should not be called for this readiness case.")


class SourceProfileReadinessServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        self._create_tables()
        self.db = Session(self.engine)

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_path_only_readable_profile_returns_path_only_and_is_runnable(self) -> None:
        source = self._add_source(source_type="external_drive", path="E:\\Photos")
        fake = _FakeProbeService(_probe_response(source_type="external_device"))

        result = SourceProfileReadinessService(self.db, fake).check_readiness(source.id)

        self.assertEqual(result.readiness_status, "path_only")
        self.assertEqual(result.identity_match_status, "not_enrolled")
        self.assertTrue(result.can_run_source_intake)
        self.assertTrue(result.requires_operator_acknowledgment)
        self.assertFalse(result.hard_block)
        self.assertEqual(result.durable_identity_status, "verified")
        self.assertEqual(result.durable_identity_identifier_type, "Volume GUID")
        self.assertEqual(fake.requests[0].source_type, "external_device")
        self.assert_non_mutating(source.id, expected_endpoint_id=None)

    def test_path_only_unreadable_profile_returns_blocked(self) -> None:
        blocker = _evidence("path_not_found", status="blocked", message="Observed path was not found.")
        source = self._add_source(source_type="external_drive", path="E:\\Missing")
        fake = _FakeProbeService(
            _probe_response(
                source_type="external_device",
                path="E:\\Missing",
                is_valid=False,
                probe_status="unavailable",
                safe_to_run=False,
                blockers=[blocker],
                evidence_items=[],
            )
        )

        result = SourceProfileReadinessService(self.db, fake).check_readiness(source.id)

        self.assertEqual(result.readiness_status, "blocked")
        self.assertEqual(result.identity_match_status, "unavailable")
        self.assertFalse(result.can_run_source_intake)
        self.assertTrue(result.hard_block)

    def test_inactive_profile_is_blocked_before_probe(self) -> None:
        source = self._add_source(profile_status="inactive")

        result = SourceProfileReadinessService(self.db, _FailingProbeService()).check_readiness(source.id)

        self.assertEqual(result.readiness_status, "blocked")
        self.assertEqual(result.blockers[0].code, "profile_not_active")
        self.assertFalse(result.can_run_source_intake)

    def test_cloud_icloud_profile_returns_provider_specific_without_probe(self) -> None:
        source = self._add_source(
            source_type="cloud_export",
            path="C:\\exports\\icloud",
            cloud_provider="icloud",
            managed_staging_path="C:\\exports\\icloud",
            account_username="private@example.com",
        )

        result = SourceProfileReadinessService(self.db, _FailingProbeService()).check_readiness(source.id)

        self.assertEqual(result.readiness_status, "provider_specific")
        self.assertEqual(result.identity_match_status, "provider_specific")
        self.assertFalse(result.can_run_source_intake)
        self.assertFalse(result.hard_block)
        self.assertEqual(result.durable_identity_status, "provider_specific")
        self.assertEqual(result.durable_identity_identifier_type, "Provider workflow")
        self.assertIn("iCloud Intake", result.recommended_next_action)
        self.assertNotIn("private@example.com", result.model_dump_json())

    def test_unsupported_source_type_returns_blocked_without_probe(self) -> None:
        source = self._add_source(source_type="scan_batch", path="C:\\scan")

        result = SourceProfileReadinessService(self.db, _FailingProbeService()).check_readiness(source.id)

        self.assertEqual(result.readiness_status, "blocked")
        self.assertEqual(result.identity_match_status, "unsupported")
        self.assertEqual(result.blockers[0].code, "unsupported_source_type")

    def test_enrolled_endpoint_strong_match_returns_ready(self) -> None:
        response = _probe_response(source_type="external_device", masked_value="volume-a")
        endpoint = self._add_endpoint_from_probe(response)
        source = self._add_source(source_type="external_drive", path="E:\\Photos", endpoint_id=endpoint.id)
        fake = _FakeProbeService(response)

        result = SourceProfileReadinessService(self.db, fake).check_readiness(source.id)

        self.assertEqual(result.readiness_status, "ready")
        self.assertEqual(result.identity_match_status, "matched")
        self.assertTrue(result.can_run_source_intake)
        self.assertFalse(result.requires_operator_acknowledgment)
        self.assertFalse(result.hard_block)
        self.assertEqual(result.durable_identity_status, "verified")
        self.assertEqual(result.durable_identity_identifier_type, "Volume GUID")
        self.assert_non_mutating(source.id, expected_endpoint_id=endpoint.id)

    def test_enrolled_endpoint_fingerprint_mismatch_returns_blocked(self) -> None:
        endpoint = self._add_endpoint_from_probe(_probe_response(source_type="external_device", masked_value="volume-a"))
        source = self._add_source(source_type="external_drive", path="E:\\Photos", endpoint_id=endpoint.id)
        fake = _FakeProbeService(_probe_response(source_type="external_device", masked_value="volume-b"))

        result = SourceProfileReadinessService(self.db, fake).check_readiness(source.id)

        self.assertEqual(result.readiness_status, "blocked")
        self.assertEqual(result.identity_match_status, "mismatch")
        self.assertEqual(result.blockers[0].code, "endpoint_identity_mismatch")
        self.assertFalse(result.can_run_source_intake)

    def test_enrolled_endpoint_readable_weak_evidence_returns_needs_review(self) -> None:
        response = _probe_response(
            source_type="external_device",
            confidence_tier="weak_manual_confirmation_required",
            safe_to_run="needs_review",
            evidence_items=[],
        )
        endpoint = self._add_endpoint_from_probe(response, identity_confidence="weak_manual_confirmation_required")
        source = self._add_source(source_type="external_drive", path="E:\\Photos", endpoint_id=endpoint.id)

        result = SourceProfileReadinessService(self.db, _FakeProbeService(response)).check_readiness(source.id)

        self.assertEqual(result.readiness_status, "needs_review")
        self.assertEqual(result.identity_match_status, "needs_review")
        self.assertTrue(result.can_run_source_intake)
        self.assertTrue(result.requires_operator_acknowledgment)
        self.assertFalse(result.hard_block)
        self.assertEqual(result.durable_identity_status, "not_verified")

    def test_enrolled_endpoint_unavailable_path_returns_blocked(self) -> None:
        endpoint = self._add_endpoint_from_probe(_probe_response(source_type="external_device", masked_value="volume-a"))
        source = self._add_source(source_type="external_drive", path="E:\\Photos", endpoint_id=endpoint.id)
        blocker = _evidence("access_denied", status="blocked", message="Observed path exists but access was denied.")
        unavailable = _probe_response(
            source_type="external_device",
            is_valid=False,
            safe_to_run=False,
            probe_status="unavailable",
            blockers=[blocker],
            evidence_items=[],
        )

        result = SourceProfileReadinessService(self.db, _FakeProbeService(unavailable)).check_readiness(source.id)

        self.assertEqual(result.readiness_status, "blocked")
        self.assertEqual(result.identity_match_status, "unavailable")
        self.assertEqual(result.blockers[0].code, "access_denied")

    def test_nas_unc_local_folder_maps_to_nas(self) -> None:
        source = self._add_source(
            source_type="local_folder",
            path=r"\\HENDERSON-NAS\Photos\Camera imports",
        )
        fake = _FakeProbeService(
            _probe_response(
                source_type="nas",
                path=r"\\HENDERSON-NAS\Photos\Camera imports",
                boundary="nas_share_folder",
                evidence_items=[],
            )
        )

        result = SourceProfileReadinessService(self.db, fake).check_readiness(source.id)

        self.assertEqual(fake.requests[0].source_type, "nas")
        self.assertEqual(result.readiness_status, "path_only")
        self.assertEqual(result.durable_identity_status, "verified")
        self.assertEqual(result.durable_identity_identifier_type, "NAS server/share")
        self.assertEqual(result.durable_identity_identifier, r"\\henderson-nas\photos")

    def test_nas_server_only_returns_blocked(self) -> None:
        source = self._add_source(source_type="local_folder", path=r"\\HENDERSON-NAS")
        blocker = _evidence(
            "nas_server_not_runnable",
            category="network_share_evidence",
            status="blocked",
            message="NAS server-only paths are endpoint seeds, not runnable source roots.",
        )
        fake = _FakeProbeService(
            _probe_response(
                source_type="nas",
                path=r"\\HENDERSON-NAS",
                boundary="nas_server_only",
                is_valid=False,
                safe_to_run=False,
                blockers=[blocker],
                evidence_items=[],
            )
        )

        result = SourceProfileReadinessService(self.db, fake).check_readiness(source.id)

        self.assertEqual(result.readiness_status, "blocked")
        self.assertEqual(result.identity_match_status, "unsupported")
        self.assertEqual(result.blockers[0].code, "nas_server_only_not_source_root")
        self.assertEqual(result.durable_identity_status, "not_verified")

    def assert_non_mutating(self, source_id: int, *, expected_endpoint_id: int | None) -> None:
        self.db.expire_all()
        source = self.db.get(IngestionSource, source_id)
        self.assertIsNotNone(source)
        self.assertEqual(source.endpoint_id, expected_endpoint_id)
        self.assertEqual(self.db.scalar(select(func.count(SourceIntakeRun.id))), 0)
        self.assertEqual(self.db.scalar(select(func.count(SourceEndpointObservedPath.id))), 0)

    def _add_source(
        self,
        *,
        source_type: str = "external_drive",
        path: str = "E:\\Photos",
        profile_status: str = "active",
        cloud_provider: str | None = None,
        managed_staging_path: str | None = None,
        account_username: str | None = None,
        endpoint_id: int | None = None,
    ) -> IngestionSource:
        source = IngestionSource(
            source_label=f"Source {len(self.db.scalars(select(IngestionSource.id)).all()) + 1}",
            source_label_normalized=f"source {len(self.db.scalars(select(IngestionSource.id)).all()) + 1}",
            source_type=source_type,
            source_root_path=path,
            source_root_path_normalized=path.casefold(),
            profile_status=profile_status,
            cloud_provider=cloud_provider,
            managed_staging_path=managed_staging_path,
            account_username=account_username,
            endpoint_id=endpoint_id,
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def _add_endpoint_from_probe(
        self,
        response: SourceIdentityProbeResponse,
        *,
        identity_confidence: str | None = None,
    ) -> SourceEndpoint:
        fingerprint = fingerprint_from_probe(response)
        endpoint = SourceEndpoint(
            source_type=response.source_type,
            alias=f"{response.source_type} endpoint",
            alias_normalized=f"{response.source_type} endpoint",
            status="active",
            identity_fingerprint_hash=fingerprint.hash_value,
            identity_fingerprint_version=fingerprint.version,
            identity_confidence=identity_confidence or response.confidence_tier,
        )
        self.db.add(endpoint)
        self.db.commit()
        self.db.refresh(endpoint)
        return endpoint

    def _create_tables(self) -> None:
        AccessNode.__table__.create(self.engine)
        SourceEndpoint.__table__.create(self.engine)
        IngestionSource.__table__.create(self.engine)
        IngestionRun.__table__.create(self.engine)
        SourceIntakeRun.__table__.create(self.engine)
        SourceEndpointObservedPath.__table__.create(self.engine)


def _probe_response(
    *,
    source_type: str = "external_device",
    path: str = "E:\\Photos",
    boundary: str = "external_folder",
    is_valid: bool = True,
    masked_value: str = "volume-guid-1234",
    evidence_items: list[SourceIdentityEvidenceItem] | None = None,
    blockers: list[SourceIdentityEvidenceItem] | None = None,
    warnings: list[SourceIdentityEvidenceItem] | None = None,
    confidence_tier: str = "strong_match",
    safe_to_run: bool | str = True,
    probe_status: str = "completed",
) -> SourceIdentityProbeResponse:
    blockers = blockers or []
    warnings = warnings or []
    if evidence_items is None:
        evidence_items = [
            SourceIdentityEvidenceItem(
                category="volume_evidence",
                code="volume_guid_present",
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
        observed_path=path,
        normalized_observed_path=path.replace("/", "\\").casefold(),
        source_root_candidate=SourceRootCandidate(
            path=path,
            is_valid_source_root_candidate=is_valid,
            filesystem_boundary_type=boundary,
            root_reason="test",
        ),
        evidence_items=[*evidence_items, *warnings, *blockers],
        evidence_summary={"path": "present"},
        confidence_tier=confidence_tier,
        safe_to_run=safe_to_run,
        blockers=blockers,
        warnings=warnings,
    )


def _evidence(
    code: str,
    *,
    category: str = "path_evidence",
    status: str = "present",
    message: str = "test evidence",
) -> SourceIdentityEvidenceItem:
    return SourceIdentityEvidenceItem(
        category=category,
        code=code,
        status=status,
        durability="supporting",
        privacy_level="normal_ui",
        source_types=["external_device", "nas"],
        message=message,
        provider_name="fake_probe",
    )


if __name__ == "__main__":
    unittest.main()
