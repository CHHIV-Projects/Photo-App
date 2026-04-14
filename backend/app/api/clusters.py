"""Cluster-oriented API routes for Milestone 10 UI integration."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.ui_api import (
    AssignPersonRequest,
    ClusterDetail,
    ClusterListResponse,
    ClusterSuggestionResponse,
    MergeClustersRequest,
    SuccessResponse,
)
from app.services.identity.ui_api_service import (
    assign_cluster_to_person,
    get_cluster_suggestions,
    get_cluster_detail,
    ignore_cluster,
    list_clusters_for_review,
    merge_clusters,
)

router = APIRouter(prefix="/api/clusters", tags=["clusters"])


@router.get("", response_model=ClusterListResponse)
def get_clusters(
    include_ignored: bool = False,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db_session),
) -> ClusterListResponse:
    """List clusters for UI review."""
    items = list_clusters_for_review(
        db,
        include_ignored=include_ignored,
        limit=limit,
        offset=offset,
    )
    return ClusterListResponse(count=len(items), items=items)


@router.get("/{cluster_id}", response_model=ClusterDetail)
def get_cluster(cluster_id: int, db: Session = Depends(get_db_session)) -> ClusterDetail:
    """Return one cluster with all face entries."""
    try:
        detail = get_cluster_detail(db, cluster_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return ClusterDetail(**detail)


@router.get("/{cluster_id}/suggestions", response_model=ClusterSuggestionResponse)
def get_cluster_person_suggestions(
    cluster_id: int,
    db: Session = Depends(get_db_session),
) -> ClusterSuggestionResponse:
    """Return deterministic person suggestions for one unresolved cluster."""
    try:
        payload = get_cluster_suggestions(db, cluster_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return ClusterSuggestionResponse(**payload)


@router.post("/{cluster_id}/assign-person", response_model=SuccessResponse)
def post_assign_person(
    cluster_id: int,
    request: AssignPersonRequest,
    db: Session = Depends(get_db_session),
) -> SuccessResponse:
    """Assign or reassign cluster ownership to a person."""
    try:
        assign_cluster_to_person(db, cluster_id, request.person_id)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "does not exist" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc

    return SuccessResponse(success=True)


@router.post("/{cluster_id}/ignore", response_model=SuccessResponse)
def post_ignore_cluster(cluster_id: int, db: Session = Depends(get_db_session)) -> SuccessResponse:
    """Set cluster ignored=true for review filtering."""
    try:
        ignore_cluster(db, cluster_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return SuccessResponse(success=True)


@router.post("/merge", response_model=SuccessResponse)
def post_merge_clusters(
    request: MergeClustersRequest,
    db: Session = Depends(get_db_session),
) -> SuccessResponse:
    """Merge one source cluster into a target cluster."""
    try:
        merge_clusters(db, request.source_cluster_id, request.target_cluster_id)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "does not exist" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc

    return SuccessResponse(success=True)
