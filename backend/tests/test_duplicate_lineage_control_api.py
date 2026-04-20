"""API tests for duplicate-lineage manual control endpoints."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.duplicates import router as duplicates_router
from app.db.session import get_db_session


class _DummySession:
    pass


def _override_db_session():
    yield _DummySession()


class DuplicateLineageControlApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(duplicates_router)
        self.app.dependency_overrides[get_db_session] = _override_db_session
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_get_merge_targets_returns_items(self) -> None:
        with patch(
            "app.api.duplicates.list_duplicate_merge_targets",
            return_value=[
                {
                    "asset_sha256": "target-sha",
                    "filename": "IMG_1000.HEIC",
                    "image_url": "/media/assets/aa/target-sha.heic",
                    "captured_at": "2025-01-01T00:00:00Z",
                    "duplicate_group_id": 11,
                    "duplicate_count": 4,
                    "is_canonical": True,
                }
            ],
        ):
            response = self.client.get("/api/duplicates/merge-targets", params={"source_asset_sha256": "source-sha"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["items"][0]["duplicate_group_id"], 11)

    def test_get_merge_targets_source_missing_returns_404(self) -> None:
        with patch("app.api.duplicates.list_duplicate_merge_targets", return_value=None):
            response = self.client.get("/api/duplicates/merge-targets", params={"source_asset_sha256": "missing"})

        self.assertEqual(response.status_code, 404)

    def test_merge_assets_returns_result_payload(self) -> None:
        with patch(
            "app.api.duplicates.merge_asset_into_target_lineage",
            return_value=type(
                "MergeResult",
                (),
                {
                    "source_asset_sha256": "source-sha",
                    "target_asset_sha256": "target-sha",
                    "resulting_group_id": 22,
                    "resulting_canonical_asset_sha256": "target-sha",
                    "affected_member_count": 5,
                    "affected_assets": [
                        {
                            "asset_sha256": "target-sha",
                            "filename": "IMG_1.HEIC",
                            "captured_at": "2026-01-20T15:22:19Z",
                            "duplicate_group_id": 22,
                            "is_canonical": True,
                        }
                    ],
                },
            )(),
        ):
            response = self.client.post(
                "/api/duplicates/merge-assets",
                json={"source_asset_sha256": "source-sha", "target_asset_sha256": "target-sha"},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["resulting_group_id"], 22)
        self.assertEqual(body["affected_member_count"], 5)

    def test_merge_assets_noop_returns_422(self) -> None:
        with patch(
            "app.api.duplicates.merge_asset_into_target_lineage",
            side_effect=ValueError("Source and target assets must be different."),
        ):
            response = self.client.post(
                "/api/duplicates/merge-assets",
                json={"source_asset_sha256": "same", "target_asset_sha256": "same"},
            )

        self.assertEqual(response.status_code, 422)

    def test_merge_assets_missing_target_returns_404(self) -> None:
        with patch(
            "app.api.duplicates.merge_asset_into_target_lineage",
            side_effect=LookupError("Target asset 'x' not found."),
        ):
            response = self.client.post(
                "/api/duplicates/merge-assets",
                json={"source_asset_sha256": "source", "target_asset_sha256": "x"},
            )

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
