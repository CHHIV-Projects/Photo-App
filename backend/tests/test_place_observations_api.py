"""API tests for global place observation review endpoints."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.place_observations import router as place_observations_router
from app.db.session import get_db_session


class _DummySession:
    pass


def _override_db_session():
    yield _DummySession()


class PlaceObservationsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(place_observations_router)
        self.app.dependency_overrides[get_db_session] = _override_db_session
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_list_place_observations_returns_items(self) -> None:
        expected = {
            "count": 1,
            "items": [
                {
                    "id": 9,
                    "place_id": None,
                    "asset_sha256": "abc",
                    "source_type": "google_vision",
                    "observation_type": "landmark",
                    "status": "pending",
                    "raw_label": "Eiffel Tower",
                    "formatted_address": None,
                    "street": None,
                    "city": None,
                    "county": None,
                    "state": None,
                    "postal_code": None,
                    "country": "France",
                    "latitude": 48.8584,
                    "longitude": 2.2945,
                    "confidence": 0.88,
                    "raw_response_json": {"provider": "google_vision"},
                    "created_at_utc": None,
                    "asset": None,
                    "linked_place": None,
                }
            ],
        }
        with patch("app.api.place_observations.list_global_place_observations", return_value=expected):
            response = self.client.get(
                "/api/place-observations",
                params={
                    "source_type": "google_vision",
                    "observation_type": "landmark",
                    "status": "pending",
                    "limit": 50,
                    "offset": 0,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["items"][0]["raw_label"], "Eiffel Tower")

    def test_patch_place_observation_maps_not_found_to_404(self) -> None:
        with patch("app.api.place_observations.patch_global_place_observation", side_effect=ValueError("Observation does not exist.")):
            response = self.client.patch(
                "/api/place-observations/99",
                json={"status": "accepted"},
            )

        self.assertEqual(response.status_code, 404)

    def test_create_place_from_observation_returns_updated_observation(self) -> None:
        expected = {
            "id": 15,
            "place_id": "23",
            "asset_sha256": "abc",
            "source_type": "google_vision",
            "observation_type": "landmark",
            "status": "accepted",
            "raw_label": "Golden Gate Bridge",
            "formatted_address": None,
            "street": None,
            "city": "San Francisco",
            "county": None,
            "state": "California",
            "postal_code": None,
            "country": "United States",
            "latitude": 37.8199,
            "longitude": -122.4783,
            "confidence": 0.91,
            "raw_response_json": None,
            "created_at_utc": None,
            "asset": {
                "asset_sha256": "abc",
                "filename": "photo.jpg",
                "image_url": "/media/previews/photo.jpg",
                "display_url": "/media/previews/photo.jpg",
            },
            "linked_place": {
                "place_id": "23",
                "display_label": "Golden Gate Bridge",
                "latitude": 37.8199,
                "longitude": -122.4783,
            },
        }
        with patch("app.api.place_observations.create_place_from_observation", return_value=expected):
            response = self.client.post(
                "/api/place-observations/15/create-place",
                json={"user_label": "Golden Gate Bridge"},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "accepted")
        self.assertEqual(body["place_id"], "23")

    def test_accept_as_context_returns_payload(self) -> None:
        expected = {
            "context_label": {
                "id": 41,
                "asset_sha256": "abc",
                "asset_filename": "IMG_4819.JPG",
                "label": "Midgley Bridge",
                "label_normalized": "midgley bridge",
                "context_type": "landmark",
                "source_type": "google_vision",
                "source_observation_id": 15,
                "status": "active",
                "confidence": 0.91,
                "created_at_utc": "2026-05-26T10:00:00Z",
            },
            "observation_status": "accepted",
            "already_present": False,
        }
        with patch("app.api.place_observations.accept_landmark_observation_as_context", return_value=expected):
            response = self.client.post(
                "/api/place-observations/15/accept-as-context",
                json={"label": "Midgley Bridge"},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["context_label"]["context_type"], "landmark")
        self.assertEqual(body["observation_status"], "accepted")

    def test_accept_as_context_maps_not_found_to_404(self) -> None:
        with patch(
            "app.api.place_observations.accept_landmark_observation_as_context",
            side_effect=ValueError("Observation does not exist."),
        ):
            response = self.client.post(
                "/api/place-observations/999/accept-as-context",
                json={},
            )

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
