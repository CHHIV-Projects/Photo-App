"""Execution service for inventory-driven historical iCloud backfill acquisition."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.icloud_acquisition_run import IcloudAcquisitionBatch
from app.models.icloud_backfill import IcloudRemoteAssetInventory
from app.services.icloud_acquisition.batch_source_intake_service import (
    STATUS_BATCH_INTAKE_COMPLETED,
    STATUS_RESOURCE_INTAKE_DUPLICATE_LINKED,
    STATUS_RESOURCE_INTAKE_PROCESSED,
    STATUS_RESOURCE_INTAKE_SKIPPED_KNOWN,
    BatchSourceIntakeResult,
    run_batch_source_intake,
)
from app.services.icloud_acquisition.durable_exact_service import (
    DurableExactAcquisitionError,
    DurableExactRunResult,
    run_durable_exact_selection_preparation,
)
from app.services.icloud_acquisition.exact_selection_adapter import (
    DEFAULT_LIBRARY,
    PREPARATION_READY,
    ExactSelectionHelperClient,
    ExactSelectionListing,
    ExactSelectionLogicalItem,
    ExactSelectionPreparation,
    ExactSelectionPrototypeError,
    build_exact_download_request_for_listing_items,
    validate_exact_selection_profile,
)
from app.services.icloud_acquisition.exact_selection_protocol import ExactSelectionProtocolError
from app.services.icloud_backfill_acquisition_preview_service import (
    DEFAULT_ACQUIRE_PREVIEW_LIMIT,
    DEFAULT_MAX_LISTING_CANDIDATES,
    IcloudBackfillAcquisitionPreviewResult,
    MAX_ACQUIRE_PREVIEW_LIMIT,
    _listing_by_remote_identity,
    _manifest_unsafe,
    _select_inventory_rows,
    _validate_acquire_limit,
    _validate_listing_limit,
    _validate_source_profile,
    preview_icloud_backfill_acquisition,
)
from app.services.icloud_backfill_schema import ensure_icloud_backfill_schema


STATUS_DRY_RUN_PREVIEW = "dry_run_preview"
STATUS_ACQUISITION_COMPLETED = "acquisition_completed"
STATUS_ACQUISITION_BLOCKED = "blocked"
STATUS_ACQUISITION_FAILED = "failed"

STOP_REASON_DRY_RUN_PREVIEW_READY = "dry_run_preview_ready"
STOP_REASON_NO_ELIGIBLE_INVENTORY_ROWS = "no_eligible_inventory_rows"
STOP_REASON_NO_SAFE_SELECTIONS = "no_safe_inventory_selections"
STOP_REASON_SOURCE_INTAKE_REQUIRED = "source_intake_required"
STOP_REASON_SOURCE_INTAKE_COMPLETED = "source_intake_completed"
STOP_REASON_SOURCE_INTAKE_FAILED = "source_intake_failed"
STOP_REASON_SOURCE_INTAKE_BLOCKED = "source_intake_blocked"
STOP_REASON_PREFLIGHT_BLOCKED = "preflight_blocked"
STOP_REASON_ACQUISITION_FAILED = "acquisition_failed"

NEXT_REVIEW_PREVIEW = "review_preview"
NEXT_RUN_ACQUIRE = "run_acquire_with_dry_run_false"
NEXT_RETRY_ACQUISITION = "retry_acquisition"
NEXT_REVIEW_SOURCE_INTAKE_FAILURE = "review_source_intake_failure"
NEXT_RUN_SOURCE_INTAKE = "run_source_intake"
NEXT_RUN_INVENTORY_SCAN = "run_inventory_scan"

STATE_SELECTED = "selected"
STATE_ACQUIRING = "acquiring"
STATE_STAGED = "staged"
STATE_SOURCE_INTAKE_REQUIRED = "source_intake_required"
STATE_SOURCE_INTAKE_COMPLETED = "source_intake_completed"
STATE_SOURCE_INTAKE_FAILED = "source_intake_failed"
STATE_SOURCE_INTAKE_PARTIAL_FAILED = "source_intake_partial_failed"
STATE_FAILED_RETRYABLE = "failed_retryable"

RESOLUTION_NEWLY_IMPORTED = "newly_imported"
RESOLUTION_EXACT_DUPLICATE_RESOLVED = "exact_duplicate_resolved"
RESOLUTION_ALREADY_KNOWN = "already_known"
RESOLUTION_FAILED_RETRYABLE = "failed_retryable"
RESOLUTION_SOURCE_INTAKE_PARTIAL_FAILED = "source_intake_partial_failed"

_RESOURCE_SUCCESS_STATES = {
    STATUS_RESOURCE_INTAKE_PROCESSED,
    STATUS_RESOURCE_INTAKE_DUPLICATE_LINKED,
    STATUS_RESOURCE_INTAKE_SKIPPED_KNOWN,
}


@dataclass(frozen=True)
class IcloudBackfillAcquireItem:
    inventory_id: int
    acquisition_state: str | None
    backfill_completed: bool
    backfill_resolution_state: str | None


@dataclass(frozen=True)
class IcloudBackfillAcquireResult:
    source_id: int
    status: str
    dry_run: bool
    auto_run_source_intake: bool
    selected_inventory_count: int
    matched_listing_count: int
    selected_logical_count: int
    selected_resource_count: int
    downloaded_logical_count: int
    downloaded_resource_count: int
    source_intake_attempted: bool
    source_intake_succeeded: bool
    source_intake_run_id: int | None
    acquisition_run_id: int | None
    acquisition_batch_id: int | None
    backfill_completed_count: int
    skipped_stale_count: int
    skipped_known_count: int
    skipped_unsupported_count: int
    skipped_ambiguous_count: int
    skipped_missing_identity_count: int
    skipped_pending_classification_count: int
    skipped_completed_count: int
    failed_retryable_count: int
    failed_terminal_count: int
    stop_reason: str
    next_safe_action: str
    items: tuple[IcloudBackfillAcquireItem, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class _PreparedSelection:
    selected_rows: tuple[IcloudRemoteAssetInventory, ...]
    selected_items: tuple[ExactSelectionLogicalItem, ...]
    selected_resource_count: int
    matched_count: int
    stale_count: int
    unsafe_count: int
    selection_skips: object


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _result_from_preview(
    preview: IcloudBackfillAcquisitionPreviewResult,
    *,
    auto_run_source_intake: bool,
) -> IcloudBackfillAcquireResult:
    return IcloudBackfillAcquireResult(
        source_id=preview.source_id,
        status=STATUS_DRY_RUN_PREVIEW,
        dry_run=True,
        auto_run_source_intake=auto_run_source_intake,
        selected_inventory_count=preview.selected_inventory_count,
        matched_listing_count=preview.matched_listing_count,
        selected_logical_count=preview.preview_selected_logical_count,
        selected_resource_count=preview.preview_selected_resource_count,
        downloaded_logical_count=0,
        downloaded_resource_count=0,
        source_intake_attempted=False,
        source_intake_succeeded=False,
        source_intake_run_id=None,
        acquisition_run_id=None,
        acquisition_batch_id=None,
        backfill_completed_count=0,
        skipped_stale_count=preview.skipped_stale_count,
        skipped_known_count=preview.skipped_known_count,
        skipped_unsupported_count=preview.skipped_unsupported_count,
        skipped_ambiguous_count=preview.skipped_ambiguous_count,
        skipped_missing_identity_count=preview.skipped_missing_identity_count,
        skipped_pending_classification_count=preview.skipped_pending_classification_count,
        skipped_completed_count=preview.skipped_completed_count,
        failed_retryable_count=0,
        failed_terminal_count=0,
        stop_reason=STOP_REASON_DRY_RUN_PREVIEW_READY,
        next_safe_action=NEXT_RUN_ACQUIRE,
    )


def _prepare_selection(
    db_session: Session,
    *,
    source_id: int,
    acquire_limit: int,
    max_listing_candidates: int,
    helper_client: ExactSelectionHelperClient,
) -> _PreparedSelection:
    source = _validate_source_profile(db_session, source_id=source_id)
    selection = _select_inventory_rows(
        db_session,
        source_id=source_id,
        acquire_limit=acquire_limit,
    )
    if not selection.selected_rows:
        return _PreparedSelection((), (), 0, 0, 0, 0, selection)

    listing = helper_client.list_candidates(
        account_username=str(source.account_username or "").strip(),
        candidate_scan_limit=max_listing_candidates,
    )
    lookup = _listing_by_remote_identity(listing)
    safe_rows: list[IcloudRemoteAssetInventory] = []
    safe_items: list[ExactSelectionLogicalItem] = []
    matched_count = 0
    stale_count = 0
    unsafe_count = 0
    for row in selection.selected_rows:
        item = lookup.get((row.remote_identity or "").strip())
        if item is None:
            stale_count += 1
            row.acquisition_state = "skipped_stale_retryable"
            row.backfill_resolution_state = "skipped_stale_retryable"
            continue
        matched_count += 1
        if _manifest_unsafe(inventory_row=row, listing_item=item):
            unsafe_count += 1
            row.acquisition_state = STATE_FAILED_RETRYABLE
            row.backfill_resolution_state = RESOLUTION_FAILED_RETRYABLE
            row.last_error_code = "unsafe_manifest"
            row.last_error_message = "Fresh helper listing did not expose a complete safe resource manifest."
            continue
        safe_rows.append(row)
        safe_items.append(item)

    db_session.commit()
    return _PreparedSelection(
        selected_rows=tuple(safe_rows),
        selected_items=tuple(safe_items),
        selected_resource_count=sum(len(item.resources) for item in safe_items),
        matched_count=matched_count,
        stale_count=stale_count,
        unsafe_count=unsafe_count,
        selection_skips=selection,
    )


def _mark_attempt_started(
    db_session: Session,
    *,
    rows: tuple[IcloudRemoteAssetInventory, ...],
) -> None:
    now = _now_utc()
    for row in rows:
        row.acquisition_state = STATE_ACQUIRING
        row.acquisition_attempt_count = int(row.acquisition_attempt_count or 0) + 1
        row.last_acquisition_attempt_at = now
        row.last_error_code = None
        row.last_error_message = None
    db_session.commit()


def _mark_acquisition_result(
    db_session: Session,
    *,
    rows: tuple[IcloudRemoteAssetInventory, ...],
    durable_result: DurableExactRunResult,
) -> None:
    for row in rows:
        row.acquisition_run_id = durable_result.run_id
        row.acquisition_batch_id = durable_result.batch_id
        if durable_result.batch_ready_for_source_intake:
            row.acquisition_state = STATE_STAGED
            row.backfill_resolution_state = None
            row.last_error_code = None
            row.last_error_message = None
        else:
            row.acquisition_state = STATE_FAILED_RETRYABLE
            row.backfill_resolution_state = RESOLUTION_FAILED_RETRYABLE
            row.last_error_code = durable_result.stop_reason or "acquisition_failed"
            row.last_error_message = "Durable acquisition did not produce a batch ready for Source Intake."
    db_session.commit()


def _resolution_for_successful_resources(statuses: list[str | None]) -> str:
    if statuses and all(status == STATUS_RESOURCE_INTAKE_SKIPPED_KNOWN for status in statuses):
        return RESOLUTION_ALREADY_KNOWN
    if any(status == STATUS_RESOURCE_INTAKE_DUPLICATE_LINKED for status in statuses):
        return RESOLUTION_EXACT_DUPLICATE_RESOLVED
    return RESOLUTION_NEWLY_IMPORTED


def _apply_source_intake_result(
    db_session: Session,
    *,
    rows: tuple[IcloudRemoteAssetInventory, ...],
    intake_result: BatchSourceIntakeResult,
) -> int:
    if intake_result.acquisition_batch_id is None:
        return 0
    batch = db_session.get(IcloudAcquisitionBatch, intake_result.acquisition_batch_id)
    if batch is None:
        return 0

    completed_count = 0
    batch_items = sorted(batch.items, key=lambda item: item.item_index)
    now = _now_utc()
    for row, item in zip(rows, batch_items, strict=False):
        row.source_intake_run_id = intake_result.source_intake_run_id
        row.acquisition_run_id = intake_result.acquisition_run_id
        row.acquisition_batch_id = intake_result.acquisition_batch_id
        statuses = [resource.source_intake_status for resource in item.resources]
        if statuses and all(status in _RESOURCE_SUCCESS_STATES for status in statuses):
            row.backfill_completed = True
            row.backfill_completed_at = now
            row.backfill_resolution_state = _resolution_for_successful_resources(statuses)
            row.acquisition_state = STATE_SOURCE_INTAKE_COMPLETED
            row.last_error_code = None
            row.last_error_message = None
            completed_count += 1
        else:
            row.backfill_completed = False
            row.backfill_resolution_state = RESOLUTION_SOURCE_INTAKE_PARTIAL_FAILED
            row.acquisition_state = STATE_SOURCE_INTAKE_PARTIAL_FAILED
            row.last_error_code = intake_result.stop_reason or "source_intake_partial_failed"
            row.last_error_message = "Not every selected resource was resolved by Source Intake."
    db_session.commit()
    return completed_count


def _safe_items(
    *,
    rows: tuple[IcloudRemoteAssetInventory, ...],
    include_items: bool,
) -> tuple[IcloudBackfillAcquireItem, ...]:
    if not include_items:
        return ()
    return tuple(
        IcloudBackfillAcquireItem(
            inventory_id=row.id,
            acquisition_state=row.acquisition_state,
            backfill_completed=bool(row.backfill_completed),
            backfill_resolution_state=row.backfill_resolution_state,
        )
        for row in rows
    )


def run_icloud_backfill_acquisition(
    db_session: Session,
    *,
    source_id: int,
    acquire_limit: int = DEFAULT_ACQUIRE_PREVIEW_LIMIT,
    max_listing_candidates: int = DEFAULT_MAX_LISTING_CANDIDATES,
    dry_run: bool = True,
    auto_run_source_intake: bool = True,
    include_items: bool = False,
    helper_client: ExactSelectionHelperClient | None = None,
) -> IcloudBackfillAcquireResult:
    """Run dry-run preview or real inventory-driven acquisition with Source Intake handoff."""

    ensure_icloud_backfill_schema(db_session)
    _validate_acquire_limit(acquire_limit)
    _validate_listing_limit(max_listing_candidates)

    helper = helper_client or ExactSelectionHelperClient()
    if dry_run:
        preview = preview_icloud_backfill_acquisition(
            db_session,
            source_id=source_id,
            acquire_limit=acquire_limit,
            max_listing_candidates=max_listing_candidates,
            include_items=include_items,
            helper_client=helper,
        )
        return _result_from_preview(preview, auto_run_source_intake=auto_run_source_intake)

    prepared = _prepare_selection(
        db_session,
        source_id=source_id,
        acquire_limit=acquire_limit,
        max_listing_candidates=max_listing_candidates,
        helper_client=helper,
    )
    skips = prepared.selection_skips
    if not prepared.selected_rows:
        stop_reason = (
            STOP_REASON_NO_ELIGIBLE_INVENTORY_ROWS
            if not getattr(skips, "selected_rows", None)
            else STOP_REASON_NO_SAFE_SELECTIONS
        )
        return IcloudBackfillAcquireResult(
            source_id=source_id,
            status=STATUS_ACQUISITION_BLOCKED,
            dry_run=False,
            auto_run_source_intake=auto_run_source_intake,
            selected_inventory_count=len(getattr(skips, "selected_rows", [])),
            matched_listing_count=prepared.matched_count,
            selected_logical_count=0,
            selected_resource_count=0,
            downloaded_logical_count=0,
            downloaded_resource_count=0,
            source_intake_attempted=False,
            source_intake_succeeded=False,
            source_intake_run_id=None,
            acquisition_run_id=None,
            acquisition_batch_id=None,
            backfill_completed_count=0,
            skipped_stale_count=prepared.stale_count,
            skipped_known_count=skips.skipped_known_count,
            skipped_unsupported_count=skips.skipped_unsupported_count,
            skipped_ambiguous_count=skips.skipped_ambiguous_count,
            skipped_missing_identity_count=skips.skipped_missing_identity_count,
            skipped_pending_classification_count=skips.skipped_pending_classification_count,
            skipped_completed_count=skips.skipped_completed_count,
            failed_retryable_count=prepared.unsafe_count,
            failed_terminal_count=0,
            stop_reason=stop_reason,
            next_safe_action=NEXT_RUN_INVENTORY_SCAN,
        )

    from app.services.admin.ingestion_operation_guardrail_service import (
        get_ingestion_operation_guardrail_snapshot,
    )

    guardrail = get_ingestion_operation_guardrail_snapshot(db_session, source_id=source_id)
    if guardrail.blocked:
        return IcloudBackfillAcquireResult(
            source_id=source_id,
            status=STATUS_ACQUISITION_BLOCKED,
            dry_run=False,
            auto_run_source_intake=auto_run_source_intake,
            selected_inventory_count=len(getattr(skips, "selected_rows", [])),
            matched_listing_count=prepared.matched_count,
            selected_logical_count=len(prepared.selected_rows),
            selected_resource_count=prepared.selected_resource_count,
            downloaded_logical_count=0,
            downloaded_resource_count=0,
            source_intake_attempted=False,
            source_intake_succeeded=False,
            source_intake_run_id=None,
            acquisition_run_id=None,
            acquisition_batch_id=None,
            backfill_completed_count=0,
            skipped_stale_count=prepared.stale_count,
            skipped_known_count=skips.skipped_known_count,
            skipped_unsupported_count=skips.skipped_unsupported_count,
            skipped_ambiguous_count=skips.skipped_ambiguous_count,
            skipped_missing_identity_count=skips.skipped_missing_identity_count,
            skipped_pending_classification_count=skips.skipped_pending_classification_count,
            skipped_completed_count=skips.skipped_completed_count,
            failed_retryable_count=0,
            failed_terminal_count=0,
            stop_reason=STOP_REASON_PREFLIGHT_BLOCKED,
            next_safe_action=NEXT_RETRY_ACQUISITION,
            items=_safe_items(rows=prepared.selected_rows, include_items=include_items),
        )

    try:
        profile = validate_exact_selection_profile(db_session, source_id=source_id)
        request = build_exact_download_request_for_listing_items(
            profile=profile,
            selected_items=prepared.selected_items,
            candidate_scan_limit=max_listing_candidates,
            library=DEFAULT_LIBRARY,
        )
    except (ExactSelectionPrototypeError, ExactSelectionProtocolError) as exc:
        code = getattr(exc, "code", "preflight_blocked")
        for row in prepared.selected_rows:
            row.acquisition_state = STATE_FAILED_RETRYABLE
            row.backfill_resolution_state = RESOLUTION_FAILED_RETRYABLE
            row.last_error_code = code
            row.last_error_message = str(exc)
        db_session.commit()
        return IcloudBackfillAcquireResult(
            source_id=source_id,
            status=STATUS_ACQUISITION_BLOCKED,
            dry_run=False,
            auto_run_source_intake=auto_run_source_intake,
            selected_inventory_count=len(getattr(skips, "selected_rows", [])),
            matched_listing_count=prepared.matched_count,
            selected_logical_count=len(prepared.selected_rows),
            selected_resource_count=prepared.selected_resource_count,
            downloaded_logical_count=0,
            downloaded_resource_count=0,
            source_intake_attempted=False,
            source_intake_succeeded=False,
            source_intake_run_id=None,
            acquisition_run_id=None,
            acquisition_batch_id=None,
            backfill_completed_count=0,
            skipped_stale_count=prepared.stale_count,
            skipped_known_count=skips.skipped_known_count,
            skipped_unsupported_count=skips.skipped_unsupported_count,
            skipped_ambiguous_count=skips.skipped_ambiguous_count,
            skipped_missing_identity_count=skips.skipped_missing_identity_count,
            skipped_pending_classification_count=skips.skipped_pending_classification_count,
            skipped_completed_count=skips.skipped_completed_count,
            failed_retryable_count=len(prepared.selected_rows),
            failed_terminal_count=0,
            stop_reason=STOP_REASON_PREFLIGHT_BLOCKED,
            next_safe_action=NEXT_RETRY_ACQUISITION,
            items=_safe_items(rows=prepared.selected_rows, include_items=include_items),
        )
    selected_listing = ExactSelectionListing(
        source_exhausted=True,
        scan_limit_reached=False,
        logical_item_count=len(prepared.selected_items),
        resource_file_count=prepared.selected_resource_count,
        ambiguous_item_count=0,
        items=prepared.selected_items,
    )
    preparation = ExactSelectionPreparation(
        status=PREPARATION_READY,
        stopping_reason="inventory_selection_ready",
        guidance=None,
        auth_state=None,
        profile=profile,
        listing=selected_listing,
        plan=None,
        download_request=request,
    )

    _mark_attempt_started(db_session, rows=prepared.selected_rows)
    try:
        durable_result = run_durable_exact_selection_preparation(
            db_session,
            source_id=source_id,
            preparation=preparation,
            helper_client=helper,
            target_new_item_count=len(prepared.selected_rows),
            candidate_scan_limit=max_listing_candidates,
            created_by="icloud_backfill_acquire",
        )
    except DurableExactAcquisitionError as exc:
        for row in prepared.selected_rows:
            row.acquisition_state = STATE_FAILED_RETRYABLE
            row.backfill_resolution_state = RESOLUTION_FAILED_RETRYABLE
            row.last_error_code = exc.code
            row.last_error_message = str(exc)
        db_session.commit()
        return IcloudBackfillAcquireResult(
            source_id=source_id,
            status=STATUS_ACQUISITION_FAILED,
            dry_run=False,
            auto_run_source_intake=auto_run_source_intake,
            selected_inventory_count=len(getattr(skips, "selected_rows", [])),
            matched_listing_count=prepared.matched_count,
            selected_logical_count=len(prepared.selected_rows),
            selected_resource_count=prepared.selected_resource_count,
            downloaded_logical_count=0,
            downloaded_resource_count=0,
            source_intake_attempted=False,
            source_intake_succeeded=False,
            source_intake_run_id=None,
            acquisition_run_id=None,
            acquisition_batch_id=None,
            backfill_completed_count=0,
            skipped_stale_count=prepared.stale_count,
            skipped_known_count=skips.skipped_known_count,
            skipped_unsupported_count=skips.skipped_unsupported_count,
            skipped_ambiguous_count=skips.skipped_ambiguous_count,
            skipped_missing_identity_count=skips.skipped_missing_identity_count,
            skipped_pending_classification_count=skips.skipped_pending_classification_count,
            skipped_completed_count=skips.skipped_completed_count,
            failed_retryable_count=len(prepared.selected_rows),
            failed_terminal_count=0,
            stop_reason=exc.code,
            next_safe_action=NEXT_RETRY_ACQUISITION,
            items=_safe_items(rows=prepared.selected_rows, include_items=include_items),
        )

    _mark_acquisition_result(db_session, rows=prepared.selected_rows, durable_result=durable_result)
    batch = db_session.get(IcloudAcquisitionBatch, durable_result.batch_id) if durable_result.batch_id else None
    downloaded_logical_count = int(batch.downloaded_item_count if batch is not None else 0)
    downloaded_resource_count = int(batch.downloaded_resource_count if batch is not None else 0)

    if not durable_result.batch_ready_for_source_intake or durable_result.batch_id is None:
        return IcloudBackfillAcquireResult(
            source_id=source_id,
            status=STATUS_ACQUISITION_FAILED,
            dry_run=False,
            auto_run_source_intake=auto_run_source_intake,
            selected_inventory_count=len(getattr(skips, "selected_rows", [])),
            matched_listing_count=prepared.matched_count,
            selected_logical_count=len(prepared.selected_rows),
            selected_resource_count=prepared.selected_resource_count,
            downloaded_logical_count=downloaded_logical_count,
            downloaded_resource_count=downloaded_resource_count,
            source_intake_attempted=False,
            source_intake_succeeded=False,
            source_intake_run_id=None,
            acquisition_run_id=durable_result.run_id,
            acquisition_batch_id=durable_result.batch_id,
            backfill_completed_count=0,
            skipped_stale_count=prepared.stale_count,
            skipped_known_count=skips.skipped_known_count,
            skipped_unsupported_count=skips.skipped_unsupported_count,
            skipped_ambiguous_count=skips.skipped_ambiguous_count,
            skipped_missing_identity_count=skips.skipped_missing_identity_count,
            skipped_pending_classification_count=skips.skipped_pending_classification_count,
            skipped_completed_count=skips.skipped_completed_count,
            failed_retryable_count=len(prepared.selected_rows),
            failed_terminal_count=0,
            stop_reason=durable_result.stop_reason or STOP_REASON_ACQUISITION_FAILED,
            next_safe_action=durable_result.next_safe_action or NEXT_RETRY_ACQUISITION,
            items=_safe_items(rows=prepared.selected_rows, include_items=include_items),
        )

    if not auto_run_source_intake:
        for row in prepared.selected_rows:
            row.acquisition_state = STATE_SOURCE_INTAKE_REQUIRED
        db_session.commit()
        return IcloudBackfillAcquireResult(
            source_id=source_id,
            status=STATUS_ACQUISITION_COMPLETED,
            dry_run=False,
            auto_run_source_intake=False,
            selected_inventory_count=len(getattr(skips, "selected_rows", [])),
            matched_listing_count=prepared.matched_count,
            selected_logical_count=len(prepared.selected_rows),
            selected_resource_count=prepared.selected_resource_count,
            downloaded_logical_count=downloaded_logical_count,
            downloaded_resource_count=downloaded_resource_count,
            source_intake_attempted=False,
            source_intake_succeeded=False,
            source_intake_run_id=None,
            acquisition_run_id=durable_result.run_id,
            acquisition_batch_id=durable_result.batch_id,
            backfill_completed_count=0,
            skipped_stale_count=prepared.stale_count,
            skipped_known_count=skips.skipped_known_count,
            skipped_unsupported_count=skips.skipped_unsupported_count,
            skipped_ambiguous_count=skips.skipped_ambiguous_count,
            skipped_missing_identity_count=skips.skipped_missing_identity_count,
            skipped_pending_classification_count=skips.skipped_pending_classification_count,
            skipped_completed_count=skips.skipped_completed_count,
            failed_retryable_count=0,
            failed_terminal_count=0,
            stop_reason=STOP_REASON_SOURCE_INTAKE_REQUIRED,
            next_safe_action=NEXT_RUN_SOURCE_INTAKE,
            items=_safe_items(rows=prepared.selected_rows, include_items=include_items),
        )

    intake_result = run_batch_source_intake(
        db_session,
        batch_id=durable_result.batch_id,
        source_id=source_id,
        created_by="icloud_backfill_acquire",
    )
    intake_succeeded = (
        intake_result.status == STATUS_BATCH_INTAKE_COMPLETED
        and intake_result.stop_reason in {None, "already_processed"}
    )
    completed_count = _apply_source_intake_result(
        db_session,
        rows=prepared.selected_rows,
        intake_result=intake_result,
    )
    failed_retryable_count = max(0, len(prepared.selected_rows) - completed_count)
    return IcloudBackfillAcquireResult(
        source_id=source_id,
        status=STATUS_ACQUISITION_COMPLETED if intake_succeeded else STATUS_ACQUISITION_FAILED,
        dry_run=False,
        auto_run_source_intake=True,
        selected_inventory_count=len(getattr(skips, "selected_rows", [])),
        matched_listing_count=prepared.matched_count,
        selected_logical_count=len(prepared.selected_rows),
        selected_resource_count=prepared.selected_resource_count,
        downloaded_logical_count=downloaded_logical_count,
        downloaded_resource_count=downloaded_resource_count,
        source_intake_attempted=True,
        source_intake_succeeded=intake_succeeded,
        source_intake_run_id=intake_result.source_intake_run_id,
        acquisition_run_id=durable_result.run_id,
        acquisition_batch_id=durable_result.batch_id,
        backfill_completed_count=completed_count,
        skipped_stale_count=prepared.stale_count,
        skipped_known_count=skips.skipped_known_count,
        skipped_unsupported_count=skips.skipped_unsupported_count,
        skipped_ambiguous_count=skips.skipped_ambiguous_count,
        skipped_missing_identity_count=skips.skipped_missing_identity_count,
        skipped_pending_classification_count=skips.skipped_pending_classification_count,
        skipped_completed_count=skips.skipped_completed_count,
        failed_retryable_count=failed_retryable_count,
        failed_terminal_count=0,
        stop_reason=(
            STOP_REASON_SOURCE_INTAKE_COMPLETED
            if intake_succeeded
            else STOP_REASON_SOURCE_INTAKE_FAILED
            if intake_result.stop_reason
            else STOP_REASON_SOURCE_INTAKE_BLOCKED
        ),
        next_safe_action=(
            intake_result.next_safe_action
            if not intake_succeeded and intake_result.next_safe_action
            else NEXT_REVIEW_SOURCE_INTAKE_FAILURE
            if not intake_succeeded
            else intake_result.next_safe_action or "cleanup_review_required"
        ),
        items=_safe_items(rows=prepared.selected_rows, include_items=include_items),
    )
