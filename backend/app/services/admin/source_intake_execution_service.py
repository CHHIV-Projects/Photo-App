"""Background source intake execution controls."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.ingestion_source import IngestionSource
from app.models.source_intake_run import SourceIntakeRun
from app.services.ingestion.pipeline_orchestrator import (
    PipelineContext,
    RuntimeArgs,
    _run_pipeline,
    resolve_runtime_path,
)
from app.services.admin.source_intake_schema import ensure_source_intake_schema

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
class SourceIntakeStatusSnapshot:
    run_id: int | None
    status: str
    ingestion_run_id: int | None
    source_label: str | None
    source_type: str | None
    source_root_path: str | None
    source_intake_limit: int | None
    ingest_batch_size: int | None
    started_at: datetime | None
    finished_at: datetime | None
    elapsed_seconds: float | None
    files_scanned: int
    skipped_known: int
    selected: int
    staged: int
    processed_new_unique: int
    failed_or_rejected: int
    remaining_unknown: int
    report_path: str | None
    error_message: str | None
    stop_requested: bool


class SourceIntakeAlreadyRunningError(RuntimeError):
    """Raised when starting while another source intake job is active."""

    def __init__(self, snapshot: SourceIntakeStatusSnapshot) -> None:
        super().__init__("A source intake run is already active.")
        self.snapshot = snapshot


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_snapshot(run: SourceIntakeRun | None) -> SourceIntakeStatusSnapshot:
    if run is None:
        return SourceIntakeStatusSnapshot(
            run_id=None,
            status=STATUS_IDLE,
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
    return SourceIntakeStatusSnapshot(
        run_id=run.id,
        status=run.status,
        ingestion_run_id=run.ingestion_run_id,
        source_label=run.source_label,
        source_type=run.source_type,
        source_root_path=run.source_root_path,
        source_intake_limit=run.source_intake_limit,
        ingest_batch_size=run.ingest_batch_size,
        started_at=run.started_at,
        finished_at=run.finished_at,
        elapsed_seconds=run.elapsed_seconds,
        files_scanned=int(run.files_scanned or 0),
        skipped_known=int(run.skipped_known or 0),
        selected=int(run.selected or 0),
        staged=int(run.staged or 0),
        processed_new_unique=int(run.processed_new_unique or 0),
        failed_or_rejected=int(run.failed_or_rejected or 0),
        remaining_unknown=int(run.remaining_unknown or 0),
        report_path=run.report_path,
        error_message=run.error_message,
        stop_requested=bool(run.stop_requested),
    )


def _legacy_backend_storage_fallback(path: Path) -> Path | None:
    """Map legacy .../backend/storage/... paths to .../storage/... when present."""
    parts = list(path.parts)
    lowered = [part.lower() for part in parts]
    for idx in range(len(lowered) - 1):
        if lowered[idx] == "backend" and lowered[idx + 1] == "storage":
            candidate = Path(*parts[:idx], parts[idx + 1], *parts[idx + 2:]).resolve()
            return candidate
    return None


def _latest_run_stmt():
    return select(SourceIntakeRun).order_by(SourceIntakeRun.id.desc()).limit(1)


def _active_run_stmt():
    return (
        select(SourceIntakeRun)
        .where(SourceIntakeRun.status.in_(RUNNING_STATUSES))
        .order_by(SourceIntakeRun.id.desc())
        .limit(1)
    )


def get_source_intake_status(db_session: Session) -> SourceIntakeStatusSnapshot:
    """Return current status snapshot."""
    ensure_source_intake_schema(db_session)
    latest_run = db_session.scalar(_latest_run_stmt())
    return _to_snapshot(latest_run)


def request_source_intake_stop(db_session: Session) -> SourceIntakeStatusSnapshot:
    """Request graceful stop of the active source intake run."""
    ensure_source_intake_schema(db_session)
    active = db_session.scalar(_active_run_stmt())
    if active is None:
        latest_run = db_session.scalar(_latest_run_stmt())
        return _to_snapshot(latest_run)

    active.stop_requested = True
    if active.status == STATUS_RUNNING:
        active.status = STATUS_STOP_REQUESTED
    db_session.commit()
    return _to_snapshot(active)


def start_source_intake(
    db_session: Session,
    *,
    ingestion_source_id: int,
    source_intake_limit: int | None,
    ingest_batch_size: int,
    created_by: str = "admin_api",
) -> SourceIntakeStatusSnapshot:
    """Validate, create a run row, and launch the background thread."""
    ensure_source_intake_schema(db_session)

    # Check for existing active run
    active = db_session.scalar(_active_run_stmt())
    if active is not None:
        raise SourceIntakeAlreadyRunningError(_to_snapshot(active))

    # Resolve source
    source = db_session.get(IngestionSource, ingestion_source_id)
    if source is None:
        raise ValueError(f"Ingestion source {ingestion_source_id} not found.")

    source_root_path = source.source_root_path or ""
    if not source_root_path.strip():
        raise ValueError("Source has no root path configured.")

    _project_root = Path(__file__).resolve().parents[4]
    raw_path = Path(source_root_path).expanduser()
    resolved_path = raw_path.resolve() if raw_path.is_absolute() else (_project_root / raw_path).resolve()
    if not resolved_path.exists():
        fallback_path = _legacy_backend_storage_fallback(resolved_path)
        if fallback_path is not None and fallback_path.exists():
            resolved_path = fallback_path
            source.source_root_path = str(fallback_path)
            source.source_root_path_normalized = str(fallback_path).strip().lower()
            db_session.commit()
    if not resolved_path.exists():
        raise ValueError(f"Source path does not exist: {resolved_path}")
    if not resolved_path.is_dir():
        raise ValueError(f"Source path is not a directory: {resolved_path}")
    canonical_source_root_path = str(resolved_path)

    # Validate drop zone is empty
    drop_zone = resolve_runtime_path(settings.drop_zone_path)
    if drop_zone.exists() and any(drop_zone.iterdir()):
        raise ValueError("Drop zone is not empty. Clear or process existing files before launching intake.")

    # Create the run row
    run = SourceIntakeRun(
        status=STATUS_RUNNING,
        ingestion_source_id=ingestion_source_id,
        ingestion_run_id=None,  # Will be set after first batch context resolve
        source_label=source.source_label,
        source_type=source.source_type,
        source_root_path=canonical_source_root_path,
        source_intake_limit=source_intake_limit,
        ingest_batch_size=ingest_batch_size,
        started_at=_utc_now(),
        created_by=created_by,
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    run_id = run.id

    # Launch background thread
    global _runner_thread
    with _runner_lock:
        t = threading.Thread(
            target=_run_background_job,
            args=(run_id, canonical_source_root_path, source.source_label, source.source_type, source_intake_limit, ingest_batch_size),
            daemon=True,
            name=f"source-intake-{run_id}",
        )
        _runner_thread = t
        t.start()

    return _to_snapshot(run)


def _check_stop(run_id: int):
    """Returns a callable that checks if stop was requested for this run."""
    def _check() -> bool:
        with SessionLocal() as db:
            run = db.get(SourceIntakeRun, run_id)
            return bool(run and run.stop_requested)
    return _check


def _update_progress(run_id: int):
    """Returns a callable to update progress after each batch."""
    def _on_batch(ctx: PipelineContext) -> None:
        with SessionLocal() as db:
            run = db.get(SourceIntakeRun, run_id)
            if run is None:
                return
            run.files_scanned = ctx.source_files_scanned_total
            run.skipped_known = ctx.source_files_skipped_known
            run.selected = ctx.source_files_selected
            run.staged = ctx.source_files_selected
            run.processed_new_unique = ctx.total_new_unique_ingested
            run.remaining_unknown = ctx.source_files_remaining_unknown
            db.commit()
    return _on_batch


def _run_background_job(
    run_id: int,
    source_root_path: str,
    source_label: str,
    source_type: str,
    limit: int | None,
    batch_size: int,
) -> None:
    started_at = time.perf_counter()
    final_status = STATUS_FAILED
    error_message: str | None = None

    try:
        ctx = PipelineContext(
            from_path=Path(source_root_path).expanduser().resolve(),
            drop_zone_path=resolve_runtime_path(settings.drop_zone_path),
            vault_path=resolve_runtime_path(settings.vault_path),
            quarantine_path=resolve_runtime_path(settings.quarantine_path),
            ingest_failures_path=resolve_runtime_path(settings.ingest_failures_path),
            ingest_batch_size=batch_size,
            ingest_source_limit=limit,
            source_label=source_label,
            source_type=source_type,
        )
        args = RuntimeArgs(
            from_path=ctx.from_path,
            source_label=source_label,
            source_type=source_type,
            dry_run=False,
            ingest_batch_size=batch_size,
            ingest_source_limit=limit,
            skip_exif_extraction=False,
            skip_metadata_normalization=False,
            skip_duplicate_lineage=True,
            skip_face_processing=True,
            skip_crop_generation=True,
            skip_event_clustering=False,
            run_face_detection_rebuild=False,
            run_face_clustering_rebuild=False,
        )

        stop_fn = _check_stop(run_id)
        progress_fn = _update_progress(run_id)

        outcomes = _run_pipeline(ctx, args, stop_requested_fn=stop_fn, on_batch_complete=progress_fn)

        failed = next((o for o in outcomes if o.status == "failed"), None)
        stop_was_requested = stop_fn()

        if failed is not None:
            final_status = STATUS_FAILED
            error_message = f"Stage failed: {failed.key}"
        elif stop_was_requested:
            final_status = STATUS_STOPPED
        else:
            final_status = STATUS_COMPLETED

        elapsed = time.perf_counter() - started_at

        with SessionLocal() as db:
            run = db.get(SourceIntakeRun, run_id)
            if run is None:
                return
            run.status = final_status
            run.finished_at = _utc_now()
            run.elapsed_seconds = elapsed
            run.files_scanned = ctx.source_files_scanned_total
            run.skipped_known = ctx.source_files_skipped_known
            run.selected = ctx.source_files_selected
            run.staged = ctx.source_files_selected
            run.processed_new_unique = ctx.total_new_unique_ingested
            run.remaining_unknown = ctx.source_files_remaining_unknown
            if ctx.source_intake_report_path is not None:
                run.report_path = str(ctx.source_intake_report_path)
            if ctx.resolved_ingestion_context is not None:
                run.ingestion_run_id = ctx.resolved_ingestion_context.ingestion_run_id
            run.error_message = error_message
            db.commit()

    except Exception as exc:  # noqa: BLE001
        elapsed = time.perf_counter() - started_at
        with SessionLocal() as db:
            run = db.get(SourceIntakeRun, run_id)
            if run is not None:
                run.status = STATUS_FAILED
                run.finished_at = _utc_now()
                run.elapsed_seconds = elapsed
                run.error_message = str(exc)[:2000]
                db.commit()


def _reset_stale_runs(db_session: Session) -> None:
    """On startup, reset any 'running' rows to 'failed' (process died mid-run)."""
    stale = db_session.scalars(
        select(SourceIntakeRun).where(SourceIntakeRun.status.in_(RUNNING_STATUSES))
    ).all()
    for run in stale:
        run.status = STATUS_FAILED
        run.error_message = (run.error_message or "") + " [reset: process restarted]"
        run.finished_at = _utc_now()
    if stale:
        db_session.commit()
