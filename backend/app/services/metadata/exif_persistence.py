"""Persistence/update service for EXIF metadata."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.services.metadata.exif_extractor import ExtractedExifData


@dataclass(frozen=True)
class UpdatedExifAsset:
	"""An asset that was successfully updated with EXIF metadata."""

	sha256: str


@dataclass(frozen=True)
class SkippedExifUpdate:
	"""An asset skipped during EXIF persistence."""

	sha256: str
	reason: str


@dataclass(frozen=True)
class FailedExifUpdate:
	"""An asset that failed during EXIF persistence."""

	sha256: str
	reason: str


@dataclass(frozen=True)
class ExifPersistenceResult:
	"""Structured EXIF persistence output."""

	updated_assets: list[UpdatedExifAsset]
	skipped_assets: list[SkippedExifUpdate]
	failed_assets: list[FailedExifUpdate]


def persist_exif_updates(
	db_session: Session,
	extracted_items: list[ExtractedExifData],
) -> ExifPersistenceResult:
	"""Update existing Asset rows with extracted EXIF metadata."""
	updated_assets: list[UpdatedExifAsset] = []
	skipped_assets: list[SkippedExifUpdate] = []
	failed_assets: list[FailedExifUpdate] = []

	for item in extracted_items:
		asset = db_session.get(Asset, item.sha256)
		if asset is None:
			skipped_assets.append(
				SkippedExifUpdate(
					sha256=item.sha256,
					reason="Asset does not exist in database.",
				)
			)
			continue

		try:
			asset.exif_datetime_original = item.exif_datetime_original
			asset.exif_create_date = item.exif_create_date
			asset.gps_latitude = item.gps_latitude
			asset.gps_longitude = item.gps_longitude
			asset.camera_make = item.camera_make
			asset.camera_model = item.camera_model
			asset.lens_model = item.lens_model
			db_session.commit()
			updated_assets.append(UpdatedExifAsset(sha256=item.sha256))
		except SQLAlchemyError as error:
			db_session.rollback()
			failed_assets.append(FailedExifUpdate(sha256=item.sha256, reason=str(error)))

	return ExifPersistenceResult(
		updated_assets=updated_assets,
		skipped_assets=skipped_assets,
		failed_assets=failed_assets,
	)
