"""Metadata normalization and heuristics service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.asset import Asset

SCANNER_BRANDS = (
    "epson",
    "canoscan",
    "hp",
    "scanjet",
    "plustek",
    "fujitsu",
    "brother",
)

SCANNING_SOFTWARE = (
    "photomyne",
    "photoscan",
    "google photoscan",
    "vuescan",
    "silverfast",
)

IPHONE_MARKERS = (
    "apple",
    "iphone",
)

DSLR_MARKERS = (
    "canon",
    "nikon",
    "sony",
    "fujifilm",
    "pentax",
    "olympus",
    "panasonic",
)


@dataclass(frozen=True)
class NormalizedMetadata:
    """Computed normalized metadata fields for one asset."""

    sha256: str
    captured_at: datetime
    is_scan: bool
    needs_date_estimation: bool
    source_type: str


@dataclass(frozen=True)
class FailedNormalization:
    """An asset that failed normalization with a reason."""

    sha256: str
    reason: str


@dataclass(frozen=True)
class MetadataNormalizationResult:
    """Structured normalization result for a batch."""

    updated_records: list[NormalizedMetadata]
    failed_records: list[FailedNormalization]


@dataclass(frozen=True)
class MetadataUpdateSummary:
    """Structured DB update result for normalization."""

    updated_records: list[str]
    failed_records: list[FailedNormalization]


def _contains_any(value: str | None, markers: tuple[str, ...]) -> bool:
    """Return True if any marker is present in a case-insensitive string."""
    normalized = (value or "").lower()
    return any(marker in normalized for marker in markers)


def _is_clearly_invalid_timestamp(value: datetime | None) -> bool:
    """Detect a clearly invalid scan-like placeholder timestamp."""
    if value is None:
        return False
    return value.year == 2000 and value.month == 1 and value.day == 1


def _choose_captured_at(asset: Asset) -> datetime:
    """Choose the best available timestamp using milestone fallback rules."""
    chosen = asset.exif_datetime_original or asset.exif_create_date or asset.modified_timestamp_utc
    if chosen.tzinfo is None:
        return chosen.replace(tzinfo=timezone.utc)
    return chosen


def _has_valid_exif_date(asset: Asset) -> bool:
    """Return True when EXIF date exists and is not clearly invalid."""
    for candidate in (asset.exif_datetime_original, asset.exif_create_date):
        if candidate is not None and not _is_clearly_invalid_timestamp(candidate):
            return True
    return False


def _classify_source_type(asset: Asset, is_scan: bool) -> str:
    """Classify asset source type using simple metadata heuristics."""
    if is_scan:
        return "scan"

    make_and_model = " ".join(filter(None, [asset.camera_make, asset.camera_model]))
    if _contains_any(make_and_model, IPHONE_MARKERS):
        return "iphone"
    if _contains_any(make_and_model, DSLR_MARKERS):
        return "dslr"
    return "unknown"


def normalize_asset_metadata(asset: Asset) -> NormalizedMetadata:
    """Normalize raw EXIF and file metadata into queryable fields."""
    make_and_model = " ".join(filter(None, [asset.camera_make, asset.camera_model]))
    captured_at = _choose_captured_at(asset)

    is_scan = (
        _contains_any(make_and_model, SCANNER_BRANDS)
        or _contains_any(asset.software, SCANNING_SOFTWARE)
        or _is_clearly_invalid_timestamp(asset.exif_datetime_original)
        or _is_clearly_invalid_timestamp(asset.exif_create_date)
    )

    needs_date_estimation = is_scan and not _has_valid_exif_date(asset)
    source_type = _classify_source_type(asset, is_scan)

    return NormalizedMetadata(
        sha256=asset.sha256,
        captured_at=captured_at,
        is_scan=is_scan,
        needs_date_estimation=needs_date_estimation,
        source_type=source_type,
    )


def normalize_assets(assets: list[Asset]) -> MetadataNormalizationResult:
    """Normalize metadata for a batch of assets."""
    updated_records: list[NormalizedMetadata] = []
    failed_records: list[FailedNormalization] = []

    for asset in assets:
        try:
            updated_records.append(normalize_asset_metadata(asset))
        except Exception as error:  # noqa: BLE001
            failed_records.append(FailedNormalization(sha256=asset.sha256, reason=str(error)))

    return MetadataNormalizationResult(
        updated_records=updated_records,
        failed_records=failed_records,
    )


def persist_normalized_metadata(
    db_session: Session,
    normalized_items: list[NormalizedMetadata],
) -> MetadataUpdateSummary:
    """Persist normalized metadata fields back into existing Asset rows."""
    updated_records: list[str] = []
    failed_records: list[FailedNormalization] = []

    for item in normalized_items:
        asset = db_session.get(Asset, item.sha256)
        if asset is None:
            failed_records.append(FailedNormalization(sha256=item.sha256, reason="Asset not found in database."))
            continue

        try:
            asset.captured_at = item.captured_at
            asset.is_scan = item.is_scan
            asset.needs_date_estimation = item.needs_date_estimation
            asset.source_type = item.source_type
            db_session.commit()
            updated_records.append(item.sha256)
        except SQLAlchemyError as error:
            db_session.rollback()
            failed_records.append(FailedNormalization(sha256=item.sha256, reason=str(error)))

    return MetadataUpdateSummary(updated_records=updated_records, failed_records=failed_records)
