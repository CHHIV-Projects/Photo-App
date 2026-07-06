"""Source-profile deferred asset ledger service."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.source_profile_deferred_asset import (
    SourceProfileDeferredAsset,
    SourceProfileDeferredAssetEvent,
)
from app.services.source_profile_deferred_asset_schema import (
    ensure_source_profile_deferred_asset_schema,
)


CATEGORY_ADJUSTED_RESOURCE = "adjusted_resource_deferred"
CATEGORY_AMBIGUOUS_METADATA = "ambiguous_metadata_deferred"
CATEGORY_UNSUPPORTED_METADATA = "unsupported_metadata_deferred"
CATEGORY_PENDING_CLASSIFICATION = "pending_classification_deferred"
CATEGORY_UNKNOWN = "unknown_deferred"

POLICY_DEFERRED_PENDING_POLICY = "deferred_pending_policy"
POLICY_DEFERRED_PENDING_REVIEW = "deferred_pending_review"
STATE_ACTIVE_DEFERRED = "active_deferred"
STATE_NO_LONGER_DEFERRED = "no_longer_deferred"

EVENT_FIRST_DEFERRED = "first_deferred"
EVENT_REASON_CHANGED = "reason_changed"
EVENT_CLASSIFICATION_CHANGED = "classification_changed"

REPORT_VERSION = 1
REPORT_ROOT = (
    Path(__file__).resolve().parents[3] / "storage" / "logs" / "deferred_asset_reports"
).resolve()


@dataclass(frozen=True)
class DeferredAssetObservation:
    source_profile_id: int
    inventory_id: int | None
    source_kind: str
    provider: str | None
    remote_identity_basis: str
    remote_identity: str
    primary_relative_path: str | None
    content_type: str | None
    created_remote_at: str | None
    added_remote_at: str | None
    resource_count: int
    is_live_photo: bool
    grouping: str | None
    eligibility_state: str | None
    known_state: str | None
    identity_ambiguous: bool
    unsupported_reasons_json: str | None
    deferred_category: str
    deferred_reason_code: str
    deferred_reason_human: str
    policy_status: str
    current_state: str = STATE_ACTIVE_DEFERRED

    @property
    def filename(self) -> str | None:
        if not self.primary_relative_path:
            return None
        return Path(self.primary_relative_path.replace("\\", "/")).name

    @property
    def extension(self) -> str | None:
        if not self.primary_relative_path:
            return None
        suffix = Path(self.primary_relative_path.replace("\\", "/")).suffix.casefold()
        return suffix or None

    @property
    def safe_metadata_json(self) -> str:
        return json.dumps(
            {
                "primary_relative_path": self.primary_relative_path,
                "extension": self.extension,
                "content_type": self.content_type,
                "resource_count": self.resource_count,
                "is_live_photo": self.is_live_photo,
                "grouping": self.grouping,
                "eligibility_state": self.eligibility_state,
                "known_state": self.known_state,
                "identity_ambiguous": self.identity_ambiguous,
                "unsupported_reason_codes": parse_reason_codes(self.unsupported_reasons_json),
            },
            separators=(",", ":"),
            sort_keys=True,
        )


@dataclass(frozen=True)
class DeferredAssetLedgerSummary:
    source_profile_id: int
    run_id: int | None
    run_kind: str
    generated_at: datetime
    total_deferred_seen: int
    new_deferred_count: int
    changed_deferred_count: int
    unchanged_deferred_count: int
    resolved_count: int
    by_category: dict[str, int]
    by_reason_code: dict[str, int]
    adjusted_resource_deferred_count: int
    adjusted_single_resource_count: int
    adjusted_live_photo_grouped_count: int
    report_path: str | None = None
    safe_sample_rows: tuple[dict[str, object], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class DeferredAssetCounts:
    current_count: int = 0
    adjusted_resource_count: int = 0
    ambiguous_count: int = 0
    unsupported_count: int = 0
    new_since_last_scan_count: int = 0
    changed_since_last_scan_count: int = 0


@dataclass(frozen=True)
class DeferredAssetListItem:
    id: int
    inventory_id: int | None
    source_profile_id: int
    primary_relative_path: str | None
    filename: str | None
    extension: str | None
    content_type: str | None
    resource_count: int
    is_live_photo: bool
    grouping: str | None
    deferred_category: str
    deferred_reason_code: str
    deferred_reason_human: str
    policy_status: str
    current_state: str
    first_seen_at: datetime
    last_seen_at: datetime
    observation_count: int


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _clean_string(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text or default


def parse_reason_codes(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return [_clean_string(value)]
    if not isinstance(loaded, list):
        return []
    reasons = {
        str(reason).strip()
        for reason in loaded
        if isinstance(reason, str) and str(reason).strip()
    }
    return sorted(reasons)


def canonical_reason_json(value: str | None) -> str:
    return json.dumps(parse_reason_codes(value), separators=(",", ":"), sort_keys=True)


def classify_deferred_asset(
    *,
    eligibility_state: str | None,
    identity_ambiguous: bool,
    unsupported_reasons_json: str | None,
) -> tuple[str, str, str, str] | None:
    eligibility = _clean_string(eligibility_state).casefold()
    reasons = parse_reason_codes(unsupported_reasons_json)
    if "unsupported_adjusted_resource" in reasons:
        return (
            CATEGORY_ADJUSTED_RESOURCE,
            "unsupported_adjusted_resource",
            "Adjusted iCloud resource deferred pending product policy.",
            POLICY_DEFERRED_PENDING_POLICY,
        )
    if eligibility == "pending_classification":
        return (
            CATEGORY_PENDING_CLASSIFICATION,
            "pending_classification",
            "Asset deferred pending classification.",
            POLICY_DEFERRED_PENDING_REVIEW,
        )
    if reasons:
        return (
            CATEGORY_UNSUPPORTED_METADATA,
            reasons[0],
            "Unsupported metadata deferred pending review.",
            POLICY_DEFERRED_PENDING_REVIEW,
        )
    if identity_ambiguous:
        return (
            CATEGORY_AMBIGUOUS_METADATA,
            "identity_ambiguous",
            "Ambiguous metadata deferred pending review.",
            POLICY_DEFERRED_PENDING_REVIEW,
        )
    if eligibility and eligibility not in {"eligible_metadata_only"}:
        return (
            CATEGORY_UNKNOWN,
            eligibility,
            "Deferred asset requires review.",
            POLICY_DEFERRED_PENDING_REVIEW,
        )
    return None


def _row_meaningful_values(row: SourceProfileDeferredAsset) -> dict[str, object]:
    return {
        "deferred_category": row.deferred_category,
        "deferred_reason_code": row.deferred_reason_code,
        "eligibility_state": row.eligibility_state,
        "known_state": row.known_state,
        "identity_ambiguous": bool(row.identity_ambiguous),
        "unsupported_reasons_json": canonical_reason_json(row.unsupported_reasons_json),
        "resource_count": int(row.resource_count or 0),
        "is_live_photo": bool(row.is_live_photo),
        "grouping": row.grouping,
        "primary_relative_path": row.primary_relative_path,
        "content_type": row.content_type,
        "current_state": row.current_state,
        "policy_status": row.policy_status,
    }


def _observation_meaningful_values(observation: DeferredAssetObservation) -> dict[str, object]:
    return {
        "deferred_category": observation.deferred_category,
        "deferred_reason_code": observation.deferred_reason_code,
        "eligibility_state": observation.eligibility_state,
        "known_state": observation.known_state,
        "identity_ambiguous": bool(observation.identity_ambiguous),
        "unsupported_reasons_json": canonical_reason_json(observation.unsupported_reasons_json),
        "resource_count": int(observation.resource_count or 0),
        "is_live_photo": bool(observation.is_live_photo),
        "grouping": observation.grouping,
        "primary_relative_path": observation.primary_relative_path,
        "content_type": observation.content_type,
        "current_state": observation.current_state,
        "policy_status": observation.policy_status,
    }


def _event(
    *,
    row: SourceProfileDeferredAsset,
    event_type: str,
    event_at: datetime,
    run_id: int | None,
    run_kind: str,
    previous_state: str | None,
    previous_reason_code: str | None,
    previous_category: str | None,
    event_summary: str,
) -> SourceProfileDeferredAssetEvent:
    return SourceProfileDeferredAssetEvent(
        deferred_asset_id=row.id,
        source_profile_id=row.source_profile_id,
        inventory_id=row.inventory_id,
        event_type=event_type,
        event_at=event_at,
        run_id=run_id,
        run_kind=run_kind,
        previous_state=previous_state,
        new_state=row.current_state,
        previous_reason_code=previous_reason_code,
        new_reason_code=row.deferred_reason_code,
        previous_category=previous_category,
        new_category=row.deferred_category,
        event_summary=event_summary,
        safe_metadata_json=row.safe_metadata_json,
    )


def _mark_other_categories_no_longer_deferred(
    db_session: Session,
    *,
    observation: DeferredAssetObservation,
    event_at: datetime,
    run_id: int | None,
    run_kind: str,
) -> int:
    rows = db_session.scalars(
        select(SourceProfileDeferredAsset).where(
            SourceProfileDeferredAsset.source_profile_id == observation.source_profile_id,
            SourceProfileDeferredAsset.remote_identity_basis == observation.remote_identity_basis,
            SourceProfileDeferredAsset.remote_identity == observation.remote_identity,
            SourceProfileDeferredAsset.deferred_category != observation.deferred_category,
            SourceProfileDeferredAsset.current_state == STATE_ACTIVE_DEFERRED,
        )
    ).all()
    changed = 0
    for row in rows:
        previous_state = row.current_state
        previous_reason = row.deferred_reason_code
        previous_category = row.deferred_category
        row.current_state = STATE_NO_LONGER_DEFERRED
        row.resolved_at = event_at
        row.resolved_by_run_id = run_id
        row.resolution_state = STATE_NO_LONGER_DEFERRED
        row.last_changed_at = event_at
        row.last_seen_at = event_at
        row.last_seen_run_id = run_id
        row.observation_count = int(row.observation_count or 0) + 1
        db_session.add(
            _event(
                row=row,
                event_type=EVENT_CLASSIFICATION_CHANGED,
                event_at=event_at,
                run_id=run_id,
                run_kind=run_kind,
                previous_state=previous_state,
                previous_reason_code=previous_reason,
                previous_category=previous_category,
                event_summary="Deferred asset category is no longer current.",
            )
        )
        changed += 1
    return changed


def mark_deferred_identity_no_longer_deferred(
    db_session: Session,
    *,
    source_profile_id: int,
    remote_identity_basis: str,
    remote_identity: str,
    inventory_id: int | None = None,
    observed_at: datetime | None = None,
    run_id: int | None = None,
    run_kind: str = "icloud_backfill_inventory_scan",
) -> int:
    """Mark all active deferrals for one identity as no longer deferred."""

    ensure_source_profile_deferred_asset_schema(db_session)
    event_at = observed_at or _now_utc()
    rows = db_session.scalars(
        select(SourceProfileDeferredAsset).where(
            SourceProfileDeferredAsset.source_profile_id == source_profile_id,
            SourceProfileDeferredAsset.remote_identity_basis == remote_identity_basis,
            SourceProfileDeferredAsset.remote_identity == remote_identity,
            SourceProfileDeferredAsset.current_state == STATE_ACTIVE_DEFERRED,
        )
    ).all()
    for row in rows:
        previous_state = row.current_state
        previous_reason = row.deferred_reason_code
        previous_category = row.deferred_category
        row.inventory_id = inventory_id
        row.current_state = STATE_NO_LONGER_DEFERRED
        row.resolved_at = event_at
        row.resolved_by_run_id = run_id
        row.resolution_state = STATE_NO_LONGER_DEFERRED
        row.last_seen_at = event_at
        row.last_seen_run_id = run_id
        row.last_changed_at = event_at
        row.observation_count = int(row.observation_count or 0) + 1
        db_session.add(
            _event(
                row=row,
                event_type=EVENT_CLASSIFICATION_CHANGED,
                event_at=event_at,
                run_id=run_id,
                run_kind=run_kind,
                previous_state=previous_state,
                previous_reason_code=previous_reason,
                previous_category=previous_category,
                event_summary="Deferred asset is no longer classified as deferred.",
            )
        )
    db_session.commit()
    return len(rows)


def _apply_observation(
    row: SourceProfileDeferredAsset,
    observation: DeferredAssetObservation,
    observed_at: datetime,
    run_id: int | None,
) -> None:
    row.inventory_id = observation.inventory_id
    row.source_kind = observation.source_kind
    row.provider = observation.provider
    row.primary_relative_path = observation.primary_relative_path
    row.filename = observation.filename
    row.extension = observation.extension
    row.content_type = observation.content_type
    row.created_remote_at = observation.created_remote_at
    row.added_remote_at = observation.added_remote_at
    row.resource_count = int(observation.resource_count or 0)
    row.is_live_photo = bool(observation.is_live_photo)
    row.grouping = observation.grouping
    row.eligibility_state = observation.eligibility_state
    row.known_state = observation.known_state
    row.identity_ambiguous = bool(observation.identity_ambiguous)
    row.unsupported_reasons_json = canonical_reason_json(observation.unsupported_reasons_json)
    row.deferred_category = observation.deferred_category
    row.deferred_reason_code = observation.deferred_reason_code
    row.deferred_reason_human = observation.deferred_reason_human
    row.policy_status = observation.policy_status
    row.current_state = observation.current_state
    row.last_seen_at = observed_at
    row.last_seen_run_id = run_id
    row.safe_metadata_json = observation.safe_metadata_json
    if observation.current_state == STATE_ACTIVE_DEFERRED:
        row.resolved_at = None
        row.resolved_by_run_id = None
        row.resolution_state = None


def upsert_deferred_asset_observations(
    db_session: Session,
    *,
    source_profile_id: int,
    observations: Iterable[DeferredAssetObservation],
    observed_at: datetime | None = None,
    run_id: int | None = None,
    run_kind: str = "icloud_backfill_inventory_scan",
    write_report: bool = True,
) -> DeferredAssetLedgerSummary:
    ensure_source_profile_deferred_asset_schema(db_session)
    event_at = observed_at or _now_utc()
    observation_list = list(observations)
    new_count = 0
    changed_count = 0
    unchanged_count = 0
    resolved_count = 0
    by_category: Counter[str] = Counter()
    by_reason: Counter[str] = Counter()
    safe_samples: list[dict[str, object]] = []

    for observation in observation_list:
        by_category[observation.deferred_category] += 1
        by_reason[observation.deferred_reason_code] += 1
        row = db_session.scalar(
            select(SourceProfileDeferredAsset)
            .where(
                SourceProfileDeferredAsset.source_profile_id == observation.source_profile_id,
                SourceProfileDeferredAsset.remote_identity_basis
                == observation.remote_identity_basis,
                SourceProfileDeferredAsset.remote_identity == observation.remote_identity,
                SourceProfileDeferredAsset.deferred_category == observation.deferred_category,
            )
            .limit(1)
        )
        if row is None:
            row = SourceProfileDeferredAsset(
                source_profile_id=observation.source_profile_id,
                remote_identity_basis=observation.remote_identity_basis,
                remote_identity=observation.remote_identity,
                first_seen_at=event_at,
                last_seen_at=event_at,
                first_seen_run_id=run_id,
                last_seen_run_id=run_id,
                last_changed_at=event_at,
                observation_count=1,
                source_kind=observation.source_kind,
                deferred_category=observation.deferred_category,
                deferred_reason_code=observation.deferred_reason_code,
                deferred_reason_human=observation.deferred_reason_human,
                policy_status=observation.policy_status,
                current_state=observation.current_state,
            )
            db_session.add(row)
            _apply_observation(row, observation, event_at, run_id)
            db_session.flush()
            db_session.add(
                _event(
                    row=row,
                    event_type=EVENT_FIRST_DEFERRED,
                    event_at=event_at,
                    run_id=run_id,
                    run_kind=run_kind,
                    previous_state=None,
                    previous_reason_code=None,
                    previous_category=None,
                    event_summary="Deferred asset first observed.",
                )
            )
            new_count += 1
        else:
            previous = _row_meaningful_values(row)
            previous_state = row.current_state
            previous_reason = row.deferred_reason_code
            previous_category = row.deferred_category
            changed = previous != _observation_meaningful_values(observation)
            _apply_observation(row, observation, event_at, run_id)
            row.observation_count = int(row.observation_count or 0) + 1
            if changed:
                row.last_changed_at = event_at
                event_type = (
                    EVENT_REASON_CHANGED
                    if previous.get("deferred_reason_code") != observation.deferred_reason_code
                    else EVENT_CLASSIFICATION_CHANGED
                )
                db_session.add(
                    _event(
                        row=row,
                        event_type=event_type,
                        event_at=event_at,
                        run_id=run_id,
                        run_kind=run_kind,
                        previous_state=previous_state,
                        previous_reason_code=previous_reason,
                        previous_category=previous_category,
                        event_summary="Deferred asset classification changed.",
                    )
                )
                changed_count += 1
                if observation.current_state == STATE_NO_LONGER_DEFERRED:
                    resolved_count += 1
            else:
                unchanged_count += 1

        resolved_count += _mark_other_categories_no_longer_deferred(
            db_session,
            observation=observation,
            event_at=event_at,
            run_id=run_id,
            run_kind=run_kind,
        )

        if len(safe_samples) < 15:
            safe_samples.append(
                {
                    "id": row.id,
                    "inventory_id": row.inventory_id,
                    "primary_relative_path": row.primary_relative_path,
                    "deferred_category": row.deferred_category,
                    "deferred_reason_code": row.deferred_reason_code,
                    "current_state": row.current_state,
                    "resource_count": row.resource_count,
                    "is_live_photo": row.is_live_photo,
                }
            )

    summary = DeferredAssetLedgerSummary(
        source_profile_id=source_profile_id,
        run_id=run_id,
        run_kind=run_kind,
        generated_at=event_at,
        total_deferred_seen=len(observation_list),
        new_deferred_count=new_count,
        changed_deferred_count=changed_count,
        unchanged_deferred_count=unchanged_count,
        resolved_count=resolved_count,
        by_category=dict(sorted(by_category.items())),
        by_reason_code=dict(sorted(by_reason.items())),
        adjusted_resource_deferred_count=by_category.get(CATEGORY_ADJUSTED_RESOURCE, 0),
        adjusted_single_resource_count=sum(
            1
            for observation in observation_list
            if observation.deferred_category == CATEGORY_ADJUSTED_RESOURCE
            and not observation.is_live_photo
            and int(observation.resource_count or 0) == 1
        ),
        adjusted_live_photo_grouped_count=sum(
            1
            for observation in observation_list
            if observation.deferred_category == CATEGORY_ADJUSTED_RESOURCE
            and (observation.is_live_photo or int(observation.resource_count or 0) > 1)
        ),
        safe_sample_rows=tuple(safe_samples),
    )
    db_session.commit()
    if write_report:
        summary = _write_report(summary)
    return summary


def _write_report(summary: DeferredAssetLedgerSummary) -> DeferredAssetLedgerSummary:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    timestamp = summary.generated_at.strftime("%Y%m%dT%H%M%SZ")
    report_path = REPORT_ROOT / (
        f"deferred_assets_source{summary.source_profile_id}_{timestamp}.json"
    )
    payload = {
        "report_version": REPORT_VERSION,
        "source_profile_id": summary.source_profile_id,
        "run_id": summary.run_id,
        "run_kind": summary.run_kind,
        "generated_at": summary.generated_at.isoformat(),
        "total_deferred_seen": summary.total_deferred_seen,
        "new_deferred_count": summary.new_deferred_count,
        "changed_deferred_count": summary.changed_deferred_count,
        "unchanged_deferred_count": summary.unchanged_deferred_count,
        "resolved_count": summary.resolved_count,
        "by_category": summary.by_category,
        "by_reason_code": summary.by_reason_code,
        "adjusted_resource_deferred_count": summary.adjusted_resource_deferred_count,
        "adjusted_single_resource_count": summary.adjusted_single_resource_count,
        "adjusted_live_photo_grouped_count": summary.adjusted_live_photo_grouped_count,
        "safe_sample_rows": list(summary.safe_sample_rows),
    }
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return DeferredAssetLedgerSummary(
        **{**summary.__dict__, "report_path": str(report_path)}
    )


def deferred_asset_counts(db_session: Session, *, source_profile_id: int) -> DeferredAssetCounts:
    ensure_source_profile_deferred_asset_schema(db_session)
    active = SourceProfileDeferredAsset.current_state == STATE_ACTIVE_DEFERRED
    current_count = int(
        db_session.scalar(
            select(func.count())
            .select_from(SourceProfileDeferredAsset)
            .where(SourceProfileDeferredAsset.source_profile_id == source_profile_id, active)
        )
        or 0
    )
    adjusted = int(
        db_session.scalar(
            select(func.count())
            .select_from(SourceProfileDeferredAsset)
            .where(
                SourceProfileDeferredAsset.source_profile_id == source_profile_id,
                active,
                SourceProfileDeferredAsset.deferred_category == CATEGORY_ADJUSTED_RESOURCE,
            )
        )
        or 0
    )
    ambiguous = int(
        db_session.scalar(
            select(func.count())
            .select_from(SourceProfileDeferredAsset)
            .where(
                SourceProfileDeferredAsset.source_profile_id == source_profile_id,
                active,
                SourceProfileDeferredAsset.deferred_category == CATEGORY_AMBIGUOUS_METADATA,
            )
        )
        or 0
    )
    unsupported = int(
        db_session.scalar(
            select(func.count())
            .select_from(SourceProfileDeferredAsset)
            .where(
                SourceProfileDeferredAsset.source_profile_id == source_profile_id,
                active,
                SourceProfileDeferredAsset.deferred_category == CATEGORY_UNSUPPORTED_METADATA,
            )
        )
        or 0
    )
    latest_seen = db_session.scalar(
        select(func.max(SourceProfileDeferredAsset.last_seen_at)).where(
            SourceProfileDeferredAsset.source_profile_id == source_profile_id
        )
    )
    new_since = changed_since = 0
    if latest_seen is not None:
        new_since = int(
            db_session.scalar(
                select(func.count())
                .select_from(SourceProfileDeferredAsset)
                .where(
                    SourceProfileDeferredAsset.source_profile_id == source_profile_id,
                    SourceProfileDeferredAsset.first_seen_at == latest_seen,
                )
            )
            or 0
        )
        changed_since = int(
            db_session.scalar(
                select(func.count())
                .select_from(SourceProfileDeferredAsset)
                .where(
                    SourceProfileDeferredAsset.source_profile_id == source_profile_id,
                    SourceProfileDeferredAsset.last_changed_at == latest_seen,
                    SourceProfileDeferredAsset.first_seen_at != latest_seen,
                )
            )
            or 0
        )
    return DeferredAssetCounts(
        current_count=current_count,
        adjusted_resource_count=adjusted,
        ambiguous_count=ambiguous,
        unsupported_count=unsupported,
        new_since_last_scan_count=new_since,
        changed_since_last_scan_count=changed_since,
    )


def list_deferred_assets(
    db_session: Session,
    *,
    source_profile_id: int,
    limit: int = 100,
    category: str | None = None,
    reason_code: str | None = None,
    state: str | None = None,
) -> tuple[DeferredAssetListItem, ...]:
    ensure_source_profile_deferred_asset_schema(db_session)
    bounded_limit = min(max(int(limit), 1), 500)
    query = select(SourceProfileDeferredAsset).where(
        SourceProfileDeferredAsset.source_profile_id == source_profile_id
    )
    if category:
        query = query.where(SourceProfileDeferredAsset.deferred_category == category.strip())
    if reason_code:
        query = query.where(SourceProfileDeferredAsset.deferred_reason_code == reason_code.strip())
    if state:
        query = query.where(SourceProfileDeferredAsset.current_state == state.strip())
    rows = db_session.scalars(
        query.order_by(
            SourceProfileDeferredAsset.last_seen_at.desc(),
            SourceProfileDeferredAsset.id.asc(),
        ).limit(bounded_limit)
    ).all()
    return tuple(
        DeferredAssetListItem(
            id=row.id,
            inventory_id=row.inventory_id,
            source_profile_id=row.source_profile_id,
            primary_relative_path=row.primary_relative_path,
            filename=row.filename,
            extension=row.extension,
            content_type=row.content_type,
            resource_count=int(row.resource_count or 0),
            is_live_photo=bool(row.is_live_photo),
            grouping=row.grouping,
            deferred_category=row.deferred_category,
            deferred_reason_code=row.deferred_reason_code,
            deferred_reason_human=row.deferred_reason_human,
            policy_status=row.policy_status,
            current_state=row.current_state,
            first_seen_at=row.first_seen_at,
            last_seen_at=row.last_seen_at,
            observation_count=int(row.observation_count or 0),
        )
        for row in rows
    )
