"""Place observation write/read helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.place import Place
from app.models.place_observation import PlaceObservation

VALID_PLACE_OBSERVATION_SOURCE_TYPES = {
    "exif",
    "reverse_geocode",
    "google_vision",
    "provenance",
    "manual",
    "system",
}

VALID_PLACE_OBSERVATION_TYPES = {
    "location",
    "address",
    "landmark",
    "place_label",
    "provenance_clue",
}

VALID_PLACE_OBSERVATION_STATUSES = {
    "pending",
    "accepted",
    "rejected",
    "ignored",
    "superseded",
}

MAX_PLACE_OBSERVATION_LIST_LIMIT = 100


@dataclass(frozen=True)
class CreatePlaceObservationInput:
    source_type: str
    observation_type: str
    status: str = "pending"
    asset_sha256: str | None = None
    place_id: int | None = None
    raw_label: str | None = None
    formatted_address: str | None = None
    street: str | None = None
    city: str | None = None
    county: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    confidence: float | None = None
    raw_response_json: dict[str, Any] | None = None


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def create_place_observation(db: Session, payload: CreatePlaceObservationInput) -> PlaceObservation:
    """Persist one place observation with validation."""
    if payload.asset_sha256 is None and payload.place_id is None:
        raise ValueError("At least one of asset_sha256 or place_id is required.")

    source_type = _clean_text(payload.source_type)
    if source_type not in VALID_PLACE_OBSERVATION_SOURCE_TYPES:
        raise ValueError("Invalid source_type for place observation.")

    observation_type = _clean_text(payload.observation_type)
    if observation_type not in VALID_PLACE_OBSERVATION_TYPES:
        raise ValueError("Invalid observation_type for place observation.")

    status = _clean_text(payload.status) or "pending"
    if status not in VALID_PLACE_OBSERVATION_STATUSES:
        raise ValueError("Invalid status for place observation.")

    place_id_value = payload.place_id
    if place_id_value is not None:
        place = db.get(Place, int(place_id_value))
        if place is None:
            raise ValueError(f"Place {place_id_value} does not exist.")

    observation = PlaceObservation(
        asset_sha256=payload.asset_sha256,
        place_id=place_id_value,
        source_type=source_type,
        observation_type=observation_type,
        status=status,
        raw_label=_clean_text(payload.raw_label),
        formatted_address=_clean_text(payload.formatted_address),
        street=_clean_text(payload.street),
        city=_clean_text(payload.city),
        county=_clean_text(payload.county),
        state=_clean_text(payload.state),
        postal_code=_clean_text(payload.postal_code),
        country=_clean_text(payload.country),
        latitude=payload.latitude,
        longitude=payload.longitude,
        confidence=payload.confidence,
        raw_response_json=payload.raw_response_json,
    )
    db.add(observation)
    db.commit()
    db.refresh(observation)
    return observation


def list_place_observations(db: Session, place_id: int, *, limit: int = 100) -> list[PlaceObservation]:
    """List recent observations for a place."""
    resolved_limit = max(1, min(int(limit), 500))
    return list(
        db.scalars(
            select(PlaceObservation)
            .where(PlaceObservation.place_id == place_id)
            .order_by(PlaceObservation.created_at_utc.desc(), PlaceObservation.id.desc())
            .limit(resolved_limit)
        ).all()
    )


def update_place_observation_status(
    db: Session,
    *,
    place_id: int,
    observation_id: int,
    status: str,
    apply_to_canonical: bool,
    set_user_verified: bool,
    set_address_locked: bool,
) -> tuple[PlaceObservation, Place | None]:
    """Update observation status and optionally apply supported fields to place canonical data."""
    normalized_status = _clean_text(status)
    if normalized_status is None or normalized_status not in VALID_PLACE_OBSERVATION_STATUSES:
        raise ValueError("Invalid status for place observation.")

    place = db.get(Place, int(place_id))
    if place is None:
        raise ValueError(f"Place {place_id} does not exist.")

    observation = db.get(PlaceObservation, int(observation_id))
    if observation is None or observation.place_id != place.place_id:
        raise ValueError("Observation does not exist for this place.")

    if apply_to_canonical:
        if normalized_status != "accepted":
            raise ValueError("apply_to_canonical requires status=accepted.")
        if observation.observation_type != "address":
            raise ValueError("apply_to_canonical is supported only for address observations.")

        place.formatted_address = observation.formatted_address
        place.street = observation.street
        place.city = observation.city
        place.county = observation.county
        place.state = observation.state
        place.postal_code = observation.postal_code
        place.country = observation.country
        place.address_source = observation.source_type

        if set_user_verified:
            place.user_verified = True
        if set_address_locked:
            place.address_locked = True

    observation.status = normalized_status
    db.commit()
    db.refresh(observation)
    if apply_to_canonical:
        db.refresh(place)
        return observation, place
    return observation, None
