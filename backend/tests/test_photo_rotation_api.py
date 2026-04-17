"""API tests for photo display rotation updates."""

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


class PhotoRotationApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(photos_router)
        self.app.dependency_overrides[get_db_session] = _override_db_session
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_update_rotation_valid_value_returns_updated_payload(self) -> None:
        with patch("app.api.photos.set_photo_display_rotation", return_value=90) as mocked_service:
            response = self.client.post(
                "/api/photos/test-sha/rotation",
                json={"rotation_degrees": 90},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "asset_sha256": "test-sha",
                "display_rotation_degrees": 90,
            },
        )

        mocked_service.assert_called_once()
        _, kwargs = mocked_service.call_args
        self.assertEqual(kwargs["asset_sha256"], "test-sha")
        self.assertEqual(kwargs["rotation_degrees"], 90)

    def test_update_rotation_invalid_value_returns_422(self) -> None:
        response = self.client.post(
            "/api/photos/test-sha/rotation",
            json={"rotation_degrees": 45},
        )

        self.assertEqual(response.status_code, 422)

    def test_update_rotation_missing_asset_returns_404(self) -> None:
        with patch("app.api.photos.set_photo_display_rotation", return_value=None):
            response = self.client.post(
                "/api/photos/missing-sha/rotation",
                json={"rotation_degrees": 270},
            )

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
