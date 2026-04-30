"""Metadata observation persistence and deterministic canonicalization logic."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from datetime import datetime, timezone
from pathlib import Path

import exiftool  # type: ignore[import-not-found]
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.asset_metadata_observation import AssetMetadataObservation
from app.models.provenance import Provenance
from app.services.duplicates.lineage import ProvenanceContext
from app.services.ingestion.deduplicator import DuplicateFile
from app.services.persistence.asset_repository import InsertedAsset

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".heic", ".webp"}
PREFERRED_EXTENSIONS = {".heic", ".heif", ".dng", ".arw", ".cr2", ".cr3", ".nef", ".orf", ".rw2", ".raf"}
GENERIC_CAMERA_VALUES = {"unknown", "none", "null", "camera", "digital camera", "-", "n/a"}
GPS_DECIMAL_PLACES = 6


@dataclass(frozen=True)
class ExtractedMetadataObservation:
    exif_datetime_original: datetime | None
    exif_create_date: datetime | None
    captured_at_observed: datetime | None
    gps_latitude: float | None
    gps_longitude: float | None
    camera_make: str | None
    camera_model: str | None
    width: int | None
    height: int | None
    observed_extension: str | None


@dataclass(frozen=True)
class IngestObservationSummary:
    inserted: int
    skipped: int
    failed: int
    affected_asset_sha256: list[str]


@dataclass(frozen=True)
class CanonicalizationSummary:
    processed: int
    updated: int
    skipped: int
    failed: int


@dataclass(frozen=True)
class BackfillCanonicalizationSummary:
    assets_considered: int
    observations_inserted: int
    observations_skipped: int
    observations_failed: int
    legacy_seeded: int
    limited_coverage_assets: int
    canonical_updated: int


def _is_image_asset(asset: Asset) -> bool:
    return (asset.extension or "").lower() in IMAGE_EXTENSIONS


def _normalize_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    return normalized or None


def _parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    raw = str(value)
    cleaned = raw.split("+")[0].strip()
    cleaned = cleaned.split("-")[0].strip() if "+" not in raw and raw.count(":") > 2 else cleaned
    try:
        return datetime.strptime(cleaned, "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None


def _parse_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(float(str(value)))
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _parse_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _apply_gps_ref(value: float | None, ref: object, *, positive_refs: set[str], negative_refs: set[str]) -> float | None:
    if value is None or ref is None:
        return value

    ref_text = str(ref).strip().upper()
    if ref_text in negative_refs:
        return -abs(value)
    if ref_text in positive_refs:
        return abs(value)
    return value


def _normalize_datetime_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _is_invalid_captured_at(value: datetime | None) -> bool:
    if value is None:
        return True
    if value.year < 1971:
        return True
    if value.year == 2000 and value.month == 1 and value.day == 1:
        return True
    return False


def _normalize_coordinate(value: float | None) -> float | None:
    if value is None:
        return None
    quantizer = Decimal("1").scaleb(-GPS_DECIMAL_PLACES)
    normalized = Decimal(str(value)).quantize(quantizer, rounding=ROUND_HALF_UP)
    return float(normalized)


def _normalized_gps_pair(latitude: float | None, longitude: float | None) -> tuple[float, float] | None:
    if latitude is None or longitude is None:
        return None
    normalized_latitude = _normalize_coordinate(latitude)
    normalized_longitude = _normalize_coordinate(longitude)
    if normalized_latitude is None or normalized_longitude is None:
        return None
    if not (-90.0 <= normalized_latitude <= 90.0):
        return None
    if not (-180.0 <= normalized_longitude <= 180.0):
        return None
    if normalized_latitude == 0.0 and normalized_longitude == 0.0:
        return None
    return normalized_latitude, normalized_longitude


def _extract_dimensions(path: Path, metadata: dict[str, object]) -> tuple[int | None, int | None]:
    width = None
    height = None
    for width_key, height_key in (
        ("EXIF:ExifImageWidth", "EXIF:ExifImageHeight"),
        ("EXIF:ImageWidth", "EXIF:ImageHeight"),
        ("File:ImageWidth", "File:ImageHeight"),
    ):
        width = _parse_int(metadata.get(width_key))
        height = _parse_int(metadata.get(height_key))
        if width and height:
            return width, height

    try:
        with Image.open(path) as image:
            width, height = image.size
            return (width if width > 0 else None, height if height > 0 else None)
    except Exception:  # noqa: BLE001
        return None, None


def _extract_observation_from_metadata(
    file_path: Path, metadata: dict[str, object]
) -> ExtractedMetadataObservation | None:
    """Build an ExtractedMetadataObservation from a pre-fetched raw metadata dict."""
    extension = file_path.suffix.lower()
    exif_datetime_original = _parse_datetime(metadata.get("EXIF:DateTimeOriginal"))
    exif_create_date = _parse_datetime(metadata.get("EXIF:CreateDate"))
    gps_latitude = _parse_float(metadata.get("EXIF:GPSLatitude"))
    gps_longitude = _parse_float(metadata.get("EXIF:GPSLongitude"))
    gps_latitude = _apply_gps_ref(
        gps_latitude,
        metadata.get("EXIF:GPSLatitudeRef"),
        positive_refs={"N"},
        negative_refs={"S"},
    )
    gps_longitude = _apply_gps_ref(
        gps_longitude,
        metadata.get("EXIF:GPSLongitudeRef"),
        positive_refs={"E"},
        negative_refs={"W"},
    )
    camera_make = _normalize_string(str(metadata.get("EXIF:Make"))) if metadata.get("EXIF:Make") else None
    camera_model = _normalize_string(str(metadata.get("EXIF:Model"))) if metadata.get("EXIF:Model") else None
    width, height = _extract_dimensions(file_path, metadata)

    captured_at_observed = _normalize_datetime_utc(exif_datetime_original or exif_create_date)

    if not any([
        captured_at_observed,
        gps_latitude,
        gps_longitude,
        camera_make,
        camera_model,
        width,
        height,
        exif_datetime_original,
        exif_create_date,
    ]):
        return None

    return ExtractedMetadataObservation(
        exif_datetime_original=exif_datetime_original,
        exif_create_date=exif_create_date,
        captured_at_observed=captured_at_observed,
        gps_latitude=gps_latitude,
        gps_longitude=gps_longitude,
        camera_make=camera_make,
        camera_model=camera_model,
        width=width,
        height=height,
        observed_extension=extension,
    )


def _batch_extract_metadata(paths: list[str]) -> dict[str, dict[str, object]]:
    """Open ExifTool once and extract raw metadata for all valid image paths.

    Returns a mapping of source_path -> raw metadata dict.
    Paths that are missing, non-image, or fail extraction are excluded.
    """
    valid = [
        p for p in paths
        if Path(p).exists() and Path(p).is_file() and Path(p).suffix.lower() in IMAGE_EXTENSIONS
    ]
    if not valid:
        return {}
    try:
        with exiftool.ExifToolHelper() as helper:
            results = helper.get_metadata(valid)  # pass as list, not *args
        return {path: (result or {}) for path, result in zip(valid, results)}
    except Exception:  # noqa: BLE001
        return {}


def extract_metadata_observation_from_path(path: str) -> ExtractedMetadataObservation | None:
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        return None

    extension = file_path.suffix.lower()
    if extension not in IMAGE_EXTENSIONS:
        return None

    try:
        with exiftool.ExifToolHelper() as helper:
            metadata_list = helper.get_metadata(str(file_path))
    except Exception:  # noqa: BLE001
        return None

    metadata = metadata_list[0] if metadata_list else {}
    return _extract_observation_from_metadata(file_path, metadata)


def build_legacy_observation_from_asset(asset: Asset) -> ExtractedMetadataObservation | None:
    if not _is_image_asset(asset):
        return None

    payload = ExtractedMetadataObservation(
        exif_datetime_original=asset.exif_datetime_original,
        exif_create_date=asset.exif_create_date,
        captured_at_observed=_normalize_datetime_utc(asset.captured_at),
        gps_latitude=asset.gps_latitude,
        gps_longitude=asset.gps_longitude,
        camera_make=_normalize_string(asset.camera_make),
        camera_model=_normalize_string(asset.camera_model),
        width=asset.width,
        height=asset.height,
        observed_extension=(asset.extension or "").lower() if asset.extension else None,
    )

    if not any([
        payload.captured_at_observed,
        payload.gps_latitude,
        payload.gps_longitude,
        payload.camera_make,
        payload.camera_model,
        payload.width,
        payload.height,
        payload.exif_datetime_original,
        payload.exif_create_date,
    ]):
        return None
    return payload


def _observation_signature(extracted: ExtractedMetadataObservation) -> tuple:
    return (
        extracted.exif_datetime_original,
        extracted.exif_create_date,
        extracted.captured_at_observed,
        _normalized_gps_pair(extracted.gps_latitude, extracted.gps_longitude),
        (extracted.camera_make or "").lower(),
        (extracted.camera_model or "").lower(),
        extracted.width,
        extracted.height,
    )


def persist_metadata_observation(
    db_session: Session,
    *,
    asset_sha256: str,
    provenance_id: int | None,
    observation_origin: str,
    observed_source_path: str | None,
    observed_source_type: str | None,
    extracted: ExtractedMetadataObservation,
    is_legacy_seeded: bool,
    _preloaded_observations: list[AssetMetadataObservation] | None = None,
) -> bool:
    existing_observations = (
        _preloaded_observations
        if _preloaded_observations is not None
        else list(
            db_session.scalars(
                select(AssetMetadataObservation).where(AssetMetadataObservation.asset_sha256 == asset_sha256)
            ).all()
        )
    )
    incoming_signature = _observation_signature(extracted)
    incoming_scope = (provenance_id, observation_origin, observed_source_path)
    for observation in existing_observations:
        current_signature = (
            observation.exif_datetime_original,
            observation.exif_create_date,
            observation.captured_at_observed,
            _normalized_gps_pair(observation.gps_latitude, observation.gps_longitude),
            (observation.camera_make or "").lower(),
            (observation.camera_model or "").lower(),
            observation.width,
            observation.height,
        )
        current_scope = (observation.provenance_id, observation.observation_origin, observation.observed_source_path)
        if current_scope != incoming_scope:
            continue

        if current_signature == incoming_signature:
            return False

        # Keep one observation row per source scope and update it when extraction changes.
        observation.observed_source_type = observed_source_type
        observation.observed_extension = extracted.observed_extension
        observation.exif_datetime_original = extracted.exif_datetime_original
        observation.exif_create_date = extracted.exif_create_date
        observation.captured_at_observed = extracted.captured_at_observed
        observation.gps_latitude = extracted.gps_latitude
        observation.gps_longitude = extracted.gps_longitude
        observation.camera_make = extracted.camera_make
        observation.camera_model = extracted.camera_model
        observation.width = extracted.width
        observation.height = extracted.height
        observation.is_legacy_seeded = is_legacy_seeded
        return True

    db_session.add(
        AssetMetadataObservation(
            asset_sha256=asset_sha256,
            provenance_id=provenance_id,
            observation_origin=observation_origin,
            observed_source_path=observed_source_path,
            observed_source_type=observed_source_type,
            observed_extension=extracted.observed_extension,
            exif_datetime_original=extracted.exif_datetime_original,
            exif_create_date=extracted.exif_create_date,
            captured_at_observed=extracted.captured_at_observed,
            gps_latitude=extracted.gps_latitude,
            gps_longitude=extracted.gps_longitude,
            camera_make=extracted.camera_make,
            camera_model=extracted.camera_model,
            width=extracted.width,
            height=extracted.height,
            is_legacy_seeded=is_legacy_seeded,
        )
    )
    return True


def _source_extension_bonus(observation: AssetMetadataObservation) -> int:
    extension = (observation.observed_extension or "").lower()
    if extension in PREFERRED_EXTENSIONS:
        return 8
    if extension in {".jpg", ".jpeg"}:
        return -2
    return 0


def _source_type_bonus(observation: AssetMetadataObservation) -> int:
    source_type = (observation.observed_source_type or "").lower()
    if source_type == "cloud_export":
        return -6
    if source_type == "external_drive":
        return 2
    if source_type == "scan_batch":
        return -3
    return 0


def _origin_base_score(observation: AssetMetadataObservation) -> int:
    if observation.observation_origin == "provenance":
        return 40
    if observation.observation_origin == "vault":
        return 24
    if observation.observation_origin == "legacy":
        return 8
    return 12


def _completeness_score(observation: AssetMetadataObservation) -> int:
    populated = 0
    populated += 1 if observation.captured_at_observed is not None else 0
    populated += 1 if observation.camera_make else 0
    populated += 1 if observation.camera_model else 0
    populated += 1 if (observation.width and observation.height) else 0
    return populated * 3


def _tiebreak_key(observation: AssetMetadataObservation) -> tuple[int, int]:
    provenance_key = observation.provenance_id if observation.provenance_id is not None else 2_000_000_000
    return provenance_key, observation.id


def _origin_trust_rank(observation: AssetMetadataObservation) -> int:
    if observation.observation_origin == "provenance":
        return 3
    if observation.observation_origin == "vault":
        return 2
    if observation.observation_origin == "legacy":
        return 1
    return 0


def _choose_best_captured_at(observations: list[AssetMetadataObservation]) -> datetime | None:
    valid = [item for item in observations if not _is_invalid_captured_at(item.captured_at_observed)]
    if not valid:
        return None

    consistency_counts: dict[datetime, int] = {}
    for item in valid:
        assert item.captured_at_observed is not None
        consistency_counts[item.captured_at_observed] = consistency_counts.get(item.captured_at_observed, 0) + 1

    best_observation = None
    best_rank: tuple[int, int, int, int] | None = None
    for item in valid:
        assert item.captured_at_observed is not None
        score = _origin_base_score(item)
        score += _completeness_score(item)
        score += _source_extension_bonus(item)
        score += _source_type_bonus(item)
        score += consistency_counts[item.captured_at_observed] * 5
        score += 12 if item.exif_datetime_original else 0
        score += 6 if (item.exif_create_date and not item.exif_datetime_original) else 0
        if item.is_legacy_seeded:
            score -= 12

        provenance_key, observation_key = _tiebreak_key(item)
        rank = (score, -consistency_counts[item.captured_at_observed], -provenance_key, -observation_key)
        if best_rank is None or rank > best_rank:
            best_rank = rank
            best_observation = item

    return best_observation.captured_at_observed if best_observation else None


def _choose_best_camera_value(
    observations: list[AssetMetadataObservation],
    field_name: str,
) -> str | None:
    values: list[tuple[AssetMetadataObservation, str]] = []
    for item in observations:
        value = _normalize_string(getattr(item, field_name))
        if value is None:
            continue
        if value.lower() in GENERIC_CAMERA_VALUES:
            continue
        values.append((item, value))

    if not values:
        return None

    consistency_counts: dict[str, int] = {}
    for _, value in values:
        key = value.lower()
        consistency_counts[key] = consistency_counts.get(key, 0) + 1

    best_value = None
    best_rank: tuple[int, int, int, int] | None = None
    for item, value in values:
        key = value.lower()
        score = _origin_base_score(item)
        score += _completeness_score(item)
        score += _source_extension_bonus(item)
        score += _source_type_bonus(item)
        score += consistency_counts[key] * 4
        if item.is_legacy_seeded:
            score -= 8

        provenance_key, observation_key = _tiebreak_key(item)
        rank = (score, -consistency_counts[key], -provenance_key, -observation_key)
        if best_rank is None or rank > best_rank:
            best_rank = rank
            best_value = value

    return best_value


def _choose_best_dimensions(observations: list[AssetMetadataObservation]) -> tuple[int | None, int | None]:
    candidates = [
        item for item in observations if item.width is not None and item.height is not None and item.width > 0 and item.height > 0
    ]
    if not candidates:
        return None, None

    consistency_counts: dict[tuple[int, int], int] = {}
    for item in candidates:
        key = (item.width or 0, item.height or 0)
        consistency_counts[key] = consistency_counts.get(key, 0) + 1

    best_observation = None
    best_rank: tuple[int, int, int, int, int] | None = None
    for item in candidates:
        assert item.width is not None and item.height is not None
        pixels = item.width * item.height
        key = (item.width, item.height)
        score = _origin_base_score(item)
        score += _completeness_score(item)
        score += _source_extension_bonus(item)
        score += _source_type_bonus(item)
        score += consistency_counts[key] * 2
        if item.is_legacy_seeded:
            score -= 6

        provenance_key, observation_key = _tiebreak_key(item)
        rank = (pixels, score, consistency_counts[key], -provenance_key, -observation_key)
        if best_rank is None or rank > best_rank:
            best_rank = rank
            best_observation = item

    if best_observation is None:
        return None, None
    return best_observation.width, best_observation.height


def _choose_best_location(observations: list[AssetMetadataObservation]) -> tuple[float | None, float | None]:
    grouped_candidates: dict[tuple[float, float], list[AssetMetadataObservation]] = {}
    for item in observations:
        pair = _normalized_gps_pair(item.gps_latitude, item.gps_longitude)
        if pair is None:
            continue
        grouped_candidates.setdefault(pair, []).append(item)

    if not grouped_candidates:
        return None, None

    best_pair: tuple[float, float] | None = None
    best_rank: tuple[int, int, int, int] | None = None
    for pair, items in grouped_candidates.items():
        winning_observation = min(
            items,
            key=lambda item: (
                item.provenance_id if item.provenance_id is not None else 2_000_000_000,
                item.id,
            ),
        )
        rank = (
            len(items),
            _origin_trust_rank(max(items, key=_origin_trust_rank)),
            -(winning_observation.provenance_id if winning_observation.provenance_id is not None else 2_000_000_000),
            -winning_observation.id,
        )
        if best_rank is None or rank > best_rank:
            best_rank = rank
            best_pair = pair

    if best_pair is None:
        return None, None
    return best_pair


def recompute_canonical_metadata_for_assets(db_session: Session, asset_sha256_list: list[str]) -> CanonicalizationSummary:
    processed = 0
    updated = 0
    skipped = 0
    failed = 0

    unique_sha256s = list(dict.fromkeys(asset_sha256_list))
    if not unique_sha256s:
        return CanonicalizationSummary(processed=0, updated=0, skipped=0, failed=0)

    # Batch-fetch all assets
    assets_map: dict[str, Asset] = {
        a.sha256: a
        for a in db_session.scalars(select(Asset).where(Asset.sha256.in_(unique_sha256s))).all()
    }

    # Batch-fetch all observations for all assets in one query
    observations_by_sha256: dict[str, list[AssetMetadataObservation]] = {}
    for obs in db_session.scalars(
        select(AssetMetadataObservation)
        .where(AssetMetadataObservation.asset_sha256.in_(unique_sha256s))
        .order_by(AssetMetadataObservation.id.asc())
    ).all():
        observations_by_sha256.setdefault(obs.asset_sha256, []).append(obs)

    for sha256 in unique_sha256s:
        asset = assets_map.get(sha256)
        if asset is None:
            skipped += 1
            continue
        if not _is_image_asset(asset):
            skipped += 1
            continue

        processed += 1
        try:
            observations = observations_by_sha256.get(sha256, [])
            if not observations:
                skipped += 1
                continue

            next_captured_at = _choose_best_captured_at(observations)
            next_gps_latitude, next_gps_longitude = _choose_best_location(observations)
            next_camera_make = _choose_best_camera_value(observations, "camera_make")
            next_camera_model = _choose_best_camera_value(observations, "camera_model")
            next_width, next_height = _choose_best_dimensions(observations)

            did_change = False
            if next_captured_at != asset.captured_at:
                asset.captured_at = next_captured_at
                did_change = True
            if next_gps_latitude != asset.gps_latitude:
                asset.gps_latitude = next_gps_latitude
                did_change = True
            if next_gps_longitude != asset.gps_longitude:
                asset.gps_longitude = next_gps_longitude
                did_change = True
            if next_camera_make != asset.camera_make:
                asset.camera_make = next_camera_make
                did_change = True
            if next_camera_model != asset.camera_model:
                asset.camera_model = next_camera_model
                did_change = True
            if next_width != asset.width:
                asset.width = next_width
                did_change = True
            if next_height != asset.height:
                asset.height = next_height
                did_change = True

            if did_change:
                updated += 1
        except Exception:  # noqa: BLE001
            failed += 1

    db_session.commit()
    return CanonicalizationSummary(processed=processed, updated=updated, skipped=skipped, failed=failed)


def _resolve_provenance_from_batch(
    provenance_rows_by_sha256: dict[str, list[Provenance]],
    asset_sha256: str,
    source_path: str,
    run_id: int | None,
) -> Provenance | None:
    """In-memory equivalent of _find_matching_provenance using pre-fetched rows."""
    rows = provenance_rows_by_sha256.get(asset_sha256, [])
    sorted_rows = sorted(rows, key=lambda r: r.id, reverse=True)
    # Primary match: sha256 + source_path [+ run_id if available]
    for row in sorted_rows:
        if row.source_path == source_path:
            if run_id is None or row.ingestion_run_id == run_id:
                return row
    # Fallback: any provenance row for this asset (mirrors DB fallback query)
    return sorted_rows[0] if sorted_rows else None


def _find_matching_provenance(
    db_session: Session,
    *,
    asset_sha256: str,
    source_path: str,
    provenance_context: ProvenanceContext | None,
) -> Provenance | None:
    query = select(Provenance).where(
        Provenance.asset_sha256 == asset_sha256,
        Provenance.source_path == source_path,
    )
    if provenance_context is not None and provenance_context.ingestion_run_id is not None:
        query = query.where(Provenance.ingestion_run_id == provenance_context.ingestion_run_id)

    rows = list(db_session.scalars(query.order_by(Provenance.id.desc())).all())
    if rows:
        return rows[0]

    fallback = list(
        db_session.scalars(
            select(Provenance)
            .where(Provenance.asset_sha256 == asset_sha256)
            .order_by(Provenance.id.desc())
            .limit(1)
        ).all()
    )
    return fallback[0] if fallback else None


def create_ingest_observations_for_batch(
    db_session: Session,
    *,
    inserted_records: list[InsertedAsset],
    duplicate_files: list[DuplicateFile],
    provenance_context: ProvenanceContext | None,
) -> IngestObservationSummary:
    inserted = 0
    skipped = 0
    failed = 0
    affected_asset_sha256: set[str] = set()

    workload: list[tuple[str, str]] = []
    for item in inserted_records:
        workload.append((item.copied_file.hashed_file.sha256, item.copied_file.hashed_file.record.original_source_path))
    for item in duplicate_files:
        workload.append((item.duplicate.sha256, item.duplicate.record.original_source_path))

    if not workload:
        return IngestObservationSummary(inserted=0, skipped=0, failed=0, affected_asset_sha256=[])

    all_sha256s = list(dict.fromkeys(sha256 for sha256, _ in workload))
    run_id = provenance_context.ingestion_run_id if provenance_context is not None else None

    # Batch-fetch assets
    assets_map: dict[str, Asset] = {
        a.sha256: a
        for a in db_session.scalars(select(Asset).where(Asset.sha256.in_(all_sha256s))).all()
    }

    # Batch-fetch provenance rows (used by _resolve_provenance_from_batch)
    provenance_rows_by_sha256: dict[str, list[Provenance]] = {}
    for row in db_session.scalars(select(Provenance).where(Provenance.asset_sha256.in_(all_sha256s))).all():
        provenance_rows_by_sha256.setdefault(row.asset_sha256, []).append(row)

    # Batch-fetch existing observations (avoids per-item SELECT in persist_metadata_observation)
    observations_by_sha256: dict[str, list[AssetMetadataObservation]] = {}
    for obs in db_session.scalars(
        select(AssetMetadataObservation).where(AssetMetadataObservation.asset_sha256.in_(all_sha256s))
    ).all():
        observations_by_sha256.setdefault(obs.asset_sha256, []).append(obs)

    # Collect image source paths for batch ExifTool extraction
    source_paths_for_extraction: list[str] = [
        source_path
        for asset_sha256, source_path in workload
        if asset_sha256 in assets_map and _is_image_asset(assets_map[asset_sha256])
    ]
    batch_metadata = _batch_extract_metadata(source_paths_for_extraction)

    for asset_sha256, source_path in workload:
        try:
            asset = assets_map.get(asset_sha256)
            if asset is None or not _is_image_asset(asset):
                skipped += 1
                continue

            provenance_row = _resolve_provenance_from_batch(
                provenance_rows_by_sha256, asset_sha256, source_path, run_id
            )

            # Use batch-extracted metadata; fall back to single ExifTool call for vault path
            raw_metadata = batch_metadata.get(source_path)
            extracted: ExtractedMetadataObservation | None
            if raw_metadata is not None:
                extracted = _extract_observation_from_metadata(Path(source_path), raw_metadata)
            else:
                extracted = None

            observation_origin = "provenance"
            observed_source_path = source_path
            observed_source_type = provenance_row.source_type if provenance_row is not None else None

            if extracted is None:
                extracted = extract_metadata_observation_from_path(asset.vault_path)
                observation_origin = "vault"
                observed_source_path = asset.vault_path
                observed_source_type = "vault"

            if extracted is None:
                skipped += 1
                continue

            was_added = persist_metadata_observation(
                db_session,
                asset_sha256=asset_sha256,
                provenance_id=provenance_row.id if provenance_row is not None else None,
                observation_origin=observation_origin,
                observed_source_path=observed_source_path,
                observed_source_type=observed_source_type,
                extracted=extracted,
                is_legacy_seeded=False,
                _preloaded_observations=observations_by_sha256.get(asset_sha256),
            )
            if was_added:
                inserted += 1
                affected_asset_sha256.add(asset_sha256)
            else:
                skipped += 1
        except Exception:  # noqa: BLE001
            failed += 1

    db_session.commit()
    return IngestObservationSummary(
        inserted=inserted,
        skipped=skipped,
        failed=failed,
        affected_asset_sha256=sorted(affected_asset_sha256),
    )


def backfill_observations_and_canonicalize(db_session: Session) -> BackfillCanonicalizationSummary:
    assets = list(db_session.scalars(select(Asset).order_by(Asset.sha256.asc())).all())

    observations_inserted = 0
    observations_skipped = 0
    observations_failed = 0
    legacy_seeded = 0
    limited_coverage_assets = 0
    assets_considered = 0
    affected_asset_sha256: list[str] = []

    for asset in assets:
        if not _is_image_asset(asset):
            continue

        assets_considered += 1
        inserted_for_asset = 0

        provenance_rows = list(
            db_session.scalars(
                select(Provenance)
                .where(Provenance.asset_sha256 == asset.sha256)
                .order_by(Provenance.id.asc())
            ).all()
        )

        for provenance_row in provenance_rows:
            try:
                extracted = extract_metadata_observation_from_path(provenance_row.source_path)
                if extracted is None:
                    observations_skipped += 1
                    continue
                if persist_metadata_observation(
                    db_session,
                    asset_sha256=asset.sha256,
                    provenance_id=provenance_row.id,
                    observation_origin="provenance",
                    observed_source_path=provenance_row.source_path,
                    observed_source_type=provenance_row.source_type,
                    extracted=extracted,
                    is_legacy_seeded=False,
                ):
                    observations_inserted += 1
                    inserted_for_asset += 1
                else:
                    observations_skipped += 1
            except Exception:  # noqa: BLE001
                observations_failed += 1

        if inserted_for_asset == 0:
            try:
                extracted_vault = extract_metadata_observation_from_path(asset.vault_path)
                if extracted_vault is not None and persist_metadata_observation(
                    db_session,
                    asset_sha256=asset.sha256,
                    provenance_id=None,
                    observation_origin="vault",
                    observed_source_path=asset.vault_path,
                    observed_source_type="vault",
                    extracted=extracted_vault,
                    is_legacy_seeded=False,
                ):
                    observations_inserted += 1
                    inserted_for_asset += 1
                else:
                    observations_skipped += 1
            except Exception:  # noqa: BLE001
                observations_failed += 1

        if inserted_for_asset == 0:
            legacy_payload = build_legacy_observation_from_asset(asset)
            if legacy_payload is not None:
                try:
                    if persist_metadata_observation(
                        db_session,
                        asset_sha256=asset.sha256,
                        provenance_id=None,
                        observation_origin="legacy",
                        observed_source_path=None,
                        observed_source_type="legacy_seed",
                        extracted=legacy_payload,
                        is_legacy_seeded=True,
                    ):
                        observations_inserted += 1
                        inserted_for_asset += 1
                        legacy_seeded += 1
                    else:
                        observations_skipped += 1
                except Exception:  # noqa: BLE001
                    observations_failed += 1

        if inserted_for_asset <= 1:
            limited_coverage_assets += 1

        if inserted_for_asset > 0:
            affected_asset_sha256.append(asset.sha256)

    canonical_summary = recompute_canonical_metadata_for_assets(db_session, affected_asset_sha256)

    return BackfillCanonicalizationSummary(
        assets_considered=assets_considered,
        observations_inserted=observations_inserted,
        observations_skipped=observations_skipped,
        observations_failed=observations_failed,
        legacy_seeded=legacy_seeded,
        limited_coverage_assets=limited_coverage_assets,
        canonical_updated=canonical_summary.updated,
    )
