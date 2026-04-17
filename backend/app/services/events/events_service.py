"""Service helpers for event/timeline API endpoints."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.event import Event
from app.models.face import Face
from app.services.photos.photos_service import _build_asset_url


@dataclass(frozen=True)
class EventMergeResult:
    target_event_id: int
    removed_event_id: int
    label: str | None
    start_time: object
    end_time: object
    photo_count: int


def _normalize_event_label(label: str | None) -> str | None:
    if label is None:
        return None
    normalized = label.strip()
    return normalized or None


def _count_event_assets(db: Session, event_id: int) -> int:
    return int(db.scalar(select(func.count(Asset.sha256)).where(Asset.event_id == event_id)) or 0)


def _event_summary_payload(db: Session, event: Event) -> dict:
    return {
        "event_id": event.id,
        "label": event.label,
        "start_time": event.start_at,
        "end_time": event.end_at,
        "photo_count": _count_event_assets(db, event.id),
    }


def list_events(db: Session) -> list[dict]:
    """Return events that have at least one photo, newest first.

    photo_count: number of assets linked to the event.
    face_count:  number of detected faces across those assets.
    """
    photo_count_subq = (
        select(Asset.event_id, func.count(Asset.sha256).label("photo_count"))
        .where(Asset.event_id.isnot(None))
        .group_by(Asset.event_id)
        .subquery()
    )

    face_count_subq = (
        select(Asset.event_id, func.count(Face.id).label("face_count"))
        .join(Face, Face.asset_sha256 == Asset.sha256)
        .where(Asset.event_id.isnot(None))
        .group_by(Asset.event_id)
        .subquery()
    )

    rows = db.execute(
        select(
            Event.id,
            Event.label,
            Event.start_at,
            Event.end_at,
            photo_count_subq.c.photo_count,
            func.coalesce(face_count_subq.c.face_count, 0).label("face_count"),
        )
        .join(photo_count_subq, Event.id == photo_count_subq.c.event_id)
        .outerjoin(face_count_subq, Event.id == face_count_subq.c.event_id)
        .order_by(Event.start_at.desc())
    ).all()

    return [
        {
            "event_id": row.id,
            "label": row.label,
            "start_time": row.start_at,
            "end_time": row.end_at,
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
            func.coalesce(face_count_subq.c.face_count, 0).label("face_count"),
        )
        .outerjoin(face_count_subq, Asset.sha256 == face_count_subq.c.asset_sha256)
        .where(Asset.event_id == event_id)
        .order_by(Asset.captured_at.asc(), Asset.sha256.asc())
    ).all()

    photos = [
        {
            "asset_sha256": row.sha256,
            "filename": row.original_filename,
            "image_url": _build_asset_url(row.sha256, row.extension),
            "face_count": row.face_count,
        }
        for row in photo_rows
    ]

    return {
        "event_id": event_id,
        "label": event.label,
        "start_time": event.start_at,
        "end_time": event.end_at,
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
        {Asset.event_id: target_event_id},
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
        start_time=target_event.start_at,
        end_time=target_event.end_at,
        photo_count=_count_event_assets(db, target_event.id),
    )
