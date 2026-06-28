from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.admin import router as admin_router
from app.db.session import get_db_session
from app.schemas.admin import InternalIcloudRunStatus
from app.services.admin.internal_icloud_run_service import InternalIcloudRunStartResult


class _DummySession:
    pass


def _override_db_session():
    yield _DummySession()


def _status(*, run_id: int | None, status: str, stop_reason: str | None = None) -> InternalIcloudRunStatus:
    return InternalIcloudRunStatus(
        run_id=run_id,
        status=status,
        stop_reason=stop_reason,
        source_id=66,
        batch_size=5,
        total_limit=10,
        candidate_search_cap=50,
        requested_media_scope="ordinary_stills",
        effective_media_scope="ordinary_stills",
        auto_cleanup_if_safe=True,
        dry_run_performed=True,
        execution_performed=(status != "stopped"),
        cleanup_performed=False,
        cleanup_recovery_used=False,
        final_verification_passed=False,
    )


class AdminInternalIcloudRunApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(admin_router)
        self.app.dependency_overrides[get_db_session] = _override_db_session
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_start_internal_run_returns_200_for_accepted_request(self) -> None:
        result = InternalIcloudRunStartResult(
            accepted=True,
            message="Internal iCloud single-flow run started.",
            status=_status(run_id=123, status="running"),
        )
        with patch("app.api.admin.start_internal_single_flow_run", return_value=result) as mocked_start:
            response = self.client.post(
                "/api/admin/internal/icloud-runs",
                json={
                    "source_id": 66,
                    "batch_size": 5,
                    "total_limit": 10,
                    "candidate_search_cap": 50,
                    "media_scope": "ordinary_stills",
                    "auto_cleanup_if_safe": True,
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "started")
        self.assertEqual(payload["current"]["run_id"], 123)
        mocked_start.assert_called_once()

    def test_start_internal_run_returns_409_for_non_accepted_request(self) -> None:
        result = InternalIcloudRunStartResult(
            accepted=False,
            message="Requested media scope is not executable yet.",
            status=_status(
                run_id=None,
                status="stopped",
                stop_reason="MEDIA_SCOPE_NOT_SUPPORTED_FOR_EXECUTION",
            ),
        )
        with patch("app.api.admin.start_internal_single_flow_run", return_value=result):
            response = self.client.post(
                "/api/admin/internal/icloud-runs",
                json={
                    "source_id": 66,
                    "batch_size": 5,
                    "total_limit": 10,
                    "candidate_search_cap": 50,
                    "media_scope": "videos_only",
                    "auto_cleanup_if_safe": True,
                },
            )

        self.assertEqual(response.status_code, 409)
        payload = response.json()
        self.assertEqual(payload["status"], "stopped")
        self.assertEqual(payload["current"]["stop_reason"], "MEDIA_SCOPE_NOT_SUPPORTED_FOR_EXECUTION")

    def test_start_internal_run_request_validation_rejects_batch_size_zero(self) -> None:
        response = self.client.post(
            "/api/admin/internal/icloud-runs",
            json={
                "source_id": 66,
                "batch_size": 0,
                "total_limit": 10,
                "candidate_search_cap": 50,
                "media_scope": "ordinary_stills",
                "auto_cleanup_if_safe": True,
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_get_internal_run_status_returns_404_when_not_found(self) -> None:
        with patch("app.api.admin.get_internal_single_flow_run_status", return_value=None):
            response = self.client.get("/api/admin/internal/icloud-runs/777")

        self.assertEqual(response.status_code, 404)
        payload = response.json()
        self.assertEqual(payload["error_code"], "INTERNAL_ICLOUD_RUN_NOT_FOUND")

    def test_get_internal_run_status_returns_current_snapshot(self) -> None:
        with patch(
            "app.api.admin.get_internal_single_flow_run_status",
            return_value=_status(run_id=321, status="completed", stop_reason="total_limit_reached"),
        ):
            response = self.client.get("/api/admin/internal/icloud-runs/321")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["current"]["run_id"], 321)
        self.assertEqual(payload["current"]["status"], "completed")


if __name__ == "__main__":
    unittest.main()
