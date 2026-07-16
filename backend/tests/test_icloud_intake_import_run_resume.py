from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
import unittest
from unittest.mock import patch

from sqlalchemy import select

from app.models.icloud_backfill import IcloudRemoteAssetInventory
from app.models.icloud_acquisition_run import (
    IcloudAcquisitionBatch,
    IcloudAcquisitionItem,
    IcloudAcquisitionResource,
    IcloudAcquisitionRun,
)
from app.models.icloud_intake_import import IcloudIntakeImportChunk, IcloudIntakeImportRun
from app.models.icloud_intake_prepare import IcloudIntakePreparedCandidate
from app.models.source_intake_run import SourceIntakeRun
from app.services.icloud_backfill_acquisition_execution_service import IcloudBackfillAcquireResult
from app.services.icloud_historical_routine_service import (
    CHUNK_STATUS_COMPLETED,
    CHUNK_STATUS_STOPPED_NEEDS_REVIEW,
    IMPORT_STATUS_COMPLETED,
    IMPORT_STATUS_RESUME_AVAILABLE,
    IMPORT_STATUS_RUNNING,
    IMPORT_STATUS_STOPPED_NEEDS_REVIEW,
    _DurableCleanupError,
    _TimedCleanupResult,
    advance_icloud_intake_import,
    get_icloud_intake_import_status,
    recover_icloud_intake_import_cleanup,
    resume_icloud_intake_import,
    start_icloud_intake_import,
)
from backend.tests.test_icloud_historical_routine_service import (
    IcloudHistoricalRoutineFixture,
    _acquire_result,
    _cleanup,
)


def _successful_acquire(db_session, *, source_id: int, inventory_ids: tuple[int, ...], resources: int | None = None) -> IcloudBackfillAcquireResult:
    rows = db_session.scalars(
        select(IcloudRemoteAssetInventory).where(IcloudRemoteAssetInventory.id.in_(inventory_ids))
    ).all()
    for row in rows:
        row.backfill_completed = True
        row.backfill_completed_at = datetime.now(UTC)
        row.acquisition_state = "source_intake_completed"
        row.backfill_resolution_state = "newly_imported"
    db_session.commit()
    return _acquire_result(source_id=source_id, logical=len(inventory_ids), resources=resources)


def _timed_cleanup(deleted: int) -> _TimedCleanupResult:
    return _TimedCleanupResult(
        dry_run=_cleanup(11, deleted=deleted),
        execution=_cleanup(12, deleted=deleted),
        reason="cleanup candidates exactly matched acquired resources",
        dry_run_seconds=0.25,
        execute_seconds=0.5,
    )


class IcloudIntakeImportRunResumeTests(IcloudHistoricalRoutineFixture):
    def _prepared_rows(self, count: int):
        self._add_state()
        rows = [
            self._add_inventory(f"remote-prepared-{index}", observed_position=index)
            for index in range(1, count + 1)
        ]
        prepare = self._add_prepare_run(rows)
        return prepare, rows

    def test_start_creates_durable_import_run_and_chunks(self) -> None:
        prepare, _ = self._prepared_rows(3)

        status = start_icloud_intake_import(
            self.db,
            source_id=self.source.id,
            internal_batch_size=2,
        )

        self.assertIsNotNone(status.import_run_id)
        self.assertEqual(status.import_status, "created")
        self.assertEqual(status.logical_candidates_total, 3)
        self.assertEqual(status.total_chunks, 2)
        run = self.db.get(IcloudIntakeImportRun, status.import_run_id)
        self.assertEqual(run.prepare_run_id, prepare.id)
        chunks = self.db.scalars(
            select(IcloudIntakeImportChunk)
            .where(IcloudIntakeImportChunk.import_run_id == run.id)
            .order_by(IcloudIntakeImportChunk.chunk_index)
        ).all()
        self.assertEqual([(chunk.candidate_start_index, chunk.candidate_end_index) for chunk in chunks], [(1, 2), (3, 3)])

    def test_advance_persists_completed_chunk_before_next_chunk(self) -> None:
        _, rows = self._prepared_rows(3)
        observed_batches: list[tuple[int, ...]] = []
        start = start_icloud_intake_import(self.db, source_id=self.source.id, internal_batch_size=2)

        def _fake_acquire(db_session, *_args, **kwargs):
            inventory_ids = tuple(kwargs["inventory_ids"])
            observed_batches.append(inventory_ids)
            return _successful_acquire(db_session, source_id=self.source.id, inventory_ids=inventory_ids)

        with patch("app.services.icloud_historical_routine_service.run_icloud_backfill_acquisition", side_effect=_fake_acquire):
            with patch("app.services.icloud_historical_routine_service._cleanup_chunk_timed", side_effect=lambda *_args, **kwargs: _timed_cleanup(len(kwargs["acquired_paths"]))):
                after_first = advance_icloud_intake_import(self.db, source_id=self.source.id, import_run_id=start.import_run_id)

        self.assertEqual(after_first.import_status, IMPORT_STATUS_RUNNING)
        self.assertEqual(after_first.completed_chunk_count, 1)
        self.assertEqual(after_first.logical_imported, 2)
        self.assertEqual(observed_batches, [(rows[0].id, rows[1].id)])
        chunks = self.db.scalars(
            select(IcloudIntakeImportChunk)
            .where(IcloudIntakeImportChunk.import_run_id == start.import_run_id)
            .order_by(IcloudIntakeImportChunk.chunk_index)
        ).all()
        self.assertEqual(chunks[0].status, CHUNK_STATUS_COMPLETED)
        self.assertEqual(chunks[1].status, "pending")
        self.assertIsNotNone(chunks[0].completed_at)
        self.assertIsNotNone(chunks[0].chunk_total_seconds)
        self.assertEqual(chunks[0].cleanup_eligible_count, 2)

    def test_running_chunk_blocks_status_and_advance(self) -> None:
        self._prepared_rows(3)
        start = start_icloud_intake_import(self.db, source_id=self.source.id, internal_batch_size=2)
        run = self.db.get(IcloudIntakeImportRun, start.import_run_id)
        chunk = self.db.scalars(
            select(IcloudIntakeImportChunk)
            .where(IcloudIntakeImportChunk.import_run_id == run.id)
            .order_by(IcloudIntakeImportChunk.chunk_index)
        ).first()
        now = datetime.now(UTC)
        run.status = IMPORT_STATUS_RUNNING
        run.last_progress_at = now
        chunk.status = "running"
        chunk.started_at = now
        self.db.commit()

        status = get_icloud_intake_import_status(self.db, source_id=self.source.id)

        self.assertFalse(status.can_advance_import)
        self.assertEqual(status.current_phase, "chunk_1_running")

        with patch("app.services.icloud_historical_routine_service.run_icloud_backfill_acquisition") as acquire:
            advanced = advance_icloud_intake_import(self.db, source_id=self.source.id, import_run_id=start.import_run_id)

        acquire.assert_not_called()
        self.assertFalse(advanced.can_advance_import)
        self.assertEqual(advanced.current_phase, "chunk_1_running")

    def test_stale_running_run_becomes_resume_available_and_resumes_pending_only(self) -> None:
        _, rows = self._prepared_rows(3)
        observed_batches: list[tuple[int, ...]] = []
        start = start_icloud_intake_import(self.db, source_id=self.source.id, internal_batch_size=2)

        def _fake_acquire(db_session, *_args, **kwargs):
            inventory_ids = tuple(kwargs["inventory_ids"])
            observed_batches.append(inventory_ids)
            return _successful_acquire(db_session, source_id=self.source.id, inventory_ids=inventory_ids)

        with patch("app.services.icloud_historical_routine_service.run_icloud_backfill_acquisition", side_effect=_fake_acquire):
            with patch("app.services.icloud_historical_routine_service._cleanup_chunk_timed", side_effect=lambda *_args, **kwargs: _timed_cleanup(len(kwargs["acquired_paths"]))):
                advance_icloud_intake_import(self.db, source_id=self.source.id, import_run_id=start.import_run_id)

        run = self.db.get(IcloudIntakeImportRun, start.import_run_id)
        run.last_progress_at = datetime.now(UTC) - timedelta(minutes=5)
        self.db.commit()
        with patch("app.services.icloud_historical_routine_service.DEFAULT_IMPORT_STALE_SECONDS", 0):
            stale = get_icloud_intake_import_status(self.db, source_id=self.source.id)
        self.assertEqual(stale.import_status, IMPORT_STATUS_RESUME_AVAILABLE)
        self.assertTrue(stale.can_resume_import)

        resumed = resume_icloud_intake_import(self.db, source_id=self.source.id, import_run_id=start.import_run_id)
        self.assertEqual(resumed.import_status, IMPORT_STATUS_RUNNING)
        with patch("app.services.icloud_historical_routine_service.run_icloud_backfill_acquisition", side_effect=_fake_acquire):
            with patch("app.services.icloud_historical_routine_service._cleanup_chunk_timed", side_effect=lambda *_args, **kwargs: _timed_cleanup(len(kwargs["acquired_paths"]))):
                final = advance_icloud_intake_import(self.db, source_id=self.source.id, import_run_id=start.import_run_id)

        self.assertEqual(final.import_status, IMPORT_STATUS_COMPLETED)
        self.assertEqual(observed_batches, [(rows[0].id, rows[1].id), (rows[2].id,)])

    def test_source_intake_failure_records_chunk_and_run_review_state(self) -> None:
        self._prepared_rows(1)
        start = start_icloud_intake_import(self.db, source_id=self.source.id, internal_batch_size=1)

        def _fake_acquire(db_session, *_args, **kwargs):
            result = _successful_acquire(db_session, source_id=self.source.id, inventory_ids=tuple(kwargs["inventory_ids"]))
            return replace(
                result,
                source_intake_succeeded=False,
                stop_reason="source_intake_failed",
            )

        with patch("app.services.icloud_historical_routine_service.run_icloud_backfill_acquisition", side_effect=_fake_acquire):
            status = advance_icloud_intake_import(self.db, source_id=self.source.id, import_run_id=start.import_run_id)

        self.assertEqual(status.import_status, IMPORT_STATUS_STOPPED_NEEDS_REVIEW)
        self.assertEqual(status.source_intake_failed_count, 1)
        self.assertEqual(status.chunks[0].status, CHUNK_STATUS_STOPPED_NEEDS_REVIEW)
        self.assertEqual(status.chunks[0].source_intake_failed_count, 1)

    def test_cleanup_failure_records_safety_counters(self) -> None:
        self._prepared_rows(1)
        start = start_icloud_intake_import(self.db, source_id=self.source.id, internal_batch_size=1)
        dry_run = replace(_cleanup(11, deleted=1), skipped_count=1, eligible_count=1)

        def _fake_acquire(db_session, *_args, **kwargs):
            return _successful_acquire(db_session, source_id=self.source.id, inventory_ids=tuple(kwargs["inventory_ids"]))

        def _fake_cleanup(*_args, **_kwargs):
            raise _DurableCleanupError(
                "Cleanup dry run had non-zero safety counters.",
                code="cleanup_safety_counters",
                dry_run=dry_run,
                dry_run_seconds=0.1,
            )

        with patch("app.services.icloud_historical_routine_service.run_icloud_backfill_acquisition", side_effect=_fake_acquire):
            with patch("app.services.icloud_historical_routine_service._cleanup_chunk_timed", side_effect=_fake_cleanup):
                status = advance_icloud_intake_import(self.db, source_id=self.source.id, import_run_id=start.import_run_id)

        self.assertEqual(status.import_status, IMPORT_STATUS_STOPPED_NEEDS_REVIEW)
        self.assertEqual(status.cleanup_failed_count, 1)
        self.assertEqual(status.chunks[0].cleanup_dry_run_id, 11)
        self.assertEqual(status.chunks[0].cleanup_skipped_count, 1)
        self.assertEqual(status.chunks[0].cleanup_failed_count, 1)

    def test_recover_interrupted_cleanup_completes_running_chunk(self) -> None:
        self._prepared_rows(1)
        SourceIntakeRun.__table__.create(self.engine, checkfirst=True)
        start = start_icloud_intake_import(self.db, source_id=self.source.id, internal_batch_size=1)
        run = self.db.get(IcloudIntakeImportRun, start.import_run_id)
        chunk = self.db.scalars(
            select(IcloudIntakeImportChunk).where(IcloudIntakeImportChunk.import_run_id == run.id)
        ).one()
        now = datetime.now(UTC)
        acquisition_run = IcloudAcquisitionRun(
            status="completed",
            source_profile_id=self.source.id,
            source_label=self.source.source_label,
            source_type=self.source.source_type,
            source_root_path=self.source.source_root_path,
            acquisition_mode="backfill_execute",
            target_new_item_count=1,
        )
        self.db.add(acquisition_run)
        self.db.flush()
        batch = IcloudAcquisitionBatch(
            run_id=acquisition_run.id,
            batch_index=1,
            status="ready_for_cleanup_dry_run",
            target_new_item_count=1,
            selected_new_item_count=1,
            selected_new_resource_count=2,
            downloaded_item_count=1,
            downloaded_resource_count=2,
            batch_ready_for_source_intake=True,
            ready_for_cleanup_dry_run=True,
            cleanup_readiness_reason="source_intake_verified",
        )
        self.db.add(batch)
        self.db.flush()
        item = IcloudAcquisitionItem(
            batch_id=batch.id,
            item_index=1,
            remote_item_digest="digest",
            status="downloaded",
            expected_resource_count=2,
            selected_resource_count=2,
            published_resource_count=2,
        )
        self.db.add(item)
        self.db.flush()
        for index, relative_path in enumerate(("2026/06/24/item-0.HEIC", "2026/06/24/item-1.HEIC"), start=1):
            self.db.add(
                IcloudAcquisitionResource(
                    item_id=item.id,
                    resource_index=index,
                    resource_role="primary",
                    relative_path=relative_path,
                    status="resource_intake_processed",
                    selected_for_download=True,
                    asset_sha256=f"{index}" * 64,
                )
            )
        self.db.add(
            SourceIntakeRun(
                id=321,
                status="completed",
                ingestion_source_id=self.source.id,
                source_label=self.source.source_label,
                source_type=self.source.source_type,
                source_root_path=self.source.source_root_path,
                files_scanned=2,
                selected=2,
                staged=2,
                processed_new_unique=2,
            )
        )
        chunk.status = "running"
        chunk.started_at = now
        chunk.logical_imported = 1
        chunk.files_resources_imported = 2
        chunk.acquisition_run_id = acquisition_run.id
        chunk.acquisition_batch_id = batch.id
        chunk.source_intake_run_id = 321
        run.status = IMPORT_STATUS_RUNNING
        run.last_progress_at = now
        self.db.commit()

        with patch("app.services.icloud_historical_routine_service.reconcile_completed_cleanup_reports", return_value=1):
            with patch("app.services.icloud_historical_routine_service._cleanup_chunk_timed", return_value=_timed_cleanup(2)) as cleanup:
                result = recover_icloud_intake_import_cleanup(self.db, source_id=self.source.id, import_run_id=run.id)

        cleanup.assert_called_once()
        self.assertEqual(result.deleted_count, 2)
        self.assertEqual(result.reconciled_cleanup_report_count, 1)
        self.assertEqual(result.status.import_status, IMPORT_STATUS_COMPLETED)
        recovered_chunk = self.db.get(IcloudIntakeImportChunk, chunk.id)
        self.assertEqual(recovered_chunk.status, CHUNK_STATUS_COMPLETED)
        self.assertEqual(recovered_chunk.local_staging_files_cleaned, 2)
        self.assertEqual(recovered_chunk.cleanup_dry_run_id, 11)
        self.assertEqual(recovered_chunk.cleanup_execution_run_id, 12)


if __name__ == "__main__":
    unittest.main()
