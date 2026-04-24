"""Service helpers for event/timeline API endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.event import Event
from app.models.face import Face
from app.services.photos.photos_service import _build_asset_url


LOGGER = logging.getLogger(__name__)


def _to_utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    utc_value = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    return utc_value.isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class EventMergeResult:
    target_event_id: int
    removed_event_id: int
    label: str | None
    start_time: object
    end_time: object
    photo_count: int


@dataclass(frozen=True)
class EventMembershipMutationResult:
    asset_sha256: str
    event: dict | None
    old_event_summary: dict | None
    new_event_summary: dict | None


def _normalize_event_label(label: str | None) -> str | None:
    if label is None:
        return None
    normalized = label.strip()
    return normalized or None


def _count_event_assets(db: Session, event_id: int) -> int:
    return int(
        db.scalar(
            select(func.count(Asset.sha256)).where(
                Asset.event_id == event_id,
                Asset.visibility_status == "visible",
            )
        )
        or 0
    )


def _count_event_faces(db: Session, event_id: int) -> int:
    return int(
        db.scalar(
            select(func.count(Face.id))
            .join(Asset, Asset.sha256 == Face.asset_sha256)
            .where(Asset.event_id == event_id, Asset.visibility_status == "visible")
        )
        or 0
    )


def _event_summary_payload(db: Session, event: Event) -> dict:
    return {
        "event_id": event.id,
        "label": event.label,
        "start_time": _to_utc_iso(event.start_at),
        "end_time": _to_utc_iso(event.end_at),
        "photo_count": _count_event_assets(db, event.id),
    }


def _event_summary_payload_with_faces(db: Session, event: Event) -> dict:
    return {
        "event_id": event.id,
        "label": event.label,
        "start_time": _to_utc_iso(event.start_at),
        "end_time": _to_utc_iso(event.end_at),
        "photo_count": _count_event_assets(db, event.id),
        "face_count": _count_event_faces(db, event.id),
    }


def _event_photo_time_bounds(db: Session, event_id: int) -> tuple[datetime | None, datetime | None]:
    return db.execute(
        select(func.min(Asset.captured_at), func.max(Asset.captured_at)).where(
            Asset.event_id == event_id,
            Asset.visibility_status == "visible",
            Asset.captured_at.is_not(None),
        )
    ).one()


def _event_fallback_time_bounds(db: Session, event_id: int) -> tuple[datetime | None, datetime | None]:
    return db.execute(
        select(func.min(Asset.created_at_utc), func.max(Asset.created_at_utc)).where(
            Asset.event_id == event_id,
            Asset.visibility_status == "visible",
        )
    ).one()


def _recalculate_event_rollup(db: Session, event_id: int) -> Event | None:
    event = db.get(Event, event_id)
    if event is None:
        return None

    asset_count = _count_event_assets(db, event_id)
    event.asset_count = asset_count

    if asset_count == 0:
        # Keep prior range for empty events to avoid non-null violations and destructive lifecycle complexity.
        return event

    min_time, max_time = _event_photo_time_bounds(db, event_id)
    if min_time is None or max_time is None:
        min_time, max_time = _event_fallback_time_bounds(db, event_id)

    if min_time is not None and max_time is not None:
        event.start_at = min_time
        event.end_at = max_time

    return event


def _photo_event_summary(db: Session, asset: Asset) -> dict | None:
    if asset.event_id is None:
        return None

    event = db.get(Event, asset.event_id)
    if event is None:
        return None

    return {
        "event_id": event.id,
        "label": event.label,
        "start_at": _to_utc_iso(event.start_at),
        "end_at": _to_utc_iso(event.end_at),
    }


def list_events(db: Session) -> list[dict]:
    """Return events, newest first.

    photo_count: number of assets linked to the event.
    face_count:  number of detected faces across those assets.
    """
    photo_count_subq = (
        select(Asset.event_id, func.count(Asset.sha256).label("photo_count"))
        .where(Asset.event_id.isnot(None), Asset.visibility_status == "visible")
        .group_by(Asset.event_id)
        .subquery()
    )

    face_count_subq = (
        select(Asset.event_id, func.count(Face.id).label("face_count"))
        .join(Face, Face.asset_sha256 == Asset.sha256)
        .where(Asset.event_id.isnot(None), Asset.visibility_status == "visible")
        .group_by(Asset.event_id)
        .subquery()
    )

    rows = db.execute(
        select(
            Event.id,
            Event.label,
            Event.start_at,
            Event.end_at,
            func.coalesce(photo_count_subq.c.photo_count, 0).label("photo_count"),
            func.coalesce(face_count_subq.c.face_count, 0).label("face_count"),
        )
        .outerjoin(photo_count_subq, Event.id == photo_count_subq.c.event_id)
        .outerjoin(face_count_subq, Event.id == face_count_subq.c.event_id)
        .order_by(Event.start_at.desc())
    ).all()

    return [
        {
            "event_id": row.id,
            "label": row.label,
            "start_time": _to_utc_iso(row.start_at),
            "end_time": _to_utc_iso(row.end_at),
            "photo_count": row.photo_count,
            "face_count": row.face_count,
        }
        for row in rows
    ]


def get_event_detail(db: Session, event_id: int) -> dict | None:
    """Return event detail with all photos, ordered chronologically."""
    event = db.get(Event, event_id)
    if event is None:
        return None

    face_count_subq = (
        select(Face.asset_sha256, func.count(Face.id).label("face_count"))
        .group_by(Face.asset_sha256)
        .subquery()
    )

    photo_rows = db.execute(
        select(
            Asset.sha256,
            Asset.original_filename,
            Asset.extension,
            Asset.captured_at,
            func.coalesce(face_count_subq.c.face_count, 0).label("face_count"),
        )
        .outerjoin(face_count_subq, Asset.sha256 == face_count_subq.c.asset_sha256)
        .where(Asset.event_id == event_id, Asset.visibility_status == "visible")
        .order_by(Asset.captured_at.asc(), Asset.sha256.asc())
    ).all()

    photos = [
        {
            "asset_sha256": row.sha256,
            "filename": row.original_filename,
            "image_url": _build_asset_url(row.sha256, row.extension),
            "captured_at": _to_utc_iso(row.captured_at),
            "face_count": row.face_count,
        }
        for row in photo_rows
    ]

    return {
        "event_id": event_id,
        "label": event.label,
        "start_time": _to_utc_iso(event.start_at),
        "end_time": _to_utc_iso(event.end_at),
        "photos": photos,
    }


def update_event_label(db: Session, event_id: int, label: str | None) -> dict | None:
    event = db.get(Event, event_id)
    if event is None:
        return None

    event.label = _normalize_event_label(label)
    db.commit()
    db.refresh(event)
    return _event_summary_payload(db, event)


def merge_events(db: Session, *, source_event_id: int, target_event_id: int) -> EventMergeResult | None:
    if source_event_id == target_event_id:
        raise ValueError("Source and target events must be different.")

    source_event = db.get(Event, source_event_id)
    target_event = db.get(Event, target_event_id)
    if source_event is None or target_event is None:
        return None

    db.query(Asset).filter(Asset.event_id == source_event_id).update(
        {
            Asset.event_id: target_event_id,
            Asset.is_user_modified: True,
        },
        synchronize_session=False,
    )

    target_event.start_at = min(target_event.start_at, source_event.start_at)
    target_event.end_at = max(target_event.end_at, source_event.end_at)
    target_event.asset_count = _count_event_assets(db, target_event_id)

    db.delete(source_event)
    db.commit()
    db.refresh(target_event)

    return EventMergeResult(
        target_event_id=target_event.id,
        removed_event_id=source_event_id,
        label=target_event.label,
        start_time=_to_utc_iso(target_event.start_at),
        end_time=_to_utc_iso(target_event.end_at),
        photo_count=_count_event_assets(db, target_event.id),
    )


def remove_asset_from_event(db: Session, *, asset_sha256: str) -> EventMembershipMutationResult | None:
    asset = db.get(Asset, asset_sha256)
    if asset is None:
        return None
    if asset.event_id is None:
        raise ValueError("Photo is not assigned to an event.")

    old_event_id = asset.event_id
    asset.event_id = None
    asset.is_user_modified = True
    old_event = _recalculate_event_rollup(db, old_event_id)

    db.commit()

    old_event_summary = _event_summary_payload_with_faces(db, old_event) if old_event is not None else None
    LOGGER.info("Removed photo %s from event %s", asset_sha256, old_event_id)

    return EventMembershipMutationResult(
        asset_sha256=asset.sha256,
        event=None,
        old_event_summary=old_event_summary,
        new_event_summary=None,
    )


def assign_asset_to_event(db: Session, *, asset_sha256: str, target_event_id: int) -> EventMembershipMutationResult | None:
    asset = db.get(Asset, asset_sha256)
    if asset is None:
        return None

    target_event = db.get(Event, target_event_id)
    if target_event is None:
        raise LookupError(f"Event {target_event_id} not found.")

    if asset.event_id == target_event_id:
        raise ValueError("Photo is already assigned to that event.")

    old_event_id = asset.event_id
    asset.event_id = target_event_id
    asset.is_user_modified = True

    old_event = _recalculate_event_rollup(db, old_event_id) if old_event_id is not None else None
    new_event = _recalculate_event_rollup(db, target_event_id)

    db.commit()
    db.refresh(asset)

    LOGGER.info(
        "Assigned photo %s from event %s to event %s",
        asset_sha256,
        old_event_id,
        target_event_id,
    )

    return EventMembershipMutationResult(
        asset_sha256=asset.sha256,
        event=_photo_event_summary(db, asset),
        old_event_summary=_event_summary_payload_with_faces(db, old_event) if old_event is not None else None,
        new_event_summary=_event_summary_payload_with_faces(db, new_event) if new_event is not None else None,
    )
