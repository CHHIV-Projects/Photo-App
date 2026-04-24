"""Places API read services backed by stable place entities."""

from sqlalchemy import func, select, nullslast
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.face import Face
from app.models.place import Place
from app.schemas.places import PlaceSummary, PlaceDetail, PlaceListResponse
from app.schemas.photos import PhotoSummary
from app.services.location.geocoding_service import build_place_display_label
from app.services.photos.photos_service import _build_asset_url

def list_places(db: Session) -> PlaceListResponse:
	"""List stable places with photo counts and representative thumbnails, sorted by usage and place_id."""
	# Subquery: rank assets within each place by most recent captured_at (nulls last), then sha256 for stability.
	asset_ranked_sq = (
		select(
			Asset.place_id,
			Asset.sha256,
			Asset.extension,
			func.row_number().over(
				partition_by=Asset.place_id,
				order_by=[nullslast(Asset.captured_at.desc()), Asset.sha256.asc()],
			).label("rn"),
		)
		.where(Asset.place_id.isnot(None), Asset.visibility_status == "visible")
		.subquery("asset_ranked")
	)

	# Filter to only the top-ranked asset per place.
	thumb_sq = (
		select(
			asset_ranked_sq.c.place_id,
			asset_ranked_sq.c.sha256,
			asset_ranked_sq.c.extension,
		)
		.where(asset_ranked_sq.c.rn == 1)
		.subquery("thumb")
	)

	rows = db.execute(
		select(
			Place.place_id,
			Place.representative_latitude,
			Place.representative_longitude,
			Place.formatted_address,
			Place.city,
			Place.county,
			Place.state,
			Place.country,
			Place.geocode_status,
			func.count(Asset.sha256).label("photo_count"),
			thumb_sq.c.sha256.label("thumb_sha256"),
			thumb_sq.c.extension.label("thumb_ext"),
		)
		.join(Asset, Asset.place_id == Place.place_id)
		.where(Asset.visibility_status == "visible")
		.outerjoin(thumb_sq, thumb_sq.c.place_id == Place.place_id)
		.group_by(
			Place.place_id,
			Place.representative_latitude,
			Place.representative_longitude,
			Place.formatted_address,
			Place.city,
			Place.county,
			Place.state,
			Place.country,
			Place.geocode_status,
			thumb_sq.c.sha256,
			thumb_sq.c.extension,
		)
		.order_by(func.count(Asset.sha256).desc(), Place.place_id.asc())
	).all()

	items = [
		PlaceSummary(
			place_id=str(row.place_id),
			latitude=row.representative_latitude,
			longitude=row.representative_longitude,
			photo_count=int(row.photo_count),
			thumbnail_url=_build_asset_url(row.thumb_sha256, row.thumb_ext) if row.thumb_sha256 else None,
			display_label=build_place_display_label(
				city=row.city,
				state=row.state,
				country=row.country,
				formatted_address=row.formatted_address,
				latitude=row.representative_latitude,
				longitude=row.representative_longitude,
			),
			formatted_address=row.formatted_address,
			city=row.city,
			county=row.county,
			state=row.state,
			country=row.country,
			geocode_status=row.geocode_status,
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
			Asset.visibility_status == "visible",
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
		display_label=build_place_display_label(
			city=place.city,
			state=place.state,
			country=place.country,
			formatted_address=place.formatted_address,
			latitude=place.representative_latitude,
			longitude=place.representative_longitude,
		),
		formatted_address=place.formatted_address,
		city=place.city,
		county=place.county,
		state=place.state,
		country=place.country,
		geocode_status=place.geocode_status,
		photos=photos,
	)
