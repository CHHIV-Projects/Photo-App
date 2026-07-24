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
from app.models.ingestion_source import IngestionSource
from app.models.source_endpoint import AccessNode, SourceEndpoint, SourceEndpointObservedPath
from app.services.source_identity.identity_fingerprint import volume_guid_fingerprint
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


class AdminSourceSelectionApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        AccessNode.__table__.create(self.engine)
        SourceEndpoint.__table__.create(self.engine)
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

    def test_select_source_endpoint_returns_selected_response(self) -> None:
        fingerprint_hash, fingerprint_version = volume_guid_fingerprint("11111111-1111-1111-1111-111111111111")
        endpoint = SourceEndpoint(
            source_type="external_device",
            alias="External 10",
            alias_normalized="external 10",
            status="active",
            identity_fingerprint_hash=fingerprint_hash,
            identity_fingerprint_version=fingerprint_version,
            identity_confidence="strong_match",
        )
        self.db.add(endpoint)
        self.db.commit()
        self.db.refresh(endpoint)
        source = IngestionSource(
            source_label="Family Photos",
            source_label_normalized="family photos",
            source_type="external_drive",
            source_root_path="E:\\Pictures",
            source_root_path_normalized="e:\\pictures",
            endpoint_id=endpoint.id,
            endpoint_relative_root="Pictures",
            profile_status="active",
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)

        with patch("app.api.admin.get_source_identity_probe_service", return_value=_FakeProbeService(_volume_probe("E:\\Pictures", "11111111-1111-1111-1111-111111111111"))):
            response = self.client.post("/api/admin/source-selection/select", json={"source_profile_id": source.id})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["result"], "selected")
        self.assertEqual(payload["availability"], "available")
        self.assertEqual(payload["workflow_kind"], "filesystem_source_intake")
        self.assertIsNotNone(payload["selected_source_context"])
        self.assertEqual(payload["selected_source_context"]["friendly_source_type"], "External")

    def test_select_source_missing_profile_returns_404(self) -> None:
        response = self.client.post("/api/admin/source-selection/select", json={"source_profile_id": 9999})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Source profile not found."})

    def _override_db(self):
        yield self.db


def _volume_probe(path: str, guid: str) -> SourceIdentityProbeResponse:
    fingerprint_hash, fingerprint_version = volume_guid_fingerprint(guid)
    evidence = SourceIdentityEvidenceItem(
        category="volume_evidence",
        code="volume_guid_present",
        status="present",
        durability="durable",
        privacy_level="masked_only",
        source_types=["external_device"],
        masked_value="{...1111}",
        fingerprint_hash=fingerprint_hash,
        fingerprint_version=fingerprint_version,
    )
    return SourceIdentityProbeResponse(
        probe_status="completed",
        source_type="external_device",
        os_family="windows",
        provider_name="fake_probe",
        provider_version="1",
        access_node_summary=AccessNodeSummary(label="Test Windows PC", os_family="windows"),
        observed_path=path,
        normalized_observed_path=path.casefold(),
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
