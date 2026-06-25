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
NEXT_ADD_NEW_ITEMS_OR_INCREASE_SCAN = "Add new ordinary stills or get approval for a larger scan limit"
NEXT_RESOLVE_STAGING = "Resolve staging state before retrying"
NEXT_RESOLVE_DROP_ZONE = "Clear or process the Drop Zone before retrying"
NEXT_INSPECT_REPORT = "Inspect orchestration report"
NEXT_COMPLETE = "No further action required"

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
    auth_state: str | None = None


@dataclass(frozen=True)
class IcloudInternalLoopResult:
    orchestration_run_id: int | None
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
        "report_path": row.report_path,
    }


def _run_payload(db_session: Session, run: IcloudOrchestrationRun) -> dict[str, Any]:
    batches = [_batch_payload(row) for row in _batch_rows(db_session, run.id)]
    return {
        "report_type": REPORT_TYPE,
        "generated_at_utc": _utc_now().isoformat(),
        "orchestration_run_id": run.id,
        "source_profile_id": run.source_profile_id,
        "batch_size": run.batch_size,
        "total_limit": run.total_limit,
        "candidate_scan_limit": run.candidate_scan_limit,
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
        "cloud_deletion_performed": False,
        "normal_ui_exposure_added": False,
        "normal_admin_api_exposure_added": False,
        "batches": batches,
    }


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
    batches = [_batch_payload(row) for row in _batch_rows(db_session, run.id)]
    return IcloudInternalLoopResult(
        orchestration_run_id=run.id,
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
) -> IcloudInternalLoopResult:
    if batch is not None:
        batch.status = BATCH_STATUS_FAILED if failure else BATCH_STATUS_BLOCKED
        batch.stop_reason = reason
        batch.failure_reason = reason if failure else None
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
    if stop_reason == STOP_SCAN_LIMIT_REACHED and not (plan and plan.selected_new_item_count):
        stop_reason = "scan_limit_reached_with_no_selection"
    if stop_reason == STOP_NO_MORE_CANDIDATES:
        stop_reason = "no_more_new_items"

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
    unsupported_or_blocked = plan.ambiguous_item_count
    if listing is not None:
        selected_adapter_item_ids = {
            item.adapter_logical_item_id
            for item in plan.items
            if item.selected_new and item.adapter_logical_item_id
        }
        unsupported_or_blocked += sum(
            1
            for item in listing.items
            if item.item_id in selected_adapter_item_ids
            and (
                item.identity_ambiguous
                or any(reason != "unsupported_adjustment_metadata_only" for reason in item.unsupported_reasons)
            )
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
    execution_safe = bool(
        preparation.status == PREPARATION_READY
        and preparation.download_request is not None
        and auth_state == AUTHENTICATED
        and preparation.stopping_reason == STOP_TARGET_NEW_COUNT_REACHED
        and plan.selected_new_item_count == batch_target
        and plan.selected_new_resource_count == batch_target
        and unsupported_or_blocked == 0
        and ordinary_safe
    )
    if not execution_safe and ordinary_still_only and plan.selected_new_item_count:
        stop_reason = "unsupported_or_ambiguous_selection"
    next_action = "Acquire exact-selection batch" if execution_safe else NEXT_INSPECT_REPORT
    if stop_reason in {"scan_limit_reached_with_no_selection", "no_more_new_items"}:
        next_action = NEXT_ADD_NEW_ITEMS_OR_INCREASE_SCAN
    return IcloudLoopPlanSummary(
        status=STATUS_COMPLETED,
        stop_reason=stop_reason,
        next_safe_action=next_action,
        execution_safe_to_attempt=execution_safe,
        batch_target=batch_target,
        logical_candidates_considered=plan.candidate_scan_item_count,
        resource_candidates_considered=plan.candidate_resource_count,
        known_logical_items=sum(1 for item in plan.items if item.already_known),
        known_resources=sum(1 for resource in all_resources if resource.already_known),
        unknown_logical_items=sum(1 for item in plan.items if not item.already_known),
        unknown_resources=sum(1 for resource in all_resources if not resource.already_known),
        selected_logical_items=plan.selected_new_item_count,
        selected_resources=plan.selected_new_resource_count,
        unsupported_or_blocked_count=unsupported_or_blocked,
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
            "candidate_scan_limit": candidate_scan_limit,
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
        "candidate_scan_limit": candidate_scan_limit,
        "ordinary_still_only": ordinary_still_only,
        "execution_safe_to_attempt": plan.execution_safe_to_attempt,
        "auth_state": plan.auth_state,
        "logical_candidates_considered": plan.logical_candidates_considered,
        "resource_candidates_considered": plan.resource_candidates_considered,
        "known_logical_items": plan.known_logical_items,
        "known_resources": plan.known_resources,
        "unknown_logical_items": plan.unknown_logical_items,
        "unknown_resources": plan.unknown_resources,
        "selected_logical_items": plan.selected_logical_items,
        "selected_resources": plan.selected_resources,
        "unsupported_or_blocked_count": plan.unsupported_or_blocked_count,
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
    if run.status != STATUS_PAUSED_FOR_CLEANUP:
        raise IcloudInternalLoopError("orchestration_not_paused_for_cleanup", "Run is not paused for cleanup.")
    batch = db_session.scalar(
        select(IcloudOrchestrationBatch)
        .where(
            IcloudOrchestrationBatch.orchestration_run_id == run.id,
            IcloudOrchestrationBatch.cleanup_dry_run_id == cleanup_dry_run_id,
        )
        .order_by(IcloudOrchestrationBatch.id.desc())
        .limit(1)
    )
    if batch is None:
        raise IcloudInternalLoopError("cleanup_dry_run_not_linked", "Cleanup dry run is not linked to this run.")

    try:
        execution = _start_and_wait_cleanup_execution(
            db_session,
            source_id=run.source_profile_id,
            dry_run_run_id=cleanup_dry_run_id,
            confirmation=confirmation,
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
