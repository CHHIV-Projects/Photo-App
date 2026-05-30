"""API tests for asset context label listing endpoint."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.asset_context_labels import router as asset_context_labels_router
from app.db.session import get_db_session


class _DummySession:
    pass


def _override_db_session():
    yield _DummySession()


class AssetContextLabelsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(asset_context_labels_router)
        self.app.dependency_overrides[get_db_session] = _override_db_session
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_list_asset_context_labels_returns_items(self) -> None:
        expected = {
            "count": 1,
            "items": [
                {
                    "id": 7,
                    "asset_sha256": "abc123",
                    "asset_filename": "IMG_4819.JPG",
                    "label": "Midgley Bridge",
                    "label_normalized": "midgley bridge",
                    "context_type": "landmark",
                    "source_type": "google_vision",
                    "source_observation_id": 15,
                    "status": "active",
                    "confidence": 0.9,
                    "created_at_utc": "2026-05-26T10:00:00Z",
                }
            ],
        }
        with patch("app.api.asset_context_labels.list_asset_context_labels", return_value=expected):
            response = self.client.get(
                "/api/asset-context-labels",
                params={
                    "context_type": "landmark",
                    "status": "active",
                    "source_type": "google_vision",
                },
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["items"][0]["label"], "Midgley Bridge")

    def test_list_asset_context_labels_invalid_filter_returns_400(self) -> None:
        with patch(
            "app.api.asset_context_labels.list_asset_context_labels",
            side_effect=ValueError("Invalid context_type for asset context label."),
        ):
            response = self.client.get("/api/asset-context-labels", params={"context_type": "invalid"})

        self.assertEqual(response.status_code, 400)

    def test_summary_batch_returns_items(self) -> None:
        expected = {
            "count": 1,
            "items": [
                {
                    "asset_sha256": "abc123",
                    "landmark_labels": ["Midgley Bridge", "Sedona"],
                    "count": 2,
                }
            ],
        }
        with patch("app.api.asset_context_labels.list_active_landmark_context_summaries", return_value=expected):
            response = self.client.post(
                "/api/asset-context-labels/summary",
                json={"asset_sha256s": ["abc123", "def456"]},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["items"][0]["asset_sha256"], "abc123")

    def test_create_asset_context_label_returns_context(self) -> None:
        expected = {
            "context_label": {
                "id": 42,
                "asset_sha256": "abc123",
                "asset_filename": "IMG_4819.JPG",
                "label": "Cathedral Rock",
                "label_normalized": "cathedral rock",
                "context_type": "landmark",
                "source_type": "user",
                "source_observation_id": None,
                "status": "active",
                "confidence": None,
                "created_at_utc": "2026-05-27T12:00:00Z",
            },
            "already_present": False,
        }
        with patch("app.api.asset_context_labels.create_asset_context_label", return_value=expected):
            response = self.client.post(
                "/api/asset-context-labels",
                json={
                    "asset_sha256": "abc123",
                    "label": "Cathedral Rock",
                    "context_type": "landmark",
                    "source_type": "user",
                },
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["context_label"]["label"], "Cathedral Rock")
        self.assertFalse(body["already_present"])

    def test_create_asset_context_label_missing_asset_maps_to_404(self) -> None:
        with patch(
            "app.api.asset_context_labels.create_asset_context_label",
            side_effect=ValueError("Asset does not exist."),
        ):
            response = self.client.post(
                "/api/asset-context-labels",
                json={
                    "asset_sha256": "missing",
                    "label": "Cathedral Rock",
                    "context_type": "landmark",
                    "source_type": "user",
                },
            )

        self.assertEqual(response.status_code, 404)

    def test_get_propagation_preview_returns_targets(self) -> None:
        expected = {
            "source_label": {
                "id": 7,
                "asset_sha256": "abc123",
                "asset_filename": "IMG_4819.JPG",
                "asset_image_url": "/media/previews/aa.jpg",
                "asset_display_url": "/media/previews/aa.jpg",
                "duplicate_group_id": 739,
                "is_canonical": False,
                "label": "Midgley Bridge",
                "label_normalized": "midgley bridge",
                "context_type": "landmark",
                "source_type": "google_vision",
                "source_observation_id": 15,
                "status": "active",
                "confidence": 0.9,
                "created_at_utc": "2026-05-26T10:00:00Z",
            },
            "duplicate_group_id": 739,
            "eligible_target_count": 1,
            "targets": [
                {
                    "asset_sha256": "xyz456",
                    "asset_filename": "IMG_4819_export.JPG",
                    "image_url": "/media/previews/bb.jpg",
                    "display_url": "/media/previews/bb.jpg",
                    "duplicate_group_id": 739,
                    "is_canonical": True,
                    "already_has_label": False,
                    "selectable": True,
                    "default_selected": True,
                }
            ],
            "message": None,
        }
        with patch("app.api.asset_context_labels.get_context_label_propagation_preview", return_value=expected):
            response = self.client.get("/api/asset-context-labels/7/propagation-preview")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["duplicate_group_id"], 739)
        self.assertEqual(body["targets"][0]["asset_sha256"], "xyz456")

    def test_get_propagation_preview_missing_label_maps_to_404(self) -> None:
        with patch(
            "app.api.asset_context_labels.get_context_label_propagation_preview",
            side_effect=ValueError("Context label does not exist."),
        ):
            response = self.client.get("/api/asset-context-labels/999/propagation-preview")

        self.assertEqual(response.status_code, 404)

    def test_post_propagate_returns_counts(self) -> None:
        expected = {
            "source_label_id": 7,
            "requested_count": 2,
            "added_count": 1,
            "already_present_count": 1,
            "skipped_count": 0,
            "failed_count": 0,
        }
        with patch("app.api.asset_context_labels.propagate_context_label_to_duplicate_group_members", return_value=expected):
            response = self.client.post(
                "/api/asset-context-labels/7/propagate",
                json={"target_asset_sha256s": ["xyz456", "aaa111"]},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["added_count"], 1)
        self.assertEqual(body["already_present_count"], 1)

    def test_post_propagate_invalid_target_returns_400(self) -> None:
        with patch(
            "app.api.asset_context_labels.propagate_context_label_to_duplicate_group_members",
            side_effect=ValueError("Target asset xyz is outside the source duplicate group."),
        ):
            response = self.client.post(
                "/api/asset-context-labels/7/propagate",
                json={"target_asset_sha256s": ["xyz"]},
            )

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
