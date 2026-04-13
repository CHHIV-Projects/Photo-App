"""Duplicate lineage service: provenance, pHash, near-duplicate groups, canonical ranking."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import imagehash
from PIL import Image
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.asset import Asset
from app.models.duplicate_group import DuplicateGroup
from app.models.provenance import Provenance

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".heic", ".webp"}


@dataclass(frozen=True)
class AssetLineageUpdate:
    """Lineage update status for one asset."""

    sha256: str
    action: str


@dataclass(frozen=True)
class DuplicateLineageSummary:
    """Batch summary for lineage backfill/update."""

    processed: int
    updated: int
    skipped: int
    failed: int


@dataclass(frozen=True)
class _FeatureRow:
    """Cached feature row used for fast near-duplicate grouping."""

    sha256: str
    phash_hex: str
    phash_int: int
    orientation: str | None
    total_pixels: int
    captured_at: object


def _is_image_asset(asset: Asset) -> bool:
    return (asset.extension or "").lower() in IMAGE_EXTENSIONS


def _safe_open_image(path: str) -> Image.Image | None:
    try:
        image = Image.open(Path(path))
        image.load()
        return image
    except Exception:  # noqa: BLE001
        return None


def _image_dimensions(asset: Asset, dimensions_cache: dict[str, tuple[int, int] | None]) -> tuple[int, int] | None:
    if asset.sha256 in dimensions_cache:
        return dimensions_cache[asset.sha256]

    if not _is_image_asset(asset):
        dimensions_cache[asset.sha256] = None
        return None

    image = _safe_open_image(asset.vault_path)
    if image is None:
        dimensions_cache[asset.sha256] = None
        return None

    dims = image.size
    dimensions_cache[asset.sha256] = dims
    return dims


def _image_orientation(asset: Asset, dimensions_cache: dict[str, tuple[int, int] | None]) -> str | None:
    dims = _image_dimensions(asset, dimensions_cache)
    if dims is None:
        return None
    width, height = dims
    if width == height:
        return "square"
    if width > height:
        return "landscape"
    return "portrait"


def _compute_phash(asset: Asset) -> str | None:
    if not _is_image_asset(asset):
        return None

    image = _safe_open_image(asset.vault_path)
    if image is None:
        return None

    try:
        return str(imagehash.phash(image))
    except Exception:  # noqa: BLE001
        return None


def _metadata_completeness_fraction(asset: Asset) -> float:
    points = 0
    points += 1 if (asset.exif_datetime_original or asset.exif_create_date) else 0
    points += 1 if asset.camera_make else 0
    points += 1 if asset.camera_model else 0
    points += 1 if (asset.gps_latitude is not None and asset.gps_longitude is not None) else 0
    return points / 4.0


def compute_quality_score(asset: Asset, dimensions_cache: dict[str, tuple[int, int] | None] | None = None) -> float:
    """Deterministic 0-100 quality score with configured milestone weights."""
    cache = dimensions_cache if dimensions_cache is not None else {}

    resolution_norm = 0.0
    dims = _image_dimensions(asset, cache)
    if dims is not None:
        width, height = dims
        total_pixels = max(1, width * height)
        resolution_norm = min(1.0, total_pixels / 12_000_000.0)

    size_norm = min(1.0, max(0, asset.size_bytes) / 8_000_000.0)
    metadata_norm = _metadata_completeness_fraction(asset)

    score = (60.0 * resolution_norm) + (25.0 * size_norm) + (15.0 * metadata_norm)
    return round(max(0.0, min(100.0, score)), 4)


def _asset_sort_key(asset: Asset, dimensions_cache: dict[str, tuple[int, int] | None]) -> tuple[float, int, int, float, str]:
    dims = _image_dimensions(asset, dimensions_cache)
    pixels = (dims[0] * dims[1]) if dims is not None else 0
    score = float(asset.quality_score or 0.0)
    created_ts = asset.created_at_utc.timestamp() if asset.created_at_utc else float("inf")
    return (score, pixels, int(asset.size_bytes or 0), -created_ts, asset.sha256)


def _hamming_distance(hex_a: str, hex_b: str) -> int:
    return int(imagehash.hex_to_hash(hex_a) - imagehash.hex_to_hash(hex_b))


def _hamming_distance_int(hash_a: int, hash_b: int) -> int:
    return (hash_a ^ hash_b).bit_count()


def _is_candidate_match(
    current: Asset,
    candidate: Asset,
    dimensions_cache: dict[str, tuple[int, int] | None],
) -> bool:
    current_dims = _image_dimensions(current, dimensions_cache)
    candidate_dims = _image_dimensions(candidate, dimensions_cache)
    if current_dims is None or candidate_dims is None:
        return False

    current_orientation = _image_orientation(current, dimensions_cache)
    candidate_orientation = _image_orientation(candidate, dimensions_cache)
    if current_orientation != candidate_orientation:
        return False

    current_pixels = max(1, current_dims[0] * current_dims[1])
    candidate_pixels = max(1, candidate_dims[0] * candidate_dims[1])
    band = max(0.0, settings.duplicate_resolution_band_ratio)
    low = current_pixels * (1.0 - band)
    high = current_pixels * (1.0 + band)
    if not (low <= candidate_pixels <= high):
        return False

    if settings.duplicate_capture_window_enabled and current.captured_at and candidate.captured_at:
        hours = max(1, settings.duplicate_capture_window_hours)
        window = timedelta(hours=hours)
        if abs(current.captured_at - candidate.captured_at) > window:
            return False

    return True


def _ensure_group_for_candidate(db_session: Session, candidate: Asset) -> int:
    if candidate.duplicate_group_id is not None:
        return candidate.duplicate_group_id

    group = DuplicateGroup(group_type="near")
    db_session.add(group)
    db_session.flush()
    candidate.duplicate_group_id = group.id
    return group.id


def recompute_group_canonical(db_session: Session, group_id: int) -> str | None:
    assets = list(db_session.scalars(select(Asset).where(Asset.duplicate_group_id == group_id)).all())
    if not assets:
        return None

    dimensions_cache: dict[str, tuple[int, int] | None] = {}
    winner = max(assets, key=lambda item: _asset_sort_key(item, dimensions_cache))
    for asset in assets:
        asset.is_canonical = asset.sha256 == winner.sha256
    db_session.flush()
    return winner.sha256


def upsert_provenance(db_session: Session, asset_sha256: str, source_path: str) -> bool:
    source_path = (source_path or "").strip()
    if not source_path:
        return False

    existing = db_session.scalar(
        select(Provenance).where(
            and_(
                Provenance.asset_sha256 == asset_sha256,
                Provenance.source_path == source_path,
            )
        )
    )
    if existing is not None:
        return False

    db_session.add(Provenance(asset_sha256=asset_sha256, source_path=source_path))
    db_session.flush()
    return True


def update_asset_lineage(db_session: Session, asset: Asset) -> AssetLineageUpdate:
    """Compute lineage fields for one asset and update canonical assignment as needed."""
    if asset.phash is None:
        asset.phash = _compute_phash(asset)
    if asset.quality_score is None:
        asset.quality_score = compute_quality_score(asset)

    # Non-image assets and assets without pHash stay outside duplicate groups.
    if not asset.phash:
        asset.duplicate_group_id = None
        asset.is_canonical = True
        db_session.flush()
        return AssetLineageUpdate(sha256=asset.sha256, action="no-phash")

    dimensions_cache: dict[str, tuple[int, int] | None] = {}
    candidates = list(
        db_session.scalars(
            select(Asset).where(
                and_(
                    Asset.sha256 != asset.sha256,
                    Asset.phash.is_not(None),
                )
            )
        ).all()
    )

    best_match: Asset | None = None
    best_distance: int | None = None
    threshold = max(0, settings.duplicate_hamming_threshold)

    for candidate in candidates:
        if not candidate.phash:
            continue
        if not _is_candidate_match(asset, candidate, dimensions_cache):
            continue

        try:
            distance = _hamming_distance(asset.phash, candidate.phash)
        except Exception:  # noqa: BLE001
            continue

        if distance > threshold:
            continue

        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_match = candidate

    if best_match is None:
        asset.duplicate_group_id = None
        asset.is_canonical = True
        db_session.flush()
        return AssetLineageUpdate(sha256=asset.sha256, action="standalone")

    group_id = _ensure_group_for_candidate(db_session, best_match)
    asset.duplicate_group_id = group_id
    winner = recompute_group_canonical(db_session, group_id)
    db_session.flush()

    if winner == asset.sha256:
        return AssetLineageUpdate(sha256=asset.sha256, action="promoted-canonical")
    return AssetLineageUpdate(sha256=asset.sha256, action="grouped-noncanonical")


def _build_feature_rows(db_session: Session) -> tuple[list[_FeatureRow], dict[str, Asset]]:
    assets = list(db_session.scalars(select(Asset).where(Asset.phash.is_not(None)).order_by(Asset.sha256.asc())).all())
    by_sha = {asset.sha256: asset for asset in assets}

    dimensions_cache: dict[str, tuple[int, int] | None] = {}
    rows: list[_FeatureRow] = []
    for asset in assets:
        if not asset.phash:
            continue
        dims = _image_dimensions(asset, dimensions_cache)
        pixels = (dims[0] * dims[1]) if dims is not None else 0
        orientation = _image_orientation(asset, dimensions_cache)
        try:
            phash_int = int(asset.phash, 16)
        except ValueError:
            continue

        rows.append(
            _FeatureRow(
                sha256=asset.sha256,
                phash_hex=asset.phash,
                phash_int=phash_int,
                orientation=orientation,
                total_pixels=max(0, pixels),
                captured_at=asset.captured_at,
            )
        )

    return rows, by_sha


def _connected_components(rows: list[_FeatureRow]) -> list[list[str]]:
    if not rows:
        return []

    threshold = max(0, settings.duplicate_hamming_threshold)
    band = max(0.0, settings.duplicate_resolution_band_ratio)
    use_time_window = settings.duplicate_capture_window_enabled
    capture_window = timedelta(hours=max(1, settings.duplicate_capture_window_hours))

    parent = {row.sha256: row.sha256 for row in rows}

    def find(item: str) -> str:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(a: str, b: str) -> None:
        root_a = find(a)
        root_b = find(b)
        if root_a != root_b:
            if root_a < root_b:
                parent[root_b] = root_a
            else:
                parent[root_a] = root_b

    # Group by orientation first to reduce comparisons.
    by_orientation: dict[str | None, list[_FeatureRow]] = {}
    for row in rows:
        by_orientation.setdefault(row.orientation, []).append(row)

    for orientation_rows in by_orientation.values():
        orientation_rows.sort(key=lambda item: (item.total_pixels, item.sha256))
        left = 0
        for right, current in enumerate(orientation_rows):
            if current.total_pixels <= 0:
                continue

            lower = int(current.total_pixels * (1.0 - band))
            upper = int(current.total_pixels * (1.0 + band))

            while left < right and orientation_rows[left].total_pixels < lower:
                left += 1

            for candidate_index in range(left, right):
                candidate = orientation_rows[candidate_index]
                if candidate.total_pixels > upper:
                    break

                if use_time_window and current.captured_at and candidate.captured_at:
                    if abs(current.captured_at - candidate.captured_at) > capture_window:
                        continue

                if _hamming_distance_int(current.phash_int, candidate.phash_int) <= threshold:
                    union(current.sha256, candidate.sha256)

    groups: dict[str, list[str]] = {}
    for row in rows:
        root = find(row.sha256)
        groups.setdefault(root, []).append(row.sha256)

    return [sorted(component) for component in groups.values() if len(component) > 1]


def recompute_near_duplicate_groups(db_session: Session, *, dry_run: bool = False) -> DuplicateLineageSummary:
    """Recompute near-duplicate groups in batch for deterministic fast processing."""
    rows, by_sha = _build_feature_rows(db_session)
    components = _connected_components(rows)

    if dry_run:
        return DuplicateLineageSummary(processed=len(rows), updated=len(components), skipped=0, failed=0)

    # Reset logical grouping and canonical flags first.
    all_assets = list(db_session.scalars(select(Asset)).all())
    for asset in all_assets:
        asset.duplicate_group_id = None
        asset.is_canonical = True

    for group in list(db_session.scalars(select(DuplicateGroup)).all()):
        db_session.delete(group)
    db_session.flush()

    updated = 0
    failed = 0
    for component in components:
        try:
            group = DuplicateGroup(group_type="near")
            db_session.add(group)
            db_session.flush()

            component_assets = [by_sha[sha] for sha in component if sha in by_sha]
            dimensions_cache: dict[str, tuple[int, int] | None] = {}
            winner = max(component_assets, key=lambda asset: _asset_sort_key(asset, dimensions_cache))

            for asset in component_assets:
                asset.duplicate_group_id = group.id
                asset.is_canonical = asset.sha256 == winner.sha256

            updated += 1
        except Exception:  # noqa: BLE001
            failed += 1

    db_session.commit()
    return DuplicateLineageSummary(processed=len(rows), updated=updated, skipped=0, failed=failed)


def backfill_missing_lineage_fields(
    db_session: Session,
    *,
    chunk_size: int = 100,
    dry_run: bool = False,
) -> DuplicateLineageSummary:
    """Backfill only missing pHash/quality_score fields in chunked deterministic order."""
    assets = list(
        db_session.scalars(
            select(Asset)
            .where(
                or_(
                    Asset.phash.is_(None),
                    Asset.quality_score.is_(None),
                )
            )
            .order_by(Asset.created_at_utc.asc(), Asset.sha256.asc())
        ).all()
    )

    processed = 0
    updated = 0
    skipped = 0
    failed = 0

    for index, asset in enumerate(assets, start=1):
        processed += 1
        try:
            if dry_run:
                skipped += 1
                continue

            if asset.phash is None:
                asset.phash = _compute_phash(asset)
            if asset.quality_score is None:
                asset.quality_score = compute_quality_score(asset)

            updated += 1

            if index % max(1, chunk_size) == 0:
                db_session.commit()
        except Exception:  # noqa: BLE001
            db_session.rollback()
            failed += 1

    if not dry_run:
        db_session.commit()

    return DuplicateLineageSummary(processed=processed, updated=updated, skipped=skipped, failed=failed)
