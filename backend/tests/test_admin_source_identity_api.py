from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.admin import router as admin_router
from app.services.source_identity.probe_schema import (
    AccessNodeSummary,
    SourceIdentityCapabilitiesResponse,
    SourceIdentityProbeRequest,
    SourceIdentityProbeResponse,
    SourceIdentityProviderCapabilities,
    SourceRootCandidate,
)


class _FakeSourceIdentityProbeService:
    def probe(self, request: SourceIdentityProbeRequest) -> SourceIdentityProbeResponse:
        return SourceIdentityProbeResponse(
            probe_status="completed",
            source_type=request.source_type,
            os_family="windows",
            provider_name="windows_non_admin_probe_v1",
            provider_version="1",
            access_node_summary=AccessNodeSummary(os_family="windows"),
            observed_path=request.observed_path,
            normalized_observed_path=(request.observed_path or "").lower() or None,
            source_root_candidate=SourceRootCandidate(
                path=request.observed_path,
                is_valid_source_root_candidate=True,
                filesystem_boundary_type="local_folder",
                root_reason="test",
            ),
            confidence_tier="not_compared",
            safe_to_run="not_applicable",
        )

    def capabilities(self) -> SourceIdentityCapabilitiesResponse:
        return SourceIdentityCapabilitiesResponse(
            os_family="windows",
            supported_providers=["windows_non_admin_probe_v1"],
            default_provider="windows_non_admin_probe_v1",
            capabilities={
                "windows_non_admin_probe_v1": SourceIdentityProviderCapabilities(
                    path_exists_check=True,
                    volume_identity=True,
                )
            },
        )


class AdminSourceIdentityApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(admin_router)
        self.client = TestClient(self.app)

    def test_probe_endpoint_returns_normalized_response(self) -> None:
        with patch("app.api.admin.get_source_identity_probe_service", return_value=_FakeSourceIdentityProbeService()):
            response = self.client.post(
                "/api/admin/source-identity/probe",
                json={"source_type": "local", "observed_path": "C:\\Photos", "os_family": "windows"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["provider_name"], "windows_non_admin_probe_v1")
        self.assertEqual(payload["source_root_candidate"]["filesystem_boundary_type"], "local_folder")

    def test_capabilities_endpoint_returns_provider_summary(self) -> None:
        with patch("app.api.admin.get_source_identity_probe_service", return_value=_FakeSourceIdentityProbeService()):
            response = self.client.get("/api/admin/source-identity/capabilities")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["default_provider"], "windows_non_admin_probe_v1")
        self.assertTrue(payload["capabilities"]["windows_non_admin_probe_v1"]["path_exists_check"])


if __name__ == "__main__":
    unittest.main()
