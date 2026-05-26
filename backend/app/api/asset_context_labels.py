"""API routes for asset context labels."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.context_labels import AssetContextLabelListResponse
from app.services.context_labels.service import list_asset_context_labels

router = APIRouter(prefix="/api/asset-context-labels", tags=["asset-context-labels"])


@router.get("", response_model=AssetContextLabelListResponse)
def get_asset_context_labels_endpoint(
    asset_sha256: str | None = Query(default=None),
    context_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db_session),
) -> AssetContextLabelListResponse:
    """List context labels with active-only default status filter."""
    try:
        return list_asset_context_labels(
            db,
            asset_sha256=asset_sha256,
            context_type=context_type,
            status=status,
            source_type=source_type,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
