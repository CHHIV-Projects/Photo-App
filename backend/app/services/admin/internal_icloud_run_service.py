"""Internal/admin single-flow wrapper for bounded iCloud runs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import threading
import time
from typing import Literal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.icloud_orchestration_run import IcloudOrchestrationRun
from app.models.ingestion_source import IngestionSource
from app.schemas.admin import InternalIcloudRunStatus
from app.services.admin.ingestion_operation_guardrail_service import (
    get_ingestion_operation_guardrail_snapshot,
)
from app.services.icloud_acquisition.internal_loop_orchestrator import (
    continue_internal_icloud_loop_cleanup,
    plan_internal_loop,
    start_internal_icloud_loop,
)
from app.services.icloud_acquisition.exact_selection_adapter import ExactSelectionHelperClient
from app.services.icloud_acquisition.orchestration_schema import ensure_icloud_orchestration_schema


MEDIA_SCOPE_ORDINARY_STILLS = "ordinary_stills"
MEDIA_SCOPE_ALL_SUPPORTED = "all_supported_media"
MediaScope = Literal[
    "ordinary_stills",
    "stills_with_live_photo_pairs",
    "videos_only",
    "all_supported_media",
]

_AUTO_CONFIRM = "DELETE LOCAL STAGING COPIES"
_RUN_DEFINITION_LOCK = threading.Lock()
_RUN_DEFINITIONS: dict[int, dict[str, object]] = {}


@dataclass(frozen=True)
class InternalIcloudRunStartResult:
    accepted: bool
    message: str
    status: InternalIcloudRunStatus


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _status_phase(status: str, stop_reason: str | None) -> str:
    if stop_reason in {"MEDIA_SCOPE_NOT_SUPPORTED_FOR_EXECUTION", "DRY_RUN_NOT_SAFE"}:
        return "Dry Run"
    if status == "running":
        return "Execution"
    if status == "paused_for_cleanup":
        return "Cleanup/Reconciliation"
    if stop_reason == "cleanup_review_required_manual":
        return "Cleanup/Reconciliation"
    if status == "completed":
        return "Completed"
    if status in {"blocked", "failed"}:
        return "Needs Review"
    return "Preflight"


def _store_run_definition(run_id: int, *, media_scope: MediaScope, auto_cleanup_if_safe: bool) -> None:
    with _RUN_DEFINITION_LOCK:
        _RUN_DEFINITIONS[run_id] = {
            "media_scope": media_scope,
            "auto_cleanup_if_safe": auto_cleanup_if_safe,
            "stored_at": _now_utc().isoformat(),
        }


def _get_run_definition(run_id: int) -> dict[str, object] | None:
    with _RUN_DEFINITION_LOCK:
        return _RUN_DEFINITIONS.get(run_id)


def _unsupported_media_scope_status(
    *,
    source_id: int,
    source_label: str | None,
    batch_size: int,
    total_limit: int,
    candidate_search_cap: int,
    media_scope: MediaScope,
    auto_cleanup_if_safe: bool,
) -> InternalIcloudRunStatus:
    requested_asset_scope = (
        "all_supported_assets" if media_scope == MEDIA_SCOPE_ALL_SUPPORTED else "ordinary_stills_only"
    )
    return InternalIcloudRunStatus(
        run_id=None,
        status="stopped",
        stop_reason="MEDIA_SCOPE_NOT_SUPPORTED_FOR_EXECUTION",
        failure_reason=None,
        current_phase="Dry Run",
        source_id=source_id,
        source_label=source_label,
        batch_size=batch_size,
        total_limit=total_limit,
        candidate_search_cap=candidate_search_cap,
        requested_media_scope=media_scope,
        effective_media_scope=None,
        requested_asset_scope=requested_asset_scope,
        effective_asset_scope=None,
        auto_cleanup_if_safe=auto_cleanup_if_safe,
        dry_run_performed=False,
        execution_performed=False,
        cleanup_performed=False,
        cleanup_recovery_used=False,
        final_verification_passed=False,
        next_safe_action="Use ordinary_stills for execution until mixed-media execution support is implemented.",
        report_path=None,
        orchestration_report_path=None,
        logical_assets_selected="not_available",
        resources_selected="not_available",
        ordinary_still_logical_count="not_available",
        ordinary_still_resource_count="not_available",
        video_logical_count="not_available",
        video_resource_count="not_available",
        ordinary_still_count="not_available",
        live_photo_logical_count="not_available",
        live_photo_still_resource_count="not_available",
        live_photo_motion_resource_count="not_available",
        video_count="not_available",
        unsupported_or_blocked_count="not_available",
        ambiguous_count="unknown",
        acquired_resource_count="not_available",
        source_intake_count="not_available",
        ingestion_count="not_available",
        cleanup_eligible_count="not_available",
        cleanup_completed_deleted_count="not_available",
        cleanup_failed_count="not_available",
        orphaned_companion_count="not_available",
        pairing_warning_count="not_available",
        final_staging_clean=None,
        drop_zone_clean=None,
        partial_workspace_clean=None,
        cloud_deletion_occurred=False,
        normal_ui_exposure_added=False,
        normal_admin_api_exposure_added=False,
        mixed_media_supported_for_execution=False,
    )


def _from_orchestration_row(
    run: IcloudOrchestrationRun,
    *,
    media_scope: MediaScope,
    auto_cleanup_if_safe: bool,
) -> InternalIcloudRunStatus:
    effective_media_scope = (
        MEDIA_SCOPE_ORDINARY_STILLS if bool(run.ordinary_still_only) else MEDIA_SCOPE_ALL_SUPPORTED
    )
    cleanup_performed = bool(run.last_cleanup_execution_run_id)
    final_verification_passed = bool(
        run.status == "completed"
        and run.stop_reason in {"total_limit_reached", "completed"}
        and run.last_cleanup_dry_run_id is not None
    )
    return InternalIcloudRunStatus(
        run_id=run.id,
        status=run.status,
        stop_reason=run.stop_reason,
        failure_reason=run.failure_reason,
        current_phase=_status_phase(run.status, run.stop_reason),
        source_id=run.source_profile_id,
        source_label=None,
        batch_size=run.batch_size,
        total_limit=run.total_limit,
        candidate_search_cap=run.candidate_scan_limit,
        requested_media_scope=media_scope,
        effective_media_scope=effective_media_scope,
        requested_asset_scope=("all_supported_assets" if media_scope == MEDIA_SCOPE_ALL_SUPPORTED else "ordinary_stills_only"),
        effective_asset_scope=("all_supported_assets" if effective_media_scope == MEDIA_SCOPE_ALL_SUPPORTED else "ordinary_stills_only"),
        auto_cleanup_if_safe=auto_cleanup_if_safe,
        dry_run_performed=True,
        execution_performed=run.attempted_batches > 0,
        cleanup_performed=cleanup_performed,
        cleanup_recovery_used=bool(run.stop_reason and "cleanup_preview" in run.stop_reason),
        final_verification_passed=final_verification_passed,
        next_safe_action=run.next_safe_action,
        report_path=run.report_path,
        orchestration_report_path=run.report_path,
        cleanup_dry_run_id=run.last_cleanup_dry_run_id,
        cleanup_execution_run_id=run.last_cleanup_execution_run_id,
        final_cleanup_verification_run_id=None,
        acquisition_run_ids=[],
        acquisition_batch_ids=[],
        source_intake_run_ids=[],
        ingestion_run_ids=[],
        cleanup_dry_run_ids=[],
        cleanup_execution_run_ids=[],
        final_cleanup_verification_run_ids=[],
        logical_assets_selected=run.completed_logical_items,
        resources_selected=run.completed_resources,
        ordinary_still_logical_count="unknown",
        ordinary_still_resource_count="unknown",
        video_logical_count="unknown",
        video_resource_count="unknown",
        ordinary_still_count=run.completed_resources,
        live_photo_logical_count="not_available",
        live_photo_still_resource_count="not_available",
        live_photo_motion_resource_count="not_available",
        video_count="not_available",
        unsupported_or_blocked_count="unknown",
        ambiguous_count="unknown",
        acquired_resource_count=run.completed_resources,
        source_intake_count=run.completed_resources,
        ingestion_count=run.completed_resources,
        cleanup_eligible_count="unknown",
        cleanup_completed_deleted_count="unknown",
        cleanup_failed_count=run.failed_batches,
        orphaned_companion_count="not_available",
        pairing_warning_count="not_available",
        final_staging_clean=None,
        drop_zone_clean=None,
        partial_workspace_clean=None,
        cloud_deletion_occurred=False,
        normal_ui_exposure_added=False,
        normal_admin_api_exposure_added=False,
        mixed_media_supported_for_execution=False,
    )


def _from_orchestration_payload(
    payload: dict[str, object],
    *,
    media_scope: MediaScope,
    auto_cleanup_if_safe: bool,
) -> InternalIcloudRunStatus:
    def _list_ints(key: str) -> list[int]:
        raw = payload.get(key) or []
        if not isinstance(raw, list):
            return []
        values: list[int] = []
        for item in raw:
            if isinstance(item, int):
                values.append(item)
        return values

    final_verification_ids = _list_ints("final_cleanup_verification_ids")
    cleanup_execution_ids = _list_ints("cleanup_execution_run_ids")

    effective_media_scope = (
        MEDIA_SCOPE_ORDINARY_STILLS
        if bool(payload.get("ordinary_still_only"))
        else MEDIA_SCOPE_ALL_SUPPORTED
    )

    def _count_or_status(key: str, fallback: str = "unknown") -> int | str:
        raw = payload.get(key)
        if isinstance(raw, int):
            return raw
        if isinstance(raw, str) and raw in {"not_available", "deferred", "not_applicable", "unknown"}:
            return raw
        return fallback

    return InternalIcloudRunStatus(
        run_id=int(payload.get("orchestration_run_id") or 0) or None,
        status=str(payload.get("status") or "unknown"),
        stop_reason=(str(payload.get("stop_reason")) if payload.get("stop_reason") is not None else None),
        failure_reason=(str(payload.get("failure_reason")) if payload.get("failure_reason") is not None else None),
        current_phase=_status_phase(
            str(payload.get("status") or "unknown"),
            (str(payload.get("stop_reason")) if payload.get("stop_reason") is not None else None),
        ),
        source_id=int(payload.get("source_profile_id") or 0),
        source_label=None,
        batch_size=int(payload.get("batch_size") or 0),
        total_limit=int(payload.get("total_limit") or 0),
        candidate_search_cap=int(payload.get("candidate_search_cap") or 0),
        requested_media_scope=media_scope,
        effective_media_scope=effective_media_scope,
        requested_asset_scope=("all_supported_assets" if media_scope == MEDIA_SCOPE_ALL_SUPPORTED else "ordinary_stills_only"),
        effective_asset_scope=(
            str(payload.get("effective_asset_scope"))
            if payload.get("effective_asset_scope") is not None
            else ("all_supported_assets" if effective_media_scope == MEDIA_SCOPE_ALL_SUPPORTED else "ordinary_stills_only")
        ),
        auto_cleanup_if_safe=auto_cleanup_if_safe,
        dry_run_performed=True,
        execution_performed=bool(int(payload.get("attempted_batches") or 0) > 0),
        cleanup_performed=bool(cleanup_execution_ids),
        cleanup_recovery_used=bool(payload.get("cleanup_recovery_required")),
        final_verification_passed=bool(final_verification_ids and payload.get("status") == "completed"),
        next_safe_action=(str(payload.get("next_safe_action")) if payload.get("next_safe_action") is not None else None),
        report_path=(str(payload.get("report_path")) if payload.get("report_path") is not None else None),
        orchestration_report_path=(str(payload.get("report_path")) if payload.get("report_path") is not None else None),
        cleanup_dry_run_id=(int(payload.get("cleanup_dry_run_id")) if payload.get("cleanup_dry_run_id") is not None else None),
        cleanup_execution_run_id=(int(payload.get("cleanup_execution_run_id")) if payload.get("cleanup_execution_run_id") is not None else None),
        final_cleanup_verification_run_id=(final_verification_ids[-1] if final_verification_ids else None),
        acquisition_run_ids=_list_ints("acquisition_run_ids"),
        acquisition_batch_ids=_list_ints("acquisition_batch_ids"),
        source_intake_run_ids=_list_ints("source_intake_run_ids"),
        ingestion_run_ids=_list_ints("ingestion_run_ids"),
        cleanup_dry_run_ids=_list_ints("cleanup_dry_run_ids"),
        cleanup_execution_run_ids=cleanup_execution_ids,
        final_cleanup_verification_run_ids=final_verification_ids,
        logical_assets_selected=(int(payload.get("completed_logical_items") or 0)),
        resources_selected=(int(payload.get("completed_resources") or 0)),
        ordinary_still_logical_count=_count_or_status("ordinary_still_logical_count"),
        ordinary_still_resource_count=_count_or_status("ordinary_still_resource_count"),
        video_logical_count=_count_or_status("video_logical_count", fallback="not_available"),
        video_resource_count=_count_or_status("video_resource_count", fallback="not_available"),
        ordinary_still_count=(int(payload.get("completed_resources") or 0)),
        live_photo_logical_count=_count_or_status("live_photo_logical_count", fallback="not_available"),
        live_photo_still_resource_count=_count_or_status("live_photo_still_resource_count", fallback="not_available"),
        live_photo_motion_resource_count=_count_or_status("live_photo_motion_resource_count", fallback="not_available"),
        video_count=_count_or_status("video_logical_count", fallback="not_available"),
        unsupported_or_blocked_count=_count_or_status("unsupported_or_blocked_count"),
        ambiguous_count=_count_or_status("ambiguous_count"),
        acquired_resource_count=(int(payload.get("completed_resources") or 0)),
        source_intake_count=(int(payload.get("completed_resources") or 0)),
        ingestion_count=(int(payload.get("completed_resources") or 0)),
        cleanup_eligible_count="unknown",
        cleanup_completed_deleted_count=("unknown" if not cleanup_execution_ids else "unknown"),
        cleanup_failed_count=(int(payload.get("failed_batches") or 0)),
        orphaned_companion_count=_count_or_status("orphaned_companion_count", fallback="unknown"),
        pairing_warning_count=_count_or_status("pairing_warning_count", fallback="unknown"),
        final_staging_clean=(bool(payload.get("staging_clean")) if payload.get("staging_clean") is not None else None),
        drop_zone_clean=(bool(payload.get("drop_zone_clean")) if payload.get("drop_zone_clean") is not None else None),
        partial_workspace_clean=(bool(payload.get("partial_workspace_clear")) if payload.get("partial_workspace_clear") is not None else None),
        cloud_deletion_occurred=False,
        normal_ui_exposure_added=False,
        normal_admin_api_exposure_added=False,
        mixed_media_supported_for_execution=False,
    )


def _run_single_flow_background(
    *,
    source_id: int,
    batch_size: int,
    total_limit: int,
    candidate_search_cap: int,
    ordinary_still_only: bool,
    auto_cleanup_if_safe: bool,
    created_by: str,
) -> None:
    with SessionLocal() as db_session:
        try:
            result = start_internal_icloud_loop(
                db_session,
                source_id=source_id,
                batch_size=batch_size,
                total_limit=total_limit,
                candidate_scan_limit=candidate_search_cap,
                ordinary_still_only=ordinary_still_only,
                pause_before_cleanup=True,
                created_by=created_by,
            )
            while auto_cleanup_if_safe and result.status == "paused_for_cleanup" and result.cleanup_dry_run_id is not None:
                result = continue_internal_icloud_loop_cleanup(
                    db_session,
                    orchestration_run_id=result.orchestration_run_id or 0,
                    cleanup_dry_run_id=result.cleanup_dry_run_id,
                    confirmation=_AUTO_CONFIRM,
                )

            if not auto_cleanup_if_safe and result.status == "paused_for_cleanup" and result.orchestration_run_id is not None:
                run = db_session.get(IcloudOrchestrationRun, result.orchestration_run_id)
                if run is not None:
                    run.stop_reason = "cleanup_review_required_manual"
                    run.next_safe_action = "Use guarded cleanup continuation with explicit confirmation."
                    db_session.commit()
        except Exception:  # noqa: BLE001 - keep failure localized to internal run row/reporting
            pass


def _wait_for_run_id(db_session: Session, *, created_by: str, timeout_seconds: float = 3.0) -> int | None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() <= deadline:
        row = db_session.scalar(
            select(IcloudOrchestrationRun)
            .where(IcloudOrchestrationRun.created_by == created_by)
            .order_by(IcloudOrchestrationRun.id.desc())
            .limit(1)
        )
        if row is not None:
            return row.id
        time.sleep(0.05)
    return None


def _ordinary_still_only_for_scope(media_scope: MediaScope) -> bool | None:
    if media_scope == MEDIA_SCOPE_ORDINARY_STILLS:
        return True
    if media_scope == MEDIA_SCOPE_ALL_SUPPORTED:
        return False
    return None


def start_internal_single_flow_run(
    db_session: Session,
    *,
    source_id: int,
    batch_size: int,
    total_limit: int,
    candidate_search_cap: int,
    media_scope: MediaScope,
    auto_cleanup_if_safe: bool,
) -> InternalIcloudRunStartResult:
    ensure_icloud_orchestration_schema(db_session)

    source = db_session.get(IngestionSource, source_id)
    if source is None:
        status = _unsupported_media_scope_status(
            source_id=source_id,
            source_label=None,
            batch_size=batch_size,
            total_limit=total_limit,
            candidate_search_cap=candidate_search_cap,
            media_scope=media_scope,
            auto_cleanup_if_safe=auto_cleanup_if_safe,
        )
        status.stop_reason = "SOURCE_PROFILE_NOT_FOUND"
        status.next_safe_action = "Select an existing active Source Profile."
        return InternalIcloudRunStartResult(False, "Source profile not found.", status)

    ordinary_still_only = _ordinary_still_only_for_scope(media_scope)
    if ordinary_still_only is None:
        status = _unsupported_media_scope_status(
            source_id=source_id,
            source_label=source.source_label,
            batch_size=batch_size,
            total_limit=total_limit,
            candidate_search_cap=candidate_search_cap,
            media_scope=media_scope,
            auto_cleanup_if_safe=auto_cleanup_if_safe,
        )
        return InternalIcloudRunStartResult(False, "Requested media scope is not executable yet.", status)

    guardrail = get_ingestion_operation_guardrail_snapshot(db_session, source_id=source_id)
    if guardrail.blocked:
        status = _unsupported_media_scope_status(
            source_id=source_id,
            source_label=source.source_label,
            batch_size=batch_size,
            total_limit=total_limit,
            candidate_search_cap=candidate_search_cap,
            media_scope=media_scope,
            auto_cleanup_if_safe=auto_cleanup_if_safe,
        )
        status.stop_reason = "INGESTION_OPERATION_ACTIVE"
        status.next_safe_action = "Wait for active ingestion-related operations to finish before starting."
        return InternalIcloudRunStartResult(False, "Operation conflict blocks this run.", status)

    dry_plan = plan_internal_loop(
        db_session,
        source_id=source_id,
        batch_size=batch_size,
        total_limit=total_limit,
        candidate_scan_limit=candidate_search_cap,
        ordinary_still_only=ordinary_still_only,
        helper_client=ExactSelectionHelperClient(),
    )
    if not bool(dry_plan.get("execution_safe_to_attempt")):
        status = _unsupported_media_scope_status(
            source_id=source_id,
            source_label=source.source_label,
            batch_size=batch_size,
            total_limit=total_limit,
            candidate_search_cap=candidate_search_cap,
            media_scope=media_scope,
            auto_cleanup_if_safe=auto_cleanup_if_safe,
        )
        status.stop_reason = "DRY_RUN_NOT_SAFE"
        status.next_safe_action = str(dry_plan.get("next_safe_action") or "Inspect dry-run report and resolve blockers.")
        status.dry_run_performed = True
        status.execution_performed = False
        status.logical_assets_selected = int(dry_plan.get("selected_logical_items") or 0)
        status.resources_selected = int(dry_plan.get("selected_resources") or 0)
        status.unsupported_or_blocked_count = int(dry_plan.get("unsupported_or_blocked_count") or 0)
        status.report_path = str(dry_plan.get("report_path") or "") or None
        return InternalIcloudRunStartResult(False, "Dry run blocked execution safety.", status)

    created_by = f"internal_ui_run_{uuid4().hex[:32]}"
    worker = threading.Thread(
        target=_run_single_flow_background,
        kwargs={
            "source_id": source_id,
            "batch_size": batch_size,
            "total_limit": total_limit,
            "candidate_search_cap": candidate_search_cap,
            "ordinary_still_only": ordinary_still_only,
            "auto_cleanup_if_safe": auto_cleanup_if_safe,
            "created_by": created_by,
        },
        daemon=True,
        name=f"internal-icloud-single-flow-{source_id}",
    )
    worker.start()

    run_id = _wait_for_run_id(db_session, created_by=created_by)
    if run_id is None:
        status = _unsupported_media_scope_status(
            source_id=source_id,
            source_label=source.source_label,
            batch_size=batch_size,
            total_limit=total_limit,
            candidate_search_cap=candidate_search_cap,
            media_scope=media_scope,
            auto_cleanup_if_safe=auto_cleanup_if_safe,
        )
        status.stop_reason = "RUN_START_TIMEOUT"
        status.next_safe_action = "Refresh internal run status shortly; run creation may still complete in background."
        status.dry_run_performed = True
        return InternalIcloudRunStartResult(False, "Run accepted but run_id was not available yet.", status)

    _store_run_definition(run_id, media_scope=media_scope, auto_cleanup_if_safe=auto_cleanup_if_safe)
    row = db_session.get(IcloudOrchestrationRun, run_id)
    if row is None:
        status = _unsupported_media_scope_status(
            source_id=source_id,
            source_label=source.source_label,
            batch_size=batch_size,
            total_limit=total_limit,
            candidate_search_cap=candidate_search_cap,
            media_scope=media_scope,
            auto_cleanup_if_safe=auto_cleanup_if_safe,
        )
        status.stop_reason = "RUN_NOT_FOUND"
        return InternalIcloudRunStartResult(False, "Run started but could not be loaded.", status)

    status = _from_orchestration_row(
        row,
        media_scope=media_scope,
        auto_cleanup_if_safe=auto_cleanup_if_safe,
    )
    status.dry_run_performed = True
    return InternalIcloudRunStartResult(True, "Internal iCloud single-flow run started.", status)


def get_internal_single_flow_run_status(db_session: Session, *, run_id: int) -> InternalIcloudRunStatus | None:
    ensure_icloud_orchestration_schema(db_session)
    row = db_session.get(IcloudOrchestrationRun, run_id)
    if row is None:
        return None

    run_def = _get_run_definition(run_id)
    media_scope = MEDIA_SCOPE_ORDINARY_STILLS
    auto_cleanup_if_safe = True
    if run_def is not None:
        raw_scope = run_def.get("media_scope")
        raw_auto = run_def.get("auto_cleanup_if_safe")
        if isinstance(raw_scope, str):
            media_scope = raw_scope  # type: ignore[assignment]
        if isinstance(raw_auto, bool):
            auto_cleanup_if_safe = raw_auto

    if row.report_path:
        try:
            import json
            from pathlib import Path

            payload_path = Path(row.report_path)
            if payload_path.exists():
                payload = json.loads(payload_path.read_text(encoding="utf-8"))
                return _from_orchestration_payload(
                    payload,
                    media_scope=media_scope,
                    auto_cleanup_if_safe=auto_cleanup_if_safe,
                )
        except Exception:  # noqa: BLE001 - fallback to row-based projection
            pass

    return _from_orchestration_row(
        row,
        media_scope=media_scope,
        auto_cleanup_if_safe=auto_cleanup_if_safe,
    )
