"""Internal iCloud exact-selection multi-batch orchestration.

This module intentionally exposes no normal API or UI route. It coordinates the
already-tested exact-selection acquisition, batch Source Intake handoff, and
guarded cleanup services for bounded operator validation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import time
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.asset import Asset
from app.models.icloud_acquisition_run import (
    IcloudAcquisitionBatch,
    IcloudAcquisitionResource,
)
from app.models.icloud_orchestration_run import (
    IcloudOrchestrationBatch,
    IcloudOrchestrationRun,
)
from app.models.ingestion_source import IngestionSource
from app.models.provenance import Provenance
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
from app.services.admin.ingestion_operation_guardrail_service import (
    get_ingestion_operation_guardrail_snapshot,
    protected_ingestion_operation_start,
)
from app.services.icloud_acquisition.batch_source_intake_service import (
    RESOURCE_SUCCESS_STATUSES,
    STATUS_BATCH_INTAKE_COMPLETED,
    BatchSourceIntakeError,
    BatchSourceIntakeResult,
    run_batch_source_intake,
)
from app.services.icloud_acquisition.durable_exact_service import (
    STATUS_BATCH_READY_FOR_SOURCE_INTAKE,
    STATUS_RESOURCE_PUBLISHED,
    DurableExactAcquisitionError,
    DurableExactRunResult,
    run_durable_exact_selection_batch,
)
from app.services.icloud_acquisition.exact_selection_adapter import (
    PREPARATION_FAILED,
    PREPARATION_READY,
    ExactSelectionHelperClient,
    ExactSelectionPreparation,
    ExactSelectionPrototypeError,
    count_partial_workspace_files,
    find_staged_unknown_resources,
    is_ordinary_still_logical_item,
    prepare_exact_selection_prototype,
    validate_exact_selection_profile,
)
from app.services.icloud_acquisition.exact_selection_protocol import AUTHENTICATED
from app.services.icloud_acquisition.new_count_planner import (
    MAX_CANDIDATE_SCAN_LIMIT,
    MAX_TARGET_NEW_ITEM_COUNT,
    STOP_NO_MORE_CANDIDATES,
    STOP_SCAN_LIMIT_REACHED,
    STOP_TARGET_NEW_COUNT_REACHED,
)
from app.services.icloud_acquisition.orchestration_schema import ensure_icloud_orchestration_schema
from app.services.icloud_acquisition.schema import ensure_icloud_acquisition_schema
from app.services.ingestion.pipeline_orchestrator import resolve_runtime_path


STATUS_CREATED = "created"
STATUS_RUNNING = "running"
STATUS_PAUSED_FOR_CLEANUP = "paused_for_cleanup"
STATUS_COMPLETED = "completed"
STATUS_BLOCKED = "blocked"
STATUS_FAILED = "failed"

BATCH_STATUS_PLANNED = "planned"
BATCH_STATUS_ACQUIRED = "acquired"
BATCH_STATUS_INTAKED = "source_intake_completed"
BATCH_STATUS_CLEANUP_DRY_RUN_COMPLETED = "cleanup_dry_run_completed"
BATCH_STATUS_CLEANUP_REVIEW_REQUIRED = "cleanup_review_required"
BATCH_STATUS_CLEANED = "cleanup_executed"
BATCH_STATUS_COMPLETED = "completed"
BATCH_STATUS_BLOCKED = "blocked"
BATCH_STATUS_FAILED = "failed"

NEXT_RUN_SOURCE_INTAKE = "Run batch Source Intake"
NEXT_CONTINUE_CLEANUP = "Review cleanup dry run, then continue cleanup with explicit confirmation"
NEXT_ADD_NEW_ITEMS_OR_INCREASE_SEARCH_CAP = "Add new ordinary stills or get approval for a larger candidate search cap"
NEXT_OPERATOR_DECISION_PARTIAL = "Operator decision required before acquiring a partial batch"
NEXT_RESOLVE_STAGING = "Resolve staging state before retrying"
NEXT_RESOLVE_DROP_ZONE = "Clear or process the Drop Zone before retrying"
NEXT_INSPECT_REPORT = "Inspect orchestration report"
NEXT_COMPLETE = "No further action required"
NEXT_FRESH_CLEANUP_PREVIEW = (
    "Run a fresh guarded cleanup dry run for this source, then continue cleanup with the new dry-run ID."
)

STOP_REASON_CLEANUP_PREVIEW_EXPIRED = "cleanup_preview_expired"
STOP_REASON_CLEANUP_PREVIEW_ALREADY_CONSUMED = "cleanup_preview_already_consumed"
STOP_REASON_CLEANUP_STATE_AMBIGUOUS = "cleanup_state_ambiguous"

_RECOVERABLE_CLEANUP_ERROR_CODES: dict[str, str] = {
    "DRY_RUN_EXPIRED": STOP_REASON_CLEANUP_PREVIEW_EXPIRED,
    "DRY_RUN_ALREADY_CONSUMED": STOP_REASON_CLEANUP_PREVIEW_ALREADY_CONSUMED,
}

_RECOVERY_STOP_REASONS = {
    STOP_REASON_CLEANUP_PREVIEW_EXPIRED,
    STOP_REASON_CLEANUP_PREVIEW_ALREADY_CONSUMED,
    STOP_REASON_CLEANUP_STATE_AMBIGUOUS,
}

REPORT_TYPE = "icloud_internal_multibatch_loop"
DEFAULT_CLEANUP_WAIT_TIMEOUT_SECONDS = 60.0
DEFAULT_CLEANUP_POLL_SECONDS = 0.05

_FORBIDDEN_REPORT_TERMS = (
    "password",
    "2fa",
    "two_factor",
    "cookie",
    "session",
    "token",
    "download_url",
    "remote_id",
    "raw_remote",
)


class IcloudInternalLoopError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        next_safe_action: str | None = NEXT_INSPECT_REPORT,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.next_safe_action = next_safe_action


@dataclass(frozen=True)
class IcloudLoopPlanSummary:
    status: str
    stop_reason: str | None
    next_safe_action: str | None
    execution_safe_to_attempt: bool
    batch_target: int
    logical_candidates_considered: int = 0
    resource_candidates_considered: int = 0
    known_logical_items: int = 0
    known_resources: int = 0
    unknown_logical_items: int = 0
    unknown_resources: int = 0
    selected_logical_items: int = 0
    selected_resources: int = 0
    unsupported_or_blocked_count: int = 0
    selected_unsupported_or_blocked_count: int = 0
    safe_but_not_selected_logical_items: int = 0
    batch_target_filled: bool = False
    partial_batch_selected: bool = False
    operator_decision_required: bool = False
    candidate_search_cap_reached: bool = False
    auth_state: str | None = None


@dataclass(frozen=True)
class IcloudInternalLoopResult:
    orchestration_run_id: int | None
    source_profile_id: int | None
    status: str
    stop_reason: str | None
    failure_reason: str | None
    next_safe_action: str | None
    report_path: str | None
    completed_logical_items: int = 0
    completed_resources: int = 0
    attempted_batches: int = 0
    completed_batches: int = 0
    failed_batches: int = 0
    current_batch_index: int = 0
    cleanup_dry_run_id: int | None = None
    cleanup_execution_run_id: int | None = None
    batches: list[dict[str, Any]] | None = None
    batch_size: int | None = None
    total_limit: int | None = None
    candidate_search_cap: int | None = None
    scan_limit_meaning: str = "candidate_search_cap"
    candidate_page_size: int | None = None
    candidate_page_size_status: str = "deferred"
    total_candidates_considered: int | None = None
    total_resource_candidates_considered: int | None = None
    acquisition_run_ids: list[int] | None = None
    acquisition_batch_ids: list[int] | None = None
    source_intake_run_ids: list[int] | None = None
    ingestion_run_ids: list[int] | None = None
    cleanup_dry_run_ids: list[int] | None = None
    cleanup_execution_run_ids: list[int] | None = None
    final_cleanup_verification_ids: list[int] | None = None
    staging_clean: bool | None = None
    drop_zone_clean: bool | None = None
    partial_workspace_clear: bool | None = None
    cleanup_review_required: bool = False
    cleanup_recovery_required: bool = False
    original_cleanup_error_code: str | None = None
    stale_cleanup_dry_run_id: int | None = None
    continue_cleanup_command_template: str | None = None
    fresh_cleanup_preview_command: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _report_directory() -> Path:
    report_root = resolve_runtime_path("../storage/logs/icloud_internal_loop_reports")
    report_root.mkdir(parents=True, exist_ok=True)
    return report_root


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _normal_staging_files(staging_root: Path) -> list[Path]:
    if not staging_root.exists():
        return []
    files: list[Path] = []
    for path in sorted(staging_root.rglob("*"), key=lambda value: str(value).casefold()):
        if not path.is_file():
            continue
        relative_parts = [part.casefold() for part in path.relative_to(staging_root).parts]
        if ".partial" in relative_parts or any(part.endswith(".partial") for part in relative_parts):
            continue
        files.append(path)
    return files


def _drop_zone_file_count() -> int:
    drop_zone = resolve_runtime_path(settings.drop_zone_path)
    if not drop_zone.exists():
        return 0
    return sum(1 for path in drop_zone.rglob("*") if path.is_file())


def _continue_cleanup_command_template(*, orchestration_run_id: int, cleanup_dry_run_id: str | int) -> str:
    return "\n".join(
        (
            "$env:PYTHONPATH='backend'",
            "& '.\\.venv\\Scripts\\python.exe' '.\\backend\\scripts\\run_icloud_internal_loop.py' `",
            "  --continue-cleanup `",
            f"  --orchestration-run-id {orchestration_run_id} `",
            f"  --cleanup-dry-run-id {cleanup_dry_run_id} `",
            f"  --confirm '{EXECUTION_CONFIRMATION_PHRASE}'",
        )
    )


def _fresh_cleanup_preview_command(*, source_id: int) -> str:
    return "\n".join(
        (
            "Invoke-RestMethod `",
            "  -Method Post `",
            "  -Uri 'http://127.0.0.1:8001/api/admin/icloud-staging-cleanup/run' `",
            "  -ContentType 'application/json' `",
            f"  -Body '{{\"source_id\": {source_id}, \"dry_run\": true}}'",
        )
    )


def _staging_state_payload(db_session: Session, *, source_id: int) -> dict[str, Any]:
    try:
        profile = validate_exact_selection_profile(db_session, source_id=source_id)
        partial_count = count_partial_workspace_files(profile)
        normal_files = _normal_staging_files(profile.staging_root)
        staged_unknown = find_staged_unknown_resources(db_session, profile=profile)
        drop_zone_count = _drop_zone_file_count()
        return {
            "staging_clean": not normal_files and partial_count == 0,
            "normal_staging_file_count": len(normal_files),
            "partial_workspace_clear": partial_count == 0,
            "partial_workspace_file_count": partial_count,
            "drop_zone_clean": drop_zone_count == 0,
            "drop_zone_file_count": drop_zone_count,
            "staged_unknown_pending_intake": bool(staged_unknown),
            "staged_unknown_resource_count": len(staged_unknown),
        }
    except Exception:  # noqa: BLE001 - status reporting must not mask the real run state
        return {
            "staging_clean": None,
            "normal_staging_file_count": None,
            "partial_workspace_clear": None,
            "partial_workspace_file_count": None,
            "drop_zone_clean": None,
            "drop_zone_file_count": None,
            "staged_unknown_pending_intake": None,
            "staged_unknown_resource_count": None,
        }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _elapsed_seconds(started_at: datetime | None, finished_at: datetime | None) -> float | None:
    if started_at is None or finished_at is None:
        return None
    end = finished_at
    start = started_at
    if end.tzinfo is not None and start.tzinfo is None:
        end = end.replace(tzinfo=None)
    elif end.tzinfo is None and start.tzinfo is not None:
        start = start.replace(tzinfo=None)
    return max(0.0, (end - start).total_seconds())


def _batch_rows(db_session: Session, run_id: int) -> list[IcloudOrchestrationBatch]:
    return list(
        db_session.scalars(
            select(IcloudOrchestrationBatch)
            .where(IcloudOrchestrationBatch.orchestration_run_id == run_id)
            .order_by(IcloudOrchestrationBatch.batch_index)
        )
    )


def _batch_payload(row: IcloudOrchestrationBatch) -> dict[str, Any]:
    return {
        "orchestration_batch_id": row.id,
        "batch_index": row.batch_index,
        "batch_target": row.batch_target,
        "status": row.status,
        "stop_reason": row.stop_reason,
        "failure_reason": row.failure_reason,
        "next_safe_action": row.next_safe_action,
        "acquisition_run_id": row.acquisition_run_id,
        "acquisition_batch_id": row.acquisition_batch_id,
        "source_intake_run_id": row.source_intake_run_id,
        "ingestion_run_id": row.ingestion_run_id,
        "cleanup_dry_run_id": row.cleanup_dry_run_id,
        "cleanup_execution_run_id": row.cleanup_execution_run_id,
        "final_cleanup_verification_run_id": row.final_cleanup_verification_run_id,
        "selected_logical_items": row.selected_logical_items,
        "selected_resources": row.selected_resources,
        "intaken_resources": row.intaken_resources,
        "cleaned_resources": row.cleaned_resources,
        "candidates_considered": row.candidates_considered,
        "resource_candidates_considered": row.resource_candidates_considered,
        "unsupported_or_blocked_count": row.unsupported_or_blocked_count,
        "safe_but_not_selected_logical_items": row.safe_but_not_selected_logical_items,
        "report_path": row.report_path,
    }


def _compact_ints(values: list[int | None]) -> list[int]:
    return [int(value) for value in values if value is not None]


def _run_payload(db_session: Session, run: IcloudOrchestrationRun) -> dict[str, Any]:
    batch_rows = _batch_rows(db_session, run.id)
    batches = [_batch_payload(row) for row in batch_rows]
    latest_batch = batch_rows[-1] if batch_rows else None
    recovery_required = run.status == STATUS_BLOCKED and run.stop_reason in _RECOVERY_STOP_REASONS
    payload = {
        "report_type": REPORT_TYPE,
        "generated_at_utc": _utc_now().isoformat(),
        "orchestration_run_id": run.id,
        "source_profile_id": run.source_profile_id,
        "batch_size": run.batch_size,
        "total_limit": run.total_limit,
        "candidate_search_cap": run.candidate_scan_limit,
        "scan_limit_meaning": "candidate_search_cap",
        "candidate_scan_limit": run.candidate_scan_limit,
        "candidate_page_size": None,
        "candidate_page_size_status": "deferred",
        "candidate_pages_scanned": None,
        "ordinary_still_only": bool(run.ordinary_still_only),
        "pause_before_cleanup": bool(run.pause_before_cleanup),
        "status": run.status,
        "stop_reason": run.stop_reason,
        "failure_reason": run.failure_reason,
        "next_safe_action": run.next_safe_action,
        "completed_logical_items": run.completed_logical_items,
        "completed_resources": run.completed_resources,
        "attempted_batches": run.attempted_batches,
        "completed_batches": run.completed_batches,
        "failed_batches": run.failed_batches,
        "current_batch_index": run.current_batch_index,
        "last_acquisition_run_id": run.last_acquisition_run_id,
        "last_acquisition_batch_id": run.last_acquisition_batch_id,
        "last_source_intake_run_id": run.last_source_intake_run_id,
        "last_cleanup_dry_run_id": run.last_cleanup_dry_run_id,
        "last_cleanup_execution_run_id": run.last_cleanup_execution_run_id,
        "total_candidates_considered": sum(row.candidates_considered for row in batch_rows),
        "total_resource_candidates_considered": sum(row.resource_candidates_considered for row in batch_rows),
        "acquisition_run_ids": _compact_ints([row.acquisition_run_id for row in batch_rows]),
        "acquisition_batch_ids": _compact_ints([row.acquisition_batch_id for row in batch_rows]),
        "source_intake_run_ids": _compact_ints([row.source_intake_run_id for row in batch_rows]),
        "ingestion_run_ids": _compact_ints([row.ingestion_run_id for row in batch_rows]),
        "cleanup_dry_run_ids": _compact_ints([row.cleanup_dry_run_id for row in batch_rows]),
        "cleanup_execution_run_ids": _compact_ints([row.cleanup_execution_run_id for row in batch_rows]),
        "final_cleanup_verification_ids": _compact_ints(
            [row.final_cleanup_verification_run_id for row in batch_rows]
        ),
        "cleanup_review_required": run.status == STATUS_PAUSED_FOR_CLEANUP,
        "cleanup_recovery_required": recovery_required,
        "original_cleanup_error_code": latest_batch.failure_reason if latest_batch is not None else None,
        "stale_cleanup_dry_run_id": latest_batch.cleanup_dry_run_id if latest_batch is not None else None,
        "cloud_deletion_performed": False,
        "normal_ui_exposure_added": False,
        "normal_admin_api_exposure_added": False,
        "batches": batches,
    }
    if recovery_required:
        payload["continue_cleanup_command_template"] = _continue_cleanup_command_template(
            orchestration_run_id=run.id,
            cleanup_dry_run_id="<fresh_cleanup_dry_run_id>",
        )
        payload["fresh_cleanup_preview_command"] = _fresh_cleanup_preview_command(source_id=run.source_profile_id)
    payload.update(_staging_state_payload(db_session, source_id=run.source_profile_id))
    return payload


def _assert_secret_free(payload: dict[str, Any]) -> None:
    serialized = json.dumps(payload, sort_keys=True, default=str).casefold()
    if any(term in serialized for term in _FORBIDDEN_REPORT_TERMS):
        raise IcloudInternalLoopError("unsafe_report_output", "Report payload contained a forbidden term.")


def _write_report(db_session: Session, run: IcloudOrchestrationRun) -> str:
    payload = _run_payload(db_session, run)
    timestamp = _utc_now().strftime("%Y%m%dT%H%M%SZ")
    report_path = _report_directory() / f"icloud_internal_loop_{run.id}_{timestamp}.json"
    payload["report_path"] = str(report_path)
    _assert_secret_free(payload)
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    run.report_path = str(report_path)
    db_session.commit()
    return str(report_path)


def _result_from_run(db_session: Session, run: IcloudOrchestrationRun) -> IcloudInternalLoopResult:
    report_path = _write_report(db_session, run)
    payload = _run_payload(db_session, run)
    batches = payload["batches"]
    return IcloudInternalLoopResult(
        orchestration_run_id=run.id,
        source_profile_id=run.source_profile_id,
        status=run.status,
        stop_reason=run.stop_reason,
        failure_reason=run.failure_reason,
        next_safe_action=run.next_safe_action,
        report_path=report_path,
        completed_logical_items=run.completed_logical_items,
        completed_resources=run.completed_resources,
        attempted_batches=run.attempted_batches,
        completed_batches=run.completed_batches,
        failed_batches=run.failed_batches,
        current_batch_index=run.current_batch_index,
        cleanup_dry_run_id=run.last_cleanup_dry_run_id,
        cleanup_execution_run_id=run.last_cleanup_execution_run_id,
        batches=batches,
        batch_size=run.batch_size,
        total_limit=run.total_limit,
        candidate_search_cap=run.candidate_scan_limit,
        total_candidates_considered=payload["total_candidates_considered"],
        total_resource_candidates_considered=payload["total_resource_candidates_considered"],
        acquisition_run_ids=payload["acquisition_run_ids"],
        acquisition_batch_ids=payload["acquisition_batch_ids"],
        source_intake_run_ids=payload["source_intake_run_ids"],
        ingestion_run_ids=payload["ingestion_run_ids"],
        cleanup_dry_run_ids=payload["cleanup_dry_run_ids"],
        cleanup_execution_run_ids=payload["cleanup_execution_run_ids"],
        final_cleanup_verification_ids=payload["final_cleanup_verification_ids"],
        staging_clean=payload["staging_clean"],
        drop_zone_clean=payload["drop_zone_clean"],
        partial_workspace_clear=payload["partial_workspace_clear"],
        cleanup_review_required=payload["cleanup_review_required"],
        cleanup_recovery_required=payload["cleanup_recovery_required"],
        original_cleanup_error_code=payload["original_cleanup_error_code"],
        stale_cleanup_dry_run_id=payload["stale_cleanup_dry_run_id"],
        continue_cleanup_command_template=payload.get("continue_cleanup_command_template"),
        fresh_cleanup_preview_command=payload.get("fresh_cleanup_preview_command"),
    )


def _finish_run(
    db_session: Session,
    run: IcloudOrchestrationRun,
    *,
    status: str,
    stop_reason: str | None,
    failure_reason: str | None = None,
    next_safe_action: str | None = None,
) -> IcloudInternalLoopResult:
    now = _utc_now()
    run.status = status
    run.stop_reason = stop_reason
    run.failure_reason = failure_reason
    run.next_safe_action = next_safe_action
    run.finished_at = now
    run.last_heartbeat_at = now
    run.elapsed_seconds = _elapsed_seconds(run.started_at, run.finished_at)
    db_session.commit()
    return _result_from_run(db_session, run)


def _block_run(
    db_session: Session,
    run: IcloudOrchestrationRun,
    *,
    reason: str,
    next_safe_action: str | None = NEXT_INSPECT_REPORT,
    batch: IcloudOrchestrationBatch | None = None,
    failure: bool = False,
    batch_failure_reason: str | None = None,
) -> IcloudInternalLoopResult:
    if batch is not None:
        batch.status = BATCH_STATUS_FAILED if failure else BATCH_STATUS_BLOCKED
        batch.stop_reason = reason
        batch.failure_reason = reason if failure else batch_failure_reason
        batch.next_safe_action = next_safe_action
        batch.finished_at = _utc_now()
        if failure:
            run.failed_batches += 1
    return _finish_run(
        db_session,
        run,
        status=STATUS_FAILED if failure else STATUS_BLOCKED,
        stop_reason=reason,
        failure_reason=reason if failure else None,
        next_safe_action=next_safe_action,
    )


def _validate_parameters(*, batch_size: int, total_limit: int, candidate_scan_limit: int) -> None:
    if batch_size < 1:
        raise IcloudInternalLoopError("invalid_batch_size", "batch_size must be positive.")
    if total_limit < 1:
        raise IcloudInternalLoopError("invalid_total_limit", "total_limit must be positive.")
    if batch_size > total_limit:
        raise IcloudInternalLoopError("batch_size_exceeds_total_limit", "batch_size must be <= total_limit.")
    if batch_size > MAX_TARGET_NEW_ITEM_COUNT:
        raise IcloudInternalLoopError("batch_size_exceeds_adapter_limit", "batch_size exceeds adapter target limit.")
    if candidate_scan_limit < batch_size or candidate_scan_limit > MAX_CANDIDATE_SCAN_LIMIT:
        raise IcloudInternalLoopError(
            "invalid_candidate_scan_limit",
            "candidate_scan_limit must be bounded and at least batch_size.",
        )


def _preflight_clean_state(
    db_session: Session,
    *,
    source_id: int,
    allow_expected_files: set[str] | None = None,
) -> tuple[bool, str | None, str | None]:
    profile = validate_exact_selection_profile(db_session, source_id=source_id)
    if count_partial_workspace_files(profile):
        return False, "partial_workspace_present", NEXT_RESOLVE_STAGING
    if _drop_zone_file_count():
        return False, "drop_zone_not_empty", NEXT_RESOLVE_DROP_ZONE

    guardrail = get_ingestion_operation_guardrail_snapshot(db_session, source_id=source_id)
    if guardrail.blocked:
        reason = guardrail.blocking_reasons[0].code.lower()
        return False, reason, "Wait for the active ingestion operation to finish"

    expected = allow_expected_files or set()
    normal_files = _normal_staging_files(profile.staging_root)
    unexpected = [
        path
        for path in normal_files
        if path.relative_to(profile.staging_root).as_posix() not in expected
    ]
    if unexpected:
        staged_unknown = find_staged_unknown_resources(db_session, profile=profile)
        if staged_unknown:
            return False, "staged_unknown_pending_intake", "Run Source Intake first"
        return False, "staging_not_clean", NEXT_RESOLVE_STAGING
    return True, None, None


def _build_plan_summary(
    preparation: ExactSelectionPreparation,
    *,
    batch_target: int,
    ordinary_still_only: bool,
) -> IcloudLoopPlanSummary:
    plan = preparation.plan
    listing = preparation.listing
    status = STATUS_FAILED if preparation.status == PREPARATION_FAILED else STATUS_COMPLETED
    stop_reason = preparation.error_code if preparation.status == PREPARATION_FAILED else preparation.stopping_reason
    auth_state = preparation.auth_state

    if plan is None:
        return IcloudLoopPlanSummary(
            status=status,
            stop_reason=stop_reason,
            next_safe_action=NEXT_INSPECT_REPORT,
            execution_safe_to_attempt=False,
            batch_target=batch_target,
            auth_state=auth_state,
        )

    all_resources = [resource for item in plan.items for resource in item.resources]
    candidates_considered = (
        listing.logical_item_count if listing is not None else plan.candidate_scan_item_count
    )
    resource_candidates_considered = (
        listing.resource_file_count if listing is not None else plan.candidate_resource_count
    )
    selected_adapter_item_ids = {
        item.adapter_logical_item_id
        for item in plan.items
        if item.selected_new and item.adapter_logical_item_id
    }
    unsupported_or_blocked = plan.ambiguous_item_count
    selected_unsupported_or_blocked = 0
    if listing is not None:
        listed_blocked_items = [
            item
            for item in listing.items
            if item.identity_ambiguous
            or item.unsupported_reasons
            or (ordinary_still_only and not is_ordinary_still_logical_item(item))
        ]
        unsupported_or_blocked += len(listed_blocked_items)
        selected_unsupported_or_blocked = sum(
            1 for item in listed_blocked_items if item.item_id in selected_adapter_item_ids
        )
    ordinary_safe = True
    if ordinary_still_only:
        try:
            from app.services.icloud_acquisition.durable_exact_service import (
                _preparation_selects_only_ordinary_stills,
            )

            ordinary_safe = _preparation_selects_only_ordinary_stills(preparation)
        except Exception:  # noqa: BLE001 - safety gate failure means not safe
            ordinary_safe = False
    selected_count = plan.selected_new_item_count
    selected_resource_count = plan.selected_new_resource_count
    batch_target_filled = selected_count == batch_target and selected_resource_count == batch_target
    partial_batch_selected = 0 < selected_count < batch_target
    search_cap_reached = bool(
        preparation.stopping_reason == STOP_SCAN_LIMIT_REACHED
        or (listing is not None and listing.scan_limit_reached)
    )
    operator_decision_required = partial_batch_selected
    execution_safe = bool(
        preparation.status == PREPARATION_READY
        and preparation.download_request is not None
        and auth_state == AUTHENTICATED
        and preparation.stopping_reason == STOP_TARGET_NEW_COUNT_REACHED
        and batch_target_filled
        and selected_unsupported_or_blocked == 0
        and ordinary_safe
    )
    if execution_safe:
        stop_reason = STOP_TARGET_NEW_COUNT_REACHED
    elif partial_batch_selected:
        stop_reason = "partial_batch_selected"
    elif selected_count > 0 and (selected_unsupported_or_blocked or not ordinary_safe):
        stop_reason = "unsupported_or_ambiguous_candidates_only"
    elif search_cap_reached:
        stop_reason = "candidate_search_cap_reached"
    elif unsupported_or_blocked and selected_count == 0:
        stop_reason = "unsupported_or_ambiguous_candidates_only"
    elif stop_reason == STOP_NO_MORE_CANDIDATES:
        stop_reason = "no_more_new_items" if plan.items else "no_more_candidates"

    next_action = "Acquire exact-selection batch" if execution_safe else NEXT_INSPECT_REPORT
    if operator_decision_required:
        next_action = NEXT_OPERATOR_DECISION_PARTIAL
    elif stop_reason in {"candidate_search_cap_reached", "no_more_new_items", "no_more_candidates"}:
        next_action = NEXT_ADD_NEW_ITEMS_OR_INCREASE_SEARCH_CAP
    return IcloudLoopPlanSummary(
        status=STATUS_COMPLETED,
        stop_reason=stop_reason,
        next_safe_action=next_action,
        execution_safe_to_attempt=execution_safe,
        batch_target=batch_target,
        logical_candidates_considered=candidates_considered,
        resource_candidates_considered=resource_candidates_considered,
        known_logical_items=sum(1 for item in plan.items if item.already_known),
        known_resources=sum(1 for resource in all_resources if resource.already_known),
        unknown_logical_items=sum(1 for item in plan.items if not item.already_known),
        unknown_resources=sum(1 for resource in all_resources if not resource.already_known),
        selected_logical_items=selected_count,
        selected_resources=selected_resource_count,
        unsupported_or_blocked_count=unsupported_or_blocked,
        selected_unsupported_or_blocked_count=selected_unsupported_or_blocked,
        safe_but_not_selected_logical_items=plan.remaining_unselected_new_item_count,
        batch_target_filled=batch_target_filled,
        partial_batch_selected=partial_batch_selected,
        operator_decision_required=operator_decision_required,
        candidate_search_cap_reached=search_cap_reached,
        auth_state=auth_state,
    )


def plan_internal_loop(
    db_session: Session,
    *,
    source_id: int,
    batch_size: int,
    total_limit: int,
    candidate_scan_limit: int,
    ordinary_still_only: bool,
    helper_client: ExactSelectionHelperClient,
) -> dict[str, Any]:
    """Run bounded preflight and first-batch plan without downloading."""

    ensure_icloud_orchestration_schema(db_session)
    ensure_icloud_acquisition_schema(db_session)
    _validate_parameters(
        batch_size=batch_size,
        total_limit=total_limit,
        candidate_scan_limit=candidate_scan_limit,
    )
    clean, reason, next_action = _preflight_clean_state(db_session, source_id=source_id)
    if not clean:
        return {
            "status": STATUS_BLOCKED,
            "stop_reason": reason,
            "next_safe_action": next_action,
            "source_profile_id": source_id,
            "batch_size": batch_size,
            "total_limit": total_limit,
            "candidate_search_cap": candidate_scan_limit,
            "scan_limit_meaning": "candidate_search_cap",
            "candidate_scan_limit": candidate_scan_limit,
            "candidate_page_size": None,
            "candidate_page_size_status": "deferred",
            "candidate_pages_scanned": None,
            "ordinary_still_only": ordinary_still_only,
            "execution_safe_to_attempt": False,
        }

    batch_target = min(batch_size, total_limit)
    preparation = prepare_exact_selection_prototype(
        db_session,
        source_id=source_id,
        target_new_item_count=batch_target,
        candidate_scan_limit=candidate_scan_limit,
        helper_client=helper_client,
        ordinary_still_only=ordinary_still_only,
    )
    plan = _build_plan_summary(
        preparation,
        batch_target=batch_target,
        ordinary_still_only=ordinary_still_only,
    )
    return {
        "status": plan.status,
        "stop_reason": plan.stop_reason,
        "next_safe_action": plan.next_safe_action,
        "source_profile_id": source_id,
        "batch_size": batch_size,
        "total_limit": total_limit,
        "batch_target": batch_target,
        "candidate_search_cap": candidate_scan_limit,
        "scan_limit_meaning": "candidate_search_cap",
        "candidate_scan_limit": candidate_scan_limit,
        "candidate_page_size": None,
        "candidate_page_size_status": "deferred",
        "candidate_pages_scanned": None,
        "ordinary_still_only": ordinary_still_only,
        "execution_safe_to_attempt": plan.execution_safe_to_attempt,
        "auth_state": plan.auth_state,
        "candidates_considered": plan.logical_candidates_considered,
        "logical_candidates_considered": plan.logical_candidates_considered,
        "resource_candidates_considered": plan.resource_candidates_considered,
        "known_logical_items": plan.known_logical_items,
        "known_resources": plan.known_resources,
        "unknown_logical_items": plan.unknown_logical_items,
        "unknown_resources": plan.unknown_resources,
        "selected_logical_items": plan.selected_logical_items,
        "selected_resources": plan.selected_resources,
        "unsupported_or_blocked_count": plan.unsupported_or_blocked_count,
        "selected_unsupported_or_blocked_count": plan.selected_unsupported_or_blocked_count,
        "safe_but_not_selected_logical_items": plan.safe_but_not_selected_logical_items,
        "batch_target_filled": plan.batch_target_filled,
        "partial_batch_selected": plan.partial_batch_selected,
        "operator_decision_required": plan.operator_decision_required,
        "candidate_search_cap_reached": plan.candidate_search_cap_reached,
        "cloud_deletion_performed": False,
        "source_intake_performed": False,
        "vault_write_performed": False,
    }


def _new_run(
    db_session: Session,
    *,
    source_id: int,
    batch_size: int,
    total_limit: int,
    candidate_scan_limit: int,
    ordinary_still_only: bool,
    pause_before_cleanup: bool,
    created_by: str,
) -> IcloudOrchestrationRun:
    now = _utc_now()
    run = IcloudOrchestrationRun(
        source_profile_id=source_id,
        batch_size=batch_size,
        total_limit=total_limit,
        candidate_scan_limit=candidate_scan_limit,
        ordinary_still_only=ordinary_still_only,
        pause_before_cleanup=pause_before_cleanup,
        status=STATUS_RUNNING,
        started_at=now,
        last_heartbeat_at=now,
        next_safe_action=None,
        created_by=created_by,
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    return run


def _new_batch(
    db_session: Session,
    *,
    run: IcloudOrchestrationRun,
    batch_target: int,
) -> IcloudOrchestrationBatch:
    batch_index = run.attempted_batches + 1
    now = _utc_now()
    row = IcloudOrchestrationBatch(
        orchestration_run_id=run.id,
        batch_index=batch_index,
        batch_target=batch_target,
        status=BATCH_STATUS_PLANNED,
        started_at=now,
        next_safe_action="Acquire exact-selection batch",
    )
    run.attempted_batches += 1
    run.current_batch_index = batch_index
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


def _batch_resources(db_session: Session, acquisition_batch_id: int) -> list[IcloudAcquisitionResource]:
    batch = db_session.get(IcloudAcquisitionBatch, acquisition_batch_id)
    if batch is None:
        return []
    return [resource for item in batch.items for resource in item.resources]


def _verify_acquired_staging(
    db_session: Session,
    *,
    source_id: int,
    acquisition_batch_id: int,
) -> tuple[bool, str | None, int]:
    profile = validate_exact_selection_profile(db_session, source_id=source_id)
    batch = db_session.get(IcloudAcquisitionBatch, acquisition_batch_id)
    if batch is None:
        return False, "acquisition_batch_missing", 0
    if not batch.batch_ready_for_source_intake or batch.status != STATUS_BATCH_READY_FOR_SOURCE_INTAKE:
        return False, "batch_not_ready_for_source_intake", 0
    if count_partial_workspace_files(profile):
        return False, "partial_file_present", 0
    if _drop_zone_file_count():
        return False, "drop_zone_not_empty", 0
    resources = _batch_resources(db_session, acquisition_batch_id)
    expected_relatives = {resource.relative_path for resource in resources}
    for resource in resources:
        if resource.status != STATUS_RESOURCE_PUBLISHED:
            return False, "resource_not_published_after_acquisition", len(resources)
        if not resource.local_sha256:
            return False, "resource_sha_missing_after_acquisition", len(resources)
        rel = Path(resource.relative_path or "")
        if rel.is_absolute() or any(part == ".." for part in rel.parts):
            return False, "resource_outside_staging_root", len(resources)
        resolved = (profile.staging_root / rel).resolve()
        if not _is_within(resolved, profile.staging_root):
            return False, "resource_outside_staging_root", len(resources)
        if ".partial" in [part.casefold() for part in resolved.relative_to(profile.staging_root).parts]:
            return False, "partial_file_present", len(resources)
        if not resolved.is_file():
            return False, "resource_missing_after_acquisition", len(resources)
        if resource.expected_size is not None and resolved.stat().st_size != resource.expected_size:
            return False, "resource_size_mismatch_after_acquisition", len(resources)
        if _sha256_file(resolved) != resource.local_sha256:
            return False, "resource_sha_mismatch_after_acquisition", len(resources)

    normal_relatives = {path.relative_to(profile.staging_root).as_posix() for path in _normal_staging_files(profile.staging_root)}
    if normal_relatives - expected_relatives:
        return False, "unexpected_staged_unknown_file", len(resources)
    return True, None, len(resources)


def _verify_source_intake(
    db_session: Session,
    *,
    result: BatchSourceIntakeResult,
    acquisition_batch_id: int,
) -> tuple[bool, str | None, int]:
    if result.status != STATUS_BATCH_INTAKE_COMPLETED or result.stop_reason is not None:
        return False, result.stop_reason or "source_intake_failed", 0
    if (
        result.resources_failed
        or result.resources_deferred
        or result.missing_files
        or result.sha_mismatches
        or not result.batch_ready_for_cleanup_dry_run
    ):
        return False, "source_intake_evidence_incomplete", 0
    resources = _batch_resources(db_session, acquisition_batch_id)
    if not resources:
        return False, "source_intake_no_resources", 0
    for resource in resources:
        if resource.source_intake_status not in RESOURCE_SUCCESS_STATUSES:
            return False, "source_intake_resource_outcome_missing", len(resources)
        if not resource.source_intake_run_id or not resource.ingestion_run_id:
            return False, "source_intake_linkage_missing", len(resources)
        if not resource.asset_sha256:
            return False, "source_intake_asset_evidence_missing", len(resources)
        provenance_count = int(
            db_session.scalar(
                select(func.count())
                .select_from(Provenance)
                .where(
                    Provenance.ingestion_source_id == result.source_profile_id,
                    Provenance.asset_sha256 == resource.asset_sha256,
                )
            )
            or 0
        )
        asset_count = int(
            db_session.scalar(
                select(func.count()).select_from(Asset).where(Asset.sha256 == resource.asset_sha256)
            )
            or 0
        )
        if provenance_count <= 0 or asset_count <= 0:
            return False, "source_intake_provenance_or_asset_missing", len(resources)
    if _drop_zone_file_count():
        return False, "drop_zone_not_empty", len(resources)
    return True, None, len(resources)


def _wait_for_cleanup(
    db_session: Session,
    *,
    run_id: int,
    source_id: int,
    timeout_seconds: float,
    poll_seconds: float,
) -> CleanupRunSnapshot:
    deadline = time.monotonic() + timeout_seconds
    latest: CleanupRunSnapshot | None = None
    while time.monotonic() <= deadline:
        db_session.expire_all()
        latest = get_cleanup_status(db_session, source_id=source_id)
        if latest is not None and latest.run_id == run_id and latest.status not in {"pending", "running", "stop_requested"}:
            return latest
        time.sleep(poll_seconds)
    raise IcloudInternalLoopError("cleanup_timeout", "Cleanup did not finish within the internal wait timeout.")


def _start_and_wait_cleanup_dry_run(
    db_session: Session,
    *,
    source_id: int,
    timeout_seconds: float,
    poll_seconds: float,
) -> CleanupRunSnapshot:
    with protected_ingestion_operation_start(db_session):
        snapshot = start_cleanup_run(db_session, source_id=source_id, dry_run=True, created_by="internal_icloud_loop")
    return _wait_for_cleanup(
        db_session,
        run_id=snapshot.run_id,
        source_id=source_id,
        timeout_seconds=timeout_seconds,
        poll_seconds=poll_seconds,
    )


def _start_and_wait_cleanup_execution(
    db_session: Session,
    *,
    source_id: int,
    dry_run_run_id: int,
    confirmation: str,
    timeout_seconds: float,
    poll_seconds: float,
) -> CleanupRunSnapshot:
    with protected_ingestion_operation_start(db_session):
        snapshot = start_cleanup_execution(
            db_session,
            source_id=source_id,
            dry_run_run_id=dry_run_run_id,
            explicit_confirmation=confirmation,
            created_by="internal_icloud_loop",
        )
    return _wait_for_cleanup(
        db_session,
        run_id=snapshot.run_id,
        source_id=source_id,
        timeout_seconds=timeout_seconds,
        poll_seconds=poll_seconds,
    )


def _verify_cleanup_dry_run(snapshot: CleanupRunSnapshot) -> tuple[bool, str | None]:
    if snapshot.status != "completed":
        return False, "cleanup_dry_run_failed"
    if snapshot.eligible_count <= 0:
        return False, "cleanup_not_eligible"
    if (
        snapshot.protected_count
        or snapshot.verification_failed_count
        or snapshot.file_missing_count
        or snapshot.delete_failed_count
    ):
        return False, "cleanup_dry_run_verification_failed"
    return True, None


def _verify_cleanup_execution(snapshot: CleanupRunSnapshot) -> tuple[bool, str | None]:
    if snapshot.status != "completed":
        return False, "cleanup_failed"
    if snapshot.deleted_count <= 0:
        return False, "cleanup_deleted_nothing"
    if (
        snapshot.protected_count
        or snapshot.verification_failed_count
        or snapshot.file_missing_count
        or snapshot.delete_failed_count
    ):
        return False, "cleanup_execution_verification_failed"
    return True, None


def _verify_final_staging_clean(
    db_session: Session,
    *,
    source_id: int,
    timeout_seconds: float,
    poll_seconds: float,
) -> tuple[bool, str | None, CleanupRunSnapshot | None]:
    snapshot = _start_and_wait_cleanup_dry_run(
        db_session,
        source_id=source_id,
        timeout_seconds=timeout_seconds,
        poll_seconds=poll_seconds,
    )
    if snapshot.status != "completed":
        return False, "final_cleanup_verification_failed", snapshot
    if snapshot.eligible_count != 0 or snapshot.total_files != 0:
        return False, "staging_not_clean", snapshot
    clean, reason, _ = _preflight_clean_state(db_session, source_id=source_id)
    if not clean:
        return False, reason, snapshot
    return True, None, snapshot


def _supports_cleanup_recovery(run: IcloudOrchestrationRun, batch: IcloudOrchestrationBatch) -> bool:
    return (
        (run.status == STATUS_PAUSED_FOR_CLEANUP or run.status == STATUS_BLOCKED)
        and (run.stop_reason in {"cleanup_review_required", *_RECOVERY_STOP_REASONS} or run.stop_reason is None)
        and batch.status in {BATCH_STATUS_CLEANUP_REVIEW_REQUIRED, BATCH_STATUS_BLOCKED}
    )


def _verify_batch_source_intake_evidence(
    db_session: Session,
    *,
    source_id: int,
    batch: IcloudOrchestrationBatch,
) -> tuple[bool, str | None]:
    if batch.acquisition_batch_id is None:
        return False, "acquisition_batch_missing"
    if batch.source_intake_run_id is None or batch.ingestion_run_id is None:
        return False, "source_intake_linkage_missing"
    resources = _batch_resources(db_session, batch.acquisition_batch_id)
    if not resources:
        return False, "source_intake_no_resources"
    for resource in resources:
        if resource.source_intake_status not in RESOURCE_SUCCESS_STATUSES:
            return False, "source_intake_resource_outcome_missing"
        if not resource.source_intake_run_id or not resource.ingestion_run_id:
            return False, "source_intake_linkage_missing"
        if not resource.asset_sha256:
            return False, "source_intake_asset_evidence_missing"
        provenance_count = int(
            db_session.scalar(
                select(func.count())
                .select_from(Provenance)
                .where(
                    Provenance.ingestion_source_id == source_id,
                    Provenance.asset_sha256 == resource.asset_sha256,
                )
            )
            or 0
        )
        asset_count = int(db_session.scalar(select(func.count()).select_from(Asset).where(Asset.sha256 == resource.asset_sha256)) or 0)
        if provenance_count <= 0 or asset_count <= 0:
            return False, "source_intake_provenance_or_asset_missing"
    return True, None


def _cleanup_continue_environment_ready(db_session: Session, *, source_id: int) -> tuple[bool, str | None, str | None]:
    profile = validate_exact_selection_profile(db_session, source_id=source_id)
    if count_partial_workspace_files(profile):
        return False, "partial_workspace_present", NEXT_RESOLVE_STAGING
    if _drop_zone_file_count():
        return False, "drop_zone_not_empty", NEXT_RESOLVE_DROP_ZONE
    return True, None, None


def _dirty_staging_reason(reason: str | None) -> bool:
    return reason in {
        "staging_not_clean",
        "staged_unknown_pending_intake",
        "resource_missing_after_acquisition",
        "partial_workspace_present",
        "drop_zone_not_empty",
    }


def _reconcile_cleanup_already_applied(
    db_session: Session,
    *,
    run: IcloudOrchestrationRun,
    batch: IcloudOrchestrationBatch,
    final_verification: CleanupRunSnapshot | None,
    helper_client: ExactSelectionHelperClient,
    cleanup_wait_timeout_seconds: float,
    cleanup_poll_seconds: float,
) -> IcloudInternalLoopResult:
    if final_verification is not None:
        batch.final_cleanup_verification_run_id = final_verification.run_id
    was_completed = batch.status == BATCH_STATUS_COMPLETED
    batch.status = BATCH_STATUS_COMPLETED
    batch.stop_reason = None
    batch.failure_reason = None
    batch.cleaned_resources = max(batch.cleaned_resources, 0)
    batch.finished_at = _utc_now()
    batch.next_safe_action = NEXT_COMPLETE
    if not was_completed:
        run.completed_batches += 1
        run.completed_logical_items += batch.selected_logical_items
        run.completed_resources += batch.selected_resources
    run.status = STATUS_RUNNING
    run.stop_reason = None
    run.failure_reason = None
    run.next_safe_action = None
    run.last_heartbeat_at = _utc_now()
    db_session.commit()

    if run.completed_logical_items >= run.total_limit:
        return _finish_run(
            db_session,
            run,
            status=STATUS_COMPLETED,
            stop_reason="total_limit_reached",
            next_safe_action=NEXT_COMPLETE,
        )
    return _execute_next_batch_until_pause_or_done(
        db_session,
        run=run,
        helper_client=helper_client,
        cleanup_wait_timeout_seconds=cleanup_wait_timeout_seconds,
        cleanup_poll_seconds=cleanup_poll_seconds,
    )


def _handle_recoverable_cleanup_error(
    db_session: Session,
    *,
    run: IcloudOrchestrationRun,
    batch: IcloudOrchestrationBatch,
    cleanup_error_code: str,
    helper_client: ExactSelectionHelperClient,
    cleanup_wait_timeout_seconds: float,
    cleanup_poll_seconds: float,
) -> IcloudInternalLoopResult:
    normalized_reason = _RECOVERABLE_CLEANUP_ERROR_CODES[cleanup_error_code]
    clean, reason, verification = _verify_final_staging_clean(
        db_session,
        source_id=run.source_profile_id,
        timeout_seconds=cleanup_wait_timeout_seconds,
        poll_seconds=cleanup_poll_seconds,
    )

    if clean:
        evidence_ok, evidence_reason = _verify_batch_source_intake_evidence(
            db_session,
            source_id=run.source_profile_id,
            batch=batch,
        )
        if evidence_ok:
            return _reconcile_cleanup_already_applied(
                db_session,
                run=run,
                batch=batch,
                final_verification=verification,
                helper_client=helper_client,
                cleanup_wait_timeout_seconds=cleanup_wait_timeout_seconds,
                cleanup_poll_seconds=cleanup_poll_seconds,
            )
        return _block_run(
            db_session,
            run,
            reason=STOP_REASON_CLEANUP_STATE_AMBIGUOUS,
            next_safe_action=NEXT_FRESH_CLEANUP_PREVIEW,
            batch=batch,
            failure=False,
            batch_failure_reason=cleanup_error_code,
        )

    reason_to_report = normalized_reason if _dirty_staging_reason(reason) else STOP_REASON_CLEANUP_STATE_AMBIGUOUS
    return _block_run(
        db_session,
        run,
        reason=reason_to_report,
        next_safe_action=NEXT_FRESH_CLEANUP_PREVIEW,
        batch=batch,
        failure=False,
        batch_failure_reason=cleanup_error_code,
    )


def _execute_next_batch_until_pause_or_done(
    db_session: Session,
    *,
    run: IcloudOrchestrationRun,
    helper_client: ExactSelectionHelperClient,
    cleanup_wait_timeout_seconds: float,
    cleanup_poll_seconds: float,
) -> IcloudInternalLoopResult:
    while run.completed_logical_items < run.total_limit:
        if run.stop_requested:
            return _finish_run(
                db_session,
                run,
                status=STATUS_COMPLETED,
                stop_reason="user_stopped",
                next_safe_action=NEXT_COMPLETE,
            )
        clean, reason, next_action = _preflight_clean_state(db_session, source_id=run.source_profile_id)
        if not clean:
            return _block_run(db_session, run, reason=reason or "preflight_failed", next_safe_action=next_action)

        remaining = run.total_limit - run.completed_logical_items
        batch_target = min(run.batch_size, remaining)
        preparation = prepare_exact_selection_prototype(
            db_session,
            source_id=run.source_profile_id,
            target_new_item_count=batch_target,
            candidate_scan_limit=run.candidate_scan_limit,
            helper_client=helper_client,
            ordinary_still_only=bool(run.ordinary_still_only),
        )
        plan = _build_plan_summary(
            preparation,
            batch_target=batch_target,
            ordinary_still_only=bool(run.ordinary_still_only),
        )
        if not plan.execution_safe_to_attempt:
            status = STATUS_COMPLETED if run.completed_logical_items > 0 and plan.stop_reason in {"no_more_new_items"} else STATUS_BLOCKED
            return _finish_run(
                db_session,
                run,
                status=status,
                stop_reason=plan.stop_reason,
                next_safe_action=plan.next_safe_action,
            )

        loop_batch = _new_batch(db_session, run=run, batch_target=batch_target)
        loop_batch.candidates_considered = plan.logical_candidates_considered
        loop_batch.resource_candidates_considered = plan.resource_candidates_considered
        loop_batch.unsupported_or_blocked_count = plan.unsupported_or_blocked_count
        loop_batch.safe_but_not_selected_logical_items = plan.safe_but_not_selected_logical_items
        db_session.commit()
        try:
            acquisition = run_durable_exact_selection_batch(
                db_session,
                source_id=run.source_profile_id,
                target_new_item_count=batch_target,
                candidate_scan_limit=run.candidate_scan_limit,
                helper_client=helper_client,
                created_by="internal_icloud_loop",
                ordinary_still_only=bool(run.ordinary_still_only),
            )
        except (DurableExactAcquisitionError, ExactSelectionPrototypeError) as exc:
            return _block_run(
                db_session,
                run,
                reason=getattr(exc, "code", "acquisition_failed"),
                next_safe_action=NEXT_INSPECT_REPORT,
                batch=loop_batch,
                failure=True,
            )

        loop_batch.acquisition_run_id = acquisition.run_id
        loop_batch.acquisition_batch_id = acquisition.batch_id
        run.last_acquisition_run_id = acquisition.run_id
        run.last_acquisition_batch_id = acquisition.batch_id
        if acquisition.status != "completed" or not acquisition.batch_ready_for_source_intake or acquisition.batch_id is None:
            return _block_run(
                db_session,
                run,
                reason=acquisition.stop_reason or "acquisition_failed",
                next_safe_action=acquisition.next_safe_action or NEXT_INSPECT_REPORT,
                batch=loop_batch,
                failure=acquisition.status == STATUS_FAILED,
            )

        verified, reason, selected_resource_count = _verify_acquired_staging(
            db_session,
            source_id=run.source_profile_id,
            acquisition_batch_id=acquisition.batch_id,
        )
        if not verified:
            return _block_run(
                db_session,
                run,
                reason=reason or "acquired_staging_verification_failed",
                next_safe_action=NEXT_RESOLVE_STAGING,
                batch=loop_batch,
            )
        acquisition_batch = db_session.get(IcloudAcquisitionBatch, acquisition.batch_id)
        loop_batch.status = BATCH_STATUS_ACQUIRED
        loop_batch.selected_logical_items = acquisition_batch.selected_new_item_count if acquisition_batch else batch_target
        loop_batch.selected_resources = selected_resource_count
        loop_batch.next_safe_action = NEXT_RUN_SOURCE_INTAKE
        db_session.commit()

        try:
            intake = run_batch_source_intake(
                db_session,
                batch_id=acquisition.batch_id,
                source_id=run.source_profile_id,
                created_by="internal_icloud_loop",
            )
        except BatchSourceIntakeError as exc:
            return _block_run(
                db_session,
                run,
                reason=exc.code,
                next_safe_action=exc.next_safe_action,
                batch=loop_batch,
                failure=True,
            )
        loop_batch.source_intake_run_id = intake.source_intake_run_id
        loop_batch.ingestion_run_id = intake.ingestion_run_id
        run.last_source_intake_run_id = intake.source_intake_run_id
        ok, reason, intaken = _verify_source_intake(
            db_session,
            result=intake,
            acquisition_batch_id=acquisition.batch_id,
        )
        if not ok:
            return _block_run(
                db_session,
                run,
                reason=reason or "source_intake_evidence_incomplete",
                next_safe_action=intake.next_safe_action or NEXT_INSPECT_REPORT,
                batch=loop_batch,
                failure=True,
            )
        loop_batch.status = BATCH_STATUS_INTAKED
        loop_batch.intaken_resources = intaken
        loop_batch.next_safe_action = "Run guarded cleanup dry run"
        db_session.commit()

        try:
            cleanup_dry_run = _start_and_wait_cleanup_dry_run(
                db_session,
                source_id=run.source_profile_id,
                timeout_seconds=cleanup_wait_timeout_seconds,
                poll_seconds=cleanup_poll_seconds,
            )
        except (
            CleanupAuthorizationError,
            CleanupBusyError,
            CleanupValidationError,
            SourceIntakeActiveError,
            IcloudInternalLoopError,
        ) as exc:
            return _block_run(
                db_session,
                run,
                reason=getattr(exc, "code", "cleanup_dry_run_failed"),
                next_safe_action=NEXT_INSPECT_REPORT,
                batch=loop_batch,
                failure=True,
            )
        loop_batch.cleanup_dry_run_id = cleanup_dry_run.run_id
        run.last_cleanup_dry_run_id = cleanup_dry_run.run_id
        ok, reason = _verify_cleanup_dry_run(cleanup_dry_run)
        if not ok:
            return _block_run(
                db_session,
                run,
                reason=reason or "cleanup_not_eligible",
                next_safe_action=NEXT_INSPECT_REPORT,
                batch=loop_batch,
            )
        loop_batch.status = BATCH_STATUS_CLEANUP_REVIEW_REQUIRED
        loop_batch.next_safe_action = NEXT_CONTINUE_CLEANUP
        run.status = STATUS_PAUSED_FOR_CLEANUP
        run.stop_reason = "cleanup_review_required"
        run.next_safe_action = NEXT_CONTINUE_CLEANUP
        db_session.commit()
        return _result_from_run(db_session, run)

    return _finish_run(
        db_session,
        run,
        status=STATUS_COMPLETED,
        stop_reason="total_limit_reached",
        next_safe_action=NEXT_COMPLETE,
    )


def start_internal_icloud_loop(
    db_session: Session,
    *,
    source_id: int,
    batch_size: int,
    total_limit: int,
    candidate_scan_limit: int,
    ordinary_still_only: bool = True,
    pause_before_cleanup: bool = True,
    helper_client: ExactSelectionHelperClient | None = None,
    created_by: str = "internal_icloud_loop",
    cleanup_wait_timeout_seconds: float = DEFAULT_CLEANUP_WAIT_TIMEOUT_SECONDS,
    cleanup_poll_seconds: float = DEFAULT_CLEANUP_POLL_SECONDS,
) -> IcloudInternalLoopResult:
    """Start a bounded internal loop and run until cleanup review or terminal stop."""

    ensure_icloud_orchestration_schema(db_session)
    ensure_icloud_acquisition_schema(db_session)
    _validate_parameters(
        batch_size=batch_size,
        total_limit=total_limit,
        candidate_scan_limit=candidate_scan_limit,
    )
    if not pause_before_cleanup:
        raise IcloudInternalLoopError(
            "cleanup_pause_required",
            "12.62.19 internal loop requires pause-before-cleanup by default.",
        )
    source = db_session.get(IngestionSource, source_id)
    if source is None:
        raise IcloudInternalLoopError("source_not_found", "Source Profile not found.")
    run = _new_run(
        db_session,
        source_id=source_id,
        batch_size=batch_size,
        total_limit=total_limit,
        candidate_scan_limit=candidate_scan_limit,
        ordinary_still_only=ordinary_still_only,
        pause_before_cleanup=pause_before_cleanup,
        created_by=created_by,
    )
    return _execute_next_batch_until_pause_or_done(
        db_session,
        run=run,
        helper_client=helper_client or ExactSelectionHelperClient(),
        cleanup_wait_timeout_seconds=cleanup_wait_timeout_seconds,
        cleanup_poll_seconds=cleanup_poll_seconds,
    )


def continue_internal_icloud_loop_cleanup(
    db_session: Session,
    *,
    orchestration_run_id: int,
    cleanup_dry_run_id: int,
    confirmation: str,
    helper_client: ExactSelectionHelperClient | None = None,
    cleanup_wait_timeout_seconds: float = DEFAULT_CLEANUP_WAIT_TIMEOUT_SECONDS,
    cleanup_poll_seconds: float = DEFAULT_CLEANUP_POLL_SECONDS,
) -> IcloudInternalLoopResult:
    """Execute approved cleanup for the paused batch, verify clean, then continue."""

    ensure_icloud_orchestration_schema(db_session)
    ensure_icloud_acquisition_schema(db_session)
    if confirmation != EXECUTION_CONFIRMATION_PHRASE:
        raise IcloudInternalLoopError("confirmation_required", "Cleanup confirmation phrase does not match.")
    run = db_session.get(IcloudOrchestrationRun, orchestration_run_id)
    if run is None:
        raise IcloudInternalLoopError("orchestration_run_not_found", "Orchestration run not found.")
    if run.status not in {STATUS_PAUSED_FOR_CLEANUP, STATUS_BLOCKED}:
        raise IcloudInternalLoopError("orchestration_not_paused_for_cleanup", "Run is not paused for cleanup.")
    batch = db_session.scalar(
        select(IcloudOrchestrationBatch)
        .where(IcloudOrchestrationBatch.orchestration_run_id == run.id)
        .order_by(IcloudOrchestrationBatch.batch_index.desc(), IcloudOrchestrationBatch.id.desc())
        .limit(1)
    )
    if batch is None:
        raise IcloudInternalLoopError("cleanup_dry_run_not_linked", "Cleanup dry run is not linked to this run.")

    if not _supports_cleanup_recovery(run, batch):
        raise IcloudInternalLoopError("orchestration_not_paused_for_cleanup", "Run is not paused for cleanup.")

    if batch.cleanup_dry_run_id != cleanup_dry_run_id:
        if run.status != STATUS_BLOCKED or run.stop_reason not in _RECOVERY_STOP_REASONS:
            raise IcloudInternalLoopError("cleanup_dry_run_not_linked", "Cleanup dry run is not linked to this run.")
        batch.cleanup_dry_run_id = cleanup_dry_run_id
        batch.stop_reason = None
        batch.failure_reason = None
        batch.status = BATCH_STATUS_CLEANUP_REVIEW_REQUIRED
        batch.next_safe_action = NEXT_CONTINUE_CLEANUP
        run.status = STATUS_PAUSED_FOR_CLEANUP
        run.stop_reason = "cleanup_review_required"
        run.failure_reason = None
        run.next_safe_action = NEXT_CONTINUE_CLEANUP
        run.last_cleanup_dry_run_id = cleanup_dry_run_id
        run.last_heartbeat_at = _utc_now()
        db_session.commit()

    env_ok, env_reason, env_next_action = _cleanup_continue_environment_ready(
        db_session,
        source_id=run.source_profile_id,
    )
    if not env_ok:
        return _block_run(
            db_session,
            run,
            reason=env_reason or "cleanup_recovery_blocked",
            next_safe_action=env_next_action or NEXT_INSPECT_REPORT,
            batch=batch,
        )

    try:
        execution = _start_and_wait_cleanup_execution(
            db_session,
            source_id=run.source_profile_id,
            dry_run_run_id=cleanup_dry_run_id,
            confirmation=confirmation,
            timeout_seconds=cleanup_wait_timeout_seconds,
            poll_seconds=cleanup_poll_seconds,
        )
    except CleanupAuthorizationError as exc:
        if exc.code in _RECOVERABLE_CLEANUP_ERROR_CODES:
            return _handle_recoverable_cleanup_error(
                db_session,
                run=run,
                batch=batch,
                cleanup_error_code=exc.code,
                helper_client=helper_client or ExactSelectionHelperClient(),
                cleanup_wait_timeout_seconds=cleanup_wait_timeout_seconds,
                cleanup_poll_seconds=cleanup_poll_seconds,
            )
        return _block_run(
            db_session,
            run,
            reason=exc.code,
            next_safe_action=NEXT_INSPECT_REPORT,
            batch=batch,
            failure=True,
        )
    except (
        CleanupBusyError,
        CleanupValidationError,
        SourceIntakeActiveError,
        IcloudInternalLoopError,
    ) as exc:
        return _block_run(
            db_session,
            run,
            reason=getattr(exc, "code", "cleanup_failed"),
            next_safe_action=NEXT_INSPECT_REPORT,
            batch=batch,
            failure=True,
        )
    batch.cleanup_execution_run_id = execution.run_id
    run.last_cleanup_execution_run_id = execution.run_id
    ok, reason = _verify_cleanup_execution(execution)
    if not ok:
        return _block_run(
            db_session,
            run,
            reason=reason or "cleanup_failed",
            next_safe_action=NEXT_INSPECT_REPORT,
            batch=batch,
            failure=True,
        )

    clean, reason, verification = _verify_final_staging_clean(
        db_session,
        source_id=run.source_profile_id,
        timeout_seconds=cleanup_wait_timeout_seconds,
        poll_seconds=cleanup_poll_seconds,
    )
    batch.cleanup_execution_run_id = execution.run_id
    run.last_cleanup_execution_run_id = execution.run_id
    if verification is not None:
        batch.final_cleanup_verification_run_id = verification.run_id
    if not clean:
        return _block_run(
            db_session,
            run,
            reason=reason or "staging_not_clean",
            next_safe_action=NEXT_RESOLVE_STAGING,
            batch=batch,
        )
    batch.status = BATCH_STATUS_COMPLETED
    batch.cleaned_resources = execution.deleted_count
    batch.finished_at = _utc_now()
    batch.next_safe_action = NEXT_COMPLETE
    run.completed_batches += 1
    run.completed_logical_items += batch.selected_logical_items
    run.completed_resources += batch.selected_resources
    run.status = STATUS_RUNNING
    run.stop_reason = None
    run.next_safe_action = None
    run.last_heartbeat_at = _utc_now()
    db_session.commit()

    if run.completed_logical_items >= run.total_limit:
        return _finish_run(
            db_session,
            run,
            status=STATUS_COMPLETED,
            stop_reason="total_limit_reached",
            next_safe_action=NEXT_COMPLETE,
        )
    return _execute_next_batch_until_pause_or_done(
        db_session,
        run=run,
        helper_client=helper_client or ExactSelectionHelperClient(),
        cleanup_wait_timeout_seconds=cleanup_wait_timeout_seconds,
        cleanup_poll_seconds=cleanup_poll_seconds,
    )
