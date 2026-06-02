"""API tests for admin source profiles endpoint."""

from __future__ import annotations

from datetime import datetime, timezone
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.admin import router as admin_router
from app.db.session import get_db_session
from app.schemas.admin import (
    SourceProfileDetail,
    SourceProfilePathCheckResponse,
    SourceProfileStagingFolderCreateResponse,
    SourceProfileSummary,
)


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

    def test_get_source_profiles_supports_non_active_filter(self) -> None:
        with patch("app.api.admin.list_source_profiles", return_value=[]) as mocked_service:
            response = self.client.get("/api/admin/source-profiles?status=inactive")

        self.assertEqual(response.status_code, 200)
        mocked_service.assert_called_once()
        _, called_kwargs = mocked_service.call_args
        self.assertEqual(called_kwargs["status"], "inactive")
        self.assertFalse(called_kwargs["include_username"])

    def test_get_source_profiles_invalid_filter_returns_400(self) -> None:
        with patch("app.api.admin.list_source_profiles", side_effect=ValueError("Invalid status filter")):
            response = self.client.get("/api/admin/source-profiles?status=bogus")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "Invalid status filter"})

    def test_patch_source_profile_status_updates_source(self) -> None:
        updated = SourceProfileSummary(
            source_id=7,
            source_label="Archive Candidate",
            source_type="local_folder",
            source_root_path="/data/archive_candidate",
            profile_status="archived",
            cloud_provider=None,
            acquisition_method=None,
            managed_staging_path=None,
            account_username_masked=None,
            account_username=None,
            first_seen_at=datetime.now(timezone.utc),
            last_run_at=None,
            provenance_count=10,
            ingestion_runs_count=3,
            source_intake_runs_count=2,
            icloud_acquisition_runs_count=0,
        )

        with patch("app.api.admin.update_source_profile_status", return_value=updated) as mocked_service:
            response = self.client.patch(
                "/api/admin/source-profiles/7?include_username=true",
                json={"profile_status": "archived"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["source_id"], 7)
        self.assertEqual(payload["profile_status"], "archived")
        mocked_service.assert_called_once()
        _, called_kwargs = mocked_service.call_args
        self.assertEqual(called_kwargs["source_id"], 7)
        self.assertEqual(called_kwargs["profile_status"], "archived")
        self.assertTrue(called_kwargs["include_username"])

    def test_patch_source_profile_status_invalid_value_returns_400(self) -> None:
        with patch("app.api.admin.update_source_profile_status", side_effect=ValueError("Invalid status filter")):
            response = self.client.patch(
                "/api/admin/source-profiles/7",
                json={"profile_status": "bogus"},
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "Invalid status filter"})

    def test_patch_source_profile_status_missing_source_returns_404(self) -> None:
        with patch("app.api.admin.update_source_profile_status", side_effect=LookupError("missing")):
            response = self.client.patch(
                "/api/admin/source-profiles/99999",
                json={"profile_status": "inactive"},
            )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Source profile not found."})

    def test_get_source_profile_detail_returns_200(self) -> None:
        detail = SourceProfileDetail(
            source_id=7,
            source_label="Archive Candidate",
            normalized_label="archive candidate",
            source_type="local_folder",
            source_root_path="/data/archive_candidate",
            source_root_path_relative=None,
            profile_status="active",
            cloud_provider=None,
            acquisition_method=None,
            managed_staging_path=None,
            managed_staging_path_relative=None,
            effective_path="/data/archive_candidate",
            effective_path_relative=None,
            effective_path_kind="source_root_path",
            expected_acquisition_path=None,
            account_username_masked=None,
            account_username=None,
            first_seen_at=datetime.now(timezone.utc),
            last_run_at=None,
            provenance_count=10,
            ingestion_runs_count=3,
            source_intake_runs_count=2,
            icloud_acquisition_runs_count=0,
            is_referenced=True,
            has_path_divergence=False,
            warnings=["This source profile has historical references. Edits should preserve provenance meaning."],
        )

        with patch("app.api.admin.get_source_profile_detail", return_value=detail) as mocked_service:
            response = self.client.get("/api/admin/source-profiles/7")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["source_id"], 7)
        self.assertTrue(payload["is_referenced"])
        self.assertIsNone(payload["expected_acquisition_path"])
        mocked_service.assert_called_once()

    def test_get_source_profile_detail_missing_source_returns_404(self) -> None:
        with patch("app.api.admin.get_source_profile_detail", side_effect=LookupError("missing")):
            response = self.client.get("/api/admin/source-profiles/99999")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Source profile not found."})

    def test_post_source_profile_create_or_get_response(self) -> None:
        created_profile = SourceProfileSummary(
            source_id=101,
            source_label="Chuck iCloud",
            source_type="cloud_export",
            source_root_path="/storage/exports/icloud/chuck-icloud",
            profile_status="active",
            cloud_provider="icloud",
            acquisition_method="icloudpd",
            managed_staging_path="/storage/exports/icloud/chuck-icloud",
            account_username_masked="c***@gmail.com",
            account_username=None,
            first_seen_at=datetime.now(timezone.utc),
            last_run_at=None,
            provenance_count=0,
            ingestion_runs_count=0,
            source_intake_runs_count=0,
            icloud_acquisition_runs_count=0,
        )
        with patch(
            "app.api.admin.create_source_profile",
            return_value={"already_exists": False, "profile": created_profile},
        ) as mocked_service:
            response = self.client.post(
                "/api/admin/source-profiles",
                json={
                    "source_label": "Chuck iCloud",
                    "source_type": "cloud_export",
                    "cloud_provider": "icloud",
                    "account_username": "chhendersoniv@gmail.com",
                    "acquisition_method": "icloudpd",
                    "profile_status": "active",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["already_exists"])
        self.assertEqual(payload["profile"]["source_label"], "Chuck iCloud")
        mocked_service.assert_called_once()

    def test_post_source_profile_invalid_payload_returns_400(self) -> None:
        with patch("app.api.admin.create_source_profile", side_effect=ValueError("Invalid source_type")):
            response = self.client.post(
                "/api/admin/source-profiles",
                json={
                    "source_label": "Bad Source",
                    "source_type": "cloud",
                    "profile_status": "active",
                },
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "Invalid source_type"})

    def test_patch_source_profile_metadata_updates_safe_fields(self) -> None:
        updated = SourceProfileSummary(
            source_id=8,
            source_label="Chuck iCloud Updated",
            source_type="cloud_export",
            source_root_path="/storage/exports/icloud/chuck-icloud",
            profile_status="inactive",
            cloud_provider="icloud",
            acquisition_method="icloudpd",
            managed_staging_path="/storage/exports/icloud/chuck-icloud",
            account_username_masked="c***@gmail.com",
            account_username=None,
            first_seen_at=datetime.now(timezone.utc),
            last_run_at=None,
            provenance_count=1,
            ingestion_runs_count=1,
            source_intake_runs_count=0,
            icloud_acquisition_runs_count=0,
        )
        with patch("app.api.admin.update_source_profile_metadata", return_value=updated) as mocked_service:
            response = self.client.patch(
                "/api/admin/source-profiles/8/metadata",
                json={
                    "source_label": "Chuck iCloud Updated",
                    "profile_status": "inactive",
                    "cloud_provider": "icloud",
                    "account_username": "chhendersoniv@gmail.com",
                    "acquisition_method": "icloudpd",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["source_id"], 8)
        self.assertEqual(payload["profile_status"], "inactive")
        mocked_service.assert_called_once()

    def test_patch_source_profile_metadata_invalid_field_returns_400(self) -> None:
        with patch("app.api.admin.update_source_profile_metadata", side_effect=ValueError("managed_staging_path can only be edited for cloud_export source profiles.")):
            response = self.client.patch(
                "/api/admin/source-profiles/8/metadata",
                json={
                    "managed_staging_path": "/tmp/example",
                },
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {"detail": "managed_staging_path can only be edited for cloud_export source profiles."},
        )

    def test_patch_source_profile_metadata_missing_source_returns_404(self) -> None:
        with patch("app.api.admin.update_source_profile_metadata", side_effect=LookupError("missing")):
            response = self.client.patch(
                "/api/admin/source-profiles/888/metadata",
                json={"source_label": "Missing"},
            )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Source profile not found."})

    def test_verify_source_profile_path_returns_200(self) -> None:
        checked = SourceProfilePathCheckResponse(
            source_id=22,
            path="/storage/exports/icloud/chuck-icloud",
            path_relative="storage/exports/icloud/chuck-icloud",
            path_kind="managed_staging_path",
            exists=True,
            is_directory=True,
            checked_at=datetime.now(timezone.utc),
        )

        with patch("app.api.admin.verify_source_profile_path", return_value=checked) as mocked_service:
            response = self.client.post("/api/admin/source-profiles/22/verify-path")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["exists"])
        mocked_service.assert_called_once()

    def test_verify_source_profile_path_missing_source_returns_404(self) -> None:
        with patch("app.api.admin.verify_source_profile_path", side_effect=LookupError("missing")):
            response = self.client.post("/api/admin/source-profiles/999/verify-path")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Source profile not found."})

    def test_create_staging_folder_returns_200(self) -> None:
        created = SourceProfileStagingFolderCreateResponse(
            source_id=22,
            path="/storage/exports/icloud/chuck-icloud",
            path_relative="storage/exports/icloud/chuck-icloud",
            created=True,
            exists=True,
            checked_at=datetime.now(timezone.utc),
        )

        with patch("app.api.admin.create_source_profile_staging_folder", return_value=created) as mocked_service:
            response = self.client.post("/api/admin/source-profiles/22/create-staging-folder")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["created"])
        mocked_service.assert_called_once()

    def test_create_staging_folder_invalid_request_returns_400(self) -> None:
        with patch(
            "app.api.admin.create_source_profile_staging_folder",
            side_effect=ValueError("managed_staging_path is outside the approved iCloud exports root."),
        ):
            response = self.client.post("/api/admin/source-profiles/22/create-staging-folder")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {"detail": "managed_staging_path is outside the approved iCloud exports root."},
        )


if __name__ == "__main__":
    unittest.main()
