"""API tests for visual enrichment candidate preview and run endpoints."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.visual_enrichment import router as visual_enrichment_router
from app.db.session import get_db_session


class _DummySession:
    pass


def _override_db_session():
    yield _DummySession()


class VisualEnrichmentApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(visual_enrichment_router)
        self.app.dependency_overrides[get_db_session] = _override_db_session
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_preview_candidates_returns_counts(self) -> None:
        expected = {
            "candidate_count": 12,
            "excluded_existing_observations_count": 2,
            "excluded_existing_context_labels_count": 1,
            "run_count": 9,
            "showing_count": 2,
            "assets": [
                {
                    "asset_sha256": "aaa111",
                    "filename": "IMG_1001.JPG",
                    "image_url": "/media/previews/a.jpg",
                    "display_url": "/media/previews/a.jpg",
                    "is_canonical": True,
                    "duplicate_group_id": 42,
                    "has_landmark_observation": False,
                    "has_landmark_context_label": False,
                },
                {
                    "asset_sha256": "bbb222",
                    "filename": "IMG_1002.JPG",
                    "image_url": "/media/previews/b.jpg",
                    "display_url": "/media/previews/b.jpg",
                    "is_canonical": True,
                    "duplicate_group_id": None,
                    "has_landmark_observation": False,
                    "has_landmark_context_label": False,
                },
            ],
        }
        with patch("app.api.visual_enrichment.preview_visual_enrichment_candidates", return_value=expected):
            response = self.client.post(
                "/api/visual-enrichment/candidates/preview",
                json={
                    "pool_type": "collection",
                    "pool_id": 5,
                    "canonical_only": True,
                    "exclude_existing_observations": True,
                    "exclude_existing_context_labels": True,
                    "limit": 50,
                },
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["candidate_count"], 12)
        self.assertEqual(body["showing_count"], 2)

    def test_preview_candidates_maps_missing_collection_to_404(self) -> None:
        with patch(
            "app.api.visual_enrichment.preview_visual_enrichment_candidates",
            side_effect=ValueError("Collection ID 999 does not exist."),
        ):
            response = self.client.post(
                "/api/visual-enrichment/candidates/preview",
                json={"pool_type": "collection", "pool_id": 999},
            )

        self.assertEqual(response.status_code, 404)

    def test_run_google_vision_returns_summary(self) -> None:
        expected = {
            "requested_count": 2,
            "processed_count": 2,
            "provider_calls_attempted": 0,
            "observations_created_count": 2,
            "no_landmark_count": 0,
            "failed_count": 0,
            "report_path": "storage/logs/google_vision_reports/google_vision_test_x.json",
            "mode": "dry_run",
            "features_requested": ["landmark"],
            "asset_results": [
                {
                    "asset_sha256": "aaa111",
                    "filename": "IMG_1001.JPG",
                    "status": "ok",
                    "error": None,
                    "landmarks": [{"description": "Mock Landmark aaa111", "score": 0.99}],
                    "web_entities": [],
                    "best_guess_labels": [],
                    "labels": [],
                    "objects": [],
                    "created_observations": 1,
                    "no_landmark": False,
                },
                {
                    "asset_sha256": "bbb222",
                    "filename": "IMG_1002.JPG",
                    "status": "ok",
                    "error": None,
                    "landmarks": [{"description": "Mock Landmark bbb222", "score": 0.99}],
                    "web_entities": [],
                    "best_guess_labels": [],
                    "labels": [],
                    "objects": [],
                    "created_observations": 1,
                    "no_landmark": False,
                },
            ],
        }
        with patch("app.api.visual_enrichment.run_visual_enrichment_landmark_detection", return_value=expected):
            response = self.client.post(
                "/api/visual-enrichment/run-google-vision",
                json={
                    "asset_sha256s": ["aaa111", "bbb222"],
                    "live": False,
                    "mock_provider": True,
                    "feature_landmark": True,
                    "feature_web": False,
                    "feature_label": False,
                    "feature_object": False,
                },
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["requested_count"], 2)
        self.assertEqual(body["mode"], "dry_run")

    def test_run_google_vision_invalid_live_runtime_returns_400(self) -> None:
        with patch(
            "app.api.visual_enrichment.run_visual_enrichment_landmark_detection",
            side_effect=ValueError("VISION_ENABLED is false."),
        ):
            response = self.client.post(
                "/api/visual-enrichment/run-google-vision",
                json={
                    "asset_sha256s": ["aaa111"],
                    "live": True,
                    "mock_provider": False,
                },
            )

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
