"""Service helpers for event/timeline API endpoints."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.event import Event
from app.models.face import Face
from app.services.photos.photos_service import _build_asset_url


def list_events(db: Session) -> list[dict]:
    """Return events that have at least one non-scan photo, newest first.

    photo_count: number of non-scan assets linked to the event.
    face_count:  number of detected faces across those assets.
    """
    photo_count_subq = (
        select(Asset.event_id, func.count(Asset.sha256).label("photo_count"))
        .where(Asset.is_scan.is_(False))
        .where(Asset.event_id.isnot(None))
        .group_by(Asset.event_id)
        .subquery()
    )

    face_count_subq = (
        select(Asset.event_id, func.count(Face.id).label("face_count"))
        .join(Face, Face.asset_sha256 == Asset.sha256)
        .where(Asset.is_scan.is_(False))
        .where(Asset.event_id.isnot(None))
        .group_by(Asset.event_id)
        .subquery()
    )

    rows = db.execute(
        select(
            Event.id,
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
            "start_time": row.start_at,
            "end_time": row.end_at,
            "photo_count": row.photo_count,
            "face_count": row.face_count,
        }
        for row in rows
    ]


def get_event_detail(db: Session, event_id: int) -> dict | None:
    """Return event detail with all non-scan photos, ordered chronologically."""
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
        .where(Asset.is_scan.is_(False))
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
        "start_time": event.start_at,
        "end_time": event.end_at,
        "photos": photos,
    }
