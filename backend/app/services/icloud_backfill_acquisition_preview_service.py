"""Dry-run preview for inventory-driven historical iCloud backfill acquisition."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.icloud_backfill import IcloudRemoteAssetInventory
from app.models.ingestion_source import IngestionSource
from app.services.icloud_acquisition.exact_selection_adapter import (
    ExactSelectionHelperClient,
    ExactSelectionListing,
    ExactSelectionLogicalItem,
)
from app.services.icloud_acquisition.exact_selection_protocol import (
    MAX_LIST_CANDIDATE_SCAN_LIMIT,
    MAX_SELECTED_ITEM_COUNT,
)
from app.services.icloud_backfill_inventory_service import (
    ELIGIBILITY_AMBIGUOUS_METADATA_ONLY,
    ELIGIBILITY_ELIGIBLE_METADATA_ONLY,
    ELIGIBILITY_UNSUPPORTED_METADATA_ONLY,
    KNOWN_STATE_PENDING_CHECK,
    REMOTE_IDENTITY_BASIS_HELPER_ITEM_ID,
    IcloudBackfillValidationError,
)
from app.services.icloud_backfill_schema import ensure_icloud_backfill_schema


DEFAULT_ACQUIRE_PREVIEW_LIMIT = 500
MAX_ACQUIRE_PREVIEW_LIMIT = MAX_SELECTED_ITEM_COUNT
DEFAULT_MAX_LISTING_CANDIDATES = MAX_LIST_CANDIDATE_SCAN_LIMIT

STATUS_PREVIEW_COMPLETED = "preview_completed"
STOP_REASON_PREVIEW_READY = "preview_ready"
STOP_REASON_NO_ELIGIBLE_INVENTORY_ROWS = "no_eligible_inventory_rows"
STOP_REASON_LISTING_REQUERY_EMPTY = "listing_requery_empty"
STOP_REASON_ALL_SELECTED_ROWS_STALE = "all_selected_rows_stale"
STOP_REASON_LIMIT_REACHED = "limit_reached"

NEXT_REVIEW_PREVIEW = "review_preview"
NEXT_RUN_INVENTORY_SCAN = "run_inventory_scan"

_SELECTABLE_KNOWN_STATES = {KNOWN_STATE_PENDING_CHECK, "unknown"}


@dataclass(frozen=True)
class IcloudBackfillPreviewItem:
    inventory_id: int
    logical_resource_count: int
    is_live_photo: bool
    primary_relative_path: str | None


@dataclass(frozen=True)
class IcloudBackfillAcquisitionPreviewResult:
    source_id: int
    status: str
    selected_inventory_count: int
    matched_listing_count: int
    preview_selected_logical_count: int
    preview_selected_resource_count: int
    skipped_stale_count: int
    skipped_known_count: int
    skipped_unsupported_count: int
    skipped_ambiguous_count: int
    skipped_missing_identity_count: int
    skipped_pending_classification_count: int
    unsafe_manifest_count: int
    acquire_limit: int
    max_listing_candidates: int
    stop_reason: str
    next_safe_action: str
    preview_items: tuple[IcloudBackfillPreviewItem, ...] = field(default_factory=tuple)


@dataclass
class _SelectionAccumulator:
    selected_rows: list[IcloudRemoteAssetInventory] = field(default_factory=list)
    selectable_total_count: int = 0
    skipped_known_count: int = 0
    skipped_unsupported_count: int = 0
    skipped_ambiguous_count: int = 0
    skipped_missing_identity_count: int = 0
    skipped_pending_classification_count: int = 0


def _validate_acquire_limit(acquire_limit: int) -> None:
    if acquire_limit < 1 or acquire_limit > MAX_ACQUIRE_PREVIEW_LIMIT:
        raise IcloudBackfillValidationError(
            f"acquire_limit must be between 1 and {MAX_ACQUIRE_PREVIEW_LIMIT}.",
            code="invalid_acquire_limit",
        )


def _validate_listing_limit(max_listing_candidates: int) -> None:
    if max_listing_candidates < 1 or max_listing_candidates > MAX_LIST_CANDIDATE_SCAN_LIMIT:
        raise IcloudBackfillValidationError(
            f"max_listing_candidates must be between 1 and {MAX_LIST_CANDIDATE_SCAN_LIMIT}.",
            code="invalid_max_listing_candidates",
        )


def _validate_source_profile(db_session: Session, *, source_id: int) -> IngestionSource:
    source = db_session.get(IngestionSource, source_id)
    if source is None:
        raise IcloudBackfillValidationError("Source Profile not found.", code="source_not_found")
    if (source.profile_status or "").strip().lower() != "active":
        raise IcloudBackfillValidationError(
            "Only an active Source Profile can be used.",
            code="profile_not_active",
        )
    if (source.source_type or "").strip().lower() != "cloud_export" or (
        source.cloud_provider or ""
    ).strip().lower() != "icloud":
        raise IcloudBackfillValidationError(
            "The selected Source Profile is not an iCloud profile.",
            code="not_icloud_profile",
        )
    if (source.acquisition_method or "").strip().lower() != "icloudpd":
        raise IcloudBackfillValidationError(
            "The selected Source Profile does not use icloudpd.",
            code="invalid_acquisition_method",
        )
    if not (source.account_username or "").strip():
        raise IcloudBackfillValidationError(
            "The selected Source Profile has no account username.",
            code="account_username_missing",
        )
    return source


def _ordered_inventory_rows(
    db_session: Session,
    *,
    source_id: int,
) -> Iterable[IcloudRemoteAssetInventory]:
    return db_session.scalars(
        select(IcloudRemoteAssetInventory)
        .where(IcloudRemoteAssetInventory.source_profile_id == source_id)
        .order_by(
            IcloudRemoteAssetInventory.created_remote_at.is_(None),
            IcloudRemoteAssetInventory.created_remote_at.asc(),
            IcloudRemoteAssetInventory.added_remote_at.is_(None),
            IcloudRemoteAssetInventory.added_remote_at.asc(),
            IcloudRemoteAssetInventory.first_observed_at.asc(),
            IcloudRemoteAssetInventory.id.asc(),
        )
    )


def _has_required_identity(row: IcloudRemoteAssetInventory) -> bool:
    return bool((row.remote_identity_basis or "").strip() and (row.remote_identity or "").strip())


def _select_inventory_rows(
    db_session: Session,
    *,
    source_id: int,
    acquire_limit: int,
) -> _SelectionAccumulator:
    selected = _SelectionAccumulator()
    for row in _ordered_inventory_rows(db_session, source_id=source_id):
        eligibility = (row.eligibility_state or "").strip()
        known_state = (row.known_state or "").strip()

        if not _has_required_identity(row):
            selected.skipped_missing_identity_count += 1
            continue
        if known_state not in _SELECTABLE_KNOWN_STATES:
            selected.skipped_known_count += 1
            continue
        if row.identity_ambiguous or eligibility == ELIGIBILITY_AMBIGUOUS_METADATA_ONLY:
            selected.skipped_ambiguous_count += 1
            continue
        if eligibility == ELIGIBILITY_UNSUPPORTED_METADATA_ONLY:
            selected.skipped_unsupported_count += 1
            continue
        if eligibility != ELIGIBILITY_ELIGIBLE_METADATA_ONLY:
            selected.skipped_pending_classification_count += 1
            continue

        selected.selectable_total_count += 1
        if len(selected.selected_rows) < acquire_limit:
            selected.selected_rows.append(row)
    return selected


def _listing_by_remote_identity(
    listing: ExactSelectionListing,
) -> dict[str, ExactSelectionLogicalItem]:
    matched: dict[str, ExactSelectionLogicalItem] = {}
    for item in listing.items:
        item_id = (item.item_id or "").strip()
        if item_id:
            matched[item_id] = item
    return matched


def _manifest_unsafe(
    *,
    inventory_row: IcloudRemoteAssetInventory,
    listing_item: ExactSelectionLogicalItem,
) -> bool:
    if listing_item.identity_ambiguous or listing_item.unsupported_reasons:
        return True
    if not listing_item.resources:
        return True
    for resource in listing_item.resources:
        if (
            not (resource.resource_id or "").strip()
            or not (resource.relative_path or "").strip()
            or resource.expected_size is None
            or not (resource.expected_checksum or "").strip()
        ):
            return True
    return bool(inventory_row.is_live_photo and len(listing_item.resources) < 2)


def preview_icloud_backfill_acquisition(
    db_session: Session,
    *,
    source_id: int,
    acquire_limit: int = DEFAULT_ACQUIRE_PREVIEW_LIMIT,
    max_listing_candidates: int = DEFAULT_MAX_LISTING_CANDIDATES,
    include_items: bool = False,
    helper_client: ExactSelectionHelperClient | None = None,
) -> IcloudBackfillAcquisitionPreviewResult:
    """Preview inventory-driven selection without downloading, staging, or mutating inventory rows."""

    ensure_icloud_backfill_schema(db_session)
    _validate_acquire_limit(acquire_limit)
    _validate_listing_limit(max_listing_candidates)
    source = _validate_source_profile(db_session, source_id=source_id)

    selection = _select_inventory_rows(
        db_session,
        source_id=source_id,
        acquire_limit=acquire_limit,
    )
    if not selection.selected_rows:
        return IcloudBackfillAcquisitionPreviewResult(
            source_id=source_id,
            status=STATUS_PREVIEW_COMPLETED,
            selected_inventory_count=0,
            matched_listing_count=0,
            preview_selected_logical_count=0,
            preview_selected_resource_count=0,
            skipped_stale_count=0,
            skipped_known_count=selection.skipped_known_count,
            skipped_unsupported_count=selection.skipped_unsupported_count,
            skipped_ambiguous_count=selection.skipped_ambiguous_count,
            skipped_missing_identity_count=selection.skipped_missing_identity_count,
            skipped_pending_classification_count=selection.skipped_pending_classification_count,
            unsafe_manifest_count=0,
            acquire_limit=acquire_limit,
            max_listing_candidates=max_listing_candidates,
            stop_reason=STOP_REASON_NO_ELIGIBLE_INVENTORY_ROWS,
            next_safe_action=NEXT_RUN_INVENTORY_SCAN,
        )

    helper = helper_client or ExactSelectionHelperClient()
    listing = helper.list_candidates(
        account_username=str(source.account_username or "").strip(),
        candidate_scan_limit=max_listing_candidates,
    )
    if not listing.items:
        return IcloudBackfillAcquisitionPreviewResult(
            source_id=source_id,
            status=STATUS_PREVIEW_COMPLETED,
            selected_inventory_count=len(selection.selected_rows),
            matched_listing_count=0,
            preview_selected_logical_count=0,
            preview_selected_resource_count=0,
            skipped_stale_count=len(selection.selected_rows),
            skipped_known_count=selection.skipped_known_count,
            skipped_unsupported_count=selection.skipped_unsupported_count,
            skipped_ambiguous_count=selection.skipped_ambiguous_count,
            skipped_missing_identity_count=selection.skipped_missing_identity_count,
            skipped_pending_classification_count=selection.skipped_pending_classification_count,
            unsafe_manifest_count=0,
            acquire_limit=acquire_limit,
            max_listing_candidates=max_listing_candidates,
            stop_reason=STOP_REASON_LISTING_REQUERY_EMPTY,
            next_safe_action=NEXT_RUN_INVENTORY_SCAN,
        )

    listing_lookup = _listing_by_remote_identity(listing)
    matched_count = 0
    stale_count = 0
    preview_logical_count = 0
    preview_resource_count = 0
    unsafe_manifest_count = 0
    preview_items: list[IcloudBackfillPreviewItem] = []

    for row in selection.selected_rows:
        item = listing_lookup.get((row.remote_identity or "").strip())
        if item is None:
            stale_count += 1
            continue
        matched_count += 1
        if _manifest_unsafe(inventory_row=row, listing_item=item):
            unsafe_manifest_count += 1
            continue
        preview_logical_count += 1
        preview_resource_count += len(item.resources)
        if include_items:
            preview_items.append(
                IcloudBackfillPreviewItem(
                    inventory_id=row.id,
                    logical_resource_count=len(item.resources),
                    is_live_photo=bool(row.is_live_photo),
                    primary_relative_path=row.primary_relative_path,
                )
            )

    if preview_logical_count > 0:
        stop_reason = (
            STOP_REASON_LIMIT_REACHED
            if selection.selectable_total_count > acquire_limit
            else STOP_REASON_PREVIEW_READY
        )
        next_safe_action = NEXT_REVIEW_PREVIEW
    else:
        stop_reason = STOP_REASON_ALL_SELECTED_ROWS_STALE if stale_count else STOP_REASON_PREVIEW_READY
        next_safe_action = NEXT_RUN_INVENTORY_SCAN if stale_count else NEXT_REVIEW_PREVIEW

    return IcloudBackfillAcquisitionPreviewResult(
        source_id=source_id,
        status=STATUS_PREVIEW_COMPLETED,
        selected_inventory_count=len(selection.selected_rows),
        matched_listing_count=matched_count,
        preview_selected_logical_count=preview_logical_count,
        preview_selected_resource_count=preview_resource_count,
        skipped_stale_count=stale_count,
        skipped_known_count=selection.skipped_known_count,
        skipped_unsupported_count=selection.skipped_unsupported_count,
        skipped_ambiguous_count=selection.skipped_ambiguous_count,
        skipped_missing_identity_count=selection.skipped_missing_identity_count,
        skipped_pending_classification_count=selection.skipped_pending_classification_count,
        unsafe_manifest_count=unsafe_manifest_count,
        acquire_limit=acquire_limit,
        max_listing_candidates=max_listing_candidates,
        stop_reason=stop_reason,
        next_safe_action=next_safe_action,
        preview_items=tuple(preview_items),
    )
