from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.admin import router as admin_router
from app.db.session import get_db_session
from app.schemas.admin import IcloudReadinessOperationConflicts, IcloudReadinessReason
from app.services.admin.ingestion_operation_guardrail_service import IngestionOperationGuardrailSnapshot
from app.services.admin.source_intake_execution_service import SourceIntakeStatusSnapshot


class _DummySession:
    pass


def _override_db_session():
    yield _DummySession()


class AdminIngestionGuardrailsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(admin_router)
        self.app.dependency_overrides[get_db_session] = _override_db_session
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @staticmethod
    def _guardrail_snapshot(
        *,
        acquisition_active: bool,
        intake_active: bool,
        cleanup_active: bool,
        intake_for_source: bool | None = None,
        cleanup_for_source: bool | None = None,
    ) -> IngestionOperationGuardrailSnapshot:
        reasons: list[IcloudReadinessReason] = []
        if acquisition_active:
            reasons.append(IcloudReadinessReason(code="ICLOUD_ACQUISITION_ACTIVE", message="Another iCloud acquisition run is currently active."))
        if intake_active:
            reasons.append(IcloudReadinessReason(code="SOURCE_INTAKE_ACTIVE", message="A Source Intake run is currently active."))
        if cleanup_active:
            reasons.append(IcloudReadinessReason(code="ICLOUD_CLEANUP_ACTIVE", message="An iCloud staging cleanup run is currently active."))

        active_operation = None
        if acquisition_active:
            active_operation = "icloud_acquisition"
        elif intake_active:
            active_operation = "source_intake"
        elif cleanup_active:
            active_operation = "icloud_cleanup"

        return IngestionOperationGuardrailSnapshot(
            operation_conflicts=IcloudReadinessOperationConflicts(
                icloud_acquisition_active=acquisition_active,
                source_intake_active=intake_active,
                icloud_cleanup_active=cleanup_active,
                source_intake_active_for_this_source=intake_for_source,
                icloud_cleanup_active_for_this_source=cleanup_for_source,
            ),
            active_operation=active_operation,
            active_source_id=None,
            blocking_reasons=reasons,
        )

    def test_icloud_acquisition_run_returns_409_guardrail_payload(self) -> None:
        from unittest.mock import patch

        guardrail_snapshot = self._guardrail_snapshot(
            acquisition_active=False,
            intake_active=True,
            cleanup_active=False,
        )

        with patch("app.api.admin.get_ingestion_operation_guardrail_snapshot", return_value=guardrail_snapshot), patch(
            "app.api.admin.start_icloud_acquisition_background"
        ) as mocked_start:
            response = self.client.post(
                "/api/admin/icloud-acquisition/run",
                json={"source_label": "chuck_icloud", "username": "chuck@example.com"},
            )

        self.assertEqual(response.status_code, 409)
        payload = response.json()
        self.assertEqual(payload["error_code"], "INGESTION_OPERATION_ACTIVE")
        self.assertEqual(payload["blocking_reasons"][0]["code"], "SOURCE_INTAKE_ACTIVE")
        self.assertTrue(payload["operation_conflicts"]["source_intake_active"])
        mocked_start.assert_not_called()

    def test_source_intake_run_preserves_current_field_on_guardrail_conflict(self) -> None:
        from unittest.mock import patch

        guardrail_snapshot = self._guardrail_snapshot(
            acquisition_active=True,
            intake_active=False,
            cleanup_active=False,
        )
        current_snapshot = SourceIntakeStatusSnapshot(
            run_id=None,
            status="idle",
            ingestion_run_id=None,
            source_label=None,
            source_type=None,
            source_root_path=None,
            source_intake_limit=None,
            ingest_batch_size=None,
            started_at=None,
            finished_at=None,
            elapsed_seconds=None,
            files_scanned=0,
            skipped_known=0,
            selected=0,
            staged=0,
            processed_new_unique=0,
            failed_or_rejected=0,
            remaining_unknown=0,
            report_path=None,
            error_message=None,
            stop_requested=False,
        )

        with patch("app.api.admin.get_ingestion_operation_guardrail_snapshot", return_value=guardrail_snapshot), patch(
            "app.api.admin.get_source_intake_status",
            return_value=current_snapshot,
        ), patch("app.api.admin.start_source_intake") as mocked_start:
            response = self.client.post(
                "/api/admin/source-intake/run",
                json={"ingestion_source_id": 7, "ingest_batch_size": 200},
            )

        self.assertEqual(response.status_code, 409)
        payload = response.json()
        self.assertEqual(payload["error_code"], "INGESTION_OPERATION_ACTIVE")
        self.assertIn("current", payload)
        self.assertEqual(payload["current"]["status"], "idle")
        mocked_start.assert_not_called()

    def test_cleanup_run_keeps_source_intake_active_error_for_same_source(self) -> None:
        from unittest.mock import patch

        guardrail_snapshot = self._guardrail_snapshot(
            acquisition_active=False,
            intake_active=True,
            cleanup_active=False,
            intake_for_source=True,
        )

        with patch("app.api.admin.get_ingestion_operation_guardrail_snapshot", return_value=guardrail_snapshot), patch(
            "app.api.admin.start_cleanup_run"
        ) as mocked_start:
            response = self.client.post(
                "/api/admin/icloud-staging-cleanup/run",
                json={"source_id": 12, "dry_run": True},
            )

        self.assertEqual(response.status_code, 409)
        payload = response.json()
        self.assertEqual(payload["error_code"], "SOURCE_INTAKE_ACTIVE")
        self.assertEqual(payload["blocking_reasons"][0]["code"], "SOURCE_INTAKE_ACTIVE")
        mocked_start.assert_not_called()

    def test_cleanup_run_uses_ingestion_active_for_cross_operation_conflict(self) -> None:
        from unittest.mock import patch

        guardrail_snapshot = self._guardrail_snapshot(
            acquisition_active=True,
            intake_active=False,
            cleanup_active=False,
            intake_for_source=False,
        )

        with patch("app.api.admin.get_ingestion_operation_guardrail_snapshot", return_value=guardrail_snapshot), patch(
            "app.api.admin.start_cleanup_run"
        ) as mocked_start:
            response = self.client.post(
                "/api/admin/icloud-staging-cleanup/run",
                json={"source_id": 12, "dry_run": True},
            )

        self.assertEqual(response.status_code, 409)
        payload = response.json()
        self.assertEqual(payload["error_code"], "INGESTION_OPERATION_ACTIVE")
        self.assertTrue(payload["operation_conflicts"]["icloud_acquisition_active"])
        mocked_start.assert_not_called()

    def test_cleanup_run_rejects_legacy_direct_execution(self) -> None:
        from unittest.mock import patch
        from app.services.admin.icloud_staging_cleanup_execution_service import CleanupAuthorizationError

        guardrail_snapshot = self._guardrail_snapshot(
            acquisition_active=False,
            intake_active=False,
            cleanup_active=False,
        )
        with patch("app.api.admin.get_ingestion_operation_guardrail_snapshot", return_value=guardrail_snapshot), patch(
            "app.api.admin.start_cleanup_run",
            side_effect=CleanupAuthorizationError(
                "Direct dry_run=false cleanup is disabled.",
                code="GUARDED_EXECUTION_REQUIRED",
            ),
        ):
            response = self.client.post(
                "/api/admin/icloud-staging-cleanup/run",
                json={"source_id": 12, "dry_run": False},
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "GUARDED_EXECUTION_REQUIRED")

    def test_cleanup_execute_requires_guarded_authorization(self) -> None:
        from unittest.mock import patch
        from app.services.admin.icloud_staging_cleanup_execution_service import CleanupAuthorizationError

        guardrail_snapshot = self._guardrail_snapshot(
            acquisition_active=False,
            intake_active=False,
            cleanup_active=False,
        )
        with patch("app.api.admin.get_ingestion_operation_guardrail_snapshot", return_value=guardrail_snapshot), patch(
            "app.api.admin.start_cleanup_execution",
            side_effect=CleanupAuthorizationError(
                "Explicit confirmation phrase does not match.",
                code="CONFIRMATION_REQUIRED",
            ),
        ):
            response = self.client.post(
                "/api/admin/icloud-staging-cleanup/execute",
                json={
                    "source_id": 12,
                    "dry_run_run_id": 45,
                    "explicit_confirmation": "delete",
                },
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "CONFIRMATION_REQUIRED")


if __name__ == "__main__":
    unittest.main()
