"""Service helpers for photo-level review API endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, nullslast, select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.asset_content_tag import AssetContentTag
from app.models.asset_metadata_observation import AssetMetadataObservation
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


ALLOWED_DISPLAY_ROTATION_DEGREES = {0, 90, 180, 270}


def _to_utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    utc_value = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    return utc_value.isoformat().replace("+00:00", "Z")


def _normalize_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    return normalized or None


def _winner_fields_for_observation(observation: AssetMetadataObservation, asset: Asset) -> list[str]:
    winner_fields: list[str] = []
    if observation.captured_at_observed is not None and observation.captured_at_observed == asset.captured_at:
        winner_fields.append("captured_at")

    if (
        observation.gps_latitude is not None
        and observation.gps_longitude is not None
        and asset.gps_latitude is not None
        and asset.gps_longitude is not None
        and round(observation.gps_latitude, 6) == round(asset.gps_latitude, 6)
        and round(observation.gps_longitude, 6) == round(asset.gps_longitude, 6)
    ):
        winner_fields.append("location")

    obs_make = _normalize_string(observation.camera_make)
    asset_make = _normalize_string(asset.camera_make)
    if obs_make is not None and asset_make is not None and obs_make.lower() == asset_make.lower():
        winner_fields.append("camera_make")

    obs_model = _normalize_string(observation.camera_model)
    asset_model = _normalize_string(asset.camera_model)
    if obs_model is not None and asset_model is not None and obs_model.lower() == asset_model.lower():
        winner_fields.append("camera_model")

    if (
        observation.width is not None
        and observation.height is not None
        and observation.width == asset.width
        and observation.height == asset.height
    ):
        winner_fields.append("dimensions")

    return winner_fields


def _validate_display_rotation_degrees(rotation_degrees: int) -> int:
    if rotation_degrees not in ALLOWED_DISPLAY_ROTATION_DEGREES:
        raise ValueError("rotation_degrees must be one of: 0, 90, 180, 270")
    return rotation_degrees


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
            "captured_at": _to_utc_iso(row.captured_at),
            "capture_time_trust": row.capture_time_trust,
            "face_count": row.face_count,
        }
        for row in rows
    ]


def _get_content_tags(db: Session, sha256: str) -> list[dict]:
    """Return persisted content tags for an asset, ordered by confidence desc."""
    rows = db.scalars(
        select(AssetContentTag)
        .where(AssetContentTag.asset_sha256 == sha256)
        .order_by(AssetContentTag.confidence_score.desc())
    ).all()
    return [{"tag": row.tag, "tag_type": row.tag_type} for row in rows]


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
                "start_at": _to_utc_iso(event.start_at),
                "end_at": _to_utc_iso(event.end_at),
            }

    location_summary: dict | None = None
    if asset.gps_latitude is not None or asset.gps_longitude is not None:
        location_summary = {
            "latitude": asset.gps_latitude,
            "longitude": asset.gps_longitude,
        }

    canonical_metadata_summary = {
        "captured_at": _to_utc_iso(asset.captured_at),
        "camera_make": asset.camera_make,
        "camera_model": asset.camera_model,
        "width": asset.width,
        "height": asset.height,
    }

    observation_rows = list(
        db.scalars(
            select(AssetMetadataObservation)
            .where(AssetMetadataObservation.asset_sha256 == sha256)
            .order_by(AssetMetadataObservation.created_at_utc.asc(), AssetMetadataObservation.id.asc())
        ).all()
    )
    metadata_observations = [
        {
            "id": row.id,
            "provenance_id": row.provenance_id,
            "observation_origin": row.observation_origin,
            "observed_source_path": row.observed_source_path,
            "observed_source_type": row.observed_source_type,
            "observed_extension": row.observed_extension,
            "exif_datetime_original": _to_utc_iso(row.exif_datetime_original),
            "exif_create_date": _to_utc_iso(row.exif_create_date),
            "captured_at_observed": _to_utc_iso(row.captured_at_observed),
            "gps_latitude": row.gps_latitude,
            "gps_longitude": row.gps_longitude,
            "camera_make": row.camera_make,
            "camera_model": row.camera_model,
            "width": row.width,
            "height": row.height,
            "is_legacy_seeded": row.is_legacy_seeded,
            "created_at_utc": _to_utc_iso(row.created_at_utc),
            "winner_fields": _winner_fields_for_observation(row, asset),
        }
        for row in observation_rows
    ]

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
            "source_label": row.source_label,
            "source_type": row.source_type,
            "source_root_path": row.source_root_path,
            "source_relative_path": row.source_relative_path,
            "ingestion_source_id": row.ingestion_source_id,
            "ingestion_run_id": row.ingestion_run_id,
            "ingested_at": _to_utc_iso(row.ingested_at),
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
        "display_rotation_degrees": _validate_display_rotation_degrees(int(asset.display_rotation_degrees or 0)),
        "is_scan": capture_type == "scan",
        "capture_type": capture_type,
        "capture_time_trust": capture_time_trust,
        "event": event_summary,
        "location": location_summary,
        "canonical_metadata": canonical_metadata_summary,
        "metadata_observations": metadata_observations,
        "provenance": provenance_summary,
        "duplicate_group_id": asset.duplicate_group_id,
        "duplicate_group_type": duplicate_group_type,
        "is_canonical": asset.is_canonical,
        "quality_score": asset.quality_score,
        "duplicate_count": duplicate_count,
        "canonical_asset_sha256": canonical_asset_sha256,
        "faces": faces,
        "content_tags": _get_content_tags(db, sha256),
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


def set_photo_display_rotation(db: Session, *, asset_sha256: str, rotation_degrees: int) -> int | None:
    """Persist display-only rotation for one asset."""
    validated_rotation = _validate_display_rotation_degrees(rotation_degrees)

    asset = db.get(Asset, asset_sha256)
    if asset is None:
        return None

    asset.display_rotation_degrees = validated_rotation
    db.commit()
    return validated_rotation
