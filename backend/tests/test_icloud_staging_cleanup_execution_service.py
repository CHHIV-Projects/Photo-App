from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.asset import Asset
from app.models.icloud_staging_cleanup_run import IcloudStagingCleanupRun
from app.models.ingestion_source import IngestionSource
from app.models.provenance import Provenance
from app.models.source_intake_run import SourceIntakeRun
from app.services.admin import icloud_staging_cleanup_execution_service as cleanup


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class IcloudStagingCleanupExecutionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        for table in (
            IngestionSource.__table__,
            Asset.__table__,
            Provenance.__table__,
            SourceIntakeRun.__table__,
            IcloudStagingCleanupRun.__table__,
        ):
            table.create(self.engine)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.db: Session = self.session_factory()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name).resolve()
        self.exports_root = self.root / "storage" / "exports" / "icloud"
        self.staging_root = self.exports_root / "icloud_test"
        self.vault_root = self.root / "storage" / "vault"
        self.reports_root = self.root / "storage" / "logs" / "icloud_cleanup_reports"
        self.staging_root.mkdir(parents=True)
        self.vault_root.mkdir(parents=True)
        self.reports_root.mkdir(parents=True)

        self.source = IngestionSource(
            source_label="iCloud Test",
            source_label_normalized="icloud_test",
            source_type="cloud_export",
            source_root_path=str(self.staging_root),
            source_root_path_normalized=str(self.staging_root).lower(),
            profile_status="active",
            cloud_provider="icloud",
            acquisition_method="icloudpd",
            managed_staging_path=str(self.staging_root),
            account_username="test@example.com",
        )
        self.db.add(self.source)
        self.db.commit()
        self.db.refresh(self.source)

        self.patches = [
            patch.object(cleanup, "_resolve_exports_root", return_value=self.exports_root),
            patch.object(cleanup, "_resolve_vault_root", return_value=self.vault_root),
            patch.object(cleanup, "resolve_icloud_staging_path", return_value=self.staging_root),
            patch.object(cleanup, "_collect_report_evidence", return_value=(set(), set())),
            patch.object(cleanup, "SessionLocal", self.session_factory),
            patch.object(
                cleanup,
                "_report_paths",
                side_effect=lambda run_id: (
                    self.reports_root / f"run_{run_id}.json",
                    self.reports_root / f"run_{run_id}.events.jsonl",
                ),
            ),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self) -> None:
        for item in reversed(self.patches):
            item.stop()
        self.db.close()
        self.engine.dispose()
        self.temp_dir.cleanup()

    def _add_verified_file(self, relative_path: str = "2026/06/IMG_0001.HEIC", content: bytes = b"verified-photo") -> tuple[Path, Path, str]:
        sha256 = _digest(content)
        staged_path = self.staging_root / relative_path
        staged_path.parent.mkdir(parents=True, exist_ok=True)
        staged_path.write_bytes(content)
        vault_path = self.vault_root / sha256[:2] / f"{sha256}.heic"
        vault_path.parent.mkdir(parents=True, exist_ok=True)
        vault_path.write_bytes(content)
        self.db.add(
            Asset(
                sha256=sha256,
                vault_path=str(vault_path),
                original_filename=staged_path.name,
                original_source_path=str(staged_path),
                extension=".heic",
                size_bytes=len(content),
                modified_timestamp_utc=datetime.now(UTC),
            )
        )
        self.db.add(
            Provenance(
                asset_sha256=sha256,
                source_path=str(staged_path),
                ingestion_source_id=self.source.id,
                ingestion_run_id=None,
                source_label=self.source.source_label,
                source_type=self.source.source_type,
                source_root_path=str(self.staging_root),
                source_relative_path=relative_path.replace("/", "\\"),
            )
        )
        self.db.commit()
        return staged_path, vault_path, sha256

    def _validated_source(self) -> cleanup.ValidatedCleanupSource:
        return cleanup._validate_cleanup_source(self.db, source_id=self.source.id)

    def _add_run(self, *, dry_run: bool, status: str = "completed", fingerprint: str | None = None) -> IcloudStagingCleanupRun:
        now = datetime.now(UTC)
        row = IcloudStagingCleanupRun(
            status=status,
            ingestion_source_id=self.source.id,
            source_label=self.source.source_label,
            source_root_path=str(self.staging_root),
            dry_run=dry_run,
            started_at=now,
            finished_at=now if status == "completed" else None,
            eligible_count=1,
            deleted_count=0,
            skipped_count=0,
            total_bytes_eligible=14,
            total_bytes_deleted=0,
            total_files=1,
            processed_files=1,
            current_stage="completed" if status == "completed" else "pending",
            protected_count=0,
            verification_failed_count=0,
            file_missing_count=0,
            delete_failed_count=0,
            manifest_fingerprint=fingerprint,
            planner_version=cleanup.PLANNER_VERSION,
            preview_expires_at=now + timedelta(minutes=10),
            skipped_reasons_json="{}",
            skipped_samples_json="{}",
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def test_plan_requires_matching_hashes_and_is_deterministic(self) -> None:
        self._add_verified_file()
        source = self._validated_source()

        first = cleanup._build_cleanup_plan(self.db, source=source)
        second = cleanup._build_cleanup_plan(self.db, source=source)

        self.assertEqual(len(first.eligible), 1)
        self.assertEqual(first.issues, [])
        self.assertEqual(first.manifest_fingerprint, second.manifest_fingerprint)
        self.assertEqual(first.eligible[0].staged_sha256, first.eligible[0].vault_sha256)

    def test_staged_replacement_is_verification_failure(self) -> None:
        staged_path, _, _ = self._add_verified_file()
        staged_path.write_bytes(b"replacement")

        plan = cleanup._build_cleanup_plan(self.db, source=self._validated_source())

        self.assertEqual(plan.eligible, [])
        self.assertIn("staged_hash_mismatch", [item.reason for item in plan.issues])

    def test_cleanup_readiness_rejects_non_icloud_and_path_mismatch(self) -> None:
        self.source.cloud_provider = "google"
        self.db.commit()
        readiness = cleanup.get_cleanup_source_readiness(self.db, source_id=self.source.id)
        self.assertFalse(readiness.ready)
        self.assertEqual(readiness.blocking_reasons[0][0], "NOT_ICLOUD_PROFILE")

        self.source.cloud_provider = "icloud"
        self.source.managed_staging_path = str(self.exports_root / "different")
        (self.exports_root / "different").mkdir()
        self.db.commit()
        readiness = cleanup.get_cleanup_source_readiness(self.db, source_id=self.source.id)
        self.assertFalse(readiness.ready)
        self.assertEqual(readiness.blocking_reasons[0][0], "STAGING_PATH_MISMATCH")

    def test_vault_outside_configured_root_is_verification_failure(self) -> None:
        _, vault_path, sha256 = self._add_verified_file()
        outside = self.root / "outside" / vault_path.name
        outside.parent.mkdir()
        outside.write_bytes(vault_path.read_bytes())
        self.db.get(Asset, sha256).vault_path = str(outside)
        self.db.commit()

        plan = cleanup._build_cleanup_plan(self.db, source=self._validated_source())

        self.assertEqual(plan.eligible, [])
        self.assertIn("vault_path_unsafe_or_missing", [item.reason for item in plan.issues])

    def test_direct_live_run_is_rejected(self) -> None:
        with self.assertRaises(cleanup.CleanupAuthorizationError) as raised:
            cleanup.start_cleanup_run(self.db, source_id=self.source.id, dry_run=False)
        self.assertEqual(raised.exception.code, "GUARDED_EXECUTION_REQUIRED")

    def test_dry_run_persists_fingerprint_and_never_deletes(self) -> None:
        staged_path, vault_path, _ = self._add_verified_file()
        dry_run = self._add_run(dry_run=True, status="pending")

        cleanup._run_cleanup_background(run_id=dry_run.id, source_id=self.source.id, dry_run_run_id=None)
        self.db.expire_all()
        result = self.db.get(IcloudStagingCleanupRun, dry_run.id)

        self.assertEqual(result.status, "completed")
        self.assertEqual(len(result.manifest_fingerprint), 64)
        self.assertEqual(result.planner_version, cleanup.PLANNER_VERSION)
        self.assertIsNotNone(result.preview_expires_at)
        self.assertEqual(result.deleted_count, 0)
        self.assertTrue(staged_path.exists())
        self.assertTrue(vault_path.exists())

    def test_execution_consumes_fresh_authorization_once(self) -> None:
        dry_run = self._add_run(dry_run=True, fingerprint="a" * 64)
        with patch.object(cleanup.threading, "Thread") as thread:
            result = cleanup.start_cleanup_execution(
                self.db,
                source_id=self.source.id,
                dry_run_run_id=dry_run.id,
                explicit_confirmation=cleanup.EXECUTION_CONFIRMATION_PHRASE,
            )
        self.assertFalse(result.dry_run)
        self.assertEqual(result.authorized_dry_run_id, dry_run.id)
        self.assertIsNotNone(self.db.get(IcloudStagingCleanupRun, dry_run.id).authorization_consumed_at)
        thread.return_value.start.assert_called_once()

        execution_row = self.db.get(IcloudStagingCleanupRun, result.run_id)
        execution_row.status = "completed"
        self.db.commit()

        with self.assertRaises(cleanup.CleanupAuthorizationError) as raised:
            cleanup.start_cleanup_execution(
                self.db,
                source_id=self.source.id,
                dry_run_run_id=dry_run.id,
                explicit_confirmation=cleanup.EXECUTION_CONFIRMATION_PHRASE,
            )
        self.assertEqual(raised.exception.code, "DRY_RUN_ALREADY_CONSUMED")

    def test_execution_rejects_stale_preview_and_wrong_phrase(self) -> None:
        dry_run = self._add_run(dry_run=True, fingerprint="b" * 64)
        dry_run.preview_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        self.db.commit()
        with self.assertRaises(cleanup.CleanupAuthorizationError) as stale:
            cleanup.start_cleanup_execution(
                self.db,
                source_id=self.source.id,
                dry_run_run_id=dry_run.id,
                explicit_confirmation=cleanup.EXECUTION_CONFIRMATION_PHRASE,
            )
        self.assertEqual(stale.exception.code, "DRY_RUN_EXPIRED")

        with self.assertRaises(cleanup.CleanupAuthorizationError) as confirmation:
            cleanup.start_cleanup_execution(
                self.db,
                source_id=self.source.id,
                dry_run_run_id=dry_run.id,
                explicit_confirmation="delete",
            )
        self.assertEqual(confirmation.exception.code, "CONFIRMATION_REQUIRED")

    def test_guarded_execution_deletes_only_disposable_staging_fixture(self) -> None:
        staged_path, vault_path, _ = self._add_verified_file()
        plan = cleanup._build_cleanup_plan(self.db, source=self._validated_source())
        dry_run = self._add_run(dry_run=True, fingerprint=plan.manifest_fingerprint)
        dry_run.authorization_consumed_at = datetime.now(UTC)
        execution = self._add_run(dry_run=False, status="pending")
        execution.authorized_dry_run_id = dry_run.id
        self.db.commit()

        cleanup._run_cleanup_background(run_id=execution.id, source_id=self.source.id, dry_run_run_id=dry_run.id)
        self.db.expire_all()
        result = self.db.get(IcloudStagingCleanupRun, execution.id)

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.deleted_count, 1)
        self.assertFalse(staged_path.exists())
        self.assertTrue(vault_path.exists())
        self.assertTrue(Path(result.report_path).exists())

    def test_manifest_mismatch_deletes_nothing(self) -> None:
        staged_path, _, _ = self._add_verified_file()
        original = cleanup._build_cleanup_plan(self.db, source=self._validated_source())
        dry_run = self._add_run(dry_run=True, fingerprint=original.manifest_fingerprint)
        dry_run.authorization_consumed_at = datetime.now(UTC)
        execution = self._add_run(dry_run=False, status="pending")
        execution.authorized_dry_run_id = dry_run.id
        self.db.commit()
        staged_path.write_bytes(b"changed-after-preview")

        cleanup._run_cleanup_background(run_id=execution.id, source_id=self.source.id, dry_run_run_id=dry_run.id)
        self.db.expire_all()
        result = self.db.get(IcloudStagingCleanupRun, execution.id)

        self.assertEqual(result.status, "failed")
        self.assertIn("Candidate manifest changed", result.error_message)
        self.assertTrue(staged_path.exists())
        self.assertEqual(result.deleted_count, 0)

    def test_delete_error_is_completed_with_errors(self) -> None:
        staged_path, vault_path, _ = self._add_verified_file()
        plan = cleanup._build_cleanup_plan(self.db, source=self._validated_source())
        dry_run = self._add_run(dry_run=True, fingerprint=plan.manifest_fingerprint)
        dry_run.authorization_consumed_at = datetime.now(UTC)
        execution = self._add_run(dry_run=False, status="pending")
        execution.authorized_dry_run_id = dry_run.id
        self.db.commit()

        original_unlink = Path.unlink

        def fail_staged_unlink(path: Path, *args, **kwargs):
            if path.resolve() == staged_path.resolve():
                raise PermissionError("locked")
            return original_unlink(path, *args, **kwargs)

        with patch.object(Path, "unlink", fail_staged_unlink):
            cleanup._run_cleanup_background(run_id=execution.id, source_id=self.source.id, dry_run_run_id=dry_run.id)
        self.db.expire_all()
        result = self.db.get(IcloudStagingCleanupRun, execution.id)

        self.assertEqual(result.status, "completed_with_errors")
        self.assertEqual(result.delete_failed_count, 1)
        self.assertTrue(staged_path.exists())
        self.assertTrue(vault_path.exists())


if __name__ == "__main__":
    unittest.main()
