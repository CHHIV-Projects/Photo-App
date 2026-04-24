"""Schemas for Places (location-based) view."""
from pydantic import BaseModel

from app.schemas.photos import PhotoSummary


class PlaceSummary(BaseModel):
	"""Summary of a geographic location."""

	place_id: str
	latitude: float
	longitude: float
	photo_count: int
	thumbnail_url: str | None = None
	display_label: str
	formatted_address: str | None = None
	city: str | None = None
	county: str | None = None
	state: str | None = None
	country: str | None = None
	geocode_status: str = "never_tried"


class PlaceListResponse(BaseModel):
	"""List of places."""

	count: int
	items: list[PlaceSummary]


class PlaceDetail(BaseModel):
	"""Detail view of a location with photos."""

	place_id: str
	latitude: float
	longitude: float
	display_label: str
	formatted_address: str | None = None
	city: str | None = None
	county: str | None = None
	state: str | None = None
	country: str | None = None
	geocode_status: str = "never_tried"
	photos: list[PhotoSummary]
