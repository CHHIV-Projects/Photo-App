from __future__ import annotations

from datetime import UTC, datetime, timedelta
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.icloud_backfill import IcloudBackfillState, IcloudRemoteAssetInventory
from app.models.icloud_intake_prepare import IcloudIntakePreparedCandidate, IcloudIntakePrepareRun
from app.models.icloud_staging_cleanup_run import IcloudStagingCleanupRun
from app.models.ingestion_source import IngestionSource
from app.services.admin.icloud_staging_cleanup_execution_service import CleanupRunSnapshot
from app.services.icloud_acquisition.schema import ensure_icloud_acquisition_schema
from app.services.icloud_backfill_acquisition_execution_service import IcloudBackfillAcquireResult
from app.services.icloud_backfill_inventory_service import (
    ELIGIBILITY_AMBIGUOUS_METADATA_ONLY,
    ELIGIBILITY_ELIGIBLE_METADATA_ONLY,
    KNOWN_STATE_PENDING_CHECK,
    REMOTE_IDENTITY_BASIS_HELPER_ITEM_ID,
    IcloudInventoryScanResult,
)
from app.services.icloud_backfill_schema import ensure_icloud_backfill_schema
from app.services.icloud_historical_routine_service import (
    AVAILABLE_NO,
    AVAILABLE_UNKNOWN,
    AVAILABLE_YES,
    CANDIDATE_STATE_EXECUTION_FAILED_RETRYABLE,
    CANDIDATE_STATE_IMPORTED,
    PREPARE_STATUS_CONSUMED,
    PREPARE_STATUS_PREPARED,
    RUN_COMPLETED_TARGET,
    RUN_FAILED,
    get_historical_routine_status,
    refresh_historical_inventory,
    run_next_historical_batch,
)
from app.services.icloud_intake_prepare_schema import ensure_icloud_intake_prepare_schema
from app.services.icloud_path_service import resolve_icloud_staging_path


class IcloudHistoricalRoutineFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
        IngestionSource.__table__.create(self.engine)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.db: Session = self.session_factory()
        ensure_icloud_backfill_schema(self.db)
        ensure_icloud_intake_prepare_schema(self.db)
        ensure_icloud_acquisition_schema(self.db)
        IcloudStagingCleanupRun.__table__.create(self.engine, checkfirst=True)
        self.source = self._add_source()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def _add_source(self) -> IngestionSource:
        staging_path = resolve_icloud_staging_path("Historical Routine")
        staging_path.mkdir(parents=True, exist_ok=True)
        source = IngestionSource(
            source_label="Historical Routine",
            source_label_normalized="historical routine",
            source_type="cloud_export",
            source_root_path=str(staging_path),
            source_root_path_normalized=str(staging_path).lower(),
            profile_status="active",
            cloud_provider="icloud",
            acquisition_method="icloudpd",
            managed_staging_path=str(staging_path),
            account_username="fixture@example.com",
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def _add_state(self, *, source_exhausted: bool = False) -> None:
        now = datetime.now(UTC)
        self.db.add(
            IcloudBackfillState(
                source_profile_id=self.source.id,
                status="inventory_scanned",
                last_inventory_scan_at=now,
                last_scan_candidate_count=10,
                last_scan_created_count=10,
                last_scan_updated_count=0,
                inventory_total_count=10,
                eligible_metadata_count=10,
                unsupported_or_ambiguous_count=0,
                source_exhausted=source_exhausted,
                scan_limit_reached=not source_exhausted,
                stop_reason="source_exhausted" if source_exhausted else "scan_limit_reached",
            )
        )
        self.db.commit()

    def _add_inventory(
        self,
        remote_identity: str,
        *,
        eligible: bool = True,
        completed: bool = False,
        observed_position: int = 1,
    ) -> IcloudRemoteAssetInventory:
        now = datetime.now(UTC)
        row = IcloudRemoteAssetInventory(
            source_profile_id=self.source.id,
            remote_identity=remote_identity,
            remote_identity_basis=REMOTE_IDENTITY_BASIS_HELPER_ITEM_ID,
            observed_remote_position=observed_position,
            observed_at=now,
            first_observed_at=now,
            last_observed_at=now,
            grouping="primary_asset_explicit",
            created_remote_at="2026-06-24T10:00:00+00:00",
            added_remote_at="2026-06-24T10:01:00+00:00",
            primary_relative_path=f"2026/06/24/{remote_identity}.HEIC",
            primary_content_type="image/heic",
            primary_expected_size_bytes=12345,
            resource_count=1,
            is_live_photo=False,
            identity_ambiguous=not eligible,
            unsupported_reasons_json="[]" if eligible else '["unsupported_adjusted_resource"]',
            eligibility_state=ELIGIBILITY_ELIGIBLE_METADATA_ONLY if eligible else ELIGIBILITY_AMBIGUOUS_METADATA_ONLY,
            known_state=KNOWN_STATE_PENDING_CHECK,
            backfill_completed=completed,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def _add_prepare_run(
        self,
        rows: list[IcloudRemoteAssetInventory],
        *,
        expires_at: datetime | None = None,
    ) -> IcloudIntakePrepareRun:
        now = datetime.now(UTC)
        run = IcloudIntakePrepareRun(
            source_profile_id=self.source.id,
            status="prepared",
            target_logical_candidates=1000,
            logical_candidates_ready=len(rows),
            new_deferred_count=0,
            provider_records_scanned=len(rows),
            scan_depth_used=len(rows),
            source_exhaustion_state="unknown",
            source_exhausted=False,
            scan_limit_reached=False,
            prepared_at=now,
            expires_at=expires_at or now + timedelta(minutes=60),
            operator_message=f"Prepared {len(rows)} logical candidates for import.",
            created_at=now,
            updated_at=now,
        )
        self.db.add(run)
        self.db.flush()
        for index, row in enumerate(rows, start=1):
            self.db.add(
                IcloudIntakePreparedCandidate(
                    prepare_run_id=run.id,
                    source_profile_id=self.source.id,
                    inventory_id=row.id,
                    remote_identity=row.remote_identity,
                    primary_relative_path=row.primary_relative_path,
                    candidate_index=index,
                    candidate_state="prepared",
                    resource_count=row.resource_count,
                    is_live_photo=row.is_live_photo,
                    created_at=now,
                    updated_at=now,
                )
            )
        self.db.commit()
        self.db.refresh(run)
        return run


def _scan_result(
    *,
    source_id: int,
    scanned_count: int,
    inventory_total: int,
    acquirable_pending: int,
    source_exhausted: bool,
    new_deferred: int = 0,
) -> IcloudInventoryScanResult:
    return IcloudInventoryScanResult(
        source_id=source_id,
        status="inventory_scanned",
        scanned_count=scanned_count,
        created_count=0,
        updated_count=scanned_count,
        inventory_total_count=inventory_total,
        eligible_metadata_count=acquirable_pending,
        unsupported_or_ambiguous_count=0,
        backfill_completed_count=0,
        unresolved_eligible_count=acquirable_pending,
        acquirable_pending_count=acquirable_pending,
        retryable_failed_count=0,
        ambiguous_or_unsupported_count=0,
        deferred_current_count=0,
        deferred_adjusted_resource_count=0,
        deferred_ambiguous_count=0,
        deferred_unsupported_count=0,
        deferred_new_since_last_scan_count=new_deferred,
        deferred_changed_since_last_scan_count=0,
        deferred_report_path=None,
        source_exhausted=source_exhausted,
        scan_limit_reached=not source_exhausted,
        stop_reason="source_exhausted" if source_exhausted else "scan_limit_reached",
        scanned_at=datetime.now(UTC),
    )


def _acquire_result(*, source_id: int, logical: int, resources: int | None = None) -> IcloudBackfillAcquireResult:
    resource_count = resources if resources is not None else logical
    return IcloudBackfillAcquireResult(
        source_id=source_id,
        status="acquisition_completed",
        dry_run=False,
        auto_run_source_intake=True,
        selected_inventory_count=logical,
        matched_listing_count=logical,
        selected_logical_count=logical,
        selected_resource_count=resource_count,
        downloaded_logical_count=logical,
        downloaded_resource_count=resource_count,
        source_intake_attempted=True,
        source_intake_succeeded=True,
        source_intake_run_id=100 + logical,
        acquisition_run_id=200 + logical,
        acquisition_batch_id=300 + logical,
        backfill_completed_count=logical,
        skipped_stale_count=0,
        skipped_known_count=0,
        skipped_unsupported_count=0,
        skipped_ambiguous_count=0,
        skipped_missing_identity_count=0,
        skipped_pending_classification_count=0,
        skipped_completed_count=0,
        failed_retryable_count=0,
        failed_terminal_count=0,
        stop_reason="source_intake_completed",
        next_safe_action="cleanup_review_required",
        acquired_resource_paths=tuple(f"2026/06/24/item-{index}.HEIC" for index in range(resource_count)),
    )


def _cleanup(run_id: int, *, deleted: int) -> CleanupRunSnapshot:
    return CleanupRunSnapshot(
        run_id=run_id,
        status="completed",
        source_id=1,
        source_label="Historical Routine",
        source_root_path="storage/exports/icloud/historical_routine",
        dry_run=run_id % 2 == 1,
        started_at=None,
        finished_at=None,
        elapsed_seconds=0.1,
        eligible_count=deleted,
        deleted_count=0 if run_id % 2 == 1 else deleted,
        skipped_count=0,
        total_bytes_eligible=deleted,
        total_bytes_deleted=deleted,
        total_files=deleted,
        processed_files=deleted,
        current_stage="completed",
        protected_count=0,
        verification_failed_count=0,
        file_missing_count=0,
        delete_failed_count=0,
        manifest_fingerprint="fixture",
        planner_version="test",
        preview_expires_at=None,
        authorized_dry_run_id=run_id if run_id % 2 == 1 else run_id - 1,
        authorization_consumed_at=None,
        skipped_reasons={},
        skipped_samples={},
        report_path=None,
        error_message=None,
    )


class IcloudHistoricalRoutineServiceTests(IcloudHistoricalRoutineFixture):
    def test_prepare_expands_scan_and_creates_durable_candidate_snapshot(self) -> None:
        depths: list[int] = []

        def _fake_scan(_db, *, source_id: int, max_candidates: int):
            depths.append(max_candidates)
            if max_candidates == 1000:
                self._add_inventory("remote-1", observed_position=1)
                self._add_inventory("remote-2", observed_position=2)
                pending = 2
            else:
                self._add_inventory("remote-3", observed_position=3)
                pending = 3
            return _scan_result(
                source_id=source_id,
                scanned_count=max_candidates,
                inventory_total=pending,
                acquirable_pending=pending,
                source_exhausted=False,
                new_deferred=1 if max_candidates == 1000 else 0,
            )

        with patch("app.services.icloud_historical_routine_service.DEFAULT_TARGET_LOGICAL_ASSETS", 3), patch(
            "app.services.icloud_historical_routine_service.run_icloud_backfill_inventory_scan",
            side_effect=_fake_scan,
        ):
            result = refresh_historical_inventory(self.db, source_id=self.source.id, max_candidates=2000)

        self.assertEqual(depths, [1000, 2000])
        self.assertEqual(result.logical_candidates_ready, 3)
        self.assertEqual(result.available_inventory, AVAILABLE_YES)
        self.assertEqual(result.new_deferred_this_prepare, 1)
        run = self.db.scalar(select(IcloudIntakePrepareRun).where(IcloudIntakePrepareRun.id == result.prepare_run_id))
        self.assertIsNotNone(run)
        candidates = self.db.scalars(
            select(IcloudIntakePreparedCandidate)
            .where(IcloudIntakePreparedCandidate.prepare_run_id == result.prepare_run_id)
            .order_by(IcloudIntakePreparedCandidate.candidate_index)
        ).all()
        self.assertEqual([candidate.remote_identity for candidate in candidates], ["remote-1", "remote-2", "remote-3"])

    def test_prepare_reports_no_available_inventory_only_when_source_exhausted(self) -> None:
        with patch("app.services.icloud_historical_routine_service.DEFAULT_TARGET_LOGICAL_ASSETS", 3), patch(
            "app.services.icloud_historical_routine_service.run_icloud_backfill_inventory_scan",
            return_value=_scan_result(
                source_id=self.source.id,
                scanned_count=25,
                inventory_total=0,
                acquirable_pending=0,
                source_exhausted=True,
            ),
        ):
            result = refresh_historical_inventory(self.db, source_id=self.source.id, max_candidates=1000)

        self.assertEqual(result.logical_candidates_ready, 0)
        self.assertEqual(result.available_inventory, AVAILABLE_NO)

    def test_prepare_reports_unknown_when_scan_ceiling_reached_without_exhaustion(self) -> None:
        with patch("app.services.icloud_historical_routine_service.DEFAULT_TARGET_LOGICAL_ASSETS", 3), patch(
            "app.services.icloud_historical_routine_service.run_icloud_backfill_inventory_scan",
            return_value=_scan_result(
                source_id=self.source.id,
                scanned_count=1000,
                inventory_total=0,
                acquirable_pending=0,
                source_exhausted=False,
            ),
        ):
            result = refresh_historical_inventory(self.db, source_id=self.source.id, max_candidates=1000)

        self.assertEqual(result.logical_candidates_ready, 0)
        self.assertEqual(result.available_inventory, AVAILABLE_UNKNOWN)
        self.assertIn("deeper inventory may remain", result.operator_message)

    def test_prepare_skips_already_imported_inventory_rows(self) -> None:
        def _fake_scan(_db, *, source_id: int, max_candidates: int):
            self._add_inventory("remote-completed", completed=True, observed_position=1)
            self._add_inventory("remote-ready", observed_position=2)
            return _scan_result(
                source_id=source_id,
                scanned_count=max_candidates,
                inventory_total=2,
                acquirable_pending=1,
                source_exhausted=True,
            )

        with patch("app.services.icloud_historical_routine_service.DEFAULT_TARGET_LOGICAL_ASSETS", 2), patch(
            "app.services.icloud_historical_routine_service.run_icloud_backfill_inventory_scan",
            side_effect=_fake_scan,
        ):
            result = refresh_historical_inventory(self.db, source_id=self.source.id, max_candidates=1000)

        candidates = self.db.scalars(
            select(IcloudIntakePreparedCandidate)
            .where(IcloudIntakePreparedCandidate.prepare_run_id == result.prepare_run_id)
            .order_by(IcloudIntakePreparedCandidate.candidate_index)
        ).all()
        self.assertEqual(result.logical_candidates_ready, 1)
        self.assertEqual([candidate.remote_identity for candidate in candidates], ["remote-ready"])

    def test_status_uses_prepared_candidates_not_old_deferred_total_for_top_level_ready_count(self) -> None:
        self._add_state()
        self._add_inventory("remote-adjusted", eligible=False)
        row = self._add_inventory("remote-ready")
        self._add_prepare_run([row])

        status = get_historical_routine_status(self.db, source_id=self.source.id)

        self.assertEqual(status.logical_candidates_ready, 1)
        self.assertEqual(status.available_inventory, AVAILABLE_YES)
        self.assertEqual(status.new_deferred_this_prepare, 0)

    def test_import_executes_exact_prepared_set_not_recalculated_inventory(self) -> None:
        self._add_state()
        prepared_a = self._add_inventory("remote-prepared-a", observed_position=20)
        prepared_b = self._add_inventory("remote-prepared-b", observed_position=21)
        unprepared = self._add_inventory("remote-unprepared-earlier", observed_position=1)
        prepare_run = self._add_prepare_run([prepared_a, prepared_b])
        observed_inventory_id_batches: list[tuple[int, ...]] = []

        def _fake_acquire(db_session, *_args, **kwargs):
            inventory_ids = tuple(kwargs["inventory_ids"])
            observed_inventory_id_batches.append(inventory_ids)
            rows = db_session.scalars(
                select(IcloudRemoteAssetInventory).where(IcloudRemoteAssetInventory.id.in_(inventory_ids))
            ).all()
            for row in rows:
                row.backfill_completed = True
                row.backfill_completed_at = datetime.now(UTC)
                row.acquisition_state = "source_intake_completed"
                row.backfill_resolution_state = "newly_imported"
            db_session.commit()
            return _acquire_result(source_id=self.source.id, logical=len(inventory_ids))

        def _fake_cleanup(*_args, **kwargs):
            count = len(kwargs["acquired_paths"])
            return _cleanup(11, deleted=count), _cleanup(12, deleted=count), "ok"

        with patch("app.services.icloud_historical_routine_service.run_icloud_backfill_acquisition", side_effect=_fake_acquire):
            with patch("app.services.icloud_historical_routine_service._cleanup_chunk", side_effect=_fake_cleanup):
                result = run_next_historical_batch(self.db, source_id=self.source.id, internal_batch_size=100)

        self.assertEqual(result.status, RUN_COMPLETED_TARGET)
        self.assertEqual(result.prepare_run_id, prepare_run.id)
        self.assertEqual(result.logical_candidates, 2)
        self.assertEqual(result.logical_imported, 2)
        self.assertEqual(observed_inventory_id_batches, [(prepared_a.id, prepared_b.id)])
        self.db.refresh(unprepared)
        self.assertFalse(unprepared.backfill_completed)
        self.db.refresh(prepare_run)
        self.assertEqual(prepare_run.status, PREPARE_STATUS_CONSUMED)
        states = self.db.scalars(
            select(IcloudIntakePreparedCandidate.candidate_state)
            .where(IcloudIntakePreparedCandidate.prepare_run_id == prepare_run.id)
            .order_by(IcloudIntakePreparedCandidate.candidate_index)
        ).all()
        self.assertEqual(states, [CANDIDATE_STATE_IMPORTED, CANDIDATE_STATE_IMPORTED])

    def test_retryable_execution_failure_is_not_deferred_and_keeps_prepare_available(self) -> None:
        self._add_state()
        prepared_a = self._add_inventory("remote-prepared-a", observed_position=1)
        prepared_b = self._add_inventory("remote-prepared-b", observed_position=2)
        prepare_run = self._add_prepare_run([prepared_a, prepared_b])

        def _fake_acquire(db_session, *_args, **kwargs):
            inventory_ids = tuple(kwargs["inventory_ids"])
            rows = db_session.scalars(
                select(IcloudRemoteAssetInventory).where(IcloudRemoteAssetInventory.id.in_(inventory_ids))
            ).all()
            for row in rows:
                row.acquisition_state = "failed_retryable"
                row.backfill_resolution_state = "failed_retryable"
                row.last_error_code = "unsafe_manifest"
                row.last_error_message = "manifest rejected"
            db_session.commit()
            return IcloudBackfillAcquireResult(
                source_id=self.source.id,
                status="failed",
                dry_run=False,
                auto_run_source_intake=True,
                selected_inventory_count=len(inventory_ids),
                matched_listing_count=len(inventory_ids),
                selected_logical_count=len(inventory_ids),
                selected_resource_count=len(inventory_ids),
                downloaded_logical_count=0,
                downloaded_resource_count=0,
                source_intake_attempted=False,
                source_intake_succeeded=False,
                source_intake_run_id=None,
                acquisition_run_id=200,
                acquisition_batch_id=300,
                backfill_completed_count=0,
                skipped_stale_count=0,
                skipped_known_count=0,
                skipped_unsupported_count=0,
                skipped_ambiguous_count=0,
                skipped_missing_identity_count=0,
                skipped_pending_classification_count=0,
                skipped_completed_count=0,
                failed_retryable_count=len(inventory_ids),
                failed_terminal_count=0,
                stop_reason="unsafe_manifest",
                next_safe_action="retry_acquisition",
            )

        with patch("app.services.icloud_historical_routine_service.run_icloud_backfill_acquisition", side_effect=_fake_acquire):
            result = run_next_historical_batch(self.db, source_id=self.source.id, internal_batch_size=2)

        self.assertEqual(result.status, RUN_FAILED)
        self.assertEqual(result.stop_reason, "unsafe_manifest")
        self.assertEqual(result.new_deferred_this_run, 0)
        self.assertEqual(result.execution_failed_this_run, 2)
        self.db.refresh(prepare_run)
        self.assertEqual(prepare_run.status, PREPARE_STATUS_PREPARED)
        self.assertIsNone(prepare_run.consumed_at)
        states = self.db.scalars(
            select(IcloudIntakePreparedCandidate.candidate_state)
            .where(IcloudIntakePreparedCandidate.prepare_run_id == prepare_run.id)
            .order_by(IcloudIntakePreparedCandidate.candidate_index)
        ).all()
        self.assertEqual(states, [CANDIDATE_STATE_EXECUTION_FAILED_RETRYABLE, CANDIDATE_STATE_EXECUTION_FAILED_RETRYABLE])
        status = get_historical_routine_status(self.db, source_id=self.source.id)
        self.assertEqual(status.logical_candidates_ready, 2)
        self.assertEqual(status.available_inventory, AVAILABLE_YES)

    def test_expired_prepare_blocks_import_without_acquisition(self) -> None:
        self._add_state()
        row = self._add_inventory("remote-expired")
        self._add_prepare_run([row], expires_at=datetime.now(UTC) - timedelta(minutes=1))

        with patch("app.services.icloud_historical_routine_service.run_icloud_backfill_acquisition") as acquire:
            result = run_next_historical_batch(self.db, source_id=self.source.id)

        self.assertEqual(result.status, RUN_FAILED)
        self.assertEqual(result.stop_reason, "fresh_prepare_required")
        self.assertIn("Refresh / Prepare Next 1000", result.operator_message)
        acquire.assert_not_called()

    def test_stale_prepared_candidate_blocks_import_without_acquisition(self) -> None:
        self._add_state()
        row = self._add_inventory("remote-stale", completed=True)
        self._add_prepare_run([row])

        with patch("app.services.icloud_historical_routine_service.run_icloud_backfill_acquisition") as acquire:
            result = run_next_historical_batch(self.db, source_id=self.source.id)

        self.assertEqual(result.status, RUN_FAILED)
        self.assertEqual(result.stop_reason, "prepared_candidates_stale")
        self.assertIn("no longer eligible/acquirable", result.operator_message)
        acquire.assert_not_called()


if __name__ == "__main__":
    unittest.main()
