"""API routes for unified metadata photo search."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.photos import SearchPhotoListResponse, SearchPhotoSummary
from app.services.photos.search_service import search_photos
from app.services.timeline.timeline_service import TimelineFilter, VALID_CAPTURE_TIME_TRUST

router = APIRouter(prefix="/api/search", tags=["search"])


def _build_timeline_filters(
    *,
    decade: int | None,
    year: int | None,
    month: str | None,
    date: str | None,
    undated: bool,
    trust: list[str] | None,
) -> TimelineFilter:
    period_flags = [decade is not None, year is not None, month is not None, date is not None, undated]
    if sum(1 for item in period_flags if item) > 1:
        raise HTTPException(
            status_code=400,
            detail="Use only one of decade, year, month, date, or undated at a time.",
        )

    trust_values = tuple(trust or [])
    invalid_trust_values = [value for value in trust_values if value not in VALID_CAPTURE_TIME_TRUST]
    if invalid_trust_values:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid trust value(s): {', '.join(invalid_trust_values)}.",
        )

    if month is not None and len(month) != 7:
        raise HTTPException(status_code=400, detail="month must use YYYY-MM format.")
    if date is not None and len(date) != 10:
        raise HTTPException(status_code=400, detail="date must use YYYY-MM-DD format.")

    return TimelineFilter(
        decade=decade,
        year=year,
        month=month,
        date=date,
        trust_values=trust_values,
        undated=undated,
    )


@router.get("/photos", response_model=SearchPhotoListResponse)
def search_photos_endpoint(
    q: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    camera: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    has_location: bool | None = Query(default=None),
    has_faces: bool | None = Query(default=None),
    has_unassigned_faces: bool | None = Query(default=None),
    canonical_first: bool = Query(default=False),
    decade: int | None = Query(default=None),
    year: int | None = Query(default=None),
    month: str | None = Query(default=None),
    date: str | None = Query(default=None),
    undated: bool = Query(default=False),
    trust: list[str] | None = Query(default=None),
    db: Session = Depends(get_db_session),
) -> SearchPhotoListResponse:
    timeline_filters = _build_timeline_filters(
        decade=decade,
        year=year,
        month=month,
        date=date,
        undated=undated,
        trust=trust,
    )

    try:
        result = search_photos(
            db,
            filename_query=q,
            start_date=start_date,
            end_date=end_date,
            camera_query=camera,
            has_location=has_location,
            has_faces=has_faces,
            has_unassigned_faces=has_unassigned_faces,
            canonical_first=canonical_first,
            timeline_filters=timeline_filters,
            offset=offset,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return SearchPhotoListResponse(
        total_count=result.total_count,
        offset=result.offset,
        limit=result.limit,
        items=[
            SearchPhotoSummary(
                asset_sha256=item.asset_sha256,
                filename=item.filename,
                image_url=item.image_url,
                captured_at=item.captured_at,
                camera_make=item.camera_make,
                camera_model=item.camera_model,
                capture_time_trust=item.capture_time_trust,
                face_count=item.face_count,
                assigned_face_count=item.assigned_face_count,
                unassigned_face_count=item.unassigned_face_count,
                duplicate_group_id=item.duplicate_group_id,
                is_canonical=item.is_canonical,
                visibility_status=item.visibility_status,
            )
            for item in result.items
        ],
    )
