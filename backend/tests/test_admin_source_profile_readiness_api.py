from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.admin import router as admin_router
from app.db.session import get_db_session
from app.models.ingestion_run import IngestionRun
from app.models.ingestion_source import IngestionSource
from app.models.source_endpoint import AccessNode, SourceEndpoint, SourceEndpointObservedPath
from app.models.source_intake_run import SourceIntakeRun
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


class _FailingProbeService:
    def probe(self, request: SourceIdentityProbeRequest) -> SourceIdentityProbeResponse:
        raise AssertionError("Probe should not be called.")


class AdminSourceProfileReadinessApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self._create_tables()
        self.db = Session(self.engine)
        self.app = FastAPI()
        self.app.include_router(admin_router)
        self.app.dependency_overrides[get_db_session] = self._override_db
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    def test_check_readiness_endpoint_returns_path_only_response(self) -> None:
        source = self._add_source(source_type="external_drive", path="E:\\Photos")
        fake = _FakeProbeService(_probe_response(source_type="external_device"))

        with patch("app.api.admin.get_source_identity_probe_service", return_value=fake):
            response = self.client.post(f"/api/admin/source-profiles/{source.id}/check-readiness")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["readiness_status"], "path_only")
        self.assertEqual(payload["identity_match_status"], "not_enrolled")
        self.assertEqual(payload["durable_identity_status"], "verified")
        self.assertEqual(payload["durable_identity_identifier_type"], "Volume GUID")
        self.assertEqual(payload["durable_identity_identifier"], "volume-guid-1234")
        self.assertTrue(payload["can_run_source_intake"])
        self.assertTrue(payload["requires_operator_acknowledgment"])
        self.assertEqual(fake.requests[0].source_type, "external_device")

    def test_check_readiness_missing_source_returns_404(self) -> None:
        response = self.client.post("/api/admin/source-profiles/9999/check-readiness")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Source profile not found."})

    def test_check_readiness_cloud_provider_specific_response_is_safe(self) -> None:
        source = self._add_source(
            source_type="cloud_export",
            path="C:\\exports\\icloud",
            cloud_provider="icloud",
            managed_staging_path="C:\\exports\\icloud",
            account_username="private@example.com",
        )

        with patch("app.api.admin.get_source_identity_probe_service", return_value=_FailingProbeService()):
            response = self.client.post(f"/api/admin/source-profiles/{source.id}/check-readiness")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["readiness_status"], "provider_specific")
        self.assertEqual(payload["identity_match_status"], "provider_specific")
        self.assertEqual(payload["durable_identity_status"], "provider_specific")
        self.assertEqual(payload["durable_identity_identifier_type"], "Provider workflow")
        self.assertFalse(payload["hard_block"])
        self.assertNotIn("private@example.com", response.text)
        self.assertNotIn("raw", response.text.lower())

    def _override_db(self):
        yield self.db

    def _add_source(
        self,
        *,
        source_type: str,
        path: str,
        cloud_provider: str | None = None,
        managed_staging_path: str | None = None,
        account_username: str | None = None,
    ) -> IngestionSource:
        source = IngestionSource(
            source_label=f"API Source {source_type}",
            source_label_normalized=f"api source {source_type}",
            source_type=source_type,
            source_root_path=path,
            source_root_path_normalized=path.casefold(),
            profile_status="active",
            cloud_provider=cloud_provider,
            managed_staging_path=managed_staging_path,
            account_username=account_username,
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def _create_tables(self) -> None:
        AccessNode.__table__.create(self.engine)
        SourceEndpoint.__table__.create(self.engine)
        IngestionSource.__table__.create(self.engine)
        IngestionRun.__table__.create(self.engine)
        SourceIntakeRun.__table__.create(self.engine)
        SourceEndpointObservedPath.__table__.create(self.engine)


def _probe_response(
    *,
    source_type: str,
    path: str = "E:\\Photos",
) -> SourceIdentityProbeResponse:
    evidence = SourceIdentityEvidenceItem(
        category="volume_evidence",
        code="volume_guid_present",
        status="present",
        durability="durable",
        privacy_level="masked_only",
        source_types=[source_type],
        masked_value="volume-guid-1234",
        provider_name="fake_probe",
    )
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
            is_valid_source_root_candidate=True,
            filesystem_boundary_type="external_folder",
            root_reason="test",
        ),
        evidence_items=[evidence],
        confidence_tier="strong_match",
        safe_to_run=True,
    )


if __name__ == "__main__":
    unittest.main()
