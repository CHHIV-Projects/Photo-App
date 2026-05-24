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
