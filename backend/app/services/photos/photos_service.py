"""Service helpers for photo-level review API endpoints."""

from __future__ import annotations

from sqlalchemy import func, nullslast, select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.event import Event
from app.models.face import Face
from app.models.face_cluster import FaceCluster
from app.models.person import Person
from app.services.metadata.metadata_normalizer import get_effective_capture_classification


def _build_asset_url(sha256: str, extension: str) -> str:
    """Build a browser-accessible URL for a vault asset.

    Vault layout: storage/vault/{sha256[:2]}/{sha256}.{ext}
    Served at:    /media/assets/{sha256[:2]}/{sha256}.{ext}
    """
    ext = extension.lower()
    if not ext.startswith("."):
        ext = f".{ext}"
    prefix = sha256[:2]
    filename = f"{sha256}{ext}"
    return f"/media/assets/{prefix}/{filename}"


def list_photos(db: Session) -> list[dict]:
    """Return all assets sorted by EXIF capture date (newest first)."""
    face_count_subq = (
        select(Face.asset_sha256, func.count(Face.id).label("face_count"))
        .group_by(Face.asset_sha256)
        .subquery()
    )

    rows = db.execute(
        select(
            Asset.sha256,
            Asset.original_filename,
            Asset.extension,
            func.coalesce(face_count_subq.c.face_count, 0).label("face_count"),
        )
        .outerjoin(face_count_subq, Asset.sha256 == face_count_subq.c.asset_sha256)
        .order_by(
            nullslast(Asset.exif_datetime_original.desc()),
            Asset.created_at_utc.desc(),
        )
    ).all()

    return [
        {
            "asset_sha256": row.sha256,
            "filename": row.original_filename,
            "image_url": _build_asset_url(row.sha256, row.extension),
            "face_count": row.face_count,
        }
        for row in rows
    ]


def get_photo_detail(db: Session, sha256: str) -> dict | None:
    """Return full photo detail with all detected faces and their identity info."""
    asset = db.get(Asset, sha256)
    if asset is None:
        return None

    face_rows = db.execute(
        select(
            Face.id,
            Face.bbox_x,
            Face.bbox_y,
            Face.bbox_width,
            Face.bbox_height,
            Face.cluster_id,
            FaceCluster.person_id,
            Person.display_name,
        )
        .where(Face.asset_sha256 == sha256)
        .outerjoin(FaceCluster, Face.cluster_id == FaceCluster.id)
        .outerjoin(Person, FaceCluster.person_id == Person.id)
        .order_by(Face.id.asc())
    ).all()

    faces = [
        {
            "face_id": row.id,
            "bbox": {
                "x": row.bbox_x,
                "y": row.bbox_y,
                "w": row.bbox_width,
                "h": row.bbox_height,
            },
            "cluster_id": row.cluster_id,
            "person_id": row.person_id,
            "person_name": row.display_name,
        }
        for row in face_rows
    ]

    capture_type, capture_time_trust = get_effective_capture_classification(asset)

    event_summary: dict | None = None
    if asset.event_id is not None:
        event = db.get(Event, asset.event_id)
        if event is not None:
            event_summary = {
                "event_id": event.id,
                "label": event.label,
                "start_at": event.start_at.isoformat() if event.start_at else None,
                "end_at": event.end_at.isoformat() if event.end_at else None,
            }

    location_summary: dict | None = None
    if asset.gps_latitude is not None or asset.gps_longitude is not None:
        location_summary = {
            "latitude": asset.gps_latitude,
            "longitude": asset.gps_longitude,
        }

    provenance_summary: dict | None = None
    if asset.original_source_path:
        provenance_summary = {
            "original_source_path": asset.original_source_path,
        }

    return {
        "asset_sha256": sha256,
        "filename": asset.original_filename,
        "image_url": _build_asset_url(asset.sha256, asset.extension),
        "is_scan": capture_type == "scan",
        "capture_type": capture_type,
        "capture_time_trust": capture_time_trust,
        "event": event_summary,
        "location": location_summary,
        "provenance": provenance_summary,
        "faces": faces,
    }


def set_capture_classification_override(
    db: Session,
    asset_sha256: str,
    capture_type: str,
    capture_time_trust: str,
) -> bool:
    """Persist manual capture classification overrides for one asset."""
    asset = db.get(Asset, asset_sha256)
    if asset is None:
        return False

    asset.capture_type_override = capture_type
    asset.capture_time_trust_override = capture_time_trust
    db.commit()
    return True
