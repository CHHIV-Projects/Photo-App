"""Places API read services backed by stable place entities."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.face import Face
from app.models.place import Place
from app.schemas.places import PlaceSummary, PlaceDetail, PlaceListResponse
from app.schemas.photos import PhotoSummary
from app.services.photos.photos_service import _build_asset_url

def list_places(db: Session) -> PlaceListResponse:
	"""List stable places with photo counts, sorted by usage and place_id."""
	rows = db.execute(
		select(
			Place.place_id,
			Place.representative_latitude,
			Place.representative_longitude,
			func.count(Asset.sha256).label("photo_count"),
		)
		.join(Asset, Asset.place_id == Place.place_id)
		.group_by(Place.place_id, Place.representative_latitude, Place.representative_longitude)
		.order_by(func.count(Asset.sha256).desc(), Place.place_id.asc())
	).all()

	items = [
		PlaceSummary(
			place_id=str(row.place_id),
			latitude=row.representative_latitude,
			longitude=row.representative_longitude,
			photo_count=int(row.photo_count),
		)
		for row in rows
	]

	return PlaceListResponse(count=len(items), items=items)


def get_place_detail(db: Session, place_id: str) -> PlaceDetail | None:
	"""Get photos assigned to a stable place entity."""
	try:
		place_pk = int(place_id)
	except (ValueError, AttributeError):
		return None

	place = db.get(Place, place_pk)
	if place is None:
		return None

	assets = (
		db.query(Asset)
		.filter(
			Asset.place_id == place.place_id,
		)
		.order_by(Asset.captured_at.asc())
		.all()
	)

	if not assets:
		return None

	photos = []
	for asset in assets:
		face_count = db.query(Face).filter(Face.asset_sha256 == asset.sha256).count()

		photo = PhotoSummary(
			asset_sha256=asset.sha256,
			filename=asset.original_filename,
			image_url=_build_asset_url(asset.sha256, asset.extension),
			face_count=face_count,
		)
		photos.append(photo)

	return PlaceDetail(
		place_id=str(place.place_id),
		latitude=place.representative_latitude,
		longitude=place.representative_longitude,
		photos=photos,
	)
