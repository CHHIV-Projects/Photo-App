"""API routes for photo-level review."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.photos import (
    CaptureClassificationOverrideRequest,
    PhotoDetail,
    PhotoListResponse,
    PhotoRotationUpdateRequest,
    PhotoRotationUpdateResponse,
    PhotoSummary,
    SuccessResponse,
)
from app.services.photos.photos_service import (
    get_photo_detail,
    list_photos,
    set_photo_display_rotation,
    set_capture_classification_override,
)
from app.services.timeline.timeline_service import TimelineFilter, VALID_CAPTURE_TIME_TRUST

router = APIRouter(prefix="/api/photos", tags=["photos"])


def _build_photo_filters(
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


@router.get("", response_model=PhotoListResponse)
def get_photos(
    decade: int | None = Query(default=None),
    year: int | None = Query(default=None),
    month: str | None = Query(default=None),
    date: str | None = Query(default=None),
    undated: bool = Query(default=False),
    trust: list[str] | None = Query(default=None),
    db: Session = Depends(get_db_session),
) -> PhotoListResponse:
    filters = _build_photo_filters(
        decade=decade,
        year=year,
        month=month,
        date=date,
        undated=undated,
        trust=trust,
    )
    items = list_photos(db, filters=filters)
    return PhotoListResponse(
        count=len(items),
        items=[PhotoSummary(**item) for item in items],
    )


@router.get("/{asset_sha256}", response_model=PhotoDetail)
def get_photo(asset_sha256: str, db: Session = Depends(get_db_session)) -> PhotoDetail:
    result = get_photo_detail(db, asset_sha256)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Photo {asset_sha256!r} not found.")
    return PhotoDetail(**result)


@router.post("/{asset_sha256}/capture-classification", response_model=SuccessResponse)
def override_photo_capture_classification(
    asset_sha256: str,
    request: CaptureClassificationOverrideRequest,
    db: Session = Depends(get_db_session),
) -> SuccessResponse:
    updated = set_capture_classification_override(
        db,
        asset_sha256=asset_sha256,
        capture_type=request.capture_type,
        capture_time_trust=request.capture_time_trust,
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Photo {asset_sha256!r} not found.")
    return SuccessResponse(success=True)


@router.post("/{asset_sha256}/rotation", response_model=PhotoRotationUpdateResponse)
def update_photo_rotation(
    asset_sha256: str,
    request: PhotoRotationUpdateRequest,
    db: Session = Depends(get_db_session),
) -> PhotoRotationUpdateResponse:
    try:
        updated_rotation = set_photo_display_rotation(
            db,
            asset_sha256=asset_sha256,
            rotation_degrees=request.rotation_degrees,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if updated_rotation is None:
        raise HTTPException(status_code=404, detail=f"Photo {asset_sha256!r} not found.")

    return PhotoRotationUpdateResponse(
        asset_sha256=asset_sha256,
        display_rotation_degrees=updated_rotation,
    )
