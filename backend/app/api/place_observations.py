"""API routes for global place observation review workflows."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.context_labels import (
    AcceptObservationAsContextRequest,
    AcceptObservationAsContextResponse,
)
from app.schemas.places import (
    GlobalPlaceObservationPatchRequest,
    PlaceObservationCreatePlaceRequest,
    PlaceObservationListResponse,
    PlaceObservationSummary,
)
from app.services.places import (
    create_place_from_observation,
    list_global_place_observations,
    patch_global_place_observation,
)
from app.services.context_labels.service import accept_landmark_observation_as_context

router = APIRouter(prefix="/api/place-observations", tags=["place-observations"])


@router.get("", response_model=PlaceObservationListResponse)
def get_place_observations_endpoint(
    source_type: str | None = Query(default=None),
    observation_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db_session),
) -> PlaceObservationListResponse:
    """List place observations independently of place_id for review workflows."""
    try:
        return list_global_place_observations(
            db,
            source_type=source_type,
            observation_type=observation_type,
            status=status,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/{observation_id}", response_model=PlaceObservationSummary)
def patch_place_observation_endpoint(
    observation_id: int,
    payload: GlobalPlaceObservationPatchRequest,
    db: Session = Depends(get_db_session),
) -> PlaceObservationSummary:
    """Patch observation status and optionally link to an existing place."""
    try:
        return patch_global_place_observation(
            db,
            observation_id=observation_id,
            payload=payload,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "does not exist" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.post("/{observation_id}/create-place", response_model=PlaceObservationSummary)
def create_place_from_observation_endpoint(
    observation_id: int,
    payload: PlaceObservationCreatePlaceRequest,
    db: Session = Depends(get_db_session),
) -> PlaceObservationSummary:
    """Create a landmark place from an observation and link the observation to it."""
    try:
        return create_place_from_observation(
            db,
            observation_id=observation_id,
            payload=payload,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "does not exist" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.post("/{observation_id}/accept-as-context", response_model=AcceptObservationAsContextResponse)
def accept_observation_as_context_endpoint(
    observation_id: int,
    payload: AcceptObservationAsContextRequest,
    db: Session = Depends(get_db_session),
) -> AcceptObservationAsContextResponse:
    """Accept a Google Vision landmark observation as a durable asset context label."""
    try:
        return accept_landmark_observation_as_context(
            db,
            observation_id=observation_id,
            payload=payload,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "does not exist" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
