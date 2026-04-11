"""Face-oriented API routes for Milestone 10 UI integration."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.ui_api import FaceListResponse, MoveFaceRequest, SuccessResponse
from app.services.identity.ui_api_service import (
    list_unassigned_faces,
    move_face_to_cluster,
    remove_face_from_cluster,
)
from app.services.vision.face_cluster_corrections import create_cluster_from_face

router = APIRouter(prefix="/api/faces", tags=["faces"])


@router.get("/unassigned", response_model=FaceListResponse)
def get_unassigned_faces(
    db: Session = Depends(get_db_session),
) -> FaceListResponse:
    """List unresolved faces that are not currently assigned to any cluster."""
    items = list_unassigned_faces(db)
    return FaceListResponse(count=len(items), items=items)


@router.post("/{face_id}/remove-from-cluster", response_model=SuccessResponse)
def post_remove_face_from_cluster(
    face_id: int,
    db: Session = Depends(get_db_session),
) -> SuccessResponse:
    """Remove one face from its current cluster."""
    try:
        remove_face_from_cluster(db, face_id)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "does not exist" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc

    return SuccessResponse(success=True)


@router.post("/{face_id}/move", response_model=SuccessResponse)
def post_move_face(
    face_id: int,
    request: MoveFaceRequest,
    db: Session = Depends(get_db_session),
) -> SuccessResponse:
    """Move one face into another cluster."""
    try:
        move_face_to_cluster(db, face_id, request.target_cluster_id)
    except ValueError as exc:
        message = str(exc)
        if "does not exist" in message:
            status_code = 404
        else:
            status_code = 400
        raise HTTPException(status_code=status_code, detail=message) from exc

    return SuccessResponse(success=True)


@router.post("/{face_id}/create-cluster", response_model=SuccessResponse)
def post_create_cluster_from_face(
    face_id: int,
    db: Session = Depends(get_db_session),
) -> SuccessResponse:
    """Create a new cluster and move the face into it."""
    try:
        create_cluster_from_face(db, face_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return SuccessResponse(success=True)
