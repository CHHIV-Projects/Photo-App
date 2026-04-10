"""Schemas for Places (location-based) view."""
from pydantic import BaseModel

from app.schemas.photos import PhotoSummary


class PlaceSummary(BaseModel):
	"""Summary of a geographic location."""

	place_id: str
	latitude: float
	longitude: float
	photo_count: int


class PlaceListResponse(BaseModel):
	"""List of places."""

	count: int
	items: list[PlaceSummary]


class PlaceDetail(BaseModel):
	"""Detail view of a location with photos."""

	place_id: str
	latitude: float
	longitude: float
	photos: list[PhotoSummary]
