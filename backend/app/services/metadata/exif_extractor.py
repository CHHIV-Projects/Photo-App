"""EXIF extraction service for stored assets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import exiftool  # type: ignore[import-not-found]

from app.models.asset import Asset


@dataclass(frozen=True)
class ExtractedExifData:
	"""Extracted EXIF fields for one asset."""

	sha256: str
	exif_datetime_original: datetime | None
	exif_create_date: datetime | None
	gps_latitude: float | None
	gps_longitude: float | None
	camera_make: str | None
	camera_model: str | None
	lens_model: str | None


@dataclass(frozen=True)
class SkippedExifAsset:
	"""An asset skipped because no objective EXIF metadata was found."""

	sha256: str
	reason: str


@dataclass(frozen=True)
class FailedExifAsset:
	"""An asset that failed EXIF extraction."""

	sha256: str
	reason: str


@dataclass(frozen=True)
class ExifExtractionResult:
	"""Structured EXIF extraction output for a batch."""

	extracted: list[ExtractedExifData]
	skipped: list[SkippedExifAsset]
	failed: list[FailedExifAsset]


def _parse_datetime(value: str | None) -> datetime | None:
	"""Parse EXIF date/time format like '2024:03:25 14:05:30'."""
	if not value:
		return None

	cleaned = value.split("+")[0].strip()
	cleaned = cleaned.split("-")[0].strip() if "+" not in value and value.count(":") > 2 else cleaned
	try:
		return datetime.strptime(cleaned, "%Y:%m:%d %H:%M:%S")
	except ValueError:
		return None


def _parse_float(value: object) -> float | None:
	"""Safely parse float values from EXIF fields."""
	if value is None:
		return None
	try:
		return float(value)
	except (TypeError, ValueError):
		return None


def _extract_single_metadata(metadata: dict[str, object], asset: Asset) -> ExtractedExifData | None:
	"""Build extracted EXIF structure from one ExifTool metadata dict."""
	exif_datetime_original = _parse_datetime(metadata.get("EXIF:DateTimeOriginal") if isinstance(metadata, dict) else None)  # type: ignore[arg-type]
	exif_create_date = _parse_datetime(metadata.get("EXIF:CreateDate") if isinstance(metadata, dict) else None)  # type: ignore[arg-type]
	gps_latitude = _parse_float(metadata.get("EXIF:GPSLatitude") if isinstance(metadata, dict) else None)  # type: ignore[arg-type]
	gps_longitude = _parse_float(metadata.get("EXIF:GPSLongitude") if isinstance(metadata, dict) else None)  # type: ignore[arg-type]
	camera_make = str(metadata.get("EXIF:Make")).strip() if metadata.get("EXIF:Make") else None
	camera_model = str(metadata.get("EXIF:Model")).strip() if metadata.get("EXIF:Model") else None
	lens_model = str(metadata.get("EXIF:LensModel")).strip() if metadata.get("EXIF:LensModel") else None

	if not any(
		[
			exif_datetime_original,
			exif_create_date,
			gps_latitude,
			gps_longitude,
			camera_make,
			camera_model,
			lens_model,
		]
	):
		return None

	return ExtractedExifData(
		sha256=asset.sha256,
		exif_datetime_original=exif_datetime_original,
		exif_create_date=exif_create_date,
		gps_latitude=gps_latitude,
		gps_longitude=gps_longitude,
		camera_make=camera_make,
		camera_model=camera_model,
		lens_model=lens_model,
	)


def extract_exif_for_assets(assets: list[Asset]) -> ExifExtractionResult:
	"""Extract objective EXIF metadata for database assets."""
	extracted: list[ExtractedExifData] = []
	skipped: list[SkippedExifAsset] = []
	failed: list[FailedExifAsset] = []

	if not assets:
		return ExifExtractionResult(extracted=extracted, skipped=skipped, failed=failed)

	try:
		with exiftool.ExifToolHelper() as helper:
			for asset in assets:
				try:
					file_path = Path(asset.vault_path)
					metadata_list = helper.get_metadata(str(file_path))
					metadata = metadata_list[0] if metadata_list else {}
					extracted_data = _extract_single_metadata(metadata, asset)
					if extracted_data is None:
						skipped.append(SkippedExifAsset(sha256=asset.sha256, reason="No objective EXIF fields found."))
					else:
						extracted.append(extracted_data)
				except Exception as error:  # noqa: BLE001
					failed.append(FailedExifAsset(sha256=asset.sha256, reason=str(error)))
	except Exception as error:  # noqa: BLE001
		for asset in assets:
			failed.append(FailedExifAsset(sha256=asset.sha256, reason=f"ExifTool unavailable: {error}"))

	return ExifExtractionResult(extracted=extracted, skipped=skipped, failed=failed)


def extract_exif_for_asset(asset: Asset) -> ExifExtractionResult:
	"""Extract EXIF metadata for a single asset."""
	return extract_exif_for_assets([asset])
