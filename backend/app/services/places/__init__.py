"""Places (location-based) service for grouping photos by GPS coordinates."""
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.face import Face
from app.schemas.places import PlaceSummary, PlaceDetail, PlaceListResponse
from app.schemas.photos import PhotoSummary
from app.services.photos.photos_service import _build_asset_url


def _round_coordinate(value: float, decimals: int = 2) -> float:
	"""Round coordinate to specified decimal places."""
	if value is None:
		return None
	multiplier = 10 ** decimals
	return round(value * multiplier) / multiplier


def _build_place_id(latitude: float, longitude: float) -> str:
	"""Build place_id from rounded coordinates."""
	lat = _round_coordinate(latitude, 2)
	lon = _round_coordinate(longitude, 2)
	return f"{lat}_{lon}"


def list_places(db: Session) -> PlaceListResponse:
	"""List all unique grouped places (rounded coordinates) with photo counts.
	
	Only includes assets with valid GPS data.
	Sorted by photo_count descending.
	"""
	# Query assets with GPS data, group by rounded coordinates
	assets_with_gps = (
		db.query(Asset)
		.filter(Asset.gps_latitude.isnot(None), Asset.gps_longitude.isnot(None))
		.all()
	)
	
	# Group by rounded coordinates
	places_dict = {}
	for asset in assets_with_gps:
		place_id = _build_place_id(asset.gps_latitude, asset.gps_longitude)
		if place_id not in places_dict:
			places_dict[place_id] = {
				"latitude": _round_coordinate(asset.gps_latitude, 2),
				"longitude": _round_coordinate(asset.gps_longitude, 2),
				"photo_count": 0,
			}
		places_dict[place_id]["photo_count"] += 1
	
	# Convert to PlaceSummary list, sorted by photo_count descending
	items = [
		PlaceSummary(
			place_id=place_id,
			latitude=data["latitude"],
			longitude=data["longitude"],
			photo_count=data["photo_count"],
		)
		for place_id, data in places_dict.items()
	]
	items.sort(key=lambda x: x.photo_count, reverse=True)
	
	return PlaceListResponse(count=len(items), items=items)


def get_place_detail(db: Session, place_id: str) -> PlaceDetail | None:
	"""Get photos at a specific location (rounded coordinates).
	
	Parse place_id to extract rounded lat/lon, then find all assets
	that round to the same coordinates.
	"""
	# Parse place_id
	try:
		lat_str, lon_str = place_id.split("_")
		target_lat = float(lat_str)
		target_lon = float(lon_str)
	except (ValueError, AttributeError):
		return None
	
	# Query assets within the tolerance of rounded coordinates
	# to account for floating-point precision
	tolerance = 0.005  # ~500 meters at equator for 2 decimal places
	assets = (
		db.query(Asset)
		.filter(
			Asset.gps_latitude.isnot(None),
			Asset.gps_longitude.isnot(None),
			func.abs(Asset.gps_latitude - target_lat) < tolerance,
			func.abs(Asset.gps_longitude - target_lon) < tolerance,
		)
		.order_by(Asset.captured_at.asc())
		.all()
	)
	
	if not assets:
		return None
	
	# Build PhotoSummary for each asset
	photos = []
	for asset in assets:
		# Count faces in this asset
		face_count = db.query(Face).filter(Face.asset_sha256 == asset.sha256).count()
		
		photo = PhotoSummary(
			asset_sha256=asset.sha256,
			filename=asset.original_filename,
			image_url=_build_asset_url(asset.sha256, asset.extension),
			face_count=face_count,
		)
		photos.append(photo)
	
	return PlaceDetail(
		place_id=place_id,
		latitude=target_lat,
		longitude=target_lon,
		photos=photos,
	)
