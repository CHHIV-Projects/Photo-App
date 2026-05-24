"""API routes for Places (location-based) view."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.places import (
    PlaceAliasCreateRequest,
    PlaceAliasListResponse,
    PlaceAliasSummary,
    PlaceDetail,
    PlaceLabelUpdateRequest,
    PlaceListResponse,
    PlaceObservationListResponse,
    PlaceObservationPatchRequest,
    PlaceObservationSummary,
    PlacePatchRequest,
)
from app.schemas.ui_api import SuccessResponse
from app.services.places import (
    add_place_alias,
    delete_place_alias,
    get_place_detail,
    get_place_observation_list,
    list_place_aliases,
    list_places,
    patch_place_observation,
    patch_place,
    update_place_user_label,
)

router = APIRouter(prefix="/api/places", tags=["places"])


@router.get("", response_model=PlaceListResponse)
def get_places(db: Session = Depends(get_db_session)) -> PlaceListResponse:
    """Get list of stable place entities."""
    return list_places(db)


@router.get("/{place_id}", response_model=PlaceDetail)
def get_place_detail_endpoint(place_id: str, db: Session = Depends(get_db_session)) -> PlaceDetail:
    """Get photos assigned to a specific place."""
    place_detail = get_place_detail(db, place_id)
    if place_detail is None:
        raise HTTPException(status_code=404, detail="Place not found")
    return place_detail


@router.post("/{place_id}/label", response_model=PlaceDetail)
def update_place_label_endpoint(
    place_id: str,
    payload: PlaceLabelUpdateRequest,
    db: Session = Depends(get_db_session),
) -> PlaceDetail:
    """Set, edit, or clear user-defined place label."""
    try:
        updated = update_place_user_label(db, place_id, payload.user_label)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if updated is None:
        raise HTTPException(status_code=404, detail="Place not found")
    return updated


@router.patch("/{place_id}", response_model=PlaceDetail)
def patch_place_endpoint(
    place_id: str,
    payload: PlacePatchRequest,
    db: Session = Depends(get_db_session),
) -> PlaceDetail:
    """Patch place metadata, address fields, and verification flags."""
    try:
        updated = patch_place(db, place_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if updated is None:
        raise HTTPException(status_code=404, detail="Place not found")
    return updated


@router.get("/{place_id}/aliases", response_model=PlaceAliasListResponse)
def get_place_aliases_endpoint(place_id: str, db: Session = Depends(get_db_session)) -> PlaceAliasListResponse:
    """List aliases for one place."""
    try:
        items = list_place_aliases(db, place_id)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "does not exist" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    return PlaceAliasListResponse(count=len(items), items=items)


@router.post("/{place_id}/aliases", response_model=PlaceAliasSummary, status_code=status.HTTP_201_CREATED)
def post_place_alias_endpoint(
    place_id: str,
    payload: PlaceAliasCreateRequest,
    db: Session = Depends(get_db_session),
) -> PlaceAliasSummary:
    """Create one alias for one place."""
    try:
        return add_place_alias(db, place_id, payload.alias)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "does not exist" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.delete("/{place_id}/aliases/{alias_id}", response_model=SuccessResponse)
def delete_place_alias_endpoint(
    place_id: str,
    alias_id: int,
    db: Session = Depends(get_db_session),
) -> SuccessResponse:
    """Delete one alias from one place."""
    try:
        delete_place_alias(db, place_id, alias_id)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "does not exist" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    return SuccessResponse(success=True)


@router.get("/{place_id}/observations", response_model=PlaceObservationListResponse)
def get_place_observations_endpoint(
    place_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db_session),
) -> PlaceObservationListResponse:
    """List recent observations for one place."""
    try:
        return get_place_observation_list(db, place_id, limit=limit)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "does not exist" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.patch("/{place_id}/observations/{observation_id}", response_model=PlaceObservationSummary)
def patch_place_observation_endpoint(
    place_id: str,
    observation_id: int,
    payload: PlaceObservationPatchRequest,
    db: Session = Depends(get_db_session),
) -> PlaceObservationSummary:
    """Patch one observation status and optionally apply address data to canonical place."""
    try:
        return patch_place_observation(
            db,
            place_id=place_id,
            observation_id=observation_id,
            payload=payload,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "does not exist" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
