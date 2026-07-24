from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.admin import router as admin_router
from app.db.session import get_db_session
from app.models.ingestion_source import IngestionSource
from app.models.source_endpoint import AccessNode, SourceEndpoint, SourceEndpointObservedPath
from app.services.source_identity.probe_schema import (
    AccessNodeSummary,
    SourceIdentityEvidenceItem,
    SourceIdentityProbeRequest,
    SourceIdentityProbeResponse,
    SourceRootCandidate,
)


class _FakeProbeService:
    def probe(self, request: SourceIdentityProbeRequest) -> SourceIdentityProbeResponse:
        return SourceIdentityProbeResponse(
            probe_status="completed",
            source_type=request.source_type,
            os_family="windows",
            provider_name="fake_probe",
            provider_version="1",
            access_node_summary=AccessNodeSummary(
                access_node_id="node-test",
                label="Test Windows PC",
                os_family="windows",
                host_fingerprint_masked="host-1234",
            ),
            observed_path=request.observed_path,
            normalized_observed_path=(request.observed_path or "").replace("/", "\\").casefold(),
            source_root_candidate=SourceRootCandidate(
                path=request.observed_path,
                is_valid_source_root_candidate=True,
                filesystem_boundary_type="external_folder",
                root_reason="test",
            ),
            evidence_items=[
                SourceIdentityEvidenceItem(
                    category="volume_evidence",
                    code="volume_guid_present",
                    status="present",
                    durability="durable",
                    privacy_level="masked_only",
                    source_types=[request.source_type],
                    masked_value="volume-guid-1234",
                    provider_name="fake_probe",
                )
            ],
            confidence_tier="strong_match",
            safe_to_run=True,
        )


class AdminSourceEndpointEnrollmentApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
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

        self.app = FastAPI()
        self.app.include_router(admin_router)
        self.app.dependency_overrides[get_db_session] = self._override_db
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    def test_plan_endpoint_returns_read_only_plan(self) -> None:
        with patch("app.api.admin.get_source_identity_probe_service", return_value=_FakeProbeService()):
            response = self.client.post(
                "/api/admin/source-endpoints/enrollment/plan",
                json={
                    "source_profile_id": self.source.id,
                    "probe_request": {
                        "source_type": "external_device",
                        "observed_path": "E:\\Photos",
                        "os_family": "windows",
                    },
                    "proposed_alias": "Camera Archive",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["plan_status"], "ready")
        self.assertEqual(payload["endpoint_action"], "create_new_endpoint")
        self.assertEqual(payload["durable_identity_status"], "verified")
        self.assertEqual(payload["durable_identity_identifier_type"], "Volume GUID")
        self.assertEqual(payload["durable_identity_identifier"], "volume-guid-1234")
        self.assertEqual(self.db.scalar(select(func.count(SourceEndpoint.id))), 0)

    def test_confirm_endpoint_creates_endpoint_and_links_profile(self) -> None:
        with patch("app.api.admin.get_source_identity_probe_service", return_value=_FakeProbeService()):
            plan_response = self.client.post(
                "/api/admin/source-endpoints/enrollment/plan",
                json={
                    "source_profile_id": self.source.id,
                    "probe_request": {
                        "source_type": "external_device",
                        "observed_path": "E:\\Photos",
                        "os_family": "windows",
                    },
                    "proposed_alias": "Camera Archive",
                },
            )
            plan = plan_response.json()
            confirm_response = self.client.post(
                "/api/admin/source-endpoints/enrollment/confirm",
                json={
                    "source_profile_id": self.source.id,
                    "probe_request": {
                        "source_type": "external_device",
                        "observed_path": "E:\\Photos",
                        "os_family": "windows",
                    },
                    "confirmed_alias": "Camera Archive",
                    "plan_fingerprint": plan["plan_fingerprint"],
                    "operator_confirmed": True,
                },
            )

        self.assertEqual(confirm_response.status_code, 200)
        payload = confirm_response.json()
        self.assertEqual(payload["enrollment_status"], "completed")
        self.assertEqual(payload["durable_identity_status"], "verified")
        self.assertTrue(payload["created_endpoint"])
        self.db.refresh(self.source)
        self.assertEqual(self.source.endpoint_id, payload["source_endpoint_id"])

    def test_plan_endpoint_blocks_unknown_source_profile(self) -> None:
        with patch("app.api.admin.get_source_identity_probe_service", return_value=_FakeProbeService()):
            response = self.client.post(
                "/api/admin/source-endpoints/enrollment/plan",
                json={
                    "source_profile_id": 9999,
                    "probe_request": {
                        "source_type": "external_device",
                        "observed_path": "E:\\Photos",
                        "os_family": "windows",
                    },
                    "proposed_alias": "Camera Archive",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["plan_status"], "blocked")
        self.assertEqual(payload["blockers"][0]["code"], "source_profile_not_found")

    def _override_db(self):
        yield self.db

    def _create_enrollment_tables(self) -> None:
        AccessNode.__table__.create(self.engine)
        SourceEndpoint.__table__.create(self.engine)
        IngestionSource.__table__.create(self.engine)
        SourceEndpointObservedPath.__table__.create(self.engine)


if __name__ == "__main__":
    unittest.main()
