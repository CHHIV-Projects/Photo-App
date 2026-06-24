from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.admin import router as admin_router
from app.db.session import get_db_session
from app.schemas.admin import IcloudAcquisitionRunStatus, IcloudReadinessOperationConflicts
from app.services.admin.ingestion_operation_guardrail_service import IngestionOperationGuardrailSnapshot
from app.services.icloud_acquisition.execution_service import (
    ACQUISITION_MODE_LIST_FIRST_NON_REPEAT,
    ACQUISITION_MODE_STANDARD,
    DEFAULT_RECENT_COUNT,
    IcloudAcquisitionAlreadyRunningError,
    IcloudAcquisitionSourceNotRegisteredError,
    IcloudAcquisitionRunResult,
    IcloudAcquisitionStatusSnapshot,
    build_icloudpd_preflight_command,
    IcloudAcquisitionStatusView,
    MAX_RECENT_COUNT,
    build_icloudpd_command,
    normalize_acquisition_mode,
    normalize_recent_count,
    resolve_staging_root,
    sanitize_source_label,
    validate_staging_root,
)


class _DummySession:
    pass


def _override_db_session():
    yield _DummySession()


class IcloudAcquisitionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._guardrail_patcher = patch(
            "app.api.admin.get_ingestion_operation_guardrail_snapshot",
            return_value=IngestionOperationGuardrailSnapshot(
                operation_conflicts=IcloudReadinessOperationConflicts(),
                active_operation=None,
                active_source_id=None,
                blocking_reasons=[],
            ),
        )
        self._guardrail_patcher.start()

        self.app = FastAPI()
        self.app.include_router(admin_router)
        self.app.dependency_overrides[get_db_session] = _override_db_session
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()
        self._guardrail_patcher.stop()

    def test_sanitize_source_label_normalizes_text(self) -> None:
        self.assertEqual(sanitize_source_label("Chuck iCloudPD"), "chuck_icloudpd")
        self.assertEqual(sanitize_source_label("  "), "unnamed_source")

    def test_sanitize_and_normalize_diverge_for_punctuated_labels(self) -> None:
        # Regression: labels with dots/spaces produce different results from
        # sanitize_source_label (used for path naming) vs normalize_source_label
        # (used for DB label matching).  _lookup_source_registration must receive
        # the original label so normalize_source_label matches the stored value.
        from app.services.ingestion.ingestion_context_service import normalize_source_label

        original = "Chuck iCloud E2E Test 12.62.10"
        sanitized = sanitize_source_label(original)   # path-safe folder name
        normalized = normalize_source_label(original)  # stored in DB

        # Sanitized → underscores replace spaces and dots → "chuck_icloud_e2e_test_12_62_10"
        self.assertEqual(sanitized, "chuck_icloud_e2e_test_12_62_10")
        # Normalized → lowercase only → "chuck icloud e2e test 12.62.10"
        self.assertEqual(normalized, "chuck icloud e2e test 12.62.10")
        # They must differ — this is the root cause of the mismatch
        self.assertNotEqual(sanitized, normalized)

        # Verify simpler label (no punctuation) also behaves consistently
        simple = "Chuck iCloud"
        self.assertEqual(sanitize_source_label(simple), "chuck_icloud")
        self.assertEqual(normalize_source_label(simple), "chuck icloud")
        self.assertNotEqual(sanitize_source_label(simple), normalize_source_label(simple))

    def test_recent_count_validation_applies_default_and_bounds(self) -> None:
        self.assertEqual(normalize_recent_count(None), DEFAULT_RECENT_COUNT)
        self.assertEqual(normalize_recent_count(MAX_RECENT_COUNT), MAX_RECENT_COUNT)
        with self.assertRaises(ValueError):
            normalize_recent_count(0)
        with self.assertRaises(ValueError):
            normalize_recent_count(MAX_RECENT_COUNT + 1)

    def test_staging_path_is_kept_under_exports_root(self) -> None:
        staging_root = resolve_staging_root("Chuck iCloudPD")
        self.assertIn("icloud", str(staging_root).lower())
        self.assertEqual(validate_staging_root(staging_root), staging_root)
        with self.assertRaises(ValueError):
            validate_staging_root(Path("C:/Windows").resolve())

    def test_build_command_contains_expected_arguments(self) -> None:
        command = build_icloudpd_command(
            executable=Path("C:/tools/icloudpd.exe"),
            username="chuck@example.com",
            staging_root=Path("C:/repo/storage/exports/icloud/chuck_icloudpd_test"),
            recent_count=25,
        )
        self.assertEqual(command[0], str(Path("C:/tools/icloudpd.exe")))
        self.assertIn("--username", command)
        self.assertIn("--directory", command)
        self.assertIn("--recent", command)
        self.assertIn("25", command)

    def test_build_preflight_command_contains_safe_flags(self) -> None:
        command = build_icloudpd_preflight_command(
            executable=Path("C:/tools/icloudpd.exe"),
            username="chuck@example.com",
            staging_root=Path("C:/repo/storage/exports/icloud/chuck_icloudpd_test"),
            recent_count=25,
        )
        self.assertIn("--only-print-filenames", command)
        self.assertIn("--dry-run", command)
        self.assertNotIn("--until-found", command)

    def test_acquisition_mode_normalization(self) -> None:
        self.assertEqual(normalize_acquisition_mode(None), ACQUISITION_MODE_STANDARD)
        self.assertEqual(
            normalize_acquisition_mode("list_first_non_repeat"),
            ACQUISITION_MODE_LIST_FIRST_NON_REPEAT,
        )
        with self.assertRaises(ValueError):
            normalize_acquisition_mode("experimental_mode")

    def test_run_endpoint_uses_default_recent_count(self) -> None:
        snapshot = IcloudAcquisitionStatusSnapshot(
            run_id=12,
            status="running",
            source_label="chuck_icloudpd_test",
            source_type="cloud_export",
            source_root_path="C:/repo/storage/exports/icloud/chuck_icloudpd_test",
            source_registration_status="registered",
            username="chuck@example.com",
            staging_path="C:/repo/storage/exports/icloud/chuck_icloudpd_test",
            recent_count=25,
            resolved_executable="C:/tools/icloudpd.exe",
            icloudpd_version="1.32.2",
            started_at=None,
            completed_at=None,
            elapsed_seconds=None,
            downloaded_count=0,
            skipped_existing_count=0,
            failed_count=0,
            stdout_tail=None,
            stderr_tail=None,
            report_path=None,
            error_code=None,
            error_message=None,
            stop_requested=False,
        )
        result = IcloudAcquisitionRunResult(status=snapshot, message="icloudpd acquisition started.")

        with patch("app.api.admin.start_icloud_acquisition_background", return_value=result) as mocked_start:
            response = self.client.post(
                "/api/admin/icloud-acquisition/run",
                json={"source_label": "chuck_icloudpd_test", "username": "chuck@example.com"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["current"]["recent_count"], 25)
        mocked_start.assert_called_once()
        _, kwargs = mocked_start.call_args
        self.assertEqual(kwargs["recent_count"], 25)
        self.assertEqual(kwargs["acquisition_mode"], ACQUISITION_MODE_STANDARD)

    def test_run_endpoint_passes_non_repeat_mode(self) -> None:
        snapshot = IcloudAcquisitionStatusSnapshot(
            run_id=15,
            status="running",
            source_label="chuck_icloudpd_test",
            source_type="cloud_export",
            source_root_path="C:/repo/storage/exports/icloud/chuck_icloudpd_test",
            source_registration_status="registered",
            username="chuck@example.com",
            staging_path="C:/repo/storage/exports/icloud/chuck_icloudpd_test",
            recent_count=20,
            resolved_executable="C:/tools/icloudpd.exe",
            icloudpd_version="1.32.2",
            started_at=None,
            completed_at=None,
            elapsed_seconds=None,
            downloaded_count=0,
            skipped_existing_count=0,
            failed_count=0,
            stdout_tail=None,
            stderr_tail=None,
            report_path=None,
            error_code=None,
            error_message=None,
            stop_requested=False,
            acquisition_mode=ACQUISITION_MODE_LIST_FIRST_NON_REPEAT,
        )
        result = IcloudAcquisitionRunResult(status=snapshot, message="icloudpd acquisition started.")

        with patch("app.api.admin.start_icloud_acquisition_background", return_value=result) as mocked_start:
            response = self.client.post(
                "/api/admin/icloud-acquisition/run",
                json={
                    "source_label": "chuck_icloudpd_test",
                    "username": "chuck@example.com",
                    "recent_count": 20,
                    "acquisition_mode": "list_first_non_repeat",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["current"]["acquisition_mode"], "list_first_non_repeat")
        _, kwargs = mocked_start.call_args
        self.assertEqual(kwargs["recent_count"], 20)
        self.assertEqual(kwargs["acquisition_mode"], ACQUISITION_MODE_LIST_FIRST_NON_REPEAT)

    def test_run_endpoint_returns_source_not_registered_error(self) -> None:
        snapshot = IcloudAcquisitionStatusSnapshot(
            run_id=13,
            status="failed",
            source_label="chuck_icloudpd_test",
            source_type="cloud_export",
            source_root_path="C:/repo/storage/exports/icloud/chuck_icloudpd_test",
            source_registration_status="missing",
            username="chuck@example.com",
            staging_path="C:/repo/storage/exports/icloud/chuck_icloudpd_test",
            recent_count=25,
            resolved_executable=None,
            icloudpd_version=None,
            started_at=None,
            completed_at=None,
            elapsed_seconds=0.0,
            downloaded_count=0,
            skipped_existing_count=0,
            failed_count=0,
            stdout_tail=None,
            stderr_tail=None,
            report_path=None,
            error_code="SOURCE_NOT_REGISTERED",
            error_message="No matching source registration exists for the requested iCloud acquisition path.",
            stop_requested=False,
        )

        with patch(
            "app.api.admin.start_icloud_acquisition_background",
            side_effect=IcloudAcquisitionSourceNotRegisteredError(
                snapshot,
                "No matching source registration exists for the requested iCloud acquisition path.",
                "SOURCE_NOT_REGISTERED",
            ),
        ):
            response = self.client.post(
                "/api/admin/icloud-acquisition/run",
                json={"source_label": "chuck_icloudpd_test", "username": "chuck@example.com"},
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "SOURCE_NOT_REGISTERED")

    def test_status_and_stop_endpoints_return_payloads(self) -> None:
        status_snapshot = IcloudAcquisitionStatusSnapshot(
            run_id=14,
            status="running",
            source_label="chuck_icloudpd_test",
            source_type="cloud_export",
            source_root_path="C:/repo/storage/exports/icloud/chuck_icloudpd_test",
            source_registration_status="registered",
            username="chuck@example.com",
            staging_path="C:/repo/storage/exports/icloud/chuck_icloudpd_test",
            recent_count=25,
            resolved_executable="C:/tools/icloudpd.exe",
            icloudpd_version="1.32.2",
            started_at=None,
            completed_at=None,
            elapsed_seconds=None,
            downloaded_count=0,
            skipped_existing_count=0,
            failed_count=0,
            stdout_tail=None,
            stderr_tail=None,
            report_path=None,
            error_code=None,
            error_message=None,
            stop_requested=False,
        )
        status_view = IcloudAcquisitionStatusView(generated_at=datetime.now(timezone.utc), current=status_snapshot)
        stop_result = IcloudAcquisitionRunResult(status=status_snapshot, message="Stop requested.")

        with patch("app.api.admin.get_icloud_acquisition_status", return_value=status_view):
            response = self.client.get("/api/admin/icloud-acquisition/status")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["current"]["run_id"], 14)

        with patch("app.api.admin.request_icloud_acquisition_stop", return_value=stop_result):
            response = self.client.post("/api/admin/icloud-acquisition/stop")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["current"]["run_id"], 14)


if __name__ == "__main__":
    unittest.main()
