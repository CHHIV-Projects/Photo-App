"""API routes for Places (location-based) view."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.places import PlaceListResponse, PlaceDetail, PlaceLabelUpdateRequest
from app.services.places import list_places, get_place_detail, update_place_user_label

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
