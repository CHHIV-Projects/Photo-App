"""Read-only API routes for Source Review workspace."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.provenance_review import (
    SourceReviewAssetResponse,
    SourceReviewCreateAlbumRequest,
    SourceReviewCreateAlbumResponse,
    SourceReviewCreateCollectionRequest,
    SourceReviewCreateCollectionResponse,
    SourceReviewCreateEventRequest,
    SourceReviewCreateEventResponse,
    SourceReviewMatchesResponse,
)
from app.services.provenance.source_review_service import (
    SourceReviewNotFoundError,
    SourceReviewValidationError,
    create_album_from_source_review_level,
    create_collection_from_source_review_level,
    create_event_from_source_review_level,
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


@router.post("/create-album", response_model=SourceReviewCreateAlbumResponse)
def post_source_review_create_album(
    payload: SourceReviewCreateAlbumRequest,
    db: Session = Depends(get_db_session),
) -> SourceReviewCreateAlbumResponse:
    try:
        result = create_album_from_source_review_level(
            db,
            provenance_id=payload.provenance_id,
            level_index=payload.level_index,
            hierarchy_mode=payload.hierarchy_mode,
            album_name=payload.album_name,
            conflict_mode=payload.conflict_mode,
        )
    except SourceReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SourceReviewValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return SourceReviewCreateAlbumResponse(**result)


@router.post("/create-collection", response_model=SourceReviewCreateCollectionResponse)
def post_source_review_create_collection(
    payload: SourceReviewCreateCollectionRequest,
    db: Session = Depends(get_db_session),
) -> SourceReviewCreateCollectionResponse:
    try:
        result = create_collection_from_source_review_level(
            db,
            provenance_id=payload.provenance_id,
            level_index=payload.level_index,
            hierarchy_mode=payload.hierarchy_mode,
            collection_name=payload.collection_name,
        )
    except SourceReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SourceReviewValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return SourceReviewCreateCollectionResponse(**result)


@router.post("/create-event", response_model=SourceReviewCreateEventResponse)
def post_source_review_create_event(
    payload: SourceReviewCreateEventRequest,
    db: Session = Depends(get_db_session),
) -> SourceReviewCreateEventResponse:
    try:
        result = create_event_from_source_review_level(
            db,
            provenance_id=payload.provenance_id,
            level_index=payload.level_index,
            hierarchy_mode=payload.hierarchy_mode,
            event_label=payload.event_label,
            start_at=payload.start_at,
            end_at=payload.end_at,
            existing_event_policy=payload.existing_event_policy,
        )
    except SourceReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SourceReviewValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return SourceReviewCreateEventResponse(**result)
