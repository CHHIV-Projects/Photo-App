"""API tests for admin source profiles endpoint."""

from __future__ import annotations

from datetime import datetime, timezone
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.admin import router as admin_router
from app.db.session import get_db_session
from app.schemas.admin import SourceProfileSummary


class _DummySession:
    pass


def _override_db_session():
    yield _DummySession()


class AdminSourceProfilesApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(admin_router)
        self.app.dependency_overrides[get_db_session] = _override_db_session
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_get_source_profiles_defaults_to_active_filter(self) -> None:
        profiles = [
            SourceProfileSummary(
                source_id=42,
                source_label="iCloud - Primary",
                source_type="cloud_export",
                source_root_path="/exports/icloud_primary",
                profile_status="active",
                cloud_provider="icloud",
                acquisition_method="icloudpd",
                managed_staging_path="/exports/icloud_primary/staging",
                account_username_masked="u***@icloud.com",
                account_username=None,
                first_seen_at=datetime.now(timezone.utc),
                last_run_at=None,
            )
        ]

        with patch("app.api.admin.list_source_profiles", return_value=profiles) as mocked_service:
            response = self.client.get("/api/admin/source-profiles")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["profiles"]), 1)
        self.assertEqual(payload["profiles"][0]["profile_status"], "active")
        mocked_service.assert_called_once()
        called_args, called_kwargs = mocked_service.call_args
        self.assertEqual(called_kwargs["status"], "active")
        self.assertFalse(called_kwargs["include_username"])
        self.assertIsInstance(called_args[0], _DummySession)

    def test_get_source_profiles_honors_query_parameters(self) -> None:
        with patch("app.api.admin.list_source_profiles", return_value=[]) as mocked_service:
            response = self.client.get("/api/admin/source-profiles?status=all&include_username=true")

        self.assertEqual(response.status_code, 200)
        mocked_service.assert_called_once()
        _, called_kwargs = mocked_service.call_args
        self.assertEqual(called_kwargs["status"], "all")
        self.assertTrue(called_kwargs["include_username"])

    def test_get_source_profiles_invalid_filter_returns_400(self) -> None:
        with patch("app.api.admin.list_source_profiles", side_effect=ValueError("Invalid status filter")):
            response = self.client.get("/api/admin/source-profiles?status=bogus")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "Invalid status filter"})


if __name__ == "__main__":
    unittest.main()
