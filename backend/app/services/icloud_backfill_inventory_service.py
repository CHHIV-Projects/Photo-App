"""Metadata-only iCloud historical backfill inventory scan service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.icloud_backfill import IcloudBackfillState, IcloudRemoteAssetInventory
from app.models.ingestion_source import IngestionSource
from app.services.icloud_acquisition.exact_selection_adapter import (
    ExactSelectionHelperClient,
    ExactSelectionListing,
    ExactSelectionLogicalItem,
)
from app.services.icloud_backfill_schema import ensure_icloud_backfill_schema


DEFAULT_INVENTORY_SCAN_LIMIT = 50_000
MAX_INVENTORY_SCAN_LIMIT = 100_000
REMOTE_IDENTITY_BASIS_HELPER_ITEM_ID = "helper_item_id_observed_stable"
ELIGIBILITY_ELIGIBLE_METADATA_ONLY = "eligible_metadata_only"
ELIGIBILITY_UNSUPPORTED_METADATA_ONLY = "unsupported_metadata_only"
ELIGIBILITY_AMBIGUOUS_METADATA_ONLY = "ambiguous_metadata_only"
KNOWN_STATE_PENDING_CHECK = "pending_known_state_check"
STATUS_INVENTORY_SCANNED = "inventory_scanned"
STOP_REASON_SOURCE_EXHAUSTED = "source_exhausted"
STOP_REASON_SCAN_LIMIT_REACHED = "scan_limit_reached"


class IcloudBackfillValidationError(ValueError):
    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


class IcloudBackfillStateNotFound(LookupError):
    pass


@dataclass(frozen=True)
class IcloudInventoryScanResult:
    source_id: int
    status: str
    scanned_count: int
    created_count: int
    updated_count: int
    inventory_total_count: int
    eligible_metadata_count: int
    unsupported_or_ambiguous_count: int
    source_exhausted: bool
    scan_limit_reached: bool
    stop_reason: str
    scanned_at: datetime


@dataclass(frozen=True)
class IcloudBackfillStatusSnapshot:
    source_id: int
    status: str
    last_inventory_scan_at: datetime | None
    last_scan_candidate_count: int
    last_scan_created_count: int
    last_scan_updated_count: int
    inventory_total_count: int
    eligible_metadata_count: int
    unsupported_or_ambiguous_count: int
    source_exhausted: bool
    scan_limit_reached: bool
    stop_reason: str | None


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _validate_max_candidates(max_candidates: int) -> None:
    if max_candidates < 1 or max_candidates > MAX_INVENTORY_SCAN_LIMIT:
        raise IcloudBackfillValidationError(
            f"max_candidates must be between 1 and {MAX_INVENTORY_SCAN_LIMIT}.",
            code="invalid_max_candidates",
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


def _primary_resource(item: ExactSelectionLogicalItem):
    for resource in item.resources:
        if resource.resource_id == "primary_original":
            return resource
    return item.resources[0] if item.resources else None


def _is_live_photo(item: ExactSelectionLogicalItem) -> bool:
    grouping = (item.grouping or "").casefold()
    if "live_photo" in grouping:
        return True
    return any(resource.resource_id == "live_photo_original" for resource in item.resources)


def _eligibility_state(item: ExactSelectionLogicalItem) -> str:
    if item.identity_ambiguous:
        return ELIGIBILITY_AMBIGUOUS_METADATA_ONLY
    if item.unsupported_reasons:
        return ELIGIBILITY_UNSUPPORTED_METADATA_ONLY
    return ELIGIBILITY_ELIGIBLE_METADATA_ONLY


def _inventory_counts(db_session: Session, *, source_id: int) -> tuple[int, int, int]:
    total = db_session.scalar(
        select(func.count())
        .select_from(IcloudRemoteAssetInventory)
        .where(IcloudRemoteAssetInventory.source_profile_id == source_id)
    )
    eligible = db_session.scalar(
        select(func.count())
        .select_from(IcloudRemoteAssetInventory)
        .where(
            IcloudRemoteAssetInventory.source_profile_id == source_id,
            IcloudRemoteAssetInventory.eligibility_state == ELIGIBILITY_ELIGIBLE_METADATA_ONLY,
        )
    )
    unsupported_or_ambiguous = db_session.scalar(
        select(func.count())
        .select_from(IcloudRemoteAssetInventory)
        .where(
            IcloudRemoteAssetInventory.source_profile_id == source_id,
            IcloudRemoteAssetInventory.eligibility_state != ELIGIBILITY_ELIGIBLE_METADATA_ONLY,
        )
    )
    return int(total or 0), int(eligible or 0), int(unsupported_or_ambiguous or 0)


def _upsert_inventory_row(
    db_session: Session,
    *,
    source_id: int,
    item: ExactSelectionLogicalItem,
    observed_remote_position: int,
    observed_at: datetime,
) -> bool:
    remote_identity = item.item_id.strip()
    if not remote_identity:
        raise IcloudBackfillValidationError(
            "Helper listing item identity was missing.",
            code="remote_identity_missing",
        )
    primary = _primary_resource(item)
    row = db_session.scalar(
        select(IcloudRemoteAssetInventory)
        .where(
            IcloudRemoteAssetInventory.source_profile_id == source_id,
            IcloudRemoteAssetInventory.remote_identity_basis == REMOTE_IDENTITY_BASIS_HELPER_ITEM_ID,
            IcloudRemoteAssetInventory.remote_identity == remote_identity,
        )
        .limit(1)
    )
    created = row is None
    if row is None:
        row = IcloudRemoteAssetInventory(
            source_profile_id=source_id,
            remote_identity=remote_identity,
            remote_identity_basis=REMOTE_IDENTITY_BASIS_HELPER_ITEM_ID,
            first_observed_at=observed_at,
        )
        db_session.add(row)

    row.observed_remote_position = observed_remote_position
    row.observed_at = observed_at
    row.last_observed_at = observed_at
    row.grouping = item.grouping
    row.created_remote_at = item.created_at
    row.added_remote_at = item.added_at
    row.primary_relative_path = primary.relative_path if primary is not None else None
    row.primary_content_type = primary.content_type if primary is not None else None
    row.primary_expected_size_bytes = primary.expected_size if primary is not None else None
    row.resource_count = len(item.resources)
    row.is_live_photo = _is_live_photo(item)
    row.identity_ambiguous = item.identity_ambiguous
    row.unsupported_reasons_json = json.dumps(list(item.unsupported_reasons), separators=(",", ":"))
    row.eligibility_state = _eligibility_state(item)
    row.known_state = KNOWN_STATE_PENDING_CHECK
    row.updated_at = observed_at
    return created


def run_icloud_backfill_inventory_scan(
    db_session: Session,
    *,
    source_id: int,
    max_candidates: int = DEFAULT_INVENTORY_SCAN_LIMIT,
    helper_client: ExactSelectionHelperClient | None = None,
) -> IcloudInventoryScanResult:
    """Scan helper listing metadata into inventory without downloading files."""

    ensure_icloud_backfill_schema(db_session)
    _validate_max_candidates(max_candidates)
    source = _validate_source_profile(db_session, source_id=source_id)

    helper = helper_client or ExactSelectionHelperClient()
    scanned_at = _now_utc()
    listing: ExactSelectionListing = helper.list_candidates(
        account_username=str(source.account_username or "").strip(),
        candidate_scan_limit=max_candidates,
    )

    created_count = 0
    updated_count = 0
    for position, item in enumerate(listing.items, start=1):
        if _upsert_inventory_row(
            db_session,
            source_id=source_id,
            item=item,
            observed_remote_position=position,
            observed_at=scanned_at,
        ):
            created_count += 1
        else:
            updated_count += 1

    inventory_total_count, eligible_count, unsupported_or_ambiguous_count = _inventory_counts(
        db_session,
        source_id=source_id,
    )
    stop_reason = (
        STOP_REASON_SOURCE_EXHAUSTED if listing.source_exhausted else STOP_REASON_SCAN_LIMIT_REACHED
    )

    state = db_session.scalar(
        select(IcloudBackfillState)
        .where(IcloudBackfillState.source_profile_id == source_id)
        .limit(1)
    )
    if state is None:
        state = IcloudBackfillState(source_profile_id=source_id)
        db_session.add(state)
    state.status = STATUS_INVENTORY_SCANNED
    state.last_inventory_scan_at = scanned_at
    state.last_scan_candidate_count = len(listing.items)
    state.last_scan_created_count = created_count
    state.last_scan_updated_count = updated_count
    state.inventory_total_count = inventory_total_count
    state.eligible_metadata_count = eligible_count
    state.unsupported_or_ambiguous_count = unsupported_or_ambiguous_count
    state.source_exhausted = listing.source_exhausted
    state.scan_limit_reached = listing.scan_limit_reached
    state.stop_reason = stop_reason
    state.updated_at = scanned_at

    db_session.commit()
    return IcloudInventoryScanResult(
        source_id=source_id,
        status=state.status,
        scanned_count=len(listing.items),
        created_count=created_count,
        updated_count=updated_count,
        inventory_total_count=inventory_total_count,
        eligible_metadata_count=eligible_count,
        unsupported_or_ambiguous_count=unsupported_or_ambiguous_count,
        source_exhausted=listing.source_exhausted,
        scan_limit_reached=listing.scan_limit_reached,
        stop_reason=stop_reason,
        scanned_at=scanned_at,
    )


def get_icloud_backfill_status(
    db_session: Session,
    *,
    source_id: int,
) -> IcloudBackfillStatusSnapshot:
    ensure_icloud_backfill_schema(db_session)
    state = db_session.scalar(
        select(IcloudBackfillState)
        .where(IcloudBackfillState.source_profile_id == source_id)
        .limit(1)
    )
    if state is None:
        raise IcloudBackfillStateNotFound(f"No iCloud backfill state exists for source {source_id}.")
    return IcloudBackfillStatusSnapshot(
        source_id=state.source_profile_id,
        status=state.status,
        last_inventory_scan_at=state.last_inventory_scan_at,
        last_scan_candidate_count=state.last_scan_candidate_count,
        last_scan_created_count=state.last_scan_created_count,
        last_scan_updated_count=state.last_scan_updated_count,
        inventory_total_count=state.inventory_total_count,
        eligible_metadata_count=state.eligible_metadata_count,
        unsupported_or_ambiguous_count=state.unsupported_or_ambiguous_count,
        source_exhausted=state.source_exhausted,
        scan_limit_reached=state.scan_limit_reached,
        stop_reason=state.stop_reason,
    )
