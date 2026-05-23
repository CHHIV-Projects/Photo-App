"""Read-only API routes for Source Review workspace."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.provenance_review import SourceReviewAssetResponse, SourceReviewMatchesResponse
from app.services.provenance.source_review_service import (
    SourceReviewNotFoundError,
    SourceReviewValidationError,
    get_source_review_asset,
    get_source_review_matches,
)

router = APIRouter(prefix="/api/provenance-review", tags=["provenance-review"])


@router.get("/assets/{asset_sha256}", response_model=SourceReviewAssetResponse)
def get_source_review_asset_detail(
    asset_sha256: str,
    db: Session = Depends(get_db_session),
) -> SourceReviewAssetResponse:
    try:
        payload = get_source_review_asset(db, asset_sha256)
    except SourceReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return SourceReviewAssetResponse(**payload)


@router.get("/matches", response_model=SourceReviewMatchesResponse)
def get_source_review_prefix_matches(
    provenance_id: int = Query(..., ge=1),
    level_index: int = Query(..., ge=0),
    hierarchy_mode: str = Query(default="relative"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db_session),
) -> SourceReviewMatchesResponse:
    try:
        payload = get_source_review_matches(
            db,
            provenance_id=provenance_id,
            level_index=level_index,
            hierarchy_mode=hierarchy_mode,
            limit=limit,
        )
    except SourceReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SourceReviewValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return SourceReviewMatchesResponse(**payload)
