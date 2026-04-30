"""Background duplicate lineage processing controls and execution."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.asset import Asset
from app.models.duplicate_processing_run import DuplicateProcessingRun
from app.services.duplicates.lineage import IMAGE_EXTENSIONS, update_asset_lineage
from app.services.duplicates.processing_schema import ensure_duplicate_processing_schema

STATUS_IDLE = "idle"
STATUS_RUNNING = "running"
STATUS_STOP_REQUESTED = "stop_requested"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_STOPPED = "stopped"

RUNNING_STATUSES = (STATUS_RUNNING, STATUS_STOP_REQUESTED)

_runner_lock = threading.Lock()
_runner_thread: threading.Thread | None = None


@dataclass(frozen=True)
class DuplicateProcessingStatusSnapshot:
    run_id: int | None
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    elapsed_seconds: float | None
    total_items: int
    processed_items: int
    current_stage: str | None
    error_message: str | None
    stop_requested: bool
    workset_cutoff: datetime | None
    last_successful_cutoff: datetime | None


@dataclass(frozen=True)
class DuplicateProcessingStatusView:
    generated_at: datetime
    pending_items: int
    current: DuplicateProcessingStatusSnapshot


@dataclass(frozen=True)
class DuplicateProcessingRunResult:
    status: DuplicateProcessingStatusSnapshot
    message: str


class DuplicateProcessingAlreadyRunningError(RuntimeError):
    """Raised when starting while another duplicate job is active."""

    def __init__(self, status: DuplicateProcessingStatusSnapshot) -> None:
        super().__init__("A duplicate-processing run is already active.")
        self.status = status


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_snapshot(run: DuplicateProcessingRun | None) -> DuplicateProcessingStatusSnapshot:
    if run is None:
        return DuplicateProcessingStatusSnapshot(
            run_id=None,
            status=STATUS_IDLE,
            started_at=None,
            finished_at=None,
            elapsed_seconds=None,
            total_items=0,
            processed_items=0,
            current_stage=None,
            error_message=None,
            stop_requested=False,
            workset_cutoff=None,
            last_successful_cutoff=None,
        )

    return DuplicateProcessingStatusSnapshot(
        run_id=run.id,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        elapsed_seconds=run.elapsed_seconds,
        total_items=int(run.total_items or 0),
        processed_items=int(run.processed_items or 0),
        current_stage=run.current_stage,
        error_message=run.error_message,
        stop_requested=bool(run.stop_requested),
        workset_cutoff=run.workset_cutoff,
        last_successful_cutoff=run.last_successful_cutoff,
    )


def _latest_run_stmt() -> Select[tuple[DuplicateProcessingRun]]:
    return select(DuplicateProcessingRun).order_by(DuplicateProcessingRun.id.desc()).limit(1)


def _active_run_stmt() -> Select[tuple[DuplicateProcessingRun]]:
    return (
        select(DuplicateProcessingRun)
        .where(DuplicateProcessingRun.status.in_(RUNNING_STATUSES))
        .order_by(DuplicateProcessingRun.id.desc())
        .limit(1)
    )


def _latest_successful_cutoff(db_session: Session) -> datetime | None:
    return db_session.scalar(
        select(DuplicateProcessingRun.workset_cutoff)
        .where(DuplicateProcessingRun.status == STATUS_COMPLETED)
        .order_by(DuplicateProcessingRun.id.desc())
        .limit(1)
    )


def _eligible_asset_query(workset_cutoff: datetime, last_successful_cutoff: datetime | None) -> Select[tuple[str]]:
    query = select(Asset.sha256).where(
        Asset.extension.in_(sorted(IMAGE_EXTENSIONS)),
        Asset.created_at_utc <= workset_cutoff,
    )
    if last_successful_cutoff is not None:
        query = query.where(Asset.created_at_utc > last_successful_cutoff)
    return query.order_by(Asset.created_at_utc.asc(), Asset.sha256.asc())


def get_duplicate_processing_status(db_session: Session) -> DuplicateProcessingStatusView:
    """Return status snapshot and pending item count derived from last successful cutoff."""
    ensure_duplicate_processing_schema(db_session)

    latest_run = db_session.scalar(_latest_run_stmt())
    latest_successful_cutoff = _latest_successful_cutoff(db_session)

    pending_query = select(func.count(Asset.sha256)).where(
        Asset.extension.in_(sorted(IMAGE_EXTENSIONS)),
    )
    if latest_successful_cutoff is not None:
        pending_query = pending_query.where(Asset.created_at_utc > latest_successful_cutoff)

    pending_items = int(db_session.scalar(pending_query) or 0)

    snapshot = _to_snapshot(latest_run)
    if snapshot.run_id is None:
        snapshot = DuplicateProcessingStatusSnapshot(
            run_id=None,
            status=STATUS_IDLE,
            started_at=None,
            finished_at=None,
            elapsed_seconds=None,
            total_items=0,
            processed_items=0,
            current_stage=None,
            error_message=None,
            stop_requested=False,
            workset_cutoff=None,
            last_successful_cutoff=latest_successful_cutoff,
        )

    return DuplicateProcessingStatusView(
        generated_at=_utc_now(),
        pending_items=pending_items,
        current=snapshot,
    )


def request_duplicate_processing_stop(db_session: Session) -> DuplicateProcessingRunResult:
    """Request graceful cancellation of the current duplicate run."""
    ensure_duplicate_processing_schema(db_session)

    active = db_session.scalar(_active_run_stmt())
    if active is None:
        latest_run = db_session.scalar(_latest_run_stmt())
        return DuplicateProcessingRunResult(
            status=_to_snapshot(latest_run),
            message="No active duplicate-processing run.",
        )

    active.stop_requested = True
    if active.status == STATUS_RUNNING:
        active.status = STATUS_STOP_REQUESTED
    active.current_stage = "stop_requested"
    db_session.commit()
    db_session.refresh(active)

    return DuplicateProcessingRunResult(
        status=_to_snapshot(active),
        message="Stop requested. The job will stop after the current safe unit.",
    )


def _create_run_record(db_session: Session, *, created_by: str | None) -> tuple[DuplicateProcessingRun, list[str]]:
    active = db_session.scalar(_active_run_stmt())
    if active is not None:
        raise DuplicateProcessingAlreadyRunningError(_to_snapshot(active))

    workset_cutoff = _utc_now()
    last_successful_cutoff = _latest_successful_cutoff(db_session)
    workset = list(
        db_session.scalars(_eligible_asset_query(workset_cutoff, last_successful_cutoff)).all()
    )

    run = DuplicateProcessingRun(
        status=STATUS_RUNNING,
        started_at=workset_cutoff,
        finished_at=None,
        elapsed_seconds=None,
        total_items=len(workset),
        processed_items=0,
        current_stage="lineage_update",
        error_message=None,
        stop_requested=False,
        workset_cutoff=workset_cutoff,
        last_successful_cutoff=last_successful_cutoff,
        created_by=created_by,
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    return run, workset


def _finalize_run(
    db_session: Session,
    run: DuplicateProcessingRun,
    *,
    status: str,
    processed_items: int,
    error_message: str | None = None,
) -> None:
    finished_at = _utc_now()
    run.status = status
    run.finished_at = finished_at
    run.elapsed_seconds = (finished_at - run.started_at).total_seconds() if run.started_at else None
    run.processed_items = processed_items
    run.current_stage = "done" if status == STATUS_COMPLETED else status
    run.error_message = error_message
    db_session.commit()


def _run_existing_workset(
    db_session: Session,
    *,
    run: DuplicateProcessingRun,
    workset: list[str],
    progress_callback: Callable[[DuplicateProcessingStatusSnapshot], None] | None,
) -> DuplicateProcessingStatusSnapshot:
    processed = 0

    for asset_sha256 in workset:
        db_session.refresh(run)
        if run.stop_requested:
            _finalize_run(
                db_session,
                run,
                status=STATUS_STOPPED,
                processed_items=processed,
                error_message=None,
            )
            db_session.refresh(run)
            snapshot = _to_snapshot(run)
            if progress_callback is not None:
                progress_callback(snapshot)
            return snapshot

        try:
            asset = db_session.get(Asset, asset_sha256)
            if asset is not None:
                update_asset_lineage(db_session, asset)
            processed += 1
            run.processed_items = processed
            run.current_stage = "lineage_update"
            db_session.commit()
            db_session.refresh(run)
            snapshot = _to_snapshot(run)
            if progress_callback is not None:
                progress_callback(snapshot)
        except Exception as exc:  # noqa: BLE001
            db_session.rollback()
            _finalize_run(
                db_session,
                run,
                status=STATUS_FAILED,
                processed_items=processed,
                error_message=str(exc) or exc.__class__.__name__,
            )
            db_session.refresh(run)
            snapshot = _to_snapshot(run)
            if progress_callback is not None:
                progress_callback(snapshot)
            return snapshot

    _finalize_run(
        db_session,
        run,
        status=STATUS_COMPLETED,
        processed_items=processed,
        error_message=None,
    )
    db_session.refresh(run)
    snapshot = _to_snapshot(run)
    if progress_callback is not None:
        progress_callback(snapshot)
    return snapshot


def run_duplicate_processing_sync(
    *,
    created_by: str | None = "script",
    progress_callback: Callable[[DuplicateProcessingStatusSnapshot], None] | None = None,
) -> DuplicateProcessingStatusSnapshot:
    """Run duplicate processing synchronously with a frozen incremental workset."""
    db_session = SessionLocal()
    try:
        ensure_duplicate_processing_schema(db_session)
        run, workset = _create_run_record(db_session, created_by=created_by)
        snapshot = _to_snapshot(run)
        if progress_callback is not None:
            progress_callback(snapshot)
        return _run_existing_workset(
            db_session,
            run=run,
            workset=workset,
            progress_callback=progress_callback,
        )
    finally:
        db_session.close()


def _run_background_job(run_id: int, workset: list[str]) -> None:
    global _runner_thread

    db_session = SessionLocal()
    try:
        run = db_session.get(DuplicateProcessingRun, run_id)
        if run is None:
            return
        _run_existing_workset(
            db_session,
            run=run,
            workset=workset,
            progress_callback=None,
        )
    finally:
        db_session.close()
        with _runner_lock:
            _runner_thread = None


def start_duplicate_processing_background(*, created_by: str | None = "admin_api") -> DuplicateProcessingRunResult:
    """Create and start a duplicate-processing run in a background thread."""
    global _runner_thread

    with _runner_lock:
        if _runner_thread is not None and _runner_thread.is_alive():
            db_session = SessionLocal()
            try:
                latest = db_session.scalar(_latest_run_stmt())
                return DuplicateProcessingRunResult(
                    status=_to_snapshot(latest),
                    message="A duplicate-processing run is already active.",
                )
            finally:
                db_session.close()

        db_session = SessionLocal()
        try:
            ensure_duplicate_processing_schema(db_session)
            run, workset = _create_run_record(db_session, created_by=created_by)
            status = _to_snapshot(run)
        finally:
            db_session.close()

        thread = threading.Thread(
            target=_run_background_job,
            args=(status.run_id, workset),
            name="duplicate-processing-runner",
            daemon=True,
        )
        _runner_thread = thread
        thread.start()

    return DuplicateProcessingRunResult(
        status=status,
        message="Duplicate processing started.",
    )
