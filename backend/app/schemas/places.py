"""Schemas for Places (location-based) view and edits."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.photos import PhotoSummary


class PlaceAliasSummary(BaseModel):
    id: int
    place_id: str
    alias: str
    alias_normalized: str
    created_at_utc: datetime | None = None


class PlaceAliasListResponse(BaseModel):
    count: int
    items: list[PlaceAliasSummary]


class PlaceAliasCreateRequest(BaseModel):
    alias: str


class PlaceObservationAssetSummary(BaseModel):
    asset_sha256: str
    filename: str | None = None
    image_url: str | None = None
    display_url: str | None = None


class PlaceObservationLinkedPlaceSummary(BaseModel):
    place_id: str
    display_label: str
    latitude: float
    longitude: float


class PlaceObservationSummary(BaseModel):
    id: int
    place_id: str | None = None
    asset_sha256: str | None = None
    source_type: str
    observation_type: str
    status: str
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
    created_at_utc: datetime | None = None
    asset: PlaceObservationAssetSummary | None = None
    linked_place: PlaceObservationLinkedPlaceSummary | None = None


class PlaceObservationListResponse(BaseModel):
    count: int
    items: list[PlaceObservationSummary]


class PlaceSummary(BaseModel):
    """Summary of a geographic location."""

    place_id: str
    latitude: float
    longitude: float
    photo_count: int
    thumbnail_url: str | None = None
    user_label: str | None = None
    display_label: str
    formatted_address: str | None = None
    city: str | None = None
    county: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    geocode_status: str = "never_tried"
    place_type: str = "generic"
    user_verified: bool = False
    address_locked: bool = False
    alias_count: int = 0


class PlaceListResponse(BaseModel):
    """List of places."""

    count: int
    items: list[PlaceSummary]


class PlaceDetail(BaseModel):
    """Detail view of a location with photos."""

    place_id: str
    latitude: float
    longitude: float
    user_label: str | None = None
    display_label: str
    formatted_address: str | None = None
    street: str | None = None
    city: str | None = None
    county: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    geocode_status: str = "never_tried"
    place_type: str = "generic"
    user_verified: bool = False
    user_verified_at_utc: datetime | None = None
    address_locked: bool = False
    address_source: str | None = None
    notes: str | None = None
    aliases: list[PlaceAliasSummary] = Field(default_factory=list)
    photos: list[PhotoSummary]


class PlaceLabelUpdateRequest(BaseModel):
    user_label: str | None = None


class PlacePatchRequest(BaseModel):
    user_label: str | None = None
    place_type: str | None = None
    formatted_address: str | None = None
    street: str | None = None
    city: str | None = None
    county: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    user_verified: bool | None = None
    address_locked: bool | None = None
    address_source: str | None = None
    notes: str | None = None


class PlaceObservationPatchRequest(BaseModel):
    status: str
    apply_to_canonical: bool = False
    set_user_verified: bool = False
    set_address_locked: bool = False


class GlobalPlaceObservationPatchRequest(BaseModel):
    status: str
    place_id: str | None = None


class PlaceObservationCreatePlaceRequest(BaseModel):
    user_label: str
