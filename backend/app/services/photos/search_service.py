"""Metadata-based photo search service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.models.asset import Asset
from app.models.face import Face
from app.models.face_cluster import FaceCluster
from app.models.live_photo_pair import LivePhotoPair
from app.models.provenance import Provenance
from app.models.person import Person
from app.models.collection import Collection
from app.models.collection_asset import CollectionAsset
from app.models.event import Event
from app.models.place import Place
from app.models.place_alias import PlaceAlias
from app.services.photos.display_url_service import build_asset_display_url_contract
from app.services.metadata.metadata_normalizer import VIDEO_EXTENSIONS
from app.services.timeline.timeline_service import TimelineFilter, apply_asset_time_filters, effective_capture_time_trust_expr


@dataclass(frozen=True)
class SearchPhotoSummary:
    asset_sha256: str
    filename: str
    image_url: str | None
    display_url: str | None
    original_url: str
    has_display_preview: bool
    display_source: str
    captured_at: str | None
    camera_make: str | None
    camera_model: str | None
    capture_time_trust: str
    face_count: int
    assigned_face_count: int
    unassigned_face_count: int
    duplicate_group_id: int | None
    is_canonical: bool
    visibility_status: str
    has_live_photo_motion_companion: bool
    is_live_photo_motion_companion: bool
    live_photo_still_asset_sha256: str | None


@dataclass(frozen=True)
class SearchPhotoListResult:
    total_count: int
    offset: int
    limit: int
    items: list[SearchPhotoSummary]


def _to_utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=datetime.now().astimezone().tzinfo).isoformat()
    return value.isoformat()


def _parse_iso_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must use YYYY-MM-DD format.") from exc


def _build_local_day_bounds(*, start_date: str | None, end_date: str | None) -> tuple[datetime | None, datetime | None]:
    """Return UTC bounds for local-day date strings.

    Boundaries are calculated from the local timezone on this backend host.
    """
    if not start_date and not end_date:
        return None, None

    local_tz = datetime.now().astimezone().tzinfo
    assert local_tz is not None

    parsed_start = _parse_iso_date(start_date, "start_date") if start_date else None
    parsed_end = _parse_iso_date(end_date, "end_date") if end_date else None

    if parsed_start and parsed_end and parsed_start > parsed_end:
        raise ValueError("start_date must be less than or equal to end_date.")

    start_bound_utc: datetime | None = None
    end_bound_utc_exclusive: datetime | None = None

    if parsed_start is not None:
        start_local = datetime.combine(parsed_start, time.min, tzinfo=local_tz)
        start_bound_utc = start_local.astimezone(timezone.utc)

    if parsed_end is not None:
        end_local_exclusive = datetime.combine(parsed_end + timedelta(days=1), time.min, tzinfo=local_tz)
        end_bound_utc_exclusive = end_local_exclusive.astimezone(timezone.utc)

    return start_bound_utc, end_bound_utc_exclusive


def search_photos(
    db: Session,
    *,
    filename_query: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    camera_query: str | None = None,
    person_ids: list[int] | None = None,
    album_id: int | None = None,
    event_id: int | None = None,
    place_query: str | None = None,
    provenance_query: str | None = None,
    has_location: bool | None = None,
    has_faces: bool | None = None,
    has_unassigned_faces: bool | None = None,
    visibility_filter: str = "all",
    media_type_filter: str = "all",
    include_live_photo_motion_companions: bool = True,
    canonical_first: bool = False,
    sort_by: str = "ingested_desc",
    timeline_filters: TimelineFilter | None = None,
    offset: int = 0,
    limit: int = 100,
) -> SearchPhotoListResult:
    """Search photos by canonical metadata fields with deterministic ordering."""
    latest_ingest_subq = (
        select(
            Provenance.asset_sha256.label("asset_sha256"),
            func.max(Provenance.ingested_at).label("latest_ingested_at"),
        )
        .group_by(Provenance.asset_sha256)
        .subquery()
    )

    face_count_subq = (
        select(
            Face.asset_sha256,
            func.count(Face.id).label("face_count"),
            func.sum(case((FaceCluster.person_id.is_not(None), 1), else_=0)).label("assigned_face_count"),
            func.sum(case((FaceCluster.person_id.is_(None), 1), else_=0)).label("unassigned_face_count"),
        )
        .outerjoin(FaceCluster, Face.cluster_id == FaceCluster.id)
        .group_by(Face.asset_sha256)
        .subquery()
    )

    trust_expr = effective_capture_time_trust_expr()
    still_pair = aliased(LivePhotoPair)
    motion_pair = aliased(LivePhotoPair)

    base_query: Any = select(
        Asset.sha256,
        Asset.original_filename,
        Asset.extension,
        Asset.display_preview_path,
        Asset.captured_at,
        Asset.camera_make,
        Asset.camera_model,
        Asset.duplicate_group_id,
        Asset.is_canonical,
        Asset.visibility_status,
        trust_expr.label("capture_time_trust"),
        func.coalesce(face_count_subq.c.face_count, 0).label("face_count"),
        func.coalesce(face_count_subq.c.assigned_face_count, 0).label("assigned_face_count"),
        func.coalesce(face_count_subq.c.unassigned_face_count, 0).label("unassigned_face_count"),
        still_pair.motion_asset_sha256.label("live_photo_motion_asset_sha256"),
        motion_pair.still_asset_sha256.label("live_photo_still_asset_sha256"),
    ).outerjoin(face_count_subq, Asset.sha256 == face_count_subq.c.asset_sha256).outerjoin(
        still_pair,
        still_pair.still_asset_sha256 == Asset.sha256,
    ).outerjoin(
        motion_pair,
        motion_pair.motion_asset_sha256 == Asset.sha256,
    ).outerjoin(
        latest_ingest_subq,
        Asset.sha256 == latest_ingest_subq.c.asset_sha256,
    )

    active_timeline_filters = timeline_filters or TimelineFilter()
    base_query = apply_asset_time_filters(base_query, active_timeline_filters, include_non_visible=True)

    if filename_query and filename_query.strip():
        q = f"%{filename_query.strip().lower()}%"
        base_query = base_query.where(func.lower(Asset.original_filename).like(q))

    if camera_query and camera_query.strip():
        q = f"%{camera_query.strip().lower()}%"
        base_query = base_query.where(
            or_(
                func.lower(func.coalesce(Asset.camera_make, "")).like(q),
                func.lower(func.coalesce(Asset.camera_model, "")).like(q),
            )
        )

    # Person filter: AND semantics (asset must contain all selected people)
    if person_ids:
        person_filter_subq = (
            select(Face.asset_sha256)
            .join(FaceCluster, Face.cluster_id == FaceCluster.id)
            .where(FaceCluster.person_id.in_(person_ids))
            .group_by(Face.asset_sha256)
            .having(func.count(func.distinct(FaceCluster.person_id)) == len(person_ids))
            .distinct()
            .subquery()
        )
        base_query = base_query.where(Asset.sha256.in_(select(person_filter_subq.c.asset_sha256)))

    # Album/Collection filter
    if album_id is not None:
        collection_filter_subq = (
            select(CollectionAsset.asset_sha256)
            .where(CollectionAsset.collection_id == album_id)
            .subquery()
        )
        base_query = base_query.where(Asset.sha256.in_(select(collection_filter_subq.c.asset_sha256)))

    # Event filter
    if event_id is not None:
        base_query = base_query.where(Asset.event_id == event_id)

    # Place filter: search by place label/address/city/state/country
    if place_query and place_query.strip():
        q = f"%{place_query.strip().lower()}%"
        place_filter_subq = (
            select(Asset.sha256)
            .outerjoin(Place, Asset.place_id == Place.place_id)
            .outerjoin(PlaceAlias, PlaceAlias.place_id == Place.place_id)
            .where(
                or_(
                    func.lower(func.coalesce(Place.user_label, "")).like(q),
                    func.lower(func.coalesce(Place.formatted_address, "")).like(q),
                    func.lower(func.coalesce(Place.city, "")).like(q),
                    func.lower(func.coalesce(Place.state, "")).like(q),
                    func.lower(func.coalesce(Place.country, "")).like(q),
                    func.lower(func.coalesce(PlaceAlias.alias, "")).like(q),
                )
            )
            .distinct()
            .subquery()
        )
        base_query = base_query.where(Asset.sha256.in_(select(place_filter_subq.c.sha256)))

    # Provenance/Source filter: search source label, type, and path fields
    if provenance_query and provenance_query.strip():
        q = f"%{provenance_query.strip().lower()}%"
        provenance_filter_subq = (
            select(Provenance.asset_sha256)
            .where(
                or_(
                    func.lower(func.coalesce(Provenance.source_label, "")).like(q),
                    func.lower(func.coalesce(Provenance.source_type, "")).like(q),
                    func.lower(func.coalesce(Provenance.source_relative_path, "")).like(q),
                    func.lower(func.coalesce(Provenance.source_root_path, "")).like(q),
                    func.lower(func.coalesce(Provenance.source_path, "")).like(q),
                )
            )
            .distinct()
            .subquery()
        )
        base_query = base_query.where(Asset.sha256.in_(select(provenance_filter_subq.c.asset_sha256)))

    if has_location is True:
        base_query = base_query.where(Asset.gps_latitude.is_not(None), Asset.gps_longitude.is_not(None))
    elif has_location is False:
        base_query = base_query.where(or_(Asset.gps_latitude.is_(None), Asset.gps_longitude.is_(None)))

    if has_faces is True:
        base_query = base_query.where(func.coalesce(face_count_subq.c.face_count, 0) > 0)
    elif has_faces is False:
        base_query = base_query.where(func.coalesce(face_count_subq.c.face_count, 0) <= 0)

    if has_unassigned_faces is True:
        base_query = base_query.where(func.coalesce(face_count_subq.c.unassigned_face_count, 0) > 0)

    if visibility_filter not in {"visible", "demoted", "all"}:
        raise ValueError("visibility_filter must be one of: visible, demoted, all.")
    if visibility_filter != "all":
        base_query = base_query.where(Asset.visibility_status == visibility_filter)

    if media_type_filter not in {"all", "photos", "videos"}:
        raise ValueError("media_type_filter must be one of: all, photos, videos.")
    normalized_video_extensions = sorted(VIDEO_EXTENSIONS)
    if media_type_filter == "photos":
        base_query = base_query.where(~Asset.extension.in_(normalized_video_extensions))
    elif media_type_filter == "videos":
        base_query = base_query.where(Asset.extension.in_(normalized_video_extensions))

    if not include_live_photo_motion_companions:
        base_query = base_query.where(motion_pair.still_asset_sha256.is_(None))

    if sort_by not in {"ingested_desc", "captured_desc"}:
        raise ValueError("sort_by must be one of: ingested_desc, captured_desc.")

    start_bound_utc, end_bound_utc_exclusive = _build_local_day_bounds(
        start_date=start_date,
        end_date=end_date,
    )
    if start_bound_utc is not None or end_bound_utc_exclusive is not None:
        base_query = base_query.where(Asset.captured_at.is_not(None))
    if start_bound_utc is not None:
        base_query = base_query.where(Asset.captured_at >= start_bound_utc)
    if end_bound_utc_exclusive is not None:
        base_query = base_query.where(Asset.captured_at < end_bound_utc_exclusive)

    total_count = int(db.execute(base_query.with_only_columns(func.count(Asset.sha256))).scalar_one())

    ordering: list[Any] = []
    if canonical_first:
        ordering.append(case((Asset.is_canonical.is_(True), 0), else_=1).asc())

    if sort_by == "captured_desc":
        ordering.extend([
            Asset.captured_at.desc().nullslast(),
            latest_ingest_subq.c.latest_ingested_at.desc().nullslast(),
        ])
    else:
        ordering.extend([
            latest_ingest_subq.c.latest_ingested_at.desc().nullslast(),
            Asset.captured_at.desc().nullslast(),
        ])

    rows = db.execute(
        base_query.order_by(
            *ordering,
            Asset.created_at_utc.desc(),
            Asset.sha256.asc(),
        )
        .offset(max(0, offset))
        .limit(max(1, min(limit, 500)))
    ).all()

    items: list[SearchPhotoSummary] = []
    for row in rows:
        contract = build_asset_display_url_contract(
            sha256=row.sha256,
            extension=row.extension,
            display_preview_path=row.display_preview_path,
        )
        items.append(
            SearchPhotoSummary(
                asset_sha256=row.sha256,
                filename=row.original_filename,
                image_url=contract.image_url,
                display_url=contract.display_url,
                original_url=contract.original_url,
                has_display_preview=contract.has_display_preview,
                display_source=contract.display_source,
                captured_at=_to_utc_iso(row.captured_at),
                camera_make=row.camera_make,
                camera_model=row.camera_model,
                capture_time_trust=row.capture_time_trust,
                face_count=int(row.face_count or 0),
                assigned_face_count=int(row.assigned_face_count or 0),
                unassigned_face_count=int(row.unassigned_face_count or 0),
                duplicate_group_id=row.duplicate_group_id,
                is_canonical=bool(row.is_canonical),
                visibility_status=row.visibility_status,
                has_live_photo_motion_companion=row.live_photo_motion_asset_sha256 is not None,
                is_live_photo_motion_companion=row.live_photo_still_asset_sha256 is not None,
                live_photo_still_asset_sha256=row.live_photo_still_asset_sha256,
            )
        )

    bounded_limit = max(1, min(limit, 500))
    return SearchPhotoListResult(total_count=total_count, offset=max(0, offset), limit=bounded_limit, items=items)
