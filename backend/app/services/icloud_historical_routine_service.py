"""Operator-level iCloud intake routine for prepared historical backfill batches."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import time

from sqlalchemy import func, inspect, select, update
from sqlalchemy.orm import Session

from app.models.icloud_acquisition_run import IcloudAcquisitionBatch, IcloudAcquisitionItem, IcloudAcquisitionResource
from app.models.icloud_acquisition_run import IcloudAcquisitionRun
from app.models.icloud_backfill import IcloudRemoteAssetInventory
from app.models.icloud_intake_import import IcloudIntakeImportChunk, IcloudIntakeImportRun
from app.models.icloud_intake_prepare import IcloudIntakePreparedCandidate, IcloudIntakePrepareRun
from app.models.icloud_staging_cleanup_run import IcloudStagingCleanupRun
from app.models.ingestion_source import IngestionSource
from app.models.source_intake_run import SourceIntakeRun
from app.services.admin.icloud_staging_cleanup_execution_service import (
    EXECUTION_CONFIRMATION_PHRASE,
    CleanupAuthorizationError,
    CleanupBusyError,
    CleanupRunSnapshot,
    CleanupValidationError,
    SourceIntakeActiveError,
    get_cleanup_status,
    reconcile_completed_cleanup_reports,
    start_cleanup_execution,
    start_cleanup_run,
)
from app.services.icloud_backfill_acquisition_execution_service import (
    IcloudBackfillAcquireResult,
    run_icloud_backfill_acquisition,
)
from app.services.icloud_backfill_inventory_service import (
    ELIGIBILITY_AMBIGUOUS_METADATA_ONLY,
    ELIGIBILITY_ELIGIBLE_METADATA_ONLY,
    ELIGIBILITY_UNSUPPORTED_METADATA_ONLY,
    KNOWN_STATE_PENDING_CHECK,
    IcloudBackfillStateNotFound,
    IcloudBackfillStatusSnapshot,
    IcloudInventoryScanResult,
    get_icloud_backfill_status,
    run_icloud_backfill_inventory_scan,
)
from app.services.icloud_backfill_schema import ensure_icloud_backfill_schema
from app.services.icloud_intake_import_schema import ensure_icloud_intake_import_schema
from app.services.icloud_intake_prepare_schema import ensure_icloud_intake_prepare_schema
from app.services.icloud_path_service import resolve_icloud_staging_path


DEFAULT_TARGET_LOGICAL_ASSETS = 1000
DEFAULT_INTERNAL_BATCH_SIZE = 100
DEFAULT_PREPARE_SCAN_CEILING = 10_000
DEFAULT_PREPARE_SCAN_DEPTHS = (1000, 2000, 3000, 5000, 10_000)
DEFAULT_MAX_LISTING_CANDIDATES = DEFAULT_PREPARE_SCAN_CEILING
DEFAULT_PREPARE_EXPIRY_MINUTES = 60
DEFAULT_CLEANUP_WAIT_SECONDS = 120.0
DEFAULT_CLEANUP_POLL_SECONDS = 0.2
DEFAULT_IMPORT_STALE_SECONDS = 30.0
INTAKE_IMPORT_REPORT_DIR = Path("storage") / "logs" / "icloud_intake_import_reports"

AVAILABLE_YES = "yes"
AVAILABLE_NO = "no"
AVAILABLE_UNKNOWN = "unknown"

PREPARE_STATUS_PREPARED = "prepared"
PREPARE_STATUS_RUNNING = "running"
PREPARE_STATUS_CONSUMED = "consumed"
PREPARE_STATUS_EXPIRED = "expired"
PREPARE_STATUS_STALE = "stale"
PREPARE_STATUS_SUPERSEDED = "superseded"

CANDIDATE_STATE_PREPARED = "prepared"
CANDIDATE_STATE_IMPORTED = "imported"
CANDIDATE_STATE_SKIPPED_STALE = "skipped_stale"
CANDIDATE_STATE_DEFERRED_AT_EXECUTION = "deferred_at_execution"
CANDIDATE_STATE_EXECUTION_FAILED_RETRYABLE = "execution_failed_retryable"
CANDIDATE_STATE_FAILED = "failed"

RUN_COMPLETED_TARGET = "completed_target"
RUN_COMPLETED_EXHAUSTED = "completed_exhausted"
RUN_COMPLETED_PARTIAL_SCAN_BOUND = "completed_partial_scan_bound"
RUN_STOPPED_NEEDS_REVIEW = "stopped_needs_review"
RUN_FAILED = "failed"

IMPORT_STATUS_CREATED = "created"
IMPORT_STATUS_RUNNING = "running"
IMPORT_STATUS_RESUME_AVAILABLE = "resume_available"
IMPORT_STATUS_PAUSED_INTERRUPTED = "paused_interrupted"
IMPORT_STATUS_COMPLETED = "completed"
IMPORT_STATUS_COMPLETED_PARTIAL = "completed_partial"
IMPORT_STATUS_STOPPED_NEEDS_REVIEW = "stopped_needs_review"
IMPORT_STATUS_FAILED = "failed"
IMPORT_STATUS_CANCELLED = "cancelled"

IMPORT_INCOMPLETE_STATUSES = {
    IMPORT_STATUS_CREATED,
    IMPORT_STATUS_RUNNING,
    IMPORT_STATUS_RESUME_AVAILABLE,
    IMPORT_STATUS_PAUSED_INTERRUPTED,
    IMPORT_STATUS_STOPPED_NEEDS_REVIEW,
}
IMPORT_TERMINAL_STATUSES = {
    IMPORT_STATUS_COMPLETED,
    IMPORT_STATUS_COMPLETED_PARTIAL,
    IMPORT_STATUS_FAILED,
    IMPORT_STATUS_CANCELLED,
}

CHUNK_STATUS_PENDING = "pending"
CHUNK_STATUS_RUNNING = "running"
CHUNK_STATUS_COMPLETED = "completed"
CHUNK_STATUS_STOPPED_NEEDS_REVIEW = "stopped_needs_review"
CHUNK_STATUS_FAILED = "failed"
CHUNK_STATUS_RETRYABLE_FAILED = "retryable_failed"
CHUNK_STATUS_SKIPPED = "skipped"

_ACQUISITION_RUNNING_STATUSES = {"running", "stop_requested"}
_SOURCE_INTAKE_RUNNING_STATUSES = {"running", "stop_requested"}
_CLEANUP_RUNNING_STATUSES = {"pending", "running", "stop_requested"}

_SELECTABLE_KNOWN_STATES = {KNOWN_STATE_PENDING_CHECK, "unknown"}


class IcloudHistoricalRoutineError(ValueError):
    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class IcloudHistoricalRoutineStatus:
    source_id: int
    source_label: str | None
    total_imported_from_source: int
    inventory_total_logical: int
    backfill_completed_logical: int
    eligible_pending_logical: int
    available_inventory: str
    logical_candidates_ready: int
    latest_prepare_run_id: int | None
    prepare_status: str | None
    prepare_expires_at: datetime | None
    target_logical_candidates: int
    new_deferred_this_prepare: int
    source_exhaustion_state: str
    provider_records_scanned: int
    scan_depth_used: int
    deferred_current_logical: int
    deferred_adjusted_resource_logical: int
    deferred_ambiguous_logical: int
    deferred_unsupported_logical: int
    retryable_failed_logical: int
    last_inventory_scan_at: datetime | None
    last_inventory_refresh_at: datetime | None
    last_historical_run_at: datetime | None
    last_historical_run_id: int | None
    last_cleanup_run_id: int | None
    local_staging_file_count: int
    partial_file_count: int
    backfill_execute_file_count: int
    operator_message: str


@dataclass(frozen=True)
class IcloudHistoricalRefreshResult:
    source_id: int
    status: str
    prepare_run_id: int
    inventory_total_logical: int
    created_logical: int
    updated_logical: int
    eligible_pending_logical: int
    available_inventory: str
    target_logical_candidates: int
    logical_candidates_ready: int
    new_deferred_this_prepare: int
    deferred_current_logical: int
    deferred_adjusted_resource_logical: int
    source_exhausted: bool
    scan_limit_reached: bool
    source_exhaustion_state: str
    provider_records_scanned: int
    scan_depth_used: int
    expires_at: datetime
    operator_message: str
    scanned_at: datetime
    scan_limit_note: str


@dataclass(frozen=True)
class IcloudHistoricalRoutineChunk:
    chunk_index: int
    requested_logical_assets: int
    imported_logical_assets: int
    imported_resources: int
    cleaned_local_staging_files: int
    acquisition_run_id: int | None
    acquisition_batch_id: int | None
    source_intake_run_id: int | None
    cleanup_dry_run_id: int | None
    cleanup_execution_run_id: int | None
    cleanup_report_path: str | None
    status: str
    stop_reason: str | None
    operator_message: str


@dataclass(frozen=True)
class IcloudHistoricalRunResult:
    source_id: int
    status: str
    prepare_run_id: int | None
    requested_logical_assets: int
    logical_candidates: int
    internal_batch_size: int
    imported_logical_assets: int
    logical_imported: int
    imported_resources: int
    files_resources_imported: int
    cleaned_local_staging_files: int
    local_staging_files_cleaned: int
    new_deferred_this_run: int
    execution_failed_this_run: int
    eligible_remaining_logical: int
    deferred_current_logical: int
    deferred_adjusted_resource_logical: int
    available_inventory: str
    operator_message: str
    stop_reason: str | None
    chunks: tuple[IcloudHistoricalRoutineChunk, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class IcloudIntakeImportChunkStatus:
    id: int
    chunk_index: int
    status: str
    candidate_start_index: int
    candidate_end_index: int
    logical_candidates: int
    logical_imported: int
    files_resources_imported: int
    local_staging_files_cleaned: int
    new_deferred_this_chunk: int
    execution_failed_retryable_count: int
    execution_failed_terminal_count: int
    source_intake_failed_count: int
    cleanup_failed_count: int
    acquisition_run_id: int | None
    acquisition_batch_id: int | None
    source_intake_run_id: int | None
    cleanup_dry_run_id: int | None
    cleanup_execution_run_id: int | None
    cleanup_report_path: str | None
    cleanup_eligible_count: int
    cleanup_skipped_count: int
    cleanup_protected_count: int
    cleanup_verification_failed_count: int
    cleanup_file_missing_count: int
    cleanup_delete_failed_count: int
    chunk_total_seconds: float | None
    candidate_load_seconds: float | None
    fresh_resolution_seconds: float | None
    download_stage_seconds: float | None
    source_intake_seconds: float | None
    cleanup_dry_run_seconds: float | None
    cleanup_execute_seconds: float | None
    db_state_update_seconds: float | None
    inter_chunk_gap_seconds: float | None
    started_at: datetime | None
    completed_at: datetime | None
    failed_at: datetime | None
    operator_message: str | None
    stop_reason: str | None
    timing_note: str | None


@dataclass(frozen=True)
class IcloudIntakeImportStatus:
    source_id: int
    source_label: str | None
    total_imported_from_source: int
    last_inventory_refresh_at: datetime | None
    available_inventory: str
    logical_candidates_ready: int
    latest_prepare_run_id: int | None
    prepare_status: str | None
    prepare_expires_at: datetime | None
    import_run_id: int | None
    import_status: str | None
    import_operator_message: str
    import_stop_reason: str | None
    target_logical_candidates: int
    logical_candidates_total: int
    logical_imported: int
    files_resources_imported: int
    local_staging_files_cleaned: int
    new_deferred_this_run: int
    execution_failed_retryable_count: int
    execution_failed_terminal_count: int
    source_intake_failed_count: int
    cleanup_failed_count: int
    current_chunk_index: int
    total_chunks: int
    internal_batch_size: int
    pending_chunk_count: int
    completed_chunk_count: int
    remaining_logical_candidates: int
    resume_available: bool
    can_start_import: bool
    can_resume_import: bool
    can_advance_import: bool
    current_phase: str | None
    last_chunk_duration_seconds: float | None
    last_inter_chunk_gap_seconds: float | None
    started_at: datetime | None
    last_progress_at: datetime | None
    completed_at: datetime | None
    failed_at: datetime | None
    interrupted_at: datetime | None
    resumed_at: datetime | None
    report_path: str | None
    local_staging_file_count: int
    partial_file_count: int
    backfill_execute_file_count: int
    chunks: tuple[IcloudIntakeImportChunkStatus, ...] = field(default_factory=tuple)


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _validate_source(db_session: Session, *, source_id: int) -> IngestionSource:
    source = db_session.get(IngestionSource, source_id)
    if source is None:
        raise IcloudHistoricalRoutineError("Source Profile not found.", code="source_not_found")
    if (source.profile_status or "").strip().lower() != "active":
        raise IcloudHistoricalRoutineError("Only an active Source Profile can be used.", code="profile_not_active")
    if (source.source_type or "").strip().lower() != "cloud_export" or (source.cloud_provider or "").strip().lower() != "icloud":
        raise IcloudHistoricalRoutineError("The selected Source Profile is not an iCloud profile.", code="not_icloud_profile")
    return source


def _ensure_schema(db_session: Session) -> None:
    ensure_icloud_backfill_schema(db_session)
    ensure_icloud_intake_prepare_schema(db_session)
    ensure_icloud_intake_import_schema(db_session)


def _file_count(root: Path) -> int:
    if not root.exists() or not root.is_dir():
        return 0
    return sum(1 for path in root.rglob("*") if path.is_file())


def _source_staging_root(source: IngestionSource) -> Path:
    raw = (source.managed_staging_path or source.source_root_path or "").strip()
    return Path(raw) if raw else resolve_icloud_staging_path(source.source_label or f"source_{source.id}")


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except (OSError, ValueError):
        return False


def _safe_relative_files(root: Path) -> tuple[str, ...]:
    if not root.exists() or not root.is_dir():
        return ()
    paths: list[str] = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise IcloudHistoricalRoutineError("Staging folder contains a symlink; cleanup review is required.", code="staging_symlink_blocked")
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            paths.append(relative)
    return tuple(sorted(paths))


def _remove_empty_subdirectories(root: Path) -> None:
    if not root.exists() or not root.is_dir():
        return
    directories = sorted(
        [path for path in root.rglob("*") if path.is_dir() and not path.is_symlink() and path != root],
        key=lambda path: len(path.parts),
        reverse=True,
    )
    for directory in directories:
        try:
            next(directory.iterdir())
        except StopIteration:
            try:
                directory.rmdir()
            except OSError:
                pass
        except OSError:
            pass


def _latest_historical_run(db_session: Session, *, source_id: int) -> IcloudAcquisitionRun | None:
    return db_session.scalar(
        select(IcloudAcquisitionRun)
        .where(
            IcloudAcquisitionRun.source_profile_id == source_id,
            IcloudAcquisitionRun.created_by == "icloud_backfill_acquire",
        )
        .order_by(IcloudAcquisitionRun.id.desc())
        .limit(1)
    )


def _latest_cleanup_run(db_session: Session, *, source_id: int) -> IcloudStagingCleanupRun | None:
    return db_session.scalar(
        select(IcloudStagingCleanupRun)
        .where(IcloudStagingCleanupRun.ingestion_source_id == source_id)
        .order_by(IcloudStagingCleanupRun.id.desc())
        .limit(1)
    )


def _latest_prepare_run(db_session: Session, *, source_id: int) -> IcloudIntakePrepareRun | None:
    return db_session.scalar(
        select(IcloudIntakePrepareRun)
        .where(IcloudIntakePrepareRun.source_profile_id == source_id)
        .order_by(IcloudIntakePrepareRun.id.desc())
        .limit(1)
    )


def _table_exists(db_session: Session, table_name: str) -> bool:
    bind = db_session.get_bind()
    return table_name in set(inspect(bind).get_table_names())


def _active_child_operation_exists(db_session: Session) -> bool:
    if _table_exists(db_session, "icloud_acquisition_runs"):
        active_acquisition = db_session.scalar(
            select(IcloudAcquisitionRun.id)
            .where(IcloudAcquisitionRun.status.in_(tuple(_ACQUISITION_RUNNING_STATUSES)))
            .limit(1)
        )
        if active_acquisition is not None:
            return True
    if _table_exists(db_session, "source_intake_runs"):
        active_intake = db_session.scalar(
            select(SourceIntakeRun.id)
            .where(SourceIntakeRun.status.in_(tuple(_SOURCE_INTAKE_RUNNING_STATUSES)))
            .limit(1)
        )
        if active_intake is not None:
            return True
    if _table_exists(db_session, "icloud_staging_cleanup_runs"):
        active_cleanup = db_session.scalar(
            select(IcloudStagingCleanupRun.id)
            .where(IcloudStagingCleanupRun.status.in_(tuple(_CLEANUP_RUNNING_STATUSES)))
            .limit(1)
        )
        if active_cleanup is not None:
            return True
    return False


def _latest_import_run(db_session: Session, *, source_id: int) -> IcloudIntakeImportRun | None:
    if not _table_exists(db_session, "icloud_intake_import_runs"):
        return None
    return db_session.scalar(
        select(IcloudIntakeImportRun)
        .where(IcloudIntakeImportRun.source_profile_id == source_id)
        .order_by(IcloudIntakeImportRun.id.desc())
        .limit(1)
    )


def _latest_incomplete_import_run(db_session: Session, *, source_id: int) -> IcloudIntakeImportRun | None:
    if not _table_exists(db_session, "icloud_intake_import_runs"):
        return None
    return db_session.scalar(
        select(IcloudIntakeImportRun)
        .where(
            IcloudIntakeImportRun.source_profile_id == source_id,
            IcloudIntakeImportRun.status.in_(tuple(IMPORT_INCOMPLETE_STATUSES)),
        )
        .order_by(IcloudIntakeImportRun.id.desc())
        .limit(1)
    )


def _import_chunks(db_session: Session, *, import_run_id: int) -> tuple[IcloudIntakeImportChunk, ...]:
    rows = db_session.scalars(
        select(IcloudIntakeImportChunk)
        .where(IcloudIntakeImportChunk.import_run_id == import_run_id)
        .order_by(IcloudIntakeImportChunk.chunk_index.asc())
    ).all()
    return tuple(rows)


def _chunk_to_status(chunk: IcloudIntakeImportChunk) -> IcloudIntakeImportChunkStatus:
    return IcloudIntakeImportChunkStatus(
        id=chunk.id,
        chunk_index=chunk.chunk_index,
        status=chunk.status,
        candidate_start_index=chunk.candidate_start_index,
        candidate_end_index=chunk.candidate_end_index,
        logical_candidates=chunk.logical_candidates,
        logical_imported=chunk.logical_imported,
        files_resources_imported=chunk.files_resources_imported,
        local_staging_files_cleaned=chunk.local_staging_files_cleaned,
        new_deferred_this_chunk=chunk.new_deferred_this_chunk,
        execution_failed_retryable_count=chunk.execution_failed_retryable_count,
        execution_failed_terminal_count=chunk.execution_failed_terminal_count,
        source_intake_failed_count=chunk.source_intake_failed_count,
        cleanup_failed_count=chunk.cleanup_failed_count,
        acquisition_run_id=chunk.acquisition_run_id,
        acquisition_batch_id=chunk.acquisition_batch_id,
        source_intake_run_id=chunk.source_intake_run_id,
        cleanup_dry_run_id=chunk.cleanup_dry_run_id,
        cleanup_execution_run_id=chunk.cleanup_execution_run_id,
        cleanup_report_path=chunk.cleanup_report_path,
        cleanup_eligible_count=chunk.cleanup_eligible_count,
        cleanup_skipped_count=chunk.cleanup_skipped_count,
        cleanup_protected_count=chunk.cleanup_protected_count,
        cleanup_verification_failed_count=chunk.cleanup_verification_failed_count,
        cleanup_file_missing_count=chunk.cleanup_file_missing_count,
        cleanup_delete_failed_count=chunk.cleanup_delete_failed_count,
        chunk_total_seconds=chunk.chunk_total_seconds,
        candidate_load_seconds=chunk.candidate_load_seconds,
        fresh_resolution_seconds=chunk.fresh_resolution_seconds,
        download_stage_seconds=chunk.download_stage_seconds,
        source_intake_seconds=chunk.source_intake_seconds,
        cleanup_dry_run_seconds=chunk.cleanup_dry_run_seconds,
        cleanup_execute_seconds=chunk.cleanup_execute_seconds,
        db_state_update_seconds=chunk.db_state_update_seconds,
        inter_chunk_gap_seconds=chunk.inter_chunk_gap_seconds,
        started_at=chunk.started_at,
        completed_at=chunk.completed_at,
        failed_at=chunk.failed_at,
        operator_message=chunk.operator_message,
        stop_reason=chunk.stop_reason,
        timing_note=chunk.timing_note,
    )


def _refresh_import_run_aggregates(db_session: Session, import_run: IcloudIntakeImportRun) -> None:
    chunks = _import_chunks(db_session, import_run_id=import_run.id)
    import_run.logical_imported = sum(int(chunk.logical_imported or 0) for chunk in chunks)
    import_run.files_resources_imported = sum(int(chunk.files_resources_imported or 0) for chunk in chunks)
    import_run.local_staging_files_cleaned = sum(int(chunk.local_staging_files_cleaned or 0) for chunk in chunks)
    import_run.new_deferred_this_run = sum(int(chunk.new_deferred_this_chunk or 0) for chunk in chunks)
    import_run.execution_failed_retryable_count = sum(int(chunk.execution_failed_retryable_count or 0) for chunk in chunks)
    import_run.execution_failed_terminal_count = sum(int(chunk.execution_failed_terminal_count or 0) for chunk in chunks)
    import_run.source_intake_failed_count = sum(int(chunk.source_intake_failed_count or 0) for chunk in chunks)
    import_run.cleanup_failed_count = sum(int(chunk.cleanup_failed_count or 0) for chunk in chunks)
    progressed = [
        chunk.chunk_index
        for chunk in chunks
        if chunk.status != CHUNK_STATUS_PENDING
    ]
    import_run.current_chunk_index = max(progressed, default=0)
    import_run.updated_at = _now_utc()


def _pending_import_chunks(db_session: Session, *, import_run_id: int) -> tuple[IcloudIntakeImportChunk, ...]:
    rows = db_session.scalars(
        select(IcloudIntakeImportChunk)
        .where(
            IcloudIntakeImportChunk.import_run_id == import_run_id,
            IcloudIntakeImportChunk.status.in_(
                (
                    CHUNK_STATUS_PENDING,
                    CHUNK_STATUS_RETRYABLE_FAILED,
                )
            ),
        )
        .order_by(IcloudIntakeImportChunk.chunk_index.asc())
    ).all()
    return tuple(rows)


def _previous_completed_chunk(
    db_session: Session,
    *,
    import_run_id: int,
    chunk_index: int,
) -> IcloudIntakeImportChunk | None:
    return db_session.scalar(
        select(IcloudIntakeImportChunk)
        .where(
            IcloudIntakeImportChunk.import_run_id == import_run_id,
            IcloudIntakeImportChunk.chunk_index < chunk_index,
            IcloudIntakeImportChunk.completed_at.is_not(None),
        )
        .order_by(IcloudIntakeImportChunk.chunk_index.desc())
        .limit(1)
    )


def _write_import_report(db_session: Session, import_run: IcloudIntakeImportRun) -> None:
    INTAKE_IMPORT_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = INTAKE_IMPORT_REPORT_DIR / f"icloud_intake_import_run_{import_run.id}.json"
    chunks = _import_chunks(db_session, import_run_id=import_run.id)
    report = {
        "source_profile_id": import_run.source_profile_id,
        "prepare_run_id": import_run.prepare_run_id,
        "import_run_id": import_run.id,
        "status": import_run.status,
        "logical_candidates_total": import_run.logical_candidates_total,
        "logical_imported": import_run.logical_imported,
        "files_resources_imported": import_run.files_resources_imported,
        "local_staging_files_cleaned": import_run.local_staging_files_cleaned,
        "new_deferred_this_run": import_run.new_deferred_this_run,
        "retryable_execution_failures": import_run.execution_failed_retryable_count,
        "terminal_execution_failures": import_run.execution_failed_terminal_count,
        "source_intake_failures": import_run.source_intake_failed_count,
        "cleanup_failures": import_run.cleanup_failed_count,
        "operator_message": import_run.operator_message,
        "stop_reason": import_run.stop_reason,
        "remaining_logical_candidates": max(
            0,
            int(import_run.logical_candidates_total or 0) - int(import_run.logical_imported or 0),
        ),
        "manual_db_repair_required": False,
        "chunks": [
            {
                "chunk_id": chunk.id,
                "chunk_index": chunk.chunk_index,
                "status": chunk.status,
                "candidate_start_index": chunk.candidate_start_index,
                "candidate_end_index": chunk.candidate_end_index,
                "logical_candidates": chunk.logical_candidates,
                "logical_imported": chunk.logical_imported,
                "files_resources_imported": chunk.files_resources_imported,
                "local_staging_files_cleaned": chunk.local_staging_files_cleaned,
                "new_deferred_this_chunk": chunk.new_deferred_this_chunk,
                "retryable_execution_failures": chunk.execution_failed_retryable_count,
                "terminal_execution_failures": chunk.execution_failed_terminal_count,
                "source_intake_failures": chunk.source_intake_failed_count,
                "cleanup_failures": chunk.cleanup_failed_count,
                "acquisition_run_id": chunk.acquisition_run_id,
                "acquisition_batch_id": chunk.acquisition_batch_id,
                "source_intake_run_id": chunk.source_intake_run_id,
                "cleanup_dry_run_id": chunk.cleanup_dry_run_id,
                "cleanup_execution_run_id": chunk.cleanup_execution_run_id,
                "cleanup_safety_counters": {
                    "eligible_count": chunk.cleanup_eligible_count,
                    "skipped_count": chunk.cleanup_skipped_count,
                    "protected_count": chunk.cleanup_protected_count,
                    "verification_failed_count": chunk.cleanup_verification_failed_count,
                    "file_missing_count": chunk.cleanup_file_missing_count,
                    "delete_failed_count": chunk.cleanup_delete_failed_count,
                },
                "timings": {
                    "chunk_total_seconds": chunk.chunk_total_seconds,
                    "candidate_load_seconds": chunk.candidate_load_seconds,
                    "fresh_resolution_seconds": chunk.fresh_resolution_seconds,
                    "download_stage_seconds": chunk.download_stage_seconds,
                    "source_intake_seconds": chunk.source_intake_seconds,
                    "cleanup_dry_run_seconds": chunk.cleanup_dry_run_seconds,
                    "cleanup_execute_seconds": chunk.cleanup_execute_seconds,
                    "db_state_update_seconds": chunk.db_state_update_seconds,
                    "inter_chunk_gap_seconds": chunk.inter_chunk_gap_seconds,
                    "timing_note": chunk.timing_note,
                },
                "operator_message": chunk.operator_message,
                "stop_reason": chunk.stop_reason,
            }
            for chunk in chunks
        ],
    }
    try:
        with open(report_path, "w") as handle:
            json.dump(report, handle, indent=2, default=str)
    except OSError:
        return
    import_run.report_path = str(report_path)


def _recover_stale_legacy_prepare_run(db_session: Session, *, source_id: int, now: datetime) -> None:
    if _active_child_operation_exists(db_session):
        return
    latest_prepare = _latest_prepare_run(db_session, source_id=source_id)
    if latest_prepare is None or latest_prepare.status != PREPARE_STATUS_RUNNING:
        return
    if _latest_incomplete_import_run(db_session, source_id=source_id) is not None:
        return
    latest_prepare.status = PREPARE_STATUS_PREPARED
    latest_prepare.operator_message = "Interrupted import detected. The prepared set is available to resume."
    latest_prepare.updated_at = now
    db_session.commit()


def _recover_stale_import_runs(db_session: Session, *, source_id: int, now: datetime | None = None) -> None:
    now = now or _now_utc()
    run = _latest_incomplete_import_run(db_session, source_id=source_id)
    if run is None or run.status != IMPORT_STATUS_RUNNING:
        _recover_stale_legacy_prepare_run(db_session, source_id=source_id, now=now)
        return
    if _active_child_operation_exists(db_session):
        return
    last_progress = _as_utc(run.last_progress_at or run.started_at or run.created_at)
    if last_progress is not None and (now - last_progress).total_seconds() < DEFAULT_IMPORT_STALE_SECONDS:
        return

    running_chunks = [
        chunk
        for chunk in _import_chunks(db_session, import_run_id=run.id)
        if chunk.status == CHUNK_STATUS_RUNNING
    ]
    needs_review = False
    for chunk in running_chunks:
        if int(chunk.files_resources_imported or 0) > int(chunk.local_staging_files_cleaned or 0):
            needs_review = True
            chunk.status = CHUNK_STATUS_STOPPED_NEEDS_REVIEW
            chunk.stop_reason = "interrupted_after_import_before_cleanup"
            chunk.operator_message = "Interrupted after files/resources were imported but before verified cleanup completed."
            chunk.failed_at = now
            chunk.cleanup_failed_count = max(int(chunk.cleanup_failed_count or 0), 1)
        else:
            chunk.status = CHUNK_STATUS_RETRYABLE_FAILED
            chunk.stop_reason = "interrupted_chunk"
            chunk.operator_message = "Interrupted while this chunk was active; it can be retried by resuming."
            chunk.failed_at = now

    prepare_run = db_session.get(IcloudIntakePrepareRun, run.prepare_run_id)
    if needs_review:
        run.status = IMPORT_STATUS_STOPPED_NEEDS_REVIEW
        run.stop_reason = "interrupted_chunk_needs_review"
        run.operator_message = "Import interrupted during a chunk. Review cleanup/staging state before resuming."
        run.failed_at = now
    else:
        run.status = IMPORT_STATUS_RESUME_AVAILABLE
        run.stop_reason = "interrupted_between_chunks"
        run.operator_message = "Import interrupted. Resume is available; no manual DB repair is required."
        run.interrupted_at = now
        if prepare_run is not None:
            prepare_run.status = PREPARE_STATUS_PREPARED
            prepare_run.operator_message = run.operator_message
            prepare_run.updated_at = now
    run.last_progress_at = now
    _refresh_import_run_aggregates(db_session, run)
    _write_import_report(db_session, run)
    db_session.commit()


def _expire_stale_prepare_runs(db_session: Session, *, source_id: int, now: datetime | None = None) -> None:
    now = now or _now_utc()
    runs = db_session.scalars(
        select(IcloudIntakePrepareRun).where(
            IcloudIntakePrepareRun.source_profile_id == source_id,
            IcloudIntakePrepareRun.status == PREPARE_STATUS_PREPARED,
            IcloudIntakePrepareRun.consumed_at.is_(None),
        )
    ).all()
    changed = False
    for run in runs:
        expires_at = _as_utc(run.expires_at)
        if expires_at is not None and expires_at <= now:
            run.status = PREPARE_STATUS_EXPIRED
            run.updated_at = now
            changed = True
    if changed:
        db_session.commit()


def _supersede_active_prepare_runs(db_session: Session, *, source_id: int, now: datetime) -> None:
    runs = db_session.scalars(
        select(IcloudIntakePrepareRun).where(
            IcloudIntakePrepareRun.source_profile_id == source_id,
            IcloudIntakePrepareRun.status.in_((PREPARE_STATUS_PREPARED, PREPARE_STATUS_RUNNING)),
            IcloudIntakePrepareRun.consumed_at.is_(None),
        )
    ).all()
    for run in runs:
        run.status = PREPARE_STATUS_SUPERSEDED
        run.updated_at = now


def _is_preparable_inventory_row(row: IcloudRemoteAssetInventory) -> bool:
    eligibility = (row.eligibility_state or "").strip()
    known_state = (row.known_state or "").strip()
    return (
        not bool(row.backfill_completed)
        and bool((row.remote_identity_basis or "").strip())
        and bool((row.remote_identity or "").strip())
        and known_state in _SELECTABLE_KNOWN_STATES
        and not bool(row.identity_ambiguous)
        and eligibility == ELIGIBILITY_ELIGIBLE_METADATA_ONLY
    )


def _select_preparable_inventory_rows(
    db_session: Session,
    *,
    source_id: int,
    limit: int,
) -> tuple[IcloudRemoteAssetInventory, ...]:
    rows = db_session.scalars(
        select(IcloudRemoteAssetInventory)
        .where(
            IcloudRemoteAssetInventory.source_profile_id == source_id,
            IcloudRemoteAssetInventory.eligibility_state == ELIGIBILITY_ELIGIBLE_METADATA_ONLY,
            IcloudRemoteAssetInventory.backfill_completed.is_(False),
            IcloudRemoteAssetInventory.known_state.in_(tuple(_SELECTABLE_KNOWN_STATES)),
            IcloudRemoteAssetInventory.identity_ambiguous.is_(False),
            IcloudRemoteAssetInventory.remote_identity != "",
            IcloudRemoteAssetInventory.remote_identity_basis != "",
        )
        .order_by(
            IcloudRemoteAssetInventory.observed_remote_position.asc(),
            IcloudRemoteAssetInventory.id.asc(),
        )
        .limit(limit)
    ).all()
    return tuple(rows)


def _available_from_prepare(*, logical_candidates_ready: int, source_exhaustion_state: str) -> str:
    if logical_candidates_ready > 0:
        return AVAILABLE_YES
    if source_exhaustion_state == "exhausted":
        return AVAILABLE_NO
    return AVAILABLE_UNKNOWN


def _status_from_snapshot(
    snapshot: IcloudBackfillStatusSnapshot,
    *,
    source: IngestionSource,
    db_session: Session,
) -> IcloudHistoricalRoutineStatus:
    now = _now_utc()
    _expire_stale_prepare_runs(db_session, source_id=source.id, now=now)
    staging_root = _source_staging_root(source)
    partial_root = staging_root / ".partial"
    backfill_execute_root = staging_root / "backfill_execute"
    latest_run = _latest_historical_run(db_session, source_id=source.id)
    latest_cleanup = _latest_cleanup_run(db_session, source_id=source.id)
    latest_prepare = _latest_prepare_run(db_session, source_id=source.id)

    logical_candidates_ready = 0
    target_logical_candidates = DEFAULT_TARGET_LOGICAL_ASSETS
    new_deferred_this_prepare = 0
    source_exhaustion_state = "unknown"
    provider_records_scanned = 0
    scan_depth_used = 0
    prepare_expires_at: datetime | None = None
    prepare_status: str | None = None
    latest_prepare_run_id: int | None = None
    operator_message = "Refresh / Prepare Next 1000 before importing."

    if latest_prepare is not None:
        latest_prepare_run_id = latest_prepare.id
        prepare_status = latest_prepare.status
        target_logical_candidates = int(latest_prepare.target_logical_candidates or DEFAULT_TARGET_LOGICAL_ASSETS)
        source_exhaustion_state = latest_prepare.source_exhaustion_state or "unknown"
        provider_records_scanned = int(latest_prepare.provider_records_scanned or 0)
        scan_depth_used = int(latest_prepare.scan_depth_used or 0)
        new_deferred_this_prepare = int(latest_prepare.new_deferred_count or 0)
        prepare_expires_at = latest_prepare.expires_at
        if latest_prepare.status == PREPARE_STATUS_PREPARED and latest_prepare.consumed_at is None and (_as_utc(latest_prepare.expires_at) or now) > now:
            logical_candidates_ready = int(latest_prepare.logical_candidates_ready or 0)
            operator_message = latest_prepare.operator_message or operator_message
        elif latest_prepare.status == PREPARE_STATUS_CONSUMED:
            operator_message = "Import completed. Refresh / Prepare Next 1000 before importing again."
        elif latest_prepare.status == PREPARE_STATUS_EXPIRED:
            operator_message = "Prepared candidate set expired. Refresh / Prepare Next 1000 again before importing."
        elif latest_prepare.status == PREPARE_STATUS_SUPERSEDED:
            operator_message = "A newer prepare run superseded this candidate set."

    available = _available_from_prepare(
        logical_candidates_ready=logical_candidates_ready,
        source_exhaustion_state=source_exhaustion_state,
    )
    if snapshot.last_inventory_scan_at is None and latest_prepare is None:
        available = AVAILABLE_UNKNOWN

    return IcloudHistoricalRoutineStatus(
        source_id=source.id,
        source_label=source.source_label,
        total_imported_from_source=snapshot.backfill_completed_count,
        inventory_total_logical=snapshot.inventory_total_count,
        backfill_completed_logical=snapshot.backfill_completed_count,
        eligible_pending_logical=snapshot.acquirable_pending_count,
        available_inventory=available,
        logical_candidates_ready=logical_candidates_ready,
        latest_prepare_run_id=latest_prepare_run_id,
        prepare_status=prepare_status,
        prepare_expires_at=prepare_expires_at,
        target_logical_candidates=target_logical_candidates,
        new_deferred_this_prepare=new_deferred_this_prepare,
        source_exhaustion_state=source_exhaustion_state,
        provider_records_scanned=provider_records_scanned,
        scan_depth_used=scan_depth_used,
        deferred_current_logical=snapshot.deferred_current_count,
        deferred_adjusted_resource_logical=snapshot.deferred_adjusted_resource_count,
        deferred_ambiguous_logical=snapshot.deferred_ambiguous_count,
        deferred_unsupported_logical=snapshot.deferred_unsupported_count,
        retryable_failed_logical=snapshot.retryable_failed_count,
        last_inventory_scan_at=snapshot.last_inventory_scan_at,
        last_inventory_refresh_at=snapshot.last_inventory_scan_at,
        last_historical_run_at=None if latest_run is None else latest_run.completed_at,
        last_historical_run_id=None if latest_run is None else latest_run.id,
        last_cleanup_run_id=None if latest_cleanup is None else latest_cleanup.id,
        local_staging_file_count=_file_count(staging_root),
        partial_file_count=_file_count(partial_root),
        backfill_execute_file_count=_file_count(backfill_execute_root),
        operator_message=operator_message,
    )


def get_historical_routine_status(
    db_session: Session,
    *,
    source_id: int,
) -> IcloudHistoricalRoutineStatus:
    _ensure_schema(db_session)
    source = _validate_source(db_session, source_id=source_id)
    try:
        snapshot = get_icloud_backfill_status(db_session, source_id=source_id)
    except IcloudBackfillStateNotFound:
        nowless = IcloudBackfillStatusSnapshot(
            source_id=source_id,
            status="not_started",
            last_inventory_scan_at=None,
            last_scan_candidate_count=0,
            last_scan_created_count=0,
            last_scan_updated_count=0,
            inventory_total_count=0,
            eligible_metadata_count=0,
            unsupported_or_ambiguous_count=0,
            backfill_completed_count=0,
            unresolved_eligible_count=0,
            acquirable_pending_count=0,
            retryable_failed_count=0,
            ambiguous_or_unsupported_count=0,
            deferred_current_count=0,
            deferred_adjusted_resource_count=0,
            deferred_ambiguous_count=0,
            deferred_unsupported_count=0,
            deferred_new_since_last_scan_count=0,
            deferred_changed_since_last_scan_count=0,
            source_exhausted=False,
            scan_limit_reached=False,
            stop_reason=None,
        )
        return _status_from_snapshot(nowless, source=source, db_session=db_session)
    return _status_from_snapshot(snapshot, source=source, db_session=db_session)


def get_icloud_intake_import_status(
    db_session: Session,
    *,
    source_id: int,
) -> IcloudIntakeImportStatus:
    _ensure_schema(db_session)
    now = _now_utc()
    _validate_source(db_session, source_id=source_id)
    _recover_stale_import_runs(db_session, source_id=source_id, now=now)
    base = get_historical_routine_status(db_session, source_id=source_id)
    import_run = _latest_import_run(db_session, source_id=source_id)

    chunks: tuple[IcloudIntakeImportChunk, ...] = ()
    chunk_statuses: tuple[IcloudIntakeImportChunkStatus, ...] = ()
    pending_chunk_count = 0
    completed_chunk_count = 0
    resume_available = False
    can_resume = False
    can_advance = False
    current_phase: str | None = None
    last_duration: float | None = None
    last_gap: float | None = None
    import_operator_message = base.operator_message
    import_stop_reason: str | None = None

    if import_run is not None:
        chunks = _import_chunks(db_session, import_run_id=import_run.id)
        chunk_statuses = tuple(_chunk_to_status(chunk) for chunk in chunks)
        pending_chunk_count = sum(
            1
            for chunk in chunks
            if chunk.status in {CHUNK_STATUS_PENDING, CHUNK_STATUS_RETRYABLE_FAILED}
        )
        completed_chunk_count = sum(1 for chunk in chunks if chunk.status == CHUNK_STATUS_COMPLETED)
        running_chunk = next((chunk for chunk in chunks if chunk.status == CHUNK_STATUS_RUNNING), None)
        active_child_exists = _active_child_operation_exists(db_session)
        resume_available = import_run.status in {
            IMPORT_STATUS_RESUME_AVAILABLE,
            IMPORT_STATUS_PAUSED_INTERRUPTED,
        }
        can_resume = resume_available and pending_chunk_count > 0
        can_advance = (
            import_run.status in {IMPORT_STATUS_CREATED, IMPORT_STATUS_RUNNING}
            and pending_chunk_count > 0
            and running_chunk is None
            and not active_child_exists
            and base.local_staging_file_count == 0
        )
        if running_chunk is not None:
            current_phase = f"chunk_{running_chunk.chunk_index}_running"
        elif can_advance:
            current_phase = "waiting_for_next_chunk"
        elif can_resume:
            current_phase = "resume_available"
        elif import_run.status in IMPORT_TERMINAL_STATUSES:
            current_phase = "complete"
        else:
            current_phase = import_run.status
        last_progressed = next(
            (
                chunk
                for chunk in reversed(chunks)
                if chunk.status != CHUNK_STATUS_PENDING
            ),
            None,
        )
        if last_progressed is not None:
            last_duration = last_progressed.chunk_total_seconds
            last_gap = last_progressed.inter_chunk_gap_seconds
        import_operator_message = import_run.operator_message or import_operator_message
        import_stop_reason = import_run.stop_reason

    has_incomplete = import_run is not None and import_run.status in IMPORT_INCOMPLETE_STATUSES
    logical_candidates_ready = base.logical_candidates_ready
    if has_incomplete and import_run is not None:
        logical_candidates_ready = max(
            0,
            int(import_run.logical_candidates_total or 0) - int(import_run.logical_imported or 0),
        )
    can_start = (
        not has_incomplete
        and base.prepare_status == PREPARE_STATUS_PREPARED
        and base.logical_candidates_ready > 0
        and base.local_staging_file_count == 0
    )

    return IcloudIntakeImportStatus(
        source_id=base.source_id,
        source_label=base.source_label,
        total_imported_from_source=base.total_imported_from_source,
        last_inventory_refresh_at=base.last_inventory_refresh_at,
        available_inventory=base.available_inventory,
        logical_candidates_ready=logical_candidates_ready,
        latest_prepare_run_id=base.latest_prepare_run_id,
        prepare_status=base.prepare_status,
        prepare_expires_at=base.prepare_expires_at,
        import_run_id=None if import_run is None else import_run.id,
        import_status=None if import_run is None else import_run.status,
        import_operator_message=import_operator_message,
        import_stop_reason=import_stop_reason,
        target_logical_candidates=base.target_logical_candidates,
        logical_candidates_total=0 if import_run is None else import_run.logical_candidates_total,
        logical_imported=0 if import_run is None else import_run.logical_imported,
        files_resources_imported=0 if import_run is None else import_run.files_resources_imported,
        local_staging_files_cleaned=0 if import_run is None else import_run.local_staging_files_cleaned,
        new_deferred_this_run=0 if import_run is None else import_run.new_deferred_this_run,
        execution_failed_retryable_count=0 if import_run is None else import_run.execution_failed_retryable_count,
        execution_failed_terminal_count=0 if import_run is None else import_run.execution_failed_terminal_count,
        source_intake_failed_count=0 if import_run is None else import_run.source_intake_failed_count,
        cleanup_failed_count=0 if import_run is None else import_run.cleanup_failed_count,
        current_chunk_index=0 if import_run is None else import_run.current_chunk_index,
        total_chunks=0 if import_run is None else import_run.total_chunks,
        internal_batch_size=DEFAULT_INTERNAL_BATCH_SIZE if import_run is None else import_run.internal_batch_size,
        pending_chunk_count=pending_chunk_count,
        completed_chunk_count=completed_chunk_count,
        remaining_logical_candidates=logical_candidates_ready,
        resume_available=resume_available,
        can_start_import=can_start,
        can_resume_import=can_resume,
        can_advance_import=can_advance,
        current_phase=current_phase,
        last_chunk_duration_seconds=last_duration,
        last_inter_chunk_gap_seconds=last_gap,
        started_at=None if import_run is None else import_run.started_at,
        last_progress_at=None if import_run is None else import_run.last_progress_at,
        completed_at=None if import_run is None else import_run.completed_at,
        failed_at=None if import_run is None else import_run.failed_at,
        interrupted_at=None if import_run is None else import_run.interrupted_at,
        resumed_at=None if import_run is None else import_run.resumed_at,
        report_path=None if import_run is None else import_run.report_path,
        local_staging_file_count=base.local_staging_file_count,
        partial_file_count=base.partial_file_count,
        backfill_execute_file_count=base.backfill_execute_file_count,
        chunks=chunk_statuses,
    )


def _scan_depths(max_candidates: int) -> tuple[int, ...]:
    ceiling = max(1, min(int(max_candidates), DEFAULT_PREPARE_SCAN_CEILING))
    depths = [depth for depth in DEFAULT_PREPARE_SCAN_DEPTHS if depth <= ceiling]
    if not depths or depths[-1] != ceiling:
        depths.append(ceiling)
    return tuple(dict.fromkeys(depths))


def _operator_message_for_prepare(
    *,
    logical_candidates_ready: int,
    target_logical_candidates: int,
    source_exhaustion_state: str,
) -> str:
    if logical_candidates_ready >= target_logical_candidates:
        return f"Prepared {logical_candidates_ready} logical candidates for import."
    if logical_candidates_ready > 0 and source_exhaustion_state == "exhausted":
        return f"Prepared {logical_candidates_ready} logical candidates; the source listing was exhausted."
    if logical_candidates_ready > 0:
        return (
            f"Prepared {logical_candidates_ready} logical candidates because the scan depth limit was reached; "
            "deeper inventory may remain."
        )
    if source_exhaustion_state == "exhausted":
        return "No importable iCloud inventory remains; the source listing was exhausted."
    return "No importable candidates were prepared; deeper inventory may remain."


def refresh_historical_inventory(
    db_session: Session,
    *,
    source_id: int,
    max_candidates: int = DEFAULT_PREPARE_SCAN_CEILING,
) -> IcloudHistoricalRefreshResult:
    _ensure_schema(db_session)
    _validate_source(db_session, source_id=source_id)

    target = DEFAULT_TARGET_LOGICAL_ASSETS
    created_total = 0
    updated_total = 0
    new_deferred_total = 0
    last_result: IcloudInventoryScanResult | None = None
    last_depth = 0
    candidates: tuple[IcloudRemoteAssetInventory, ...] = ()

    for depth in _scan_depths(max_candidates):
        last_depth = depth
        result = run_icloud_backfill_inventory_scan(
            db_session,
            source_id=source_id,
            max_candidates=depth,
        )
        last_result = result
        created_total += result.created_count
        updated_total += result.updated_count
        new_deferred_total += result.deferred_new_since_last_scan_count + result.deferred_changed_since_last_scan_count
        candidates = _select_preparable_inventory_rows(db_session, source_id=source_id, limit=target)
        if len(candidates) >= target or result.source_exhausted:
            break

    if last_result is None:
        raise IcloudHistoricalRoutineError("Inventory refresh did not return a scan result.", code="inventory_refresh_failed")

    if last_result.source_exhausted:
        source_exhaustion_state = "exhausted"
    elif len(candidates) >= target:
        source_exhaustion_state = "not_exhausted"
    else:
        source_exhaustion_state = "unknown"

    now = _now_utc()
    expires_at = now + timedelta(minutes=DEFAULT_PREPARE_EXPIRY_MINUTES)
    operator_message = _operator_message_for_prepare(
        logical_candidates_ready=len(candidates),
        target_logical_candidates=target,
        source_exhaustion_state=source_exhaustion_state,
    )
    _supersede_active_prepare_runs(db_session, source_id=source_id, now=now)
    prepare_run = IcloudIntakePrepareRun(
        source_profile_id=source_id,
        status=PREPARE_STATUS_PREPARED,
        target_logical_candidates=target,
        logical_candidates_ready=len(candidates),
        new_deferred_count=new_deferred_total,
        provider_records_scanned=last_result.scanned_count,
        scan_depth_used=last_depth,
        source_exhaustion_state=source_exhaustion_state,
        source_exhausted=last_result.source_exhausted,
        scan_limit_reached=not last_result.source_exhausted and len(candidates) < target,
        prepared_at=now,
        expires_at=expires_at,
        operator_message=operator_message,
        created_at=now,
        updated_at=now,
    )
    db_session.add(prepare_run)
    db_session.flush()
    for index, row in enumerate(candidates, start=1):
        db_session.add(
            IcloudIntakePreparedCandidate(
                prepare_run_id=prepare_run.id,
                source_profile_id=source_id,
                inventory_id=row.id,
                remote_identity=row.remote_identity,
                primary_relative_path=row.primary_relative_path,
                candidate_index=index,
                candidate_state=CANDIDATE_STATE_PREPARED,
                resource_count=int(row.resource_count or 0),
                is_live_photo=bool(row.is_live_photo),
                created_at=now,
                updated_at=now,
            )
        )
    db_session.commit()

    return IcloudHistoricalRefreshResult(
        source_id=source_id,
        status=PREPARE_STATUS_PREPARED,
        prepare_run_id=prepare_run.id,
        inventory_total_logical=last_result.inventory_total_count,
        created_logical=created_total,
        updated_logical=updated_total,
        eligible_pending_logical=last_result.acquirable_pending_count,
        available_inventory=_available_from_prepare(
            logical_candidates_ready=len(candidates),
            source_exhaustion_state=source_exhaustion_state,
        ),
        target_logical_candidates=target,
        logical_candidates_ready=len(candidates),
        new_deferred_this_prepare=new_deferred_total,
        deferred_current_logical=last_result.deferred_current_count,
        deferred_adjusted_resource_logical=last_result.deferred_adjusted_resource_count,
        source_exhausted=last_result.source_exhausted,
        scan_limit_reached=not last_result.source_exhausted and len(candidates) < target,
        source_exhaustion_state=source_exhaustion_state,
        provider_records_scanned=last_result.scanned_count,
        scan_depth_used=last_depth,
        expires_at=expires_at,
        operator_message=operator_message,
        scanned_at=last_result.scanned_at,
        scan_limit_note=(
            "Prepare scans expand deterministically up to the local ceiling. "
            "If the ceiling is reached without provider exhaustion, deeper inventory may remain."
        ),
    )


def _safe_report_paths(report_path: str | None) -> list[str]:
    if not report_path:
        return []
    try:
        report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    rows = report.get("eligible_files")
    if not isinstance(rows, list):
        return []
    paths: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        value = row.get("relative_path")
        if isinstance(value, str) and value.strip():
            paths.append(value.replace("\\", "/").lstrip("/"))
    return sorted(set(paths))


def _paths_match(cleanup: CleanupRunSnapshot, acquired_paths: tuple[str, ...]) -> tuple[bool, str]:
    cleanup_paths = _safe_report_paths(cleanup.report_path)
    acquired = sorted(set(path.replace("\\", "/").lstrip("/") for path in acquired_paths if path.strip()))
    if not cleanup_paths:
        return False, "cleanup dry run had no eligible files"
    if not acquired:
        return False, "acquisition result did not include acquired resource paths"
    if cleanup_paths != acquired:
        unexpected = len([path for path in cleanup_paths if path not in set(acquired)])
        missing = len([path for path in acquired if path not in set(cleanup_paths)])
        return False, f"cleanup candidates did not match acquired resources ({unexpected} unexpected, {missing} missing)"
    if any(".partial" in path.casefold() or "backfill_execute" in path.casefold() for path in cleanup_paths):
        return False, "cleanup candidates included protected workspace paths"
    return True, "cleanup candidates exactly matched acquired resources"


def _wait_for_cleanup(
    db_session: Session,
    *,
    source_id: int,
    run_id: int,
    timeout_seconds: float = DEFAULT_CLEANUP_WAIT_SECONDS,
    poll_seconds: float = DEFAULT_CLEANUP_POLL_SECONDS,
) -> CleanupRunSnapshot:
    deadline = time.monotonic() + timeout_seconds
    latest = get_cleanup_status(db_session, source_id=source_id)
    while latest is not None and latest.run_id == run_id and latest.status in {"pending", "running", "stop_requested"}:
        if time.monotonic() > deadline:
            raise IcloudHistoricalRoutineError("Cleanup did not finish within the routine wait timeout.", code="cleanup_timeout")
        time.sleep(poll_seconds)
        latest = get_cleanup_status(db_session, source_id=source_id)
    if latest is None or latest.run_id != run_id:
        raise IcloudHistoricalRoutineError("Cleanup status could not be resolved.", code="cleanup_status_missing")
    return latest


def _cleanup_chunk(
    db_session: Session,
    *,
    source_id: int,
    acquired_paths: tuple[str, ...],
) -> tuple[CleanupRunSnapshot, CleanupRunSnapshot, str | None]:
    try:
        dry_start = start_cleanup_run(db_session, source_id=source_id, dry_run=True, created_by="historical_icloud_routine")
    except (CleanupBusyError, CleanupValidationError, SourceIntakeActiveError, CleanupAuthorizationError) as exc:
        raise IcloudHistoricalRoutineError(str(exc), code=getattr(exc, "code", "cleanup_dry_run_start_failed")) from exc
    dry = _wait_for_cleanup(db_session, source_id=source_id, run_id=dry_start.run_id)
    if dry.status != "completed":
        raise IcloudHistoricalRoutineError("Cleanup dry run did not complete.", code="cleanup_dry_run_failed")
    if any(
        count != 0
        for count in (
            dry.skipped_count,
            dry.protected_count,
            dry.verification_failed_count,
            dry.file_missing_count,
            dry.delete_failed_count,
        )
    ):
        raise IcloudHistoricalRoutineError("Cleanup dry run had non-zero safety counters.", code="cleanup_safety_counters")
    ok, reason = _paths_match(dry, acquired_paths)
    if not ok:
        raise IcloudHistoricalRoutineError(reason, code="cleanup_exact_match_failed")

    try:
        exec_start = start_cleanup_execution(
            db_session,
            source_id=source_id,
            dry_run_run_id=dry.run_id,
            explicit_confirmation=EXECUTION_CONFIRMATION_PHRASE,
            created_by="historical_icloud_routine",
        )
    except (CleanupBusyError, CleanupValidationError, SourceIntakeActiveError, CleanupAuthorizationError) as exc:
        raise IcloudHistoricalRoutineError(str(exc), code=getattr(exc, "code", "cleanup_execution_start_failed")) from exc
    executed = _wait_for_cleanup(db_session, source_id=source_id, run_id=exec_start.run_id)
    if executed.status != "completed":
        raise IcloudHistoricalRoutineError("Guarded cleanup execution did not complete.", code="cleanup_execution_failed")
    if executed.deleted_count != len(set(acquired_paths)):
        raise IcloudHistoricalRoutineError("Cleanup deleted count did not match acquired resources.", code="cleanup_deleted_count_mismatch")
    return dry, executed, reason


@dataclass(frozen=True)
class _TimedCleanupResult:
    dry_run: CleanupRunSnapshot
    execution: CleanupRunSnapshot
    reason: str
    dry_run_seconds: float
    execute_seconds: float


@dataclass(frozen=True)
class IcloudIntakeCleanupRecoveryResult:
    source_id: int
    import_run_id: int
    chunk_index: int
    acquisition_batch_id: int
    source_intake_run_id: int
    cleanup_dry_run_id: int
    cleanup_execution_run_id: int
    acquired_path_count: int
    deleted_count: int
    reconciled_cleanup_report_count: int
    status: IcloudIntakeImportStatus


@dataclass(frozen=True)
class _FailedAcquisitionStagingDiscard:
    chunk_index: int
    acquisition_batch_id: int
    discarded_count: int
    discarded_bytes: int


class _DurableCleanupError(IcloudHistoricalRoutineError):
    def __init__(
        self,
        message: str,
        *,
        code: str,
        dry_run: CleanupRunSnapshot | None = None,
        execution: CleanupRunSnapshot | None = None,
        dry_run_seconds: float | None = None,
        execute_seconds: float | None = None,
    ) -> None:
        super().__init__(message, code=code)
        self.dry_run = dry_run
        self.execution = execution
        self.dry_run_seconds = dry_run_seconds
        self.execute_seconds = execute_seconds


def _cleanup_chunk_timed(
    db_session: Session,
    *,
    source_id: int,
    acquired_paths: tuple[str, ...],
) -> _TimedCleanupResult:
    dry_start_clock = time.perf_counter()
    try:
        dry_start = start_cleanup_run(db_session, source_id=source_id, dry_run=True, created_by="icloud_intake_import")
    except (CleanupBusyError, CleanupValidationError, SourceIntakeActiveError) as exc:
        raise _DurableCleanupError(str(exc), code=getattr(exc, "code", "cleanup_dry_run_start_failed")) from exc

    dry = _wait_for_cleanup(db_session, source_id=source_id, run_id=dry_start.run_id)
    dry_seconds = time.perf_counter() - dry_start_clock
    if dry.status != "completed":
        raise _DurableCleanupError(
            "Cleanup dry run did not complete.",
            code="cleanup_dry_run_failed",
            dry_run=dry,
            dry_run_seconds=dry_seconds,
        )
    if any(
        count != 0
        for count in (
            dry.skipped_count,
            dry.protected_count,
            dry.verification_failed_count,
            dry.file_missing_count,
            dry.delete_failed_count,
        )
    ):
        raise _DurableCleanupError(
            "Cleanup dry run had non-zero safety counters.",
            code="cleanup_safety_counters",
            dry_run=dry,
            dry_run_seconds=dry_seconds,
        )
    ok, reason = _paths_match(dry, acquired_paths)
    if not ok:
        raise _DurableCleanupError(
            reason,
            code="cleanup_exact_match_failed",
            dry_run=dry,
            dry_run_seconds=dry_seconds,
        )

    exec_start_clock = time.perf_counter()
    try:
        exec_start = start_cleanup_execution(
            db_session,
            source_id=source_id,
            dry_run_run_id=dry.run_id,
            explicit_confirmation=EXECUTION_CONFIRMATION_PHRASE,
            created_by="icloud_intake_import",
        )
    except (CleanupBusyError, CleanupValidationError, SourceIntakeActiveError, CleanupAuthorizationError) as exc:
        raise _DurableCleanupError(
            str(exc),
            code=getattr(exc, "code", "cleanup_execution_start_failed"),
            dry_run=dry,
            dry_run_seconds=dry_seconds,
        ) from exc
    executed = _wait_for_cleanup(db_session, source_id=source_id, run_id=exec_start.run_id)
    exec_seconds = time.perf_counter() - exec_start_clock
    if executed.status != "completed":
        raise _DurableCleanupError(
            "Guarded cleanup execution did not complete.",
            code="cleanup_execution_failed",
            dry_run=dry,
            execution=executed,
            dry_run_seconds=dry_seconds,
            execute_seconds=exec_seconds,
        )
    if executed.deleted_count != len(set(acquired_paths)):
        raise _DurableCleanupError(
            "Cleanup deleted count did not match acquired resources.",
            code="cleanup_deleted_count_mismatch",
            dry_run=dry,
            execution=executed,
            dry_run_seconds=dry_seconds,
            execute_seconds=exec_seconds,
        )
    return _TimedCleanupResult(
        dry_run=dry,
        execution=executed,
        reason=reason,
        dry_run_seconds=dry_seconds,
        execute_seconds=exec_seconds,
    )


def _active_prepare_run(db_session: Session, *, source_id: int) -> IcloudIntakePrepareRun | None:
    now = _now_utc()
    _expire_stale_prepare_runs(db_session, source_id=source_id, now=now)
    run = db_session.scalar(
        select(IcloudIntakePrepareRun)
        .where(
            IcloudIntakePrepareRun.source_profile_id == source_id,
            IcloudIntakePrepareRun.status == PREPARE_STATUS_PREPARED,
            IcloudIntakePrepareRun.consumed_at.is_(None),
        )
        .order_by(IcloudIntakePrepareRun.id.desc())
        .limit(1)
    )
    if run is None:
        return None
    expires_at = _as_utc(run.expires_at)
    if expires_at is not None and expires_at <= now:
        run.status = PREPARE_STATUS_EXPIRED
        run.updated_at = now
        db_session.commit()
        return None
    return run


def _prepared_candidates(
    db_session: Session,
    *,
    prepare_run_id: int,
) -> tuple[IcloudIntakePreparedCandidate, ...]:
    rows = db_session.scalars(
        select(IcloudIntakePreparedCandidate)
        .where(
            IcloudIntakePreparedCandidate.prepare_run_id == prepare_run_id,
            IcloudIntakePreparedCandidate.candidate_state.in_(
                (
                    CANDIDATE_STATE_PREPARED,
                    CANDIDATE_STATE_EXECUTION_FAILED_RETRYABLE,
                )
            ),
        )
        .order_by(IcloudIntakePreparedCandidate.candidate_index.asc())
    ).all()
    return tuple(rows)


def _inventory_rows_by_id(
    db_session: Session,
    *,
    source_id: int,
    inventory_ids: tuple[int, ...],
) -> dict[int, IcloudRemoteAssetInventory]:
    if not inventory_ids:
        return {}
    rows = db_session.scalars(
        select(IcloudRemoteAssetInventory).where(
            IcloudRemoteAssetInventory.source_profile_id == source_id,
            IcloudRemoteAssetInventory.id.in_(inventory_ids),
        )
    ).all()
    return {int(row.id): row for row in rows}


def _validate_prepared_candidates(
    db_session: Session,
    *,
    source_id: int,
    candidates: tuple[IcloudIntakePreparedCandidate, ...],
) -> tuple[bool, str | None]:
    inventory = _inventory_rows_by_id(
        db_session,
        source_id=source_id,
        inventory_ids=tuple(candidate.inventory_id for candidate in candidates),
    )
    now = _now_utc()
    invalid_count = 0
    for candidate in candidates:
        row = inventory.get(int(candidate.inventory_id))
        if row is None or not _is_preparable_inventory_row(row):
            invalid_count += 1
            candidate.candidate_state = CANDIDATE_STATE_SKIPPED_STALE
            candidate.updated_at = now
    if invalid_count:
        db_session.commit()
        return False, f"{invalid_count} prepared candidates are no longer eligible/acquirable."
    return True, None


@dataclass(frozen=True)
class _CandidateStateSummary:
    new_deferred_count: int = 0
    execution_failed_retryable_count: int = 0


def _mark_candidate_states_for_chunk(
    db_session: Session,
    *,
    source_id: int,
    prepare_run_id: int,
    inventory_ids: tuple[int, ...],
) -> _CandidateStateSummary:
    candidates = db_session.scalars(
        select(IcloudIntakePreparedCandidate).where(
            IcloudIntakePreparedCandidate.prepare_run_id == prepare_run_id,
            IcloudIntakePreparedCandidate.inventory_id.in_(inventory_ids),
        )
    ).all()
    by_inventory_id = {int(candidate.inventory_id): candidate for candidate in candidates}
    inventory = _inventory_rows_by_id(db_session, source_id=source_id, inventory_ids=inventory_ids)
    now = _now_utc()
    new_deferred = 0
    execution_failed_retryable = 0
    for inventory_id in inventory_ids:
        candidate = by_inventory_id.get(int(inventory_id))
        row = inventory.get(int(inventory_id))
        if candidate is None:
            continue
        if row is None:
            candidate.candidate_state = CANDIDATE_STATE_SKIPPED_STALE
        elif bool(row.backfill_completed):
            candidate.candidate_state = CANDIDATE_STATE_IMPORTED
        elif (row.acquisition_state or "") == "skipped_stale_retryable" or (row.backfill_resolution_state or "") == "skipped_stale_retryable":
            candidate.candidate_state = CANDIDATE_STATE_SKIPPED_STALE
        elif row.identity_ambiguous or (row.eligibility_state or "") in {
            ELIGIBILITY_AMBIGUOUS_METADATA_ONLY,
            ELIGIBILITY_UNSUPPORTED_METADATA_ONLY,
        }:
            candidate.candidate_state = CANDIDATE_STATE_DEFERRED_AT_EXECUTION
            new_deferred += 1
        elif (row.acquisition_state or "") == "failed_retryable" or (row.backfill_resolution_state or "") == "failed_retryable":
            candidate.candidate_state = CANDIDATE_STATE_EXECUTION_FAILED_RETRYABLE
            execution_failed_retryable += 1
        else:
            candidate.candidate_state = CANDIDATE_STATE_FAILED
        candidate.updated_at = now
    db_session.commit()
    return _CandidateStateSummary(
        new_deferred_count=new_deferred,
        execution_failed_retryable_count=execution_failed_retryable,
    )


def _failed_run_result(
    db_session: Session,
    *,
    source_id: int,
    prepare_run_id: int | None,
    requested_logical_assets: int,
    internal_batch_size: int,
    operator_message: str,
    stop_reason: str,
) -> IcloudHistoricalRunResult:
    final_status = get_historical_routine_status(db_session, source_id=source_id)
    return IcloudHistoricalRunResult(
        source_id=source_id,
        status=RUN_FAILED,
        prepare_run_id=prepare_run_id,
        requested_logical_assets=requested_logical_assets,
        logical_candidates=0,
        internal_batch_size=internal_batch_size,
        imported_logical_assets=0,
        logical_imported=0,
        imported_resources=0,
        files_resources_imported=0,
        cleaned_local_staging_files=0,
        local_staging_files_cleaned=0,
        new_deferred_this_run=0,
        execution_failed_this_run=0,
        eligible_remaining_logical=final_status.eligible_pending_logical,
        deferred_current_logical=final_status.deferred_current_logical,
        deferred_adjusted_resource_logical=final_status.deferred_adjusted_resource_logical,
        available_inventory=final_status.available_inventory,
        operator_message=operator_message,
        stop_reason=stop_reason,
    )


def _prepared_candidates_for_chunk(
    db_session: Session,
    *,
    prepare_run_id: int,
    start_index: int,
    end_index: int,
) -> tuple[IcloudIntakePreparedCandidate, ...]:
    rows = db_session.scalars(
        select(IcloudIntakePreparedCandidate)
        .where(
            IcloudIntakePreparedCandidate.prepare_run_id == prepare_run_id,
            IcloudIntakePreparedCandidate.candidate_index >= start_index,
            IcloudIntakePreparedCandidate.candidate_index <= end_index,
            IcloudIntakePreparedCandidate.candidate_state.in_(
                (
                    CANDIDATE_STATE_PREPARED,
                    CANDIDATE_STATE_EXECUTION_FAILED_RETRYABLE,
                )
            ),
        )
        .order_by(IcloudIntakePreparedCandidate.candidate_index.asc())
    ).all()
    return tuple(rows)


def _acquired_resource_paths_for_batch(
    db_session: Session,
    *,
    acquisition_batch_id: int,
) -> tuple[str, ...]:
    rows = db_session.scalars(
        select(IcloudAcquisitionResource.relative_path)
        .join(IcloudAcquisitionItem, IcloudAcquisitionItem.id == IcloudAcquisitionResource.item_id)
        .where(
            IcloudAcquisitionItem.batch_id == acquisition_batch_id,
            IcloudAcquisitionResource.selected_for_download.is_(True),
        )
        .order_by(IcloudAcquisitionResource.relative_path.asc())
    ).all()
    return tuple(str(path).replace("\\", "/").lstrip("/") for path in rows if str(path).strip())


def _resource_paths_for_batch_status(
    db_session: Session,
    *,
    acquisition_batch_id: int,
    status: str,
) -> tuple[str, ...]:
    rows = db_session.scalars(
        select(IcloudAcquisitionResource.relative_path)
        .join(IcloudAcquisitionItem, IcloudAcquisitionItem.id == IcloudAcquisitionResource.item_id)
        .where(
            IcloudAcquisitionItem.batch_id == acquisition_batch_id,
            IcloudAcquisitionResource.selected_for_download.is_(True),
            IcloudAcquisitionResource.status == status,
        )
        .order_by(IcloudAcquisitionResource.relative_path.asc())
    ).all()
    return tuple(str(path).replace("\\", "/").lstrip("/") for path in rows if str(path).strip())


def _discard_failed_acquisition_staging_for_resume(
    db_session: Session,
    *,
    source: IngestionSource,
    import_run: IcloudIntakeImportRun,
) -> _FailedAcquisitionStagingDiscard | None:
    chunks = [
        chunk
        for chunk in _import_chunks(db_session, import_run_id=import_run.id)
        if chunk.status == CHUNK_STATUS_RETRYABLE_FAILED
        and int(chunk.files_resources_imported or 0) > int(chunk.local_staging_files_cleaned or 0)
        and chunk.source_intake_run_id is None
        and chunk.cleanup_dry_run_id is None
        and chunk.cleanup_execution_run_id is None
    ]
    if not chunks:
        return None
    if len(chunks) != 1:
        raise IcloudHistoricalRoutineError(
            "Multiple retryable failed chunks have local staging files; cleanup review is required.",
            code="failed_acquisition_staging_not_unique",
        )
    chunk = chunks[0]
    if chunk.acquisition_batch_id is None:
        raise IcloudHistoricalRoutineError(
            "Retryable failed chunk is missing acquisition batch evidence.",
            code="failed_acquisition_batch_missing",
        )
    batch = db_session.get(IcloudAcquisitionBatch, chunk.acquisition_batch_id)
    if batch is None or batch.status != "blocked" or batch.source_intake_run_id is not None or batch.batch_ready_for_source_intake:
        raise IcloudHistoricalRoutineError(
            "Retryable failed chunk is not a pre-Source Intake partial acquisition failure.",
            code="failed_acquisition_state_mismatch",
        )
    if (batch.failure_reason or "") != "local_file_error":
        raise IcloudHistoricalRoutineError(
            "Retryable failed chunk has an unsupported failure reason for automatic staging discard.",
            code="failed_acquisition_reason_unsupported",
        )

    published_paths = sorted(set(_resource_paths_for_batch_status(db_session, acquisition_batch_id=batch.id, status="published")))
    failed_paths = sorted(set(_resource_paths_for_batch_status(db_session, acquisition_batch_id=batch.id, status="failed")))
    if not published_paths or len(published_paths) != int(batch.downloaded_resource_count or 0):
        raise IcloudHistoricalRoutineError(
            "Published acquisition resource evidence is incomplete.",
            code="published_resource_evidence_incomplete",
        )

    root = _source_staging_root(source).resolve()
    folder_paths = list(_safe_relative_files(root))
    protected = [path for path in folder_paths if ".partial" in path.casefold() or "backfill_execute" in path.casefold()]
    if protected:
        raise IcloudHistoricalRoutineError(
            "Staging contains protected partial/backfill_execute files; cleanup review is required.",
            code="protected_staging_files_present",
        )
    if folder_paths != published_paths:
        unexpected = len([path for path in folder_paths if path not in set(published_paths)])
        missing = len([path for path in published_paths if path not in set(folder_paths)])
        raise IcloudHistoricalRoutineError(
            f"Staging files do not exactly match failed acquisition published resources ({unexpected} unexpected, {missing} missing).",
            code="failed_acquisition_staging_mismatch",
        )
    if any(path in set(folder_paths) for path in failed_paths):
        raise IcloudHistoricalRoutineError(
            "Failed acquisition resource is present in staging; cleanup review is required.",
            code="failed_resource_present",
        )

    targets: list[Path] = []
    discarded_bytes = 0
    for relative in published_paths:
        target = (root / relative).resolve()
        if not _is_within(target, root) or target.is_symlink() or not target.is_file():
            raise IcloudHistoricalRoutineError(
                "Staging discard target failed final path verification.",
                code="failed_acquisition_discard_path_unsafe",
            )
        discarded_bytes += int(target.stat().st_size)
        targets.append(target)

    for target in targets:
        target.unlink()
    _remove_empty_subdirectories(root)

    chunk.local_staging_files_cleaned = max(int(chunk.local_staging_files_cleaned or 0), len(targets))
    chunk.operator_message = (
        f"Discarded {len(targets)} local staging files from a failed acquisition attempt; retry is available."
    )
    import_run.operator_message = chunk.operator_message
    _refresh_import_run_aggregates(db_session, import_run)
    db_session.commit()
    return _FailedAcquisitionStagingDiscard(
        chunk_index=chunk.chunk_index,
        acquisition_batch_id=batch.id,
        discarded_count=len(targets),
        discarded_bytes=discarded_bytes,
    )


def _apply_cleanup_snapshot_to_chunk(chunk: IcloudIntakeImportChunk, cleanup: CleanupRunSnapshot | None) -> None:
    if cleanup is None:
        return
    chunk.cleanup_eligible_count = int(cleanup.eligible_count or 0)
    chunk.cleanup_skipped_count = int(cleanup.skipped_count or 0)
    chunk.cleanup_protected_count = int(cleanup.protected_count or 0)
    chunk.cleanup_verification_failed_count = int(cleanup.verification_failed_count or 0)
    chunk.cleanup_file_missing_count = int(cleanup.file_missing_count or 0)
    chunk.cleanup_delete_failed_count = int(cleanup.delete_failed_count or 0)
    chunk.cleanup_report_path = cleanup.report_path


def _finalize_import_run_if_done(db_session: Session, import_run: IcloudIntakeImportRun) -> None:
    pending = _pending_import_chunks(db_session, import_run_id=import_run.id)
    if pending:
        return
    now = _now_utc()
    if import_run.logical_imported >= import_run.logical_candidates_total:
        import_run.status = IMPORT_STATUS_COMPLETED
        import_run.operator_message = "iCloud Intake import completed."
    else:
        import_run.status = IMPORT_STATUS_COMPLETED_PARTIAL
        import_run.operator_message = "iCloud Intake import completed partially; see retryable/deferred counts."
    import_run.completed_at = now
    import_run.last_progress_at = now
    prepare_run = db_session.get(IcloudIntakePrepareRun, import_run.prepare_run_id)
    if prepare_run is not None:
        prepare_run.status = PREPARE_STATUS_CONSUMED
        prepare_run.consumed_at = now
        prepare_run.updated_at = now


def _terminal_status_for_chunk_stop(import_run: IcloudIntakeImportRun, *, retryable: bool = False) -> str:
    if retryable:
        return IMPORT_STATUS_RESUME_AVAILABLE
    return IMPORT_STATUS_STOPPED_NEEDS_REVIEW


def start_icloud_intake_import(
    db_session: Session,
    *,
    source_id: int,
    target_logical_assets: int = DEFAULT_TARGET_LOGICAL_ASSETS,
    internal_batch_size: int = DEFAULT_INTERNAL_BATCH_SIZE,
) -> IcloudIntakeImportStatus:
    _ensure_schema(db_session)
    _validate_source(db_session, source_id=source_id)
    if target_logical_assets < 1 or target_logical_assets > DEFAULT_TARGET_LOGICAL_ASSETS:
        raise IcloudHistoricalRoutineError("target_logical_assets must be between 1 and 1000.", code="invalid_target_logical_assets")
    if internal_batch_size < 1 or internal_batch_size > DEFAULT_INTERNAL_BATCH_SIZE:
        raise IcloudHistoricalRoutineError("internal_batch_size must be between 1 and 100.", code="invalid_internal_batch_size")

    existing = _latest_incomplete_import_run(db_session, source_id=source_id)
    if existing is not None:
        return get_icloud_intake_import_status(db_session, source_id=source_id)

    prepare_run = _active_prepare_run(db_session, source_id=source_id)
    if prepare_run is None:
        return get_icloud_intake_import_status(db_session, source_id=source_id)

    candidates = _prepared_candidates(db_session, prepare_run_id=prepare_run.id)
    if not candidates:
        prepare_run.operator_message = "No prepared candidates are available to import. Refresh / Prepare Next 1000 again before importing."
        prepare_run.updated_at = _now_utc()
        db_session.commit()
        return get_icloud_intake_import_status(db_session, source_id=source_id)

    valid, invalid_reason = _validate_prepared_candidates(
        db_session,
        source_id=source_id,
        candidates=candidates,
    )
    if not valid:
        prepare_run.status = PREPARE_STATUS_STALE
        prepare_run.operator_message = f"{invalid_reason} Refresh / Prepare Next 1000 again before importing."
        prepare_run.updated_at = _now_utc()
        db_session.commit()
        return get_icloud_intake_import_status(db_session, source_id=source_id)

    now = _now_utc()
    selected = candidates[:target_logical_assets]
    total_chunks = (len(selected) + internal_batch_size - 1) // internal_batch_size
    import_run = IcloudIntakeImportRun(
        source_profile_id=source_id,
        prepare_run_id=prepare_run.id,
        status=IMPORT_STATUS_CREATED,
        target_logical_candidates=target_logical_assets,
        logical_candidates_total=len(selected),
        current_chunk_index=0,
        total_chunks=total_chunks,
        internal_batch_size=internal_batch_size,
        started_at=now,
        last_progress_at=now,
        operator_message=f"Import run created for {len(selected)} prepared logical candidates.",
        created_at=now,
        updated_at=now,
    )
    db_session.add(import_run)
    db_session.flush()
    for offset in range(0, len(selected), internal_batch_size):
        chunk_candidates = selected[offset : offset + internal_batch_size]
        db_session.add(
            IcloudIntakeImportChunk(
                import_run_id=import_run.id,
                source_profile_id=source_id,
                prepare_run_id=prepare_run.id,
                chunk_index=(offset // internal_batch_size) + 1,
                status=CHUNK_STATUS_PENDING,
                candidate_start_index=chunk_candidates[0].candidate_index,
                candidate_end_index=chunk_candidates[-1].candidate_index,
                logical_candidates=len(chunk_candidates),
                operator_message="Pending.",
                created_at=now,
                updated_at=now,
            )
        )
    prepare_run.status = PREPARE_STATUS_RUNNING
    prepare_run.updated_at = now
    prepare_run.operator_message = "Import run started for the prepared candidate set."
    _write_import_report(db_session, import_run)
    db_session.commit()
    return get_icloud_intake_import_status(db_session, source_id=source_id)


def resume_icloud_intake_import(
    db_session: Session,
    *,
    source_id: int,
    import_run_id: int | None = None,
) -> IcloudIntakeImportStatus:
    _ensure_schema(db_session)
    source = _validate_source(db_session, source_id=source_id)
    run = db_session.get(IcloudIntakeImportRun, import_run_id) if import_run_id is not None else _latest_incomplete_import_run(db_session, source_id=source_id)
    if run is None or run.source_profile_id != source_id:
        return get_icloud_intake_import_status(db_session, source_id=source_id)
    if run.status not in {IMPORT_STATUS_RESUME_AVAILABLE, IMPORT_STATUS_PAUSED_INTERRUPTED, IMPORT_STATUS_CREATED}:
        return get_icloud_intake_import_status(db_session, source_id=source_id)
    discard = _discard_failed_acquisition_staging_for_resume(db_session, source=source, import_run=run)
    now = _now_utc()
    run.status = IMPORT_STATUS_RUNNING
    run.resumed_at = now
    run.last_progress_at = now
    run.operator_message = (
        f"Discarded {discard.discarded_count} local staging files from failed acquisition batch {discard.acquisition_batch_id}. "
        "Resume confirmed. Ready to advance the next pending chunk."
        if discard is not None
        else "Resume confirmed. Ready to advance the next pending chunk."
    )
    run.stop_reason = None
    prepare_run = db_session.get(IcloudIntakePrepareRun, run.prepare_run_id)
    if prepare_run is not None:
        prepare_run.status = PREPARE_STATUS_RUNNING
        prepare_run.updated_at = now
    _write_import_report(db_session, run)
    db_session.commit()
    return get_icloud_intake_import_status(db_session, source_id=source_id)


def advance_icloud_intake_import(
    db_session: Session,
    *,
    source_id: int,
    import_run_id: int | None = None,
    max_listing_candidates: int = DEFAULT_MAX_LISTING_CANDIDATES,
) -> IcloudIntakeImportStatus:
    _ensure_schema(db_session)
    source = _validate_source(db_session, source_id=source_id)
    import_run = db_session.get(IcloudIntakeImportRun, import_run_id) if import_run_id is not None else _latest_incomplete_import_run(db_session, source_id=source_id)
    if import_run is None or import_run.source_profile_id != source_id:
        return get_icloud_intake_import_status(db_session, source_id=source_id)
    if import_run.status == IMPORT_STATUS_CREATED:
        import_run.status = IMPORT_STATUS_RUNNING
        db_session.execute(
            update(IcloudIntakeImportRun)
            .where(IcloudIntakeImportRun.id == import_run.id)
            .values(status=IMPORT_STATUS_RUNNING, updated_at=_now_utc())
        )
        db_session.flush()
    if import_run.status != IMPORT_STATUS_RUNNING:
        return get_icloud_intake_import_status(db_session, source_id=source_id)
    if any(chunk.status == CHUNK_STATUS_RUNNING for chunk in _import_chunks(db_session, import_run_id=import_run.id)):
        return get_icloud_intake_import_status(db_session, source_id=source_id)
    if _active_child_operation_exists(db_session):
        return get_icloud_intake_import_status(db_session, source_id=source_id)
    if _file_count(_source_staging_root(source)) > 0:
        return get_icloud_intake_import_status(db_session, source_id=source_id)

    pending = _pending_import_chunks(db_session, import_run_id=import_run.id)
    if not pending:
        _refresh_import_run_aggregates(db_session, import_run)
        _finalize_import_run_if_done(db_session, import_run)
        _write_import_report(db_session, import_run)
        db_session.commit()
        return get_icloud_intake_import_status(db_session, source_id=source_id)

    chunk = pending[0]
    chunk_start_clock = time.perf_counter()
    now = _now_utc()
    previous = _previous_completed_chunk(db_session, import_run_id=import_run.id, chunk_index=chunk.chunk_index)
    if previous is not None and previous.completed_at is not None:
        previous_completed_at = _as_utc(previous.completed_at)
        if previous_completed_at is not None:
            chunk.inter_chunk_gap_seconds = max(0.0, (now - previous_completed_at).total_seconds())
    chunk.status = CHUNK_STATUS_RUNNING
    chunk.started_at = now
    chunk.failed_at = None
    chunk.stop_reason = None
    chunk.operator_message = "Chunk running."
    import_run.status = IMPORT_STATUS_RUNNING
    import_run.current_chunk_index = chunk.chunk_index
    import_run.last_progress_at = now
    db_session.execute(
        update(IcloudIntakeImportRun)
        .where(IcloudIntakeImportRun.id == import_run.id)
        .values(
            status=IMPORT_STATUS_RUNNING,
            current_chunk_index=chunk.chunk_index,
            last_progress_at=now,
            updated_at=now,
        )
    )
    prepare_run = db_session.get(IcloudIntakePrepareRun, import_run.prepare_run_id)
    if prepare_run is not None:
        prepare_run.status = PREPARE_STATUS_RUNNING
        prepare_run.updated_at = now
    db_session.commit()

    candidate_clock = time.perf_counter()
    candidates = _prepared_candidates_for_chunk(
        db_session,
        prepare_run_id=chunk.prepare_run_id,
        start_index=chunk.candidate_start_index,
        end_index=chunk.candidate_end_index,
    )
    chunk.candidate_load_seconds = time.perf_counter() - candidate_clock
    inventory_ids = tuple(int(candidate.inventory_id) for candidate in candidates)
    if not inventory_ids:
        finished = _now_utc()
        chunk.status = CHUNK_STATUS_SKIPPED
        chunk.completed_at = finished
        chunk.chunk_total_seconds = time.perf_counter() - chunk_start_clock
        chunk.operator_message = "No pending prepared candidates remained for this chunk."
        import_run.last_progress_at = finished
        _refresh_import_run_aggregates(db_session, import_run)
        if import_run.status in {IMPORT_STATUS_CREATED, IMPORT_STATUS_RUNNING}:
            import_run.status = IMPORT_STATUS_RUNNING
        _finalize_import_run_if_done(db_session, import_run)
        _write_import_report(db_session, import_run)
        db_session.commit()
        return get_icloud_intake_import_status(db_session, source_id=source_id)

    acquisition_clock = time.perf_counter()
    acquisition: IcloudBackfillAcquireResult = run_icloud_backfill_acquisition(
        db_session,
        source_id=source_id,
        acquire_limit=len(inventory_ids),
        max_listing_candidates=max_listing_candidates,
        dry_run=False,
        auto_run_source_intake=True,
        include_items=True,
        inventory_ids=inventory_ids,
    )
    acquisition_seconds = time.perf_counter() - acquisition_clock
    chunk.fresh_resolution_seconds = acquisition_seconds
    chunk.download_stage_seconds = acquisition_seconds
    chunk.source_intake_seconds = 0.0
    chunk.timing_note = (
        "Acquisition service does not yet expose separate fresh-resolution, download, "
        "and Source Intake phase timings; acquisition elapsed time is recorded as an approximation."
    )
    chunk.acquisition_run_id = acquisition.acquisition_run_id
    chunk.acquisition_batch_id = acquisition.acquisition_batch_id
    chunk.source_intake_run_id = acquisition.source_intake_run_id

    db_update_clock = time.perf_counter()
    candidate_summary = _mark_candidate_states_for_chunk(
        db_session,
        source_id=source_id,
        prepare_run_id=chunk.prepare_run_id,
        inventory_ids=inventory_ids,
    )
    chunk.new_deferred_this_chunk = candidate_summary.new_deferred_count
    chunk.execution_failed_retryable_count = candidate_summary.execution_failed_retryable_count
    chunk.execution_failed_terminal_count = int(acquisition.failed_terminal_count or 0)
    chunk.logical_imported = int(acquisition.backfill_completed_count or 0)
    chunk.files_resources_imported = int(acquisition.downloaded_resource_count or 0)
    chunk.db_state_update_seconds = time.perf_counter() - db_update_clock

    if acquisition.backfill_completed_count <= 0:
        finished = _now_utc()
        retryable = candidate_summary.execution_failed_retryable_count > 0 and int(acquisition.failed_terminal_count or 0) == 0
        chunk.status = CHUNK_STATUS_RETRYABLE_FAILED if retryable else CHUNK_STATUS_FAILED
        chunk.failed_at = finished
        chunk.chunk_total_seconds = time.perf_counter() - chunk_start_clock
        chunk.stop_reason = acquisition.stop_reason
        chunk.operator_message = "No candidates in this chunk were imported."
        import_run.status = _terminal_status_for_chunk_stop(import_run, retryable=retryable)
        import_run.stop_reason = acquisition.stop_reason
        import_run.operator_message = (
            "Retryable execution failure recorded; resume can retry the prepared chunk."
            if retryable
            else "Import stopped before completing the prepared set."
        )
        if retryable:
            import_run.interrupted_at = finished
            if prepare_run is not None:
                prepare_run.status = PREPARE_STATUS_PREPARED
                prepare_run.updated_at = finished
        else:
            import_run.failed_at = finished
        import_run.last_progress_at = finished
        _refresh_import_run_aggregates(db_session, import_run)
        _write_import_report(db_session, import_run)
        db_session.commit()
        return get_icloud_intake_import_status(db_session, source_id=source_id)

    if not acquisition.source_intake_succeeded:
        finished = _now_utc()
        chunk.status = CHUNK_STATUS_STOPPED_NEEDS_REVIEW
        chunk.failed_at = finished
        chunk.source_intake_failed_count = 1
        chunk.chunk_total_seconds = time.perf_counter() - chunk_start_clock
        chunk.stop_reason = acquisition.stop_reason
        chunk.operator_message = "Source Intake did not complete successfully."
        import_run.status = IMPORT_STATUS_STOPPED_NEEDS_REVIEW
        import_run.stop_reason = acquisition.stop_reason
        import_run.operator_message = "Import stopped for review. Reason: Source Intake did not complete successfully."
        import_run.failed_at = finished
        import_run.last_progress_at = finished
        _refresh_import_run_aggregates(db_session, import_run)
        _write_import_report(db_session, import_run)
        db_session.commit()
        return get_icloud_intake_import_status(db_session, source_id=source_id)

    try:
        cleanup = _cleanup_chunk_timed(
            db_session,
            source_id=source_id,
            acquired_paths=acquisition.acquired_resource_paths,
        )
    except _DurableCleanupError as exc:
        finished = _now_utc()
        chunk.status = CHUNK_STATUS_STOPPED_NEEDS_REVIEW
        chunk.failed_at = finished
        chunk.cleanup_failed_count = 1
        chunk.cleanup_dry_run_id = None if exc.dry_run is None else exc.dry_run.run_id
        chunk.cleanup_execution_run_id = None if exc.execution is None else exc.execution.run_id
        chunk.cleanup_dry_run_seconds = exc.dry_run_seconds
        chunk.cleanup_execute_seconds = exc.execute_seconds
        _apply_cleanup_snapshot_to_chunk(chunk, exc.execution or exc.dry_run)
        chunk.chunk_total_seconds = time.perf_counter() - chunk_start_clock
        chunk.stop_reason = exc.code
        chunk.operator_message = str(exc)
        import_run.status = IMPORT_STATUS_STOPPED_NEEDS_REVIEW
        import_run.stop_reason = exc.code
        import_run.operator_message = f"Import stopped for review. Reason: {exc}"
        import_run.failed_at = finished
        import_run.last_progress_at = finished
        _refresh_import_run_aggregates(db_session, import_run)
        _write_import_report(db_session, import_run)
        db_session.commit()
        return get_icloud_intake_import_status(db_session, source_id=source_id)

    finished = _now_utc()
    chunk.status = CHUNK_STATUS_COMPLETED
    chunk.completed_at = finished
    chunk.cleanup_dry_run_id = cleanup.dry_run.run_id
    chunk.cleanup_execution_run_id = cleanup.execution.run_id
    chunk.local_staging_files_cleaned = int(cleanup.execution.deleted_count or 0)
    chunk.cleanup_dry_run_seconds = cleanup.dry_run_seconds
    chunk.cleanup_execute_seconds = cleanup.execute_seconds
    _apply_cleanup_snapshot_to_chunk(chunk, cleanup.dry_run)
    chunk.cleanup_report_path = cleanup.execution.report_path
    chunk.chunk_total_seconds = time.perf_counter() - chunk_start_clock
    chunk.operator_message = cleanup.reason or "Chunk completed."
    chunk.stop_reason = None
    import_run.last_progress_at = finished
    import_run.operator_message = f"Chunk {chunk.chunk_index} of {import_run.total_chunks} completed."
    _refresh_import_run_aggregates(db_session, import_run)
    if import_run.status in {IMPORT_STATUS_CREATED, IMPORT_STATUS_RUNNING}:
        import_run.status = IMPORT_STATUS_RUNNING
    _finalize_import_run_if_done(db_session, import_run)
    _write_import_report(db_session, import_run)
    db_session.commit()
    return get_icloud_intake_import_status(db_session, source_id=source_id)


def recover_icloud_intake_import_cleanup(
    db_session: Session,
    *,
    source_id: int,
    import_run_id: int | None = None,
) -> IcloudIntakeCleanupRecoveryResult:
    _ensure_schema(db_session)
    _validate_source(db_session, source_id=source_id)
    reconciled = reconcile_completed_cleanup_reports(db_session, source_id=source_id)

    import_run = db_session.get(IcloudIntakeImportRun, import_run_id) if import_run_id is not None else _latest_incomplete_import_run(db_session, source_id=source_id)
    if import_run is None or import_run.source_profile_id != source_id:
        raise IcloudHistoricalRoutineError("No incomplete iCloud Intake import run is available for cleanup recovery.", code="import_run_not_found")
    if import_run.status != IMPORT_STATUS_RUNNING:
        raise IcloudHistoricalRoutineError("Cleanup recovery requires a running iCloud Intake import run.", code="import_run_not_running")

    running_chunks = [
        chunk
        for chunk in _import_chunks(db_session, import_run_id=import_run.id)
        if chunk.status == CHUNK_STATUS_RUNNING
    ]
    if len(running_chunks) != 1:
        raise IcloudHistoricalRoutineError("Cleanup recovery requires exactly one running import chunk.", code="running_chunk_not_unique")
    chunk = running_chunks[0]
    if int(chunk.files_resources_imported or 0) <= int(chunk.local_staging_files_cleaned or 0):
        raise IcloudHistoricalRoutineError("Running chunk does not have imported resources awaiting cleanup.", code="no_cleanup_gap")
    if chunk.acquisition_batch_id is None or chunk.source_intake_run_id is None:
        raise IcloudHistoricalRoutineError("Running chunk is missing acquisition or Source Intake evidence.", code="cleanup_recovery_evidence_missing")

    source_intake = db_session.get(SourceIntakeRun, chunk.source_intake_run_id)
    if source_intake is None or source_intake.status != "completed":
        raise IcloudHistoricalRoutineError("Source Intake is not completed for the running chunk.", code="source_intake_not_completed")

    acquired_paths = _acquired_resource_paths_for_batch(db_session, acquisition_batch_id=chunk.acquisition_batch_id)
    if not acquired_paths:
        raise IcloudHistoricalRoutineError("Acquisition batch did not expose acquired resource paths.", code="acquired_paths_missing")
    if len(set(acquired_paths)) != int(chunk.files_resources_imported or 0):
        raise IcloudHistoricalRoutineError("Acquired resource path count does not match the running chunk.", code="acquired_path_count_mismatch")

    try:
        cleanup = _cleanup_chunk_timed(
            db_session,
            source_id=source_id,
            acquired_paths=acquired_paths,
        )
    except _DurableCleanupError as exc:
        finished = _now_utc()
        chunk.status = CHUNK_STATUS_STOPPED_NEEDS_REVIEW
        chunk.failed_at = finished
        chunk.cleanup_failed_count = max(int(chunk.cleanup_failed_count or 0), 1)
        chunk.cleanup_dry_run_id = None if exc.dry_run is None else exc.dry_run.run_id
        chunk.cleanup_execution_run_id = None if exc.execution is None else exc.execution.run_id
        chunk.cleanup_dry_run_seconds = exc.dry_run_seconds
        chunk.cleanup_execute_seconds = exc.execute_seconds
        _apply_cleanup_snapshot_to_chunk(chunk, exc.execution or exc.dry_run)
        chunk.stop_reason = exc.code
        chunk.operator_message = str(exc)
        import_run.status = IMPORT_STATUS_STOPPED_NEEDS_REVIEW
        import_run.stop_reason = exc.code
        import_run.operator_message = f"Cleanup recovery stopped for review. Reason: {exc}"
        import_run.failed_at = finished
        import_run.last_progress_at = finished
        _refresh_import_run_aggregates(db_session, import_run)
        _write_import_report(db_session, import_run)
        db_session.commit()
        raise

    finished = _now_utc()
    chunk.status = CHUNK_STATUS_COMPLETED
    chunk.completed_at = finished
    chunk.failed_at = None
    chunk.cleanup_failed_count = 0
    chunk.cleanup_dry_run_id = cleanup.dry_run.run_id
    chunk.cleanup_execution_run_id = cleanup.execution.run_id
    chunk.local_staging_files_cleaned = int(cleanup.execution.deleted_count or 0)
    chunk.cleanup_dry_run_seconds = cleanup.dry_run_seconds
    chunk.cleanup_execute_seconds = cleanup.execute_seconds
    _apply_cleanup_snapshot_to_chunk(chunk, cleanup.dry_run)
    chunk.cleanup_report_path = cleanup.execution.report_path
    if chunk.started_at is not None:
        chunk.chunk_total_seconds = max(0.0, (finished - _as_utc(chunk.started_at)).total_seconds())
    chunk.operator_message = cleanup.reason or "Recovered cleanup completed."
    chunk.stop_reason = None
    import_run.last_progress_at = finished
    import_run.operator_message = f"Recovered cleanup for chunk {chunk.chunk_index} of {import_run.total_chunks}."
    import_run.stop_reason = None
    import_run.failed_at = None
    _refresh_import_run_aggregates(db_session, import_run)
    _finalize_import_run_if_done(db_session, import_run)
    _write_import_report(db_session, import_run)
    db_session.commit()
    status = get_icloud_intake_import_status(db_session, source_id=source_id)
    return IcloudIntakeCleanupRecoveryResult(
        source_id=source_id,
        import_run_id=import_run.id,
        chunk_index=chunk.chunk_index,
        acquisition_batch_id=chunk.acquisition_batch_id,
        source_intake_run_id=chunk.source_intake_run_id,
        cleanup_dry_run_id=cleanup.dry_run.run_id,
        cleanup_execution_run_id=cleanup.execution.run_id,
        acquired_path_count=len(set(acquired_paths)),
        deleted_count=int(cleanup.execution.deleted_count or 0),
        reconciled_cleanup_report_count=reconciled,
        status=status,
    )


def run_next_historical_batch(
    db_session: Session,
    *,
    source_id: int,
    target_logical_assets: int = DEFAULT_TARGET_LOGICAL_ASSETS,
    internal_batch_size: int = DEFAULT_INTERNAL_BATCH_SIZE,
    max_listing_candidates: int = DEFAULT_MAX_LISTING_CANDIDATES,
) -> IcloudHistoricalRunResult:
    _ensure_schema(db_session)
    _validate_source(db_session, source_id=source_id)
    if target_logical_assets < 1 or target_logical_assets > DEFAULT_TARGET_LOGICAL_ASSETS:
        raise IcloudHistoricalRoutineError("target_logical_assets must be between 1 and 1000.", code="invalid_target_logical_assets")
    if internal_batch_size < 1 or internal_batch_size > DEFAULT_INTERNAL_BATCH_SIZE:
        raise IcloudHistoricalRoutineError("internal_batch_size must be between 1 and 100.", code="invalid_internal_batch_size")

    prepare_run = _active_prepare_run(db_session, source_id=source_id)
    if prepare_run is None:
        return _failed_run_result(
            db_session,
            source_id=source_id,
            prepare_run_id=None,
            requested_logical_assets=target_logical_assets,
            internal_batch_size=internal_batch_size,
            operator_message="Refresh / Prepare Next 1000 again before importing.",
            stop_reason="fresh_prepare_required",
        )

    candidates = _prepared_candidates(db_session, prepare_run_id=prepare_run.id)
    if not candidates:
        return _failed_run_result(
            db_session,
            source_id=source_id,
            prepare_run_id=prepare_run.id,
            requested_logical_assets=0,
            internal_batch_size=internal_batch_size,
            operator_message="No prepared candidates are available to import. Refresh / Prepare Next 1000 again before importing.",
            stop_reason="no_prepared_candidates",
        )

    valid, invalid_reason = _validate_prepared_candidates(
        db_session,
        source_id=source_id,
        candidates=candidates,
    )
    if not valid:
        prepare_run.status = PREPARE_STATUS_STALE
        prepare_run.updated_at = _now_utc()
        db_session.commit()
        return _failed_run_result(
            db_session,
            source_id=source_id,
            prepare_run_id=prepare_run.id,
            requested_logical_assets=len(candidates),
            internal_batch_size=internal_batch_size,
            operator_message=f"{invalid_reason} Refresh / Prepare Next 1000 again before importing.",
            stop_reason="prepared_candidates_stale",
        )

    now = _now_utc()
    prepare_run.status = PREPARE_STATUS_RUNNING
    prepare_run.updated_at = now
    db_session.commit()

    inventory_ids = tuple(int(candidate.inventory_id) for candidate in candidates)
    chunks: list[IcloudHistoricalRoutineChunk] = []
    imported_logical = 0
    imported_resources = 0
    cleaned_files = 0
    new_deferred_this_run = 0
    execution_failed_this_run = 0
    stop_reason: str | None = None
    status = RUN_COMPLETED_TARGET
    operator_message = "iCloud Intake import completed."

    for offset in range(0, len(inventory_ids), internal_batch_size):
        chunk_ids = inventory_ids[offset : offset + internal_batch_size]
        chunk_index = len(chunks) + 1
        acquisition: IcloudBackfillAcquireResult = run_icloud_backfill_acquisition(
            db_session,
            source_id=source_id,
            acquire_limit=len(chunk_ids),
            max_listing_candidates=max_listing_candidates,
            dry_run=False,
            auto_run_source_intake=True,
            include_items=True,
            inventory_ids=chunk_ids,
        )
        candidate_summary = _mark_candidate_states_for_chunk(
            db_session,
            source_id=source_id,
            prepare_run_id=prepare_run.id,
            inventory_ids=chunk_ids,
        )
        new_deferred_this_run += candidate_summary.new_deferred_count
        execution_failed_this_run += candidate_summary.execution_failed_retryable_count

        if acquisition.backfill_completed_count <= 0:
            chunks.append(
                IcloudHistoricalRoutineChunk(
                    chunk_index=chunk_index,
                    requested_logical_assets=len(chunk_ids),
                    imported_logical_assets=0,
                    imported_resources=0,
                    cleaned_local_staging_files=0,
                    acquisition_run_id=acquisition.acquisition_run_id,
                    acquisition_batch_id=acquisition.acquisition_batch_id,
                    source_intake_run_id=acquisition.source_intake_run_id,
                    cleanup_dry_run_id=None,
                    cleanup_execution_run_id=None,
                    cleanup_report_path=None,
                    status=acquisition.status,
                    stop_reason=acquisition.stop_reason,
                    operator_message="No candidates in this chunk were imported.",
                )
            )
            if acquisition.stop_reason not in {"no_safe_inventory_selections", "no_eligible_inventory_rows"}:
                status = RUN_FAILED if imported_logical == 0 else RUN_STOPPED_NEEDS_REVIEW
                stop_reason = acquisition.stop_reason
                operator_message = "Import stopped before completing the prepared set."
                break
            continue

        if not acquisition.source_intake_succeeded:
            status = RUN_STOPPED_NEEDS_REVIEW
            stop_reason = acquisition.stop_reason
            operator_message = "Import stopped for review. Reason: Source Intake did not complete successfully."
            chunks.append(
                IcloudHistoricalRoutineChunk(
                    chunk_index=chunk_index,
                    requested_logical_assets=len(chunk_ids),
                    imported_logical_assets=acquisition.backfill_completed_count,
                    imported_resources=acquisition.downloaded_resource_count,
                    cleaned_local_staging_files=0,
                    acquisition_run_id=acquisition.acquisition_run_id,
                    acquisition_batch_id=acquisition.acquisition_batch_id,
                    source_intake_run_id=acquisition.source_intake_run_id,
                    cleanup_dry_run_id=None,
                    cleanup_execution_run_id=None,
                    cleanup_report_path=None,
                    status=status,
                    stop_reason=acquisition.stop_reason,
                    operator_message=operator_message,
                )
            )
            imported_logical += acquisition.backfill_completed_count
            imported_resources += acquisition.downloaded_resource_count
            break

        try:
            dry, executed, cleanup_reason = _cleanup_chunk(
                db_session,
                source_id=source_id,
                acquired_paths=acquisition.acquired_resource_paths,
            )
        except IcloudHistoricalRoutineError as exc:
            status = RUN_STOPPED_NEEDS_REVIEW
            stop_reason = exc.code
            operator_message = f"Import stopped for review. Reason: {exc}"
            chunks.append(
                IcloudHistoricalRoutineChunk(
                    chunk_index=chunk_index,
                    requested_logical_assets=len(chunk_ids),
                    imported_logical_assets=acquisition.backfill_completed_count,
                    imported_resources=acquisition.downloaded_resource_count,
                    cleaned_local_staging_files=0,
                    acquisition_run_id=acquisition.acquisition_run_id,
                    acquisition_batch_id=acquisition.acquisition_batch_id,
                    source_intake_run_id=acquisition.source_intake_run_id,
                    cleanup_dry_run_id=None,
                    cleanup_execution_run_id=None,
                    cleanup_report_path=None,
                    status=status,
                    stop_reason=exc.code,
                    operator_message=operator_message,
                )
            )
            imported_logical += acquisition.backfill_completed_count
            imported_resources += acquisition.downloaded_resource_count
            break

        imported_logical += acquisition.backfill_completed_count
        imported_resources += acquisition.downloaded_resource_count
        cleaned_files += executed.deleted_count
        chunks.append(
            IcloudHistoricalRoutineChunk(
                chunk_index=chunk_index,
                requested_logical_assets=len(chunk_ids),
                imported_logical_assets=acquisition.backfill_completed_count,
                imported_resources=acquisition.downloaded_resource_count,
                cleaned_local_staging_files=executed.deleted_count,
                acquisition_run_id=acquisition.acquisition_run_id,
                acquisition_batch_id=acquisition.acquisition_batch_id,
                source_intake_run_id=acquisition.source_intake_run_id,
                cleanup_dry_run_id=dry.run_id,
                cleanup_execution_run_id=executed.run_id,
                cleanup_report_path=executed.report_path,
                status="completed",
                stop_reason=None,
                operator_message=cleanup_reason or "Chunk completed.",
            )
        )

    if status == RUN_COMPLETED_TARGET and imported_logical < len(inventory_ids):
        status = RUN_COMPLETED_EXHAUSTED if imported_logical == 0 and prepare_run.source_exhaustion_state == "exhausted" else RUN_COMPLETED_PARTIAL_SCAN_BOUND
        operator_message = "iCloud Intake imported fewer logical items than prepared; see run summary for skipped/deferred candidates."
    elif status == RUN_COMPLETED_TARGET:
        operator_message = "iCloud Intake import completed."

    finished_at = _now_utc()
    if imported_logical == 0 and status == RUN_FAILED:
        prepare_run.status = PREPARE_STATUS_PREPARED
        prepare_run.consumed_at = None
        prepare_run.operator_message = "Import failed before any candidates were imported. The prepared set remains available for retry."
    else:
        prepare_run.status = PREPARE_STATUS_CONSUMED
        prepare_run.consumed_at = finished_at
    prepare_run.updated_at = finished_at
    db_session.commit()

    final_status = get_historical_routine_status(db_session, source_id=source_id)

    return IcloudHistoricalRunResult(
        source_id=source_id,
        status=status,
        prepare_run_id=prepare_run.id,
        requested_logical_assets=len(inventory_ids),
        logical_candidates=len(inventory_ids),
        internal_batch_size=internal_batch_size,
        imported_logical_assets=imported_logical,
        logical_imported=imported_logical,
        imported_resources=imported_resources,
        files_resources_imported=imported_resources,
        cleaned_local_staging_files=cleaned_files,
        local_staging_files_cleaned=cleaned_files,
        new_deferred_this_run=new_deferred_this_run,
        execution_failed_this_run=execution_failed_this_run,
        eligible_remaining_logical=final_status.eligible_pending_logical,
        deferred_current_logical=final_status.deferred_current_logical,
        deferred_adjusted_resource_logical=final_status.deferred_adjusted_resource_logical,
        available_inventory=final_status.available_inventory,
        operator_message=operator_message,
        stop_reason=stop_reason,
        chunks=tuple(chunks),
    )
