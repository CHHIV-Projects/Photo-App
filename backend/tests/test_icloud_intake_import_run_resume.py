from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
import unittest
from unittest.mock import patch

from sqlalchemy import select

from app.models.icloud_backfill import IcloudRemoteAssetInventory
from app.models.icloud_intake_import import IcloudIntakeImportChunk, IcloudIntakeImportRun
from app.models.icloud_intake_prepare import IcloudIntakePreparedCandidate
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


if __name__ == "__main__":
    unittest.main()
