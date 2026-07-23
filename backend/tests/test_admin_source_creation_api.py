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
from app.models.source_endpoint import (
    AccessNode,
    SourceEndpoint,
    SourceEndpointAliasEvent,
    SourceEndpointObservedPath,
)
from app.services.source_identity.identity_fingerprint import optical_media_fingerprint_v2, volume_guid_fingerprint
from app.services.source_identity.probe_schema import (
    AccessNodeSummary,
    SourceIdentityEvidenceItem,
    SourceIdentityProbeRequest,
    SourceIdentityProbeResponse,
    SourceRootCandidate,
)


class _FakeProbeService:
    def probe(self, request: SourceIdentityProbeRequest) -> SourceIdentityProbeResponse:
        if request.source_type == "optical_media":
            fingerprint_hash, fingerprint_version = optical_media_fingerprint_v2(
                {
                    "algorithm": "optical_media_fingerprint_v2",
                    "disc_metadata": {"filesystem_type": "udf", "volume_serial": "7967c7ec"},
                    "manifest": {
                        "entries": [{"relative_path": "ordinary.txt", "entry_type": "file", "file_size": 42}],
                        "file_count": 1,
                        "directory_count": 0,
                    },
                }
            )
            evidence = SourceIdentityEvidenceItem(
                category="media_evidence",
                code="optical_media_fingerprint_present",
                status="present",
                durability="durable",
                privacy_level="masked_only",
                source_types=[request.source_type],
                masked_value=f"sha256:...{fingerprint_hash[-12:]}",
                fingerprint_hash=fingerprint_hash,
                fingerprint_version=fingerprint_version,
            )
            boundary = "optical_media_root" if (request.observed_path or "").rstrip("\\/").endswith(":") else "optical_media_folder"
        else:
            fingerprint_hash, fingerprint_version = volume_guid_fingerprint(
                "12345678-90AB-CDEF-1234-567890ABCDEF"
            )
            evidence = SourceIdentityEvidenceItem(
                category="volume_evidence",
                code="volume_guid_present",
                status="present",
                durability="durable",
                privacy_level="masked_only",
                source_types=[request.source_type],
                masked_value="{...cdef}",
                fingerprint_hash=fingerprint_hash,
                fingerprint_version=fingerprint_version,
            )
            boundary = "external_folder"
        return SourceIdentityProbeResponse(
            probe_status="completed",
            source_type=request.source_type,
            os_family="windows",
            provider_name="fake_probe",
            provider_version="1",
            access_node_summary=AccessNodeSummary(label="Test Windows PC", os_family="windows"),
            observed_path=request.observed_path,
            normalized_observed_path=(request.observed_path or "").casefold(),
            source_root_candidate=SourceRootCandidate(
                path=request.observed_path,
                is_valid_source_root_candidate=True,
                filesystem_boundary_type=boundary,
                root_reason="test",
            ),
            evidence_items=[evidence],
            confidence_tier="strong_match",
            safe_to_run=True,
        )


class AdminSourceCreationApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        AccessNode.__table__.create(self.engine)
        SourceEndpoint.__table__.create(self.engine)
        SourceEndpointAliasEvent.__table__.create(self.engine)
        IngestionSource.__table__.create(self.engine)
        SourceEndpointObservedPath.__table__.create(self.engine)
        self.db = Session(self.engine)
        self.app = FastAPI()
        self.app.include_router(admin_router)
        self.app.dependency_overrides[get_db_session] = self._override_db
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    def test_plan_then_confirm_creates_linked_source_atomically(self) -> None:
        request = {
            "source_type": "external",
            "device_name": "External 1",
            "naming_action": "create_new",
            "observed_path": "E:\\Archive\\Family Photos",
        }
        with patch("app.api.admin.get_source_identity_probe_service", return_value=_FakeProbeService()):
            plan_response = self.client.post("/api/admin/source-creation/plan", json=request)
            self.assertEqual(self.db.scalar(select(func.count(IngestionSource.id))), 0)
            plan = plan_response.json()
            confirm_response = self.client.post(
                "/api/admin/source-creation/confirm",
                json={
                    **request,
                    "plan_fingerprint": plan["plan_fingerprint"],
                    "operator_confirmed": True,
                },
            )

        self.assertEqual(plan_response.status_code, 200)
        self.assertEqual(plan["endpoint_relative_root"], "Archive\\Family Photos")
        self.assertEqual(plan["source_display_name"], "Family Photos")
        self.assertEqual(plan["durable_identity_status"], "verified")
        self.assertEqual(confirm_response.status_code, 200)
        result = confirm_response.json()
        self.assertEqual(result["creation_status"], "completed")
        self.assertTrue(result["created_source"])
        self.assertEqual(result["source_display_name"], "Family Photos")
        source = self.db.get(IngestionSource, result["source_profile_id"])
        self.assertEqual(source.endpoint_relative_root, "Archive\\Family Photos")
        self.assertEqual(source.source_label, "Family Photos")
        self.assertIsNotNone(source.endpoint_id)

    def test_confirm_persists_operator_source_name(self) -> None:
        request = {
            "source_type": "external",
            "device_name": "External 1",
            "source_name": "  Vacation Photos  ",
            "naming_action": "create_new",
            "observed_path": "E:\\Archive\\Family Photos",
        }
        with patch("app.api.admin.get_source_identity_probe_service", return_value=_FakeProbeService()):
            plan_response = self.client.post("/api/admin/source-creation/plan", json=request)
            plan = plan_response.json()
            confirm_response = self.client.post(
                "/api/admin/source-creation/confirm",
                json={
                    **request,
                    "plan_fingerprint": plan["plan_fingerprint"],
                    "operator_confirmed": True,
                },
            )

        self.assertEqual(plan_response.status_code, 200)
        self.assertEqual(plan["source_display_name"], "Vacation Photos")
        self.assertEqual(confirm_response.status_code, 200)
        result = confirm_response.json()
        source = self.db.get(IngestionSource, result["source_profile_id"])
        self.assertEqual(result["source_display_name"], "Vacation Photos")
        self.assertEqual(source.source_label, "Vacation Photos")

    def test_path_first_plan_does_not_require_device_name_or_write_rows(self) -> None:
        with patch("app.api.admin.get_source_identity_probe_service", return_value=_FakeProbeService()):
            response = self.client.post(
                "/api/admin/source-creation/plan",
                json={
                    "source_type": "external",
                    "observed_path": "E:\\Archive\\Family Photos",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["recognition_status"], "new_device")
        self.assertEqual(payload["plan_status"], "needs_review")
        self.assertEqual(self.db.scalar(select(func.count(SourceEndpoint.id))), 0)
        self.assertEqual(self.db.scalar(select(func.count(IngestionSource.id))), 0)

    def test_blocked_plan_writes_nothing(self) -> None:
        response = self.client.post(
            "/api/admin/source-creation/plan",
            json={
                "source_type": "local",
                "device_name": "Chuck PC",
                "observed_path": "\\\\HENDERSON-NAS\\Photos",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["plan_status"], "blocked")
        self.assertEqual(self.db.scalar(select(func.count(SourceEndpoint.id))), 0)
        self.assertEqual(self.db.scalar(select(func.count(IngestionSource.id))), 0)

    def test_generic_creation_rejects_provider_specific_and_unsupported_types(self) -> None:
        for source_type in ("icloud",):
            response = self.client.post(
                "/api/admin/source-creation/plan",
                json={
                    "source_type": source_type,
                    "device_name": "Unsupported source",
                    "observed_path": "C:\\Photos",
                },
            )
            self.assertEqual(response.status_code, 422)

        self.assertEqual(self.db.scalar(select(func.count(SourceEndpoint.id))), 0)
        self.assertEqual(self.db.scalar(select(func.count(IngestionSource.id))), 0)

    def test_removable_plan_is_accepted(self) -> None:
        request = {
            "source_type": "removable",
            "device_name": "Camera SD Card",
            "naming_action": "create_new",
            "observed_path": "H:\\DCIM",
        }
        with patch("app.api.admin.get_source_identity_probe_service", return_value=_FakeProbeService()):
            response = self.client.post("/api/admin/source-creation/plan", json=request)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["recognized_source_type"], "removable")
        self.assertEqual(payload["persisted_source_type"], "removable_media")

    def test_optical_plan_is_accepted(self) -> None:
        request = {
            "source_type": "optical",
            "device_name": "12.63.18.6 Validation CD-RW",
            "naming_action": "create_new",
            "observed_path": "E:\\",
        }
        with patch("app.api.admin.get_source_identity_probe_service", return_value=_FakeProbeService()):
            response = self.client.post("/api/admin/source-creation/plan", json=request)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["recognized_source_type"], "optical")
        self.assertEqual(payload["persisted_source_type"], "optical_media")
        self.assertEqual(payload["entire_endpoint_label"], "Entire disc")

    def _override_db(self):
        yield self.db


if __name__ == "__main__":
    unittest.main()
