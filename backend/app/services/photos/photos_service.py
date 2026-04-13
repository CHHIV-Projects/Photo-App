"""Service helpers for photo-level review API endpoints."""

from __future__ import annotations

from sqlalchemy import func, nullslast, select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.duplicate_group import DuplicateGroup
from app.models.event import Event
from app.models.face import Face
from app.models.face_cluster import FaceCluster
from app.models.person import Person
from app.models.provenance import Provenance
from app.services.metadata.metadata_normalizer import get_effective_capture_classification
from app.services.timeline.timeline_service import (
    TimelineFilter,
    apply_asset_time_filters,
    effective_capture_time_trust_expr,
)


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


def list_photos(db: Session, *, filters: TimelineFilter | None = None) -> list[dict]:
    """Return asset summaries with optional time/trust filtering."""
    face_count_subq = (
        select(Face.asset_sha256, func.count(Face.id).label("face_count"))
        .group_by(Face.asset_sha256)
        .subquery()
    )

    active_filters = filters or TimelineFilter()
    trust_expr = effective_capture_time_trust_expr()

    query = select(
        Asset.sha256,
        Asset.original_filename,
        Asset.extension,
        Asset.captured_at,
        trust_expr.label("capture_time_trust"),
        func.coalesce(face_count_subq.c.face_count, 0).label("face_count"),
    ).outerjoin(face_count_subq, Asset.sha256 == face_count_subq.c.asset_sha256)

    query = apply_asset_time_filters(query, active_filters)

    rows = db.execute(
        query
        .order_by(
            nullslast(Asset.captured_at.desc()),
            Asset.created_at_utc.desc(),
        )
    ).all()

    return [
        {
            "asset_sha256": row.sha256,
            "filename": row.original_filename,
            "image_url": _build_asset_url(row.sha256, row.extension),
            "captured_at": row.captured_at.isoformat() if row.captured_at else None,
            "capture_time_trust": row.capture_time_trust,
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

    provenance_rows = list(
        db.scalars(
            select(Provenance)
            .where(Provenance.asset_sha256 == sha256)
            .order_by(Provenance.ingested_at.asc(), Provenance.id.asc())
        ).all()
    )
    provenance_summary = [
        {
            "source_path": row.source_path,
            "ingested_at": row.ingested_at.isoformat() if row.ingested_at else None,
            "source_hash": row.source_hash,
        }
        for row in provenance_rows
    ]

    duplicate_group_type: str | None = None
    duplicate_count = 1
    canonical_asset_sha256: str | None = asset.sha256
    if asset.duplicate_group_id is not None:
        group = db.get(DuplicateGroup, asset.duplicate_group_id)
        duplicate_group_type = group.group_type if group is not None else "near"
        duplicate_count = int(
            db.scalar(select(func.count(Asset.sha256)).where(Asset.duplicate_group_id == asset.duplicate_group_id)) or 1
        )
        canonical_asset_sha256 = db.scalar(
            select(Asset.sha256)
            .where(
                Asset.duplicate_group_id == asset.duplicate_group_id,
                Asset.is_canonical.is_(True),
            )
            .limit(1)
        )

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
        "duplicate_group_id": asset.duplicate_group_id,
        "duplicate_group_type": duplicate_group_type,
        "is_canonical": asset.is_canonical,
        "quality_score": asset.quality_score,
        "duplicate_count": duplicate_count,
        "canonical_asset_sha256": canonical_asset_sha256,
        "faces": faces,
    }


def get_duplicate_group_detail(db: Session, group_id: int) -> dict | None:
    """Return duplicate-group details and canonical member."""
    group = db.get(DuplicateGroup, group_id)
    if group is None:
        return None

    assets = list(
        db.scalars(
            select(Asset)
            .where(Asset.duplicate_group_id == group_id)
            .order_by(Asset.is_canonical.desc(), nullslast(Asset.quality_score.desc()), Asset.sha256.asc())
        ).all()
    )
    if not assets:
        return {
            "group_id": group.id,
            "group_type": group.group_type,
            "canonical_asset_sha256": None,
            "duplicate_count": 0,
            "assets": [],
        }

    canonical = next((asset for asset in assets if asset.is_canonical), None)
    items: list[dict] = []
    for asset in assets:
        capture_type, capture_time_trust = get_effective_capture_classification(asset)
        items.append(
            {
                "asset_sha256": asset.sha256,
                "filename": asset.original_filename,
                "image_url": _build_asset_url(asset.sha256, asset.extension),
                "is_canonical": asset.is_canonical,
                "quality_score": asset.quality_score,
                "capture_type": capture_type,
                "capture_time_trust": capture_time_trust,
            }
        )

    return {
        "group_id": group.id,
        "group_type": group.group_type,
        "canonical_asset_sha256": canonical.sha256 if canonical is not None else None,
        "duplicate_count": len(items),
        "assets": items,
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
