"""API routes for duplicate lineage groups."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.photos import (
    DuplicateGroupDetail,
    DuplicateLineageMergeRequest,
    DuplicateLineageMergeResponse,
    DuplicateMergeTargetListResponse,
)
from app.services.duplicates.manual_control import (
    list_duplicate_merge_targets,
    merge_asset_into_target_lineage,
)
from app.services.photos.photos_service import get_duplicate_group_detail

router = APIRouter(prefix="/api/duplicates", tags=["duplicates"])


@router.get("/merge-targets", response_model=DuplicateMergeTargetListResponse)
def get_duplicate_merge_targets(
    source_asset_sha256: str,
    q: str | None = None,
    limit: int = 30,
    db: Session = Depends(get_db_session),
) -> DuplicateMergeTargetListResponse:
    items = list_duplicate_merge_targets(
        db,
        source_asset_sha256=source_asset_sha256,
        filename_query=q,
        limit=limit,
    )
    if items is None:
        raise HTTPException(status_code=404, detail=f"Source asset {source_asset_sha256!r} not found.")
    return DuplicateMergeTargetListResponse(count=len(items), items=items)


@router.post("/merge-assets", response_model=DuplicateLineageMergeResponse)
def merge_duplicate_assets(
    payload: DuplicateLineageMergeRequest,
    db: Session = Depends(get_db_session),
) -> DuplicateLineageMergeResponse:
    try:
        result = merge_asset_into_target_lineage(
            db,
            source_asset_sha256=payload.source_asset_sha256,
            target_asset_sha256=payload.target_asset_sha256,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if result is None:
        raise HTTPException(status_code=404, detail=f"Source asset {payload.source_asset_sha256!r} not found.")

    return DuplicateLineageMergeResponse(
        success=True,
        source_asset_sha256=result.source_asset_sha256,
        target_asset_sha256=result.target_asset_sha256,
        resulting_group_id=result.resulting_group_id,
        resulting_canonical_asset_sha256=result.resulting_canonical_asset_sha256,
        affected_member_count=result.affected_member_count,
        affected_assets=result.affected_assets,
    )


@router.get("/{group_id}", response_model=DuplicateGroupDetail)
def get_duplicate_group(group_id: int, db: Session = Depends(get_db_session)) -> DuplicateGroupDetail:
    result = get_duplicate_group_detail(db, group_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Duplicate group {group_id!r} not found.")
    return DuplicateGroupDetail(**result)
