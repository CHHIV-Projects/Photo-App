"""Operator-level iCloud intake routine for prepared historical backfill batches."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import time

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.icloud_acquisition_run import IcloudAcquisitionRun
from app.models.icloud_backfill import IcloudRemoteAssetInventory
from app.models.icloud_intake_prepare import IcloudIntakePreparedCandidate, IcloudIntakePrepareRun
from app.models.icloud_staging_cleanup_run import IcloudStagingCleanupRun
from app.models.ingestion_source import IngestionSource
from app.services.admin.icloud_staging_cleanup_execution_service import (
    EXECUTION_CONFIRMATION_PHRASE,
    CleanupAuthorizationError,
    CleanupBusyError,
    CleanupRunSnapshot,
    CleanupValidationError,
    SourceIntakeActiveError,
    get_cleanup_status,
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


def _file_count(root: Path) -> int:
    if not root.exists() or not root.is_dir():
        return 0
    return sum(1 for path in root.rglob("*") if path.is_file())


def _source_staging_root(source: IngestionSource) -> Path:
    raw = (source.managed_staging_path or source.source_root_path or "").strip()
    return Path(raw) if raw else resolve_icloud_staging_path(source.source_label or f"source_{source.id}")


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
