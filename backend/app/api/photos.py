"""API routes for photo-level review."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.photos import (
    CaptureClassificationOverrideRequest,
    PhotoDetail,
    PhotoListResponse,
    PhotoSummary,
    SuccessResponse,
)
from app.services.photos.photos_service import (
    get_photo_detail,
    list_photos,
    set_capture_classification_override,
)

router = APIRouter(prefix="/api/photos", tags=["photos"])


@router.get("", response_model=PhotoListResponse)
def get_photos(db: Session = Depends(get_db_session)) -> PhotoListResponse:
    items = list_photos(db)
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
