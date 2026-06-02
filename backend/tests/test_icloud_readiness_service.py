from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.admin import SourceProfileDetail
from app.schemas.admin import IcloudReadinessOperationConflicts, IcloudReadinessReason
from app.services.admin.ingestion_operation_guardrail_service import IngestionOperationGuardrailSnapshot
from app.services.admin.icloud_readiness_service import get_icloud_source_readiness

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_ICLOUD_PATH = str((_PROJECT_ROOT / "storage" / "exports" / "icloud" / "chuck_icloud").resolve())


def _detail(
    *,
    source_type: str = "cloud_export",
    cloud_provider: str | None = "icloud",
    profile_status: str = "active",
    source_root_path: str | None = _DEFAULT_ICLOUD_PATH,
    managed_staging_path: str | None = _DEFAULT_ICLOUD_PATH,
    expected_acquisition_path: str | None = _DEFAULT_ICLOUD_PATH,
) -> SourceProfileDetail:
    return SourceProfileDetail(
        source_id=7,
        source_label="Chuck iCloud",
        source_type=source_type,
        source_root_path=source_root_path,
        profile_status=profile_status,
        cloud_provider=cloud_provider,
        acquisition_method="icloudpd" if source_type == "cloud_export" else None,
        managed_staging_path=managed_staging_path,
        account_username_masked="c***@example.com",
        account_username=None,
        first_seen_at=datetime.now(timezone.utc),
        last_run_at=None,
        provenance_count=0,
        ingestion_runs_count=0,
        source_intake_runs_count=0,
        icloud_acquisition_runs_count=0,
        normalized_label="chuck icloud",
        effective_path=managed_staging_path,
        effective_path_kind="managed_staging_path",
        expected_acquisition_path=expected_acquisition_path,
        source_root_path_relative=None,
        managed_staging_path_relative=None,
        effective_path_relative=None,
        is_referenced=False,
        has_path_divergence=False,
        warnings=[],
    )


class IcloudReadinessServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = MagicMock()
        self.db.scalar.return_value = None

    def test_non_icloud_profile_returns_not_ready_not_icloud(self) -> None:
        detail = _detail(source_type="local_folder", cloud_provider=None)

        with patch("app.services.admin.icloud_readiness_service.get_source_profile_detail", return_value=detail):
            snapshot = get_icloud_source_readiness(self.db, source_id=7)

        self.assertFalse(snapshot.is_icloud_profile)
        self.assertEqual(snapshot.readiness_status, "not_ready")
        self.assertIn("NOT_ICLOUD_PROFILE", [reason.code for reason in snapshot.blocking_reasons])

    def test_path_mismatch_returns_not_ready(self) -> None:
        detail = _detail(managed_staging_path="C:/repo/storage/exports/icloud/chuck_icloud_legacy")

        with patch("app.services.admin.icloud_readiness_service.get_source_profile_detail", return_value=detail):
            snapshot = get_icloud_source_readiness(self.db, source_id=7)

        self.assertEqual(snapshot.readiness_status, "not_ready")
        self.assertIn("PATH_MISMATCH", [reason.code for reason in snapshot.blocking_reasons])

    def test_auth_required_blocks_readiness(self) -> None:
        detail = _detail()
        matching_run = SimpleNamespace(
            status="failed",
            started_at=None,
            completed_at=None,
            downloaded_count=0,
            skipped_existing_count=0,
            failed_count=1,
            error_code="AUTH_REQUIRED",
            report_path=None,
        )

        with patch("app.services.admin.icloud_readiness_service.get_source_profile_detail", return_value=detail), patch(
            "app.services.admin.icloud_readiness_service._resolve_latest_matching_acquisition",
            return_value=matching_run,
        ):
            snapshot = get_icloud_source_readiness(self.db, source_id=7)

        self.assertEqual(snapshot.auth_status, "action_required")
        self.assertEqual(snapshot.readiness_status, "not_ready")
        self.assertIn("AUTH_REQUIRED", [reason.code for reason in snapshot.blocking_reasons])

    def test_global_source_intake_conflict_blocks_readiness(self) -> None:
        detail = _detail()
        guardrail_snapshot = IngestionOperationGuardrailSnapshot(
            operation_conflicts=IcloudReadinessOperationConflicts(
                icloud_acquisition_active=False,
                source_intake_active=True,
                icloud_cleanup_active=False,
                source_intake_active_for_this_source=False,
                icloud_cleanup_active_for_this_source=None,
            ),
            active_operation="source_intake",
            active_source_id=999,
            blocking_reasons=[
                IcloudReadinessReason(
                    code="SOURCE_INTAKE_ACTIVE",
                    message="A Source Intake run is currently active.",
                )
            ],
        )

        with patch("app.services.admin.icloud_readiness_service.get_source_profile_detail", return_value=detail), patch(
            "app.services.admin.icloud_readiness_service.get_ingestion_operation_guardrail_snapshot",
            return_value=guardrail_snapshot,
        ):
            snapshot = get_icloud_source_readiness(self.db, source_id=7)

        self.assertEqual(snapshot.readiness_status, "not_ready")
        self.assertTrue(snapshot.operation_conflicts.source_intake_active)
        self.assertFalse(snapshot.operation_conflicts.source_intake_active_for_this_source)
        self.assertIn("SOURCE_INTAKE_ACTIVE", [reason.code for reason in snapshot.blocking_reasons])

    def test_no_recent_acquisition_warns_when_core_alignment_passes(self) -> None:
        detail = _detail()

        with patch("app.services.admin.icloud_readiness_service.get_source_profile_detail", return_value=detail):
            snapshot = get_icloud_source_readiness(self.db, source_id=7)

        warning_codes = {reason.code for reason in snapshot.warnings}
        self.assertEqual(snapshot.readiness_status, "warning")
        self.assertIn("AUTH_UNKNOWN", warning_codes)
        self.assertIn("NO_RECENT_ACQUISITION", warning_codes)


if __name__ == "__main__":
    unittest.main()