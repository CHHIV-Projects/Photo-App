"""API routes for duplicate lineage groups."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.photos import (
    DuplicateAdjudicationResponse,
    DuplicateDemoteRequest,
    DuplicateGroupSummary,
    DuplicateGroupDetail,
    DuplicateGroupListResponse,
    DuplicateLineageMergeRequest,
    DuplicateLineageMergeResponse,
    DuplicateRemoveFromGroupRequest,
    DuplicateRestoreRequest,
    DuplicateSetCanonicalRequest,
    DuplicateMergeTargetListResponse,
    DuplicateSuggestionListResponse,
    DuplicateSuggestionSummary,
    DuplicateSuggestionConfirmRequest,
    DuplicateSuggestionRejectRequest,
    DuplicateSuggestionRejectResponse,
)
from app.services.duplicates.manual_control import (
    demote_group_asset,
    list_duplicate_groups,
    list_duplicate_merge_targets,
    merge_asset_into_target_lineage,
    remove_asset_from_group,
    restore_group_asset,
    set_group_canonical,
)
from app.services.duplicates.suggestion_service import list_duplicate_suggestions, reject_duplicate_pair
from app.services.photos.photos_service import get_duplicate_group_detail

router = APIRouter(prefix="/api/duplicates", tags=["duplicates"])


@router.get("/suggestions", response_model=DuplicateSuggestionListResponse)
def get_duplicate_suggestions(
    offset: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db_session),
) -> DuplicateSuggestionListResponse:
    result = list_duplicate_suggestions(db, offset=max(0, offset), limit=max(1, min(limit, 200)))

    def _asset_payload(asset: object) -> dict[str, object]:
        if isinstance(asset, dict):
            return {
                "asset_sha256": asset.get("asset_sha256"),
                "filename": asset.get("filename"),
                "image_url": asset.get("image_url"),
                "duplicate_group_id": asset.get("duplicate_group_id"),
                "quality_score": asset.get("quality_score"),
            }
        return {
            "asset_sha256": getattr(asset, "asset_sha256"),
            "filename": getattr(asset, "filename"),
            "image_url": getattr(asset, "image_url"),
            "duplicate_group_id": getattr(asset, "duplicate_group_id"),
            "quality_score": getattr(asset, "quality_score"),
        }

    return DuplicateSuggestionListResponse(
        total_count=result.total_count,
        offset=max(0, offset),
        limit=max(1, min(limit, 200)),
        items=[
            DuplicateSuggestionSummary(
                confidence=item.confidence,
                distance=item.distance,
                asset_a=_asset_payload(item.asset_a),
                asset_b=_asset_payload(item.asset_b),
            )
            for item in result.items
        ],
    )


@router.get("/groups", response_model=DuplicateGroupListResponse)
def list_groups(
    q: str | None = None,
    offset: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db_session),
) -> DuplicateGroupListResponse:
    """List duplicate groups with pagination and optional filename search."""
    try:
        print(f"[DEBUG] list_groups called: q={q}, offset={offset}, limit={limit}")
        result = list_duplicate_groups(
            db,
            filename_query=q,
            offset=max(0, offset),
            limit=max(1, min(limit, 200)),
        )
        print(f"[DEBUG] list_groups result: total_count={result.total_count}, items_count={len(result.items)}")
        items = [
            DuplicateGroupSummary(
                group_id=item.group_id,
                member_count=item.member_count,
                canonical_asset_sha256=item.canonical_asset_sha256,
                canonical_thumbnail_url=item.canonical_thumbnail_url,
                created_at=item.created_at,
            )
            for item in result.items
        ]
        return DuplicateGroupListResponse(total_count=result.total_count, items=items)
    except Exception as e:
        print(f"[DEBUG] list_groups error: {e}")
        import traceback
        traceback.print_exc()
        raise


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


@router.post("/confirm", response_model=DuplicateLineageMergeResponse)
def confirm_duplicate_suggestion(
    payload: DuplicateSuggestionConfirmRequest,
    db: Session = Depends(get_db_session),
) -> DuplicateLineageMergeResponse:
    try:
        result = merge_asset_into_target_lineage(
            db,
            source_asset_sha256=payload.source_asset_sha256,
            target_asset_sha256=payload.target_asset_sha256,
        )
    except ValueError as exc:
        error_message = str(exc)
        if "already in the same duplicate group" in error_message.lower():
            return DuplicateLineageMergeResponse(
                success=True,
                source_asset_sha256=payload.source_asset_sha256,
                target_asset_sha256=payload.target_asset_sha256,
                resulting_group_id=0,
                resulting_canonical_asset_sha256=payload.target_asset_sha256,
                affected_member_count=0,
                affected_assets=[],
                noop=True,
                message="Assets already in same duplicate group",
            )
        raise HTTPException(status_code=422, detail=error_message) from exc
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
        noop=False,
    )


@router.post("/reject", response_model=DuplicateSuggestionRejectResponse)
def reject_duplicate_suggestion(
    payload: DuplicateSuggestionRejectRequest,
    db: Session = Depends(get_db_session),
) -> DuplicateSuggestionRejectResponse:
    if payload.asset_sha256_a == payload.asset_sha256_b:
        raise HTTPException(status_code=422, detail="Rejected pair must contain two different assets.")

    created = reject_duplicate_pair(
        db,
        asset_sha256_a=payload.asset_sha256_a,
        asset_sha256_b=payload.asset_sha256_b,
    )

    left, right = sorted([payload.asset_sha256_a, payload.asset_sha256_b])
    return DuplicateSuggestionRejectResponse(
        success=True,
        created=created,
        asset_sha256_a=left,
        asset_sha256_b=right,
    )


@router.post("/set-canonical", response_model=DuplicateAdjudicationResponse)
def set_duplicate_group_canonical(
    payload: DuplicateSetCanonicalRequest,
    db: Session = Depends(get_db_session),
) -> DuplicateAdjudicationResponse:
    try:
        result = set_group_canonical(db, asset_sha256=payload.asset_sha256)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if result is None:
        raise HTTPException(status_code=404, detail=f"Asset {payload.asset_sha256!r} not found.")

    return DuplicateAdjudicationResponse(
        success=result.success,
        noop=result.noop,
        message=result.message,
        group_id=result.group_id,
        asset_sha256=result.asset_sha256,
        affected_assets=result.affected_assets,
    )


@router.post("/remove-from-group", response_model=DuplicateAdjudicationResponse)
def remove_duplicate_group_member(
    payload: DuplicateRemoveFromGroupRequest,
    db: Session = Depends(get_db_session),
) -> DuplicateAdjudicationResponse:
    try:
        result = remove_asset_from_group(db, asset_sha256=payload.asset_sha256)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if result is None:
        raise HTTPException(status_code=404, detail=f"Asset {payload.asset_sha256!r} not found.")

    return DuplicateAdjudicationResponse(
        success=result.success,
        noop=result.noop,
        message=result.message,
        group_id=result.group_id,
        asset_sha256=result.asset_sha256,
        affected_assets=result.affected_assets,
    )


@router.post("/demote", response_model=DuplicateAdjudicationResponse)
def demote_duplicate_group_member(
    payload: DuplicateDemoteRequest,
    db: Session = Depends(get_db_session),
) -> DuplicateAdjudicationResponse:
    try:
        result = demote_group_asset(db, asset_sha256=payload.asset_sha256)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if result is None:
        raise HTTPException(status_code=404, detail=f"Asset {payload.asset_sha256!r} not found.")

    return DuplicateAdjudicationResponse(
        success=result.success,
        noop=result.noop,
        message=result.message,
        group_id=result.group_id,
        asset_sha256=result.asset_sha256,
        affected_assets=result.affected_assets,
    )


@router.post("/restore", response_model=DuplicateAdjudicationResponse)
def restore_duplicate_group_member(
    payload: DuplicateRestoreRequest,
    db: Session = Depends(get_db_session),
) -> DuplicateAdjudicationResponse:
    result = restore_group_asset(db, asset_sha256=payload.asset_sha256)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Asset {payload.asset_sha256!r} not found.")

    return DuplicateAdjudicationResponse(
        success=result.success,
        noop=result.noop,
        message=result.message,
        group_id=result.group_id,
        asset_sha256=result.asset_sha256,
        affected_assets=result.affected_assets,
    )


@router.get("/{group_id}", response_model=DuplicateGroupDetail)
def get_duplicate_group(group_id: int, db: Session = Depends(get_db_session)) -> DuplicateGroupDetail:
    result = get_duplicate_group_detail(db, group_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Duplicate group {group_id!r} not found.")
    return DuplicateGroupDetail(**result)
