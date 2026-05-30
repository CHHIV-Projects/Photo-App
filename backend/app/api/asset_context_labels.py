"""API routes for asset context labels."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.context_labels import (
    AssetContextLabelCreateRequest,
    AssetContextLabelCreateResponse,
    AssetContextLabelSummaryBatchRequest,
    AssetContextLabelSummaryBatchResponse,
    AssetContextLabelListResponse,
    ContextLabelPropagationPreviewResponse,
    ContextLabelPropagationRequest,
    ContextLabelPropagationResponse,
)
from app.services.context_labels.service import (
    create_asset_context_label,
    get_context_label_propagation_preview,
    list_active_landmark_context_summaries,
    list_asset_context_labels,
    propagate_context_label_to_duplicate_group_members,
)

router = APIRouter(prefix="/api/asset-context-labels", tags=["asset-context-labels"])


@router.post("", response_model=AssetContextLabelCreateResponse)
def create_asset_context_label_endpoint(
    payload: AssetContextLabelCreateRequest,
    db: Session = Depends(get_db_session),
) -> AssetContextLabelCreateResponse:
    """Create one active context label for an asset (manual or provider-assisted)."""
    try:
        return create_asset_context_label(db, payload=payload)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "does not exist" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.post("/summary", response_model=AssetContextLabelSummaryBatchResponse)
def get_asset_context_label_summary_batch_endpoint(
    payload: AssetContextLabelSummaryBatchRequest,
    db: Session = Depends(get_db_session),
) -> AssetContextLabelSummaryBatchResponse:
    """Return active landmark context summaries for an explicit asset list."""
    try:
        return list_active_landmark_context_summaries(db, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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


@router.get("/{label_id}/propagation-preview", response_model=ContextLabelPropagationPreviewResponse)
def get_context_label_propagation_preview_endpoint(
    label_id: int,
    db: Session = Depends(get_db_session),
) -> ContextLabelPropagationPreviewResponse:
    """Preview duplicate-group propagation targets for one active landmark context label."""
    try:
        return get_context_label_propagation_preview(
            db,
            label_id=label_id,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "does not exist" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.post("/{label_id}/propagate", response_model=ContextLabelPropagationResponse)
def propagate_context_label_endpoint(
    label_id: int,
    payload: ContextLabelPropagationRequest,
    db: Session = Depends(get_db_session),
) -> ContextLabelPropagationResponse:
    """Propagate one active landmark context label to selected duplicate-group members."""
    try:
        return propagate_context_label_to_duplicate_group_members(
            db,
            label_id=label_id,
            payload=payload,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "does not exist" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
