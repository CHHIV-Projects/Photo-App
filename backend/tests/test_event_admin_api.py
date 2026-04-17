"""API tests for event admin workflows."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.events import router as events_router
from app.db.session import get_db_session


class _DummySession:
    pass


def _override_db_session():
    yield _DummySession()


class EventAdminApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(events_router)
        self.app.dependency_overrides[get_db_session] = _override_db_session
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_update_event_returns_updated_payload(self) -> None:
        with patch(
            "app.api.events.update_event_label",
            return_value={
                "event_id": 7,
                "label": "Family Picnic",
                "start_time": "2024-01-01T10:00:00Z",
                "end_time": "2024-01-01T12:00:00Z",
                "photo_count": 4,
            },
        ) as mocked_service:
            response = self.client.post("/api/events/7/update", json={"label": "Family Picnic"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["label"], "Family Picnic")
        mocked_service.assert_called_once()

    def test_update_event_missing_returns_404(self) -> None:
        with patch("app.api.events.update_event_label", return_value=None):
            response = self.client.post("/api/events/999/update", json={"label": "Missing"})

        self.assertEqual(response.status_code, 404)

    def test_merge_events_returns_summary_payload(self) -> None:
        with patch(
            "app.api.events.merge_events",
            return_value=type(
                "MergeResult",
                (),
                {
                    "target_event_id": 11,
                    "removed_event_id": 5,
                    "label": "Summer 1980",
                    "start_time": "1980-06-01T00:00:00Z",
                    "end_time": "1980-08-31T23:59:59Z",
                    "photo_count": 22,
                },
            )(),
        ) as mocked_service:
            response = self.client.post(
                "/api/events/merge",
                json={"source_event_id": 5, "target_event_id": 11},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "target_event_id": 11,
                "removed_event_id": 5,
                "label": "Summer 1980",
                "start_time": "1980-06-01T00:00:00Z",
                "end_time": "1980-08-31T23:59:59Z",
                "photo_count": 22,
            },
        )
        mocked_service.assert_called_once()

    def test_merge_same_event_returns_422(self) -> None:
        with patch("app.api.events.merge_events", side_effect=ValueError("Source and target events must be different.")):
            response = self.client.post(
                "/api/events/merge",
                json={"source_event_id": 5, "target_event_id": 5},
            )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()