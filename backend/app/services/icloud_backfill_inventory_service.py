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
from app.services.source_profile_deferred_asset_service import (
    DeferredAssetLedgerSummary,
    DeferredAssetObservation,
    classify_deferred_asset,
    deferred_asset_counts,
    mark_deferred_identity_no_longer_deferred,
    upsert_deferred_asset_observations,
)


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
    backfill_completed_count: int
    unresolved_eligible_count: int
    acquirable_pending_count: int
    retryable_failed_count: int
    ambiguous_or_unsupported_count: int
    deferred_current_count: int
    deferred_adjusted_resource_count: int
    deferred_ambiguous_count: int
    deferred_unsupported_count: int
    deferred_new_since_last_scan_count: int
    deferred_changed_since_last_scan_count: int
    deferred_report_path: str | None
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
    backfill_completed_count: int
    unresolved_eligible_count: int
    acquirable_pending_count: int
    retryable_failed_count: int
    ambiguous_or_unsupported_count: int
    deferred_current_count: int
    deferred_adjusted_resource_count: int
    deferred_ambiguous_count: int
    deferred_unsupported_count: int
    deferred_new_since_last_scan_count: int
    deferred_changed_since_last_scan_count: int
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


def _deferred_observation_from_row(
    row: IcloudRemoteAssetInventory,
) -> DeferredAssetObservation | None:
    if not (row.remote_identity_basis or "").strip() or not (row.remote_identity or "").strip():
        return None
    classification = classify_deferred_asset(
        eligibility_state=row.eligibility_state,
        identity_ambiguous=bool(row.identity_ambiguous),
        unsupported_reasons_json=row.unsupported_reasons_json,
    )
    if classification is None:
        return None
    category, reason_code, reason_human, policy_status = classification
    return DeferredAssetObservation(
        source_profile_id=row.source_profile_id,
        inventory_id=row.id,
        source_kind="icloud",
        provider="icloud",
        remote_identity_basis=row.remote_identity_basis,
        remote_identity=row.remote_identity,
        primary_relative_path=row.primary_relative_path,
        content_type=row.primary_content_type,
        created_remote_at=row.created_remote_at,
        added_remote_at=row.added_remote_at,
        resource_count=int(row.resource_count or 0),
        is_live_photo=bool(row.is_live_photo),
        grouping=row.grouping,
        eligibility_state=row.eligibility_state,
        known_state=row.known_state,
        identity_ambiguous=bool(row.identity_ambiguous),
        unsupported_reasons_json=row.unsupported_reasons_json,
        deferred_category=category,
        deferred_reason_code=reason_code,
        deferred_reason_human=reason_human,
        policy_status=policy_status,
    )


def _inventory_counts(db_session: Session, *, source_id: int) -> tuple[int, int, int, int, int, int, int, int]:
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
    completed = db_session.scalar(
        select(func.count())
        .select_from(IcloudRemoteAssetInventory)
        .where(
            IcloudRemoteAssetInventory.source_profile_id == source_id,
            IcloudRemoteAssetInventory.backfill_completed.is_(True),
        )
    )
    unresolved_eligible = db_session.scalar(
        select(func.count())
        .select_from(IcloudRemoteAssetInventory)
        .where(
            IcloudRemoteAssetInventory.source_profile_id == source_id,
            IcloudRemoteAssetInventory.eligibility_state == ELIGIBILITY_ELIGIBLE_METADATA_ONLY,
            IcloudRemoteAssetInventory.backfill_completed.is_(False),
        )
    )
    retryable_failed = db_session.scalar(
        select(func.count())
        .select_from(IcloudRemoteAssetInventory)
        .where(
            IcloudRemoteAssetInventory.source_profile_id == source_id,
            IcloudRemoteAssetInventory.backfill_completed.is_(False),
            (
                (IcloudRemoteAssetInventory.acquisition_state == "failed_retryable")
                | (IcloudRemoteAssetInventory.backfill_resolution_state == "failed_retryable")
            ),
        )
    )
    acquirable_pending = db_session.scalar(
        select(func.count())
        .select_from(IcloudRemoteAssetInventory)
        .where(
            IcloudRemoteAssetInventory.source_profile_id == source_id,
            IcloudRemoteAssetInventory.eligibility_state == ELIGIBILITY_ELIGIBLE_METADATA_ONLY,
            IcloudRemoteAssetInventory.backfill_completed.is_(False),
            IcloudRemoteAssetInventory.known_state.in_((KNOWN_STATE_PENDING_CHECK, "unknown")),
            IcloudRemoteAssetInventory.identity_ambiguous.is_(False),
            IcloudRemoteAssetInventory.remote_identity != "",
            IcloudRemoteAssetInventory.remote_identity_basis != "",
            IcloudRemoteAssetInventory.acquisition_state.is_distinct_from("failed_retryable"),
            IcloudRemoteAssetInventory.backfill_resolution_state.is_distinct_from("failed_retryable"),
        )
    )
    unsupported_or_ambiguous_int = int(unsupported_or_ambiguous or 0)
    return (
        int(total or 0),
        int(eligible or 0),
        unsupported_or_ambiguous_int,
        int(completed or 0),
        int(unresolved_eligible or 0),
        int(acquirable_pending or 0),
        int(retryable_failed or 0),
        unsupported_or_ambiguous_int,
    )


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
    current_remote_identities: set[str] = set()
    for position, item in enumerate(listing.items, start=1):
        remote_identity = item.item_id.strip()
        if remote_identity:
            if remote_identity in current_remote_identities:
                continue
            current_remote_identities.add(remote_identity)
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

    # Session autoflush is disabled in the app; flush so first-scan count snapshots
    # include rows added above before the final transaction commit.
    db_session.flush()
    state = db_session.scalar(
        select(IcloudBackfillState)
        .where(IcloudBackfillState.source_profile_id == source_id)
        .limit(1)
    )
    deferred_run_id = state.id if state is not None else None
    inventory_rows = (
        db_session.scalars(
            select(IcloudRemoteAssetInventory).where(
                IcloudRemoteAssetInventory.source_profile_id == source_id,
                IcloudRemoteAssetInventory.remote_identity.in_(current_remote_identities),
            )
        )
        .all()
        if current_remote_identities
        else []
    )
    deferred_observations: list[DeferredAssetObservation] = []
    for row in inventory_rows:
        observation = _deferred_observation_from_row(row)
        if observation is not None:
            deferred_observations.append(observation)
        else:
            mark_deferred_identity_no_longer_deferred(
                db_session,
                source_profile_id=row.source_profile_id,
                remote_identity_basis=row.remote_identity_basis,
                remote_identity=row.remote_identity,
                inventory_id=row.id,
                observed_at=scanned_at,
                run_id=deferred_run_id,
            )
    deferred_summary: DeferredAssetLedgerSummary = upsert_deferred_asset_observations(
        db_session,
        source_profile_id=source_id,
        observations=deferred_observations,
        observed_at=scanned_at,
        run_id=deferred_run_id,
        write_report=True,
    )
    deferred_counts = deferred_asset_counts(db_session, source_profile_id=source_id)
    (
        inventory_total_count,
        eligible_count,
        unsupported_or_ambiguous_count,
        backfill_completed_count,
        unresolved_eligible_count,
        acquirable_pending_count,
        retryable_failed_count,
        ambiguous_or_unsupported_count,
    ) = _inventory_counts(
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
        backfill_completed_count=backfill_completed_count,
        unresolved_eligible_count=unresolved_eligible_count,
        acquirable_pending_count=acquirable_pending_count,
        retryable_failed_count=retryable_failed_count,
        ambiguous_or_unsupported_count=ambiguous_or_unsupported_count,
        deferred_current_count=deferred_counts.current_count,
        deferred_adjusted_resource_count=deferred_counts.adjusted_resource_count,
        deferred_ambiguous_count=deferred_counts.ambiguous_count,
        deferred_unsupported_count=deferred_counts.unsupported_count,
        deferred_new_since_last_scan_count=deferred_summary.new_deferred_count,
        deferred_changed_since_last_scan_count=deferred_summary.changed_deferred_count,
        deferred_report_path=deferred_summary.report_path,
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
    (
        inventory_total_count,
        eligible_count,
        unsupported_or_ambiguous_count,
        backfill_completed_count,
        unresolved_eligible_count,
        acquirable_pending_count,
        retryable_failed_count,
        ambiguous_or_unsupported_count,
    ) = _inventory_counts(db_session, source_id=source_id)
    deferred_counts = deferred_asset_counts(db_session, source_profile_id=source_id)
    return IcloudBackfillStatusSnapshot(
        source_id=state.source_profile_id,
        status=state.status,
        last_inventory_scan_at=state.last_inventory_scan_at,
        last_scan_candidate_count=state.last_scan_candidate_count,
        last_scan_created_count=state.last_scan_created_count,
        last_scan_updated_count=state.last_scan_updated_count,
        inventory_total_count=inventory_total_count,
        eligible_metadata_count=eligible_count,
        unsupported_or_ambiguous_count=unsupported_or_ambiguous_count,
        backfill_completed_count=backfill_completed_count,
        unresolved_eligible_count=unresolved_eligible_count,
        acquirable_pending_count=acquirable_pending_count,
        retryable_failed_count=retryable_failed_count,
        ambiguous_or_unsupported_count=ambiguous_or_unsupported_count,
        deferred_current_count=deferred_counts.current_count,
        deferred_adjusted_resource_count=deferred_counts.adjusted_resource_count,
        deferred_ambiguous_count=deferred_counts.ambiguous_count,
        deferred_unsupported_count=deferred_counts.unsupported_count,
        deferred_new_since_last_scan_count=deferred_counts.new_since_last_scan_count,
        deferred_changed_since_last_scan_count=deferred_counts.changed_since_last_scan_count,
        source_exhausted=state.source_exhausted,
        scan_limit_reached=state.scan_limit_reached,
        stop_reason=state.stop_reason,
    )
