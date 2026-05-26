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


if __name__ == "__main__":
    unittest.main()
