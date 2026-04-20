"""API tests for photo-level event membership correction endpoints."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.photos import router as photos_router
from app.db.session import get_db_session


class _DummySession:
    pass


def _override_db_session():
    yield _DummySession()


class PhotoEventMembershipApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(photos_router)
        self.app.dependency_overrides[get_db_session] = _override_db_session
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_remove_photo_event_returns_impacted_old_event(self) -> None:
        with patch(
            "app.api.photos.remove_asset_from_event",
            return_value=type(
                "MutationResult",
                (),
                {
                    "asset_sha256": "test-sha",
                    "event": None,
                    "old_event_summary": {
                        "event_id": 11,
                        "label": "Trip",
                        "start_time": "2025-01-01T01:00:00Z",
                        "end_time": "2025-01-03T03:00:00Z",
                        "photo_count": 9,
                        "face_count": 2,
                    },
                    "new_event_summary": None,
                },
            )(),
        ):
            response = self.client.post("/api/photos/test-sha/event/remove")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["success"], True)
        self.assertIsNone(response.json()["event"])
        self.assertEqual(response.json()["old_event"]["event_id"], 11)

    def test_remove_photo_event_missing_assignment_returns_422(self) -> None:
        with patch("app.api.photos.remove_asset_from_event", side_effect=ValueError("Photo is not assigned to an event.")):
            response = self.client.post("/api/photos/test-sha/event/remove")

        self.assertEqual(response.status_code, 422)

    def test_assign_photo_event_returns_old_and_new_event_summaries(self) -> None:
        with patch(
            "app.api.photos.assign_asset_to_event",
            return_value=type(
                "MutationResult",
                (),
                {
                    "asset_sha256": "test-sha",
                    "event": {
                        "event_id": 17,
                        "label": "Picnic",
                        "start_at": "2026-01-20T15:22:19Z",
                        "end_at": "2026-01-20T15:22:19Z",
                    },
                    "old_event_summary": {
                        "event_id": 5,
                        "label": "Old",
                        "start_time": "2024-06-01T00:00:00Z",
                        "end_time": "2024-06-02T00:00:00Z",
                        "photo_count": 1,
                        "face_count": 0,
                    },
                    "new_event_summary": {
                        "event_id": 17,
                        "label": "Picnic",
                        "start_time": "2026-01-20T00:00:00Z",
                        "end_time": "2026-01-20T23:59:59Z",
                        "photo_count": 7,
                        "face_count": 3,
                    },
                },
            )(),
        ) as mocked_service:
            response = self.client.post("/api/photos/test-sha/event/assign", json={"event_id": 17})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["event"]["event_id"], 17)
        self.assertEqual(body["old_event"]["event_id"], 5)
        self.assertEqual(body["new_event"]["event_id"], 17)

        mocked_service.assert_called_once()
        _, kwargs = mocked_service.call_args
        self.assertEqual(kwargs["asset_sha256"], "test-sha")
        self.assertEqual(kwargs["target_event_id"], 17)

    def test_assign_photo_event_same_event_returns_422(self) -> None:
        with patch("app.api.photos.assign_asset_to_event", side_effect=ValueError("Photo is already assigned to that event.")):
            response = self.client.post("/api/photos/test-sha/event/assign", json={"event_id": 7})

        self.assertEqual(response.status_code, 422)

    def test_assign_photo_event_missing_target_returns_404(self) -> None:
        with patch("app.api.photos.assign_asset_to_event", side_effect=LookupError("Event 999 not found.")):
            response = self.client.post("/api/photos/test-sha/event/assign", json={"event_id": 999})

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
