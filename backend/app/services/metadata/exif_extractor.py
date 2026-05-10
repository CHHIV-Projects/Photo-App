"""EXIF extraction service for stored assets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import exiftool  # type: ignore[import-not-found]

from app.models.asset import Asset

VIDEO_EXTENSIONS = {".mov", ".mp4", ".m4v"}
# Video-native date priority for 12.40 stays narrow and deterministic.
VIDEO_PRIMARY_DATE_FIELDS = (
	"QuickTime:CreationDate",
	"Keys:CreationDate",
	"com.apple.quicktime.creationdate",
)
VIDEO_SECONDARY_DATE_FIELDS = (
	"QuickTime:CreateDate",
	"QuickTime:MediaCreateDate",
	"QuickTime:TrackCreateDate",
)


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
	software: str | None


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
	"""Parse EXIF/QuickTime date formats and normalize aware values to naive UTC."""
	if not value:
		return None

	raw = str(value).strip()
	if not raw:
		return None

	for candidate in (raw, raw.replace("Z", "+00:00")):
		for fmt in (
			"%Y:%m:%d %H:%M:%S%z",
			"%Y-%m-%d %H:%M:%S%z",
			"%Y:%m:%d %H:%M:%S",
			"%Y-%m-%d %H:%M:%S",
		):
			try:
				parsed = datetime.strptime(candidate, fmt)
				if parsed.tzinfo is not None:
					return parsed.astimezone(timezone.utc).replace(tzinfo=None)
				return parsed
			except ValueError:
				continue

	cleaned = raw.split("+")[0].strip()
	if raw.count(":") > 2 and "-" in raw[10:]:
		cleaned = raw.rsplit("-", 1)[0].strip()
	for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
		try:
			return datetime.strptime(cleaned, fmt)
		except ValueError:
			continue
	return None


def _first_metadata_value(metadata: dict[str, object], field_names: tuple[str, ...]) -> object | None:
	lookup = {str(key).casefold(): value for key, value in metadata.items()}
	for field_name in field_names:
		value = lookup.get(field_name.casefold())
		if value not in (None, ""):
			return value
	return None


def _extract_video_dates(metadata: dict[str, object]) -> tuple[datetime | None, datetime | None]:
	primary_value = _first_metadata_value(metadata, VIDEO_PRIMARY_DATE_FIELDS)
	primary_date = _parse_datetime(str(primary_value)) if primary_value is not None else None

	secondary_date = None
	for field_name in VIDEO_SECONDARY_DATE_FIELDS:
		value = _first_metadata_value(metadata, (field_name,))
		candidate = _parse_datetime(str(value)) if value is not None else None
		if candidate is not None:
			secondary_date = candidate
			break

	if primary_date is not None:
		return primary_date, secondary_date
	return secondary_date, None


def _parse_float(value: object) -> float | None:
	"""Safely parse float values from EXIF fields."""
	if value is None:
		return None
	try:
		return float(value)
	except (TypeError, ValueError):
		return None


def _apply_gps_ref(value: float | None, ref: object, *, positive_refs: set[str], negative_refs: set[str]) -> float | None:
	"""Apply hemisphere reference tags to GPS values when present."""
	if value is None or ref is None:
		return value

	ref_text = str(ref).strip().upper()
	if ref_text in negative_refs:
		return -abs(value)
	if ref_text in positive_refs:
		return abs(value)
	return value


def _extract_single_metadata(metadata: dict[str, object], asset: Asset) -> ExtractedExifData | None:
	"""Build extracted EXIF structure from one ExifTool metadata dict."""
	asset_extension = (asset.extension or "").lower()
	exif_datetime_original = _parse_datetime(metadata.get("EXIF:DateTimeOriginal") if isinstance(metadata, dict) else None)  # type: ignore[arg-type]
	exif_create_date = _parse_datetime(metadata.get("EXIF:CreateDate") if isinstance(metadata, dict) else None)  # type: ignore[arg-type]
	gps_latitude = _parse_float(metadata.get("EXIF:GPSLatitude") if isinstance(metadata, dict) else None)  # type: ignore[arg-type]
	gps_longitude = _parse_float(metadata.get("EXIF:GPSLongitude") if isinstance(metadata, dict) else None)  # type: ignore[arg-type]
	gps_latitude = _apply_gps_ref(
		gps_latitude,
		metadata.get("EXIF:GPSLatitudeRef") if isinstance(metadata, dict) else None,
		positive_refs={"N"},
		negative_refs={"S"},
	)
	gps_longitude = _apply_gps_ref(
		gps_longitude,
		metadata.get("EXIF:GPSLongitudeRef") if isinstance(metadata, dict) else None,
		positive_refs={"E"},
		negative_refs={"W"},
	)
	camera_make = str(metadata.get("EXIF:Make")).strip() if metadata.get("EXIF:Make") else None
	camera_model = str(metadata.get("EXIF:Model")).strip() if metadata.get("EXIF:Model") else None
	lens_model = str(metadata.get("EXIF:LensModel")).strip() if metadata.get("EXIF:LensModel") else None
	software = str(metadata.get("EXIF:Software")).strip() if metadata.get("EXIF:Software") else None

	if asset_extension in VIDEO_EXTENSIONS:
		video_primary, video_secondary = _extract_video_dates(metadata)
		exif_datetime_original = video_primary or exif_datetime_original
		exif_create_date = video_secondary or exif_create_date
		camera_make = camera_make or (str(_first_metadata_value(metadata, ("QuickTime:Make",))).strip() if _first_metadata_value(metadata, ("QuickTime:Make",)) else None)
		camera_model = camera_model or (str(_first_metadata_value(metadata, ("QuickTime:Model",))).strip() if _first_metadata_value(metadata, ("QuickTime:Model",)) else None)
		lens_model = lens_model or (str(_first_metadata_value(metadata, ("QuickTime:LensModel",))).strip() if _first_metadata_value(metadata, ("QuickTime:LensModel",)) else None)
		software = software or (str(_first_metadata_value(metadata, ("QuickTime:Software",))).strip() if _first_metadata_value(metadata, ("QuickTime:Software",)) else None)

	if not any(
		[
			exif_datetime_original,
			exif_create_date,
			gps_latitude,
			gps_longitude,
			camera_make,
			camera_model,
			lens_model,
			software,
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
		software=software,
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
