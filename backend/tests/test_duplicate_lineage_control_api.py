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

    def test_get_suggestions_returns_items(self) -> None:
        with patch(
            "app.api.duplicates.list_duplicate_suggestions",
            return_value=type(
                "SuggestionResult",
                (),
                {
                    "total_count": 1,
                    "items": [
                        type(
                            "SuggestionItem",
                            (),
                            {
                                "confidence": "high",
                                "distance": 3,
                                "asset_a": {
                                    "asset_sha256": "a",
                                    "filename": "A.jpg",
                                    "image_url": "/media/assets/aa/a.jpg",
                                    "duplicate_group_id": None,
                                    "quality_score": 87.5,
                                },
                                "asset_b": {
                                    "asset_sha256": "b",
                                    "filename": "B.jpg",
                                    "image_url": "/media/assets/bb/b.jpg",
                                    "duplicate_group_id": 12,
                                    "quality_score": None,
                                },
                            },
                        )()
                    ],
                },
            )(),
        ):
            response = self.client.get("/api/duplicates/suggestions", params={"offset": 0, "limit": 50})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total_count"], 1)
        self.assertEqual(body["items"][0]["confidence"], "high")
        self.assertEqual(body["items"][0]["distance"], 3)

    def test_confirm_endpoint_reuses_merge_payload(self) -> None:
        with patch(
            "app.api.duplicates.merge_asset_into_target_lineage",
            return_value=type(
                "MergeResult",
                (),
                {
                    "source_asset_sha256": "source-sha",
                    "target_asset_sha256": "target-sha",
                    "resulting_group_id": 33,
                    "resulting_canonical_asset_sha256": "target-sha",
                    "affected_member_count": 2,
                    "affected_assets": [],
                },
            )(),
        ):
            response = self.client.post(
                "/api/duplicates/confirm",
                json={"source_asset_sha256": "source-sha", "target_asset_sha256": "target-sha"},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["resulting_group_id"], 33)
        self.assertFalse(body["noop"])

    def test_confirm_endpoint_already_grouped_returns_noop_success(self) -> None:
        with patch(
            "app.api.duplicates.merge_asset_into_target_lineage",
            side_effect=ValueError("Source and target assets are already in the same duplicate group."),
        ):
            response = self.client.post(
                "/api/duplicates/confirm",
                json={"source_asset_sha256": "source-sha", "target_asset_sha256": "target-sha"},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertTrue(body["noop"])

    def test_reject_endpoint_returns_canonical_order(self) -> None:
        with patch("app.api.duplicates.reject_duplicate_pair", return_value=True):
            response = self.client.post(
                "/api/duplicates/reject",
                json={"asset_sha256_a": "z-sha", "asset_sha256_b": "a-sha"},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertTrue(body["created"])
        self.assertEqual(body["asset_sha256_a"], "a-sha")
        self.assertEqual(body["asset_sha256_b"], "z-sha")

    def test_reject_endpoint_same_asset_returns_422(self) -> None:
        response = self.client.post(
            "/api/duplicates/reject",
            json={"asset_sha256_a": "same", "asset_sha256_b": "same"},
        )

        self.assertEqual(response.status_code, 422)

    def test_set_canonical_endpoint_returns_payload(self) -> None:
        with patch(
            "app.api.duplicates.set_group_canonical",
            return_value=type(
                "AdjudicationResult",
                (),
                {
                    "success": True,
                    "noop": False,
                    "message": "Canonical asset updated.",
                    "group_id": 42,
                    "asset_sha256": "asset-a",
                    "affected_assets": [],
                },
            )(),
        ):
            response = self.client.post("/api/duplicates/set-canonical", json={"asset_sha256": "asset-a"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertFalse(body["noop"])
        self.assertEqual(body["group_id"], 42)

    def test_remove_from_group_endpoint_not_found_returns_404(self) -> None:
        with patch("app.api.duplicates.remove_asset_from_group", return_value=None):
            response = self.client.post("/api/duplicates/remove-from-group", json={"asset_sha256": "missing"})

        self.assertEqual(response.status_code, 404)

    def test_demote_endpoint_validation_error_returns_422(self) -> None:
        with patch("app.api.duplicates.demote_group_asset", side_effect=ValueError("Cannot demote canonical asset.")):
            response = self.client.post("/api/duplicates/demote", json={"asset_sha256": "canonical"})

        self.assertEqual(response.status_code, 422)

    def test_restore_endpoint_noop_success(self) -> None:
        with patch(
            "app.api.duplicates.restore_group_asset",
            return_value=type(
                "AdjudicationResult",
                (),
                {
                    "success": True,
                    "noop": True,
                    "message": "Asset is already visible.",
                    "group_id": 7,
                    "asset_sha256": "asset-v",
                    "affected_assets": [],
                },
            )(),
        ):
            response = self.client.post("/api/duplicates/restore", json={"asset_sha256": "asset-v"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertTrue(body["noop"])


if __name__ == "__main__":
    unittest.main()
