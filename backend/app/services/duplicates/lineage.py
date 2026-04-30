"""Duplicate lineage service: provenance, pHash, near-duplicate groups, canonical ranking."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import imagehash
import pillow_heif
from PIL import Image

pillow_heif.register_heif_opener()
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
class AssetLineageMetrics:
    """Per-asset performance and outcome metrics for one lineage update call."""

    sha256: str
    mode: str  # "baseline" or "optimized"
    phash_computed: bool
    candidates_queried: int
    candidates_after_python_filter: int
    hamming_comparisons: int
    match_found: bool
    best_distance: int | None
    action: str
    db_query_seconds: float
    python_filter_seconds: float
    hamming_seconds: float
    db_write_seconds: float
    total_seconds: float


@dataclass(frozen=True)
class ProvenanceContext:
    """Optional ingestion context attached to a provenance write."""

    ingestion_source_id: int | None
    ingestion_run_id: int | None
    source_label: str | None
    source_type: str | None
    source_root_path: str | None


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


def _candidate_query_baseline(asset_sha256: str):  # type: ignore[return]
    """Unfiltered candidate query: all phash-populated assets except self."""
    return select(Asset).where(
        Asset.sha256 != asset_sha256,
        Asset.phash.is_not(None),
    )


def _candidate_query_optimized(asset: Asset):  # type: ignore[return]
    """SQL-prefiltered candidate query with NULL fallthrough on all filters.

    Pushes orientation, resolution band, and capture-time window into SQL
    to reduce candidates before Python-level comparison.  Any filter that
    cannot be evaluated due to missing data (NULL width/height/captured_at)
    falls through conservatively so no valid duplicates are excluded.
    """
    base_clauses = [
        Asset.sha256 != asset.sha256,
        Asset.phash.is_not(None),
    ]

    # Allow exact pHash match to bypass all other filters.
    exact_phash = (Asset.phash == asset.phash) if asset.phash else None

    filter_parts = []

    if asset.width is not None and asset.height is not None:
        w, h = asset.width, asset.height

        # Orientation filter (NULL = pass through)
        if w > h:
            orient_ok = or_(Asset.width.is_(None), Asset.height.is_(None), Asset.width > Asset.height)
        elif h > w:
            orient_ok = or_(Asset.width.is_(None), Asset.height.is_(None), Asset.height > Asset.width)
        else:
            orient_ok = or_(Asset.width.is_(None), Asset.height.is_(None), Asset.width == Asset.height)
        filter_parts.append(orient_ok)

        # Resolution band filter (NULL = pass through)
        band = max(0.0, settings.duplicate_resolution_band_ratio)
        current_pixels = max(1, w * h)
        low_px = int(current_pixels * (1.0 - band))
        high_px = int(current_pixels * (1.0 + band))
        res_ok = or_(
            Asset.width.is_(None),
            Asset.height.is_(None),
            and_(
                (Asset.width * Asset.height) >= low_px,
                (Asset.width * Asset.height) <= high_px,
            ),
        )
        filter_parts.append(res_ok)

    # Capture-time window filter (NULL = pass through)
    if settings.duplicate_capture_window_enabled and asset.captured_at is not None:
        hours = max(1, settings.duplicate_capture_window_hours)
        window = timedelta(hours=hours)
        low_t = asset.captured_at - window
        high_t = asset.captured_at + window
        time_ok = or_(
            Asset.captured_at.is_(None),
            and_(Asset.captured_at >= low_t, Asset.captured_at <= high_t),
        )
        filter_parts.append(time_ok)

    if filter_parts:
        combined = and_(*filter_parts)
        if exact_phash is not None:
            base_clauses.append(or_(exact_phash, combined))
        else:
            base_clauses.append(combined)

    return select(Asset).where(and_(*base_clauses))


def _is_candidate_match(
    current: Asset,
    candidate: Asset,
    dimensions_cache: dict[str, tuple[int, int] | None],
) -> bool:
    # Exact pHash matches are allowed across different resolutions/formats.
    if current.phash and candidate.phash and current.phash == candidate.phash:
        return True

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


def _resolve_source_relative_path(source_path: str, source_root_path: str | None) -> str | None:
    if not source_root_path:
        return None

    try:
        relative = Path(source_path).resolve().relative_to(Path(source_root_path).resolve())
        return str(relative)
    except Exception:  # noqa: BLE001
        # Preserve path meaning when relative computation is not possible.
        return source_path


def upsert_provenance(
    db_session: Session,
    asset_sha256: str,
    source_path: str,
    context: ProvenanceContext | None = None,
) -> bool:
    source_path = (source_path or "").strip()
    if not source_path:
        return False

    where_clauses = [
        Provenance.asset_sha256 == asset_sha256,
        Provenance.source_path == source_path,
    ]
    if context is not None and context.ingestion_run_id is not None:
        where_clauses.append(Provenance.ingestion_run_id == context.ingestion_run_id)
    else:
        where_clauses.append(Provenance.ingestion_run_id.is_(None))

    existing = db_session.scalar(
        select(Provenance).where(and_(*where_clauses))
    )
    if existing is not None:
        return False

    source_root_path = context.source_root_path if context is not None else None
    source_relative_path = _resolve_source_relative_path(source_path, source_root_path)
    db_session.add(
        Provenance(
            asset_sha256=asset_sha256,
            source_path=source_path,
            ingestion_source_id=context.ingestion_source_id if context is not None else None,
            ingestion_run_id=context.ingestion_run_id if context is not None else None,
            source_label=context.source_label if context is not None else None,
            source_type=context.source_type if context is not None else None,
            source_root_path=source_root_path,
            source_relative_path=source_relative_path,
        )
    )
    db_session.flush()
    return True


def update_asset_lineage_instrumented(
    db_session: Session,
    asset: Asset,
    *,
    mode: str = "optimized",
) -> tuple[AssetLineageUpdate, AssetLineageMetrics]:
    """Compute lineage for one asset and return detailed performance metrics.

    mode="optimized" uses SQL-prefiltered candidate query.
    mode="baseline" uses the original unfiltered query.
    Production behavior (best-match selection logic) is unchanged.
    """
    import time

    t_start = time.perf_counter()
    phash_computed = False

    if asset.phash is None:
        asset.phash = _compute_phash(asset)
        phash_computed = True
    if asset.quality_score is None:
        asset.quality_score = compute_quality_score(asset)

    if not asset.phash:
        asset.duplicate_group_id = None
        asset.is_canonical = True
        db_session.flush()
        t_end = time.perf_counter()
        return (
            AssetLineageUpdate(sha256=asset.sha256, action="no-phash"),
            AssetLineageMetrics(
                sha256=asset.sha256,
                mode=mode,
                phash_computed=phash_computed,
                candidates_queried=0,
                candidates_after_python_filter=0,
                hamming_comparisons=0,
                match_found=False,
                best_distance=None,
                action="no-phash",
                db_query_seconds=0.0,
                python_filter_seconds=0.0,
                hamming_seconds=0.0,
                db_write_seconds=0.0,
                total_seconds=t_end - t_start,
            ),
        )

    dimensions_cache: dict[str, tuple[int, int] | None] = {}
    threshold = max(0, settings.duplicate_hamming_threshold)

    # --- DB candidate query ---
    t_q0 = time.perf_counter()
    if mode == "optimized":
        candidates = list(db_session.scalars(_candidate_query_optimized(asset)).all())
    else:
        candidates = list(db_session.scalars(_candidate_query_baseline(asset.sha256)).all())
    db_query_seconds = time.perf_counter() - t_q0
    candidates_queried = len(candidates)

    # --- Python filter + Hamming ---
    t_f0 = time.perf_counter()
    best_match: Asset | None = None
    best_distance: int | None = None
    candidates_after_python_filter = 0
    hamming_comparisons = 0
    hamming_seconds_acc = 0.0

    for candidate in candidates:
        if not candidate.phash:
            continue
        if not _is_candidate_match(asset, candidate, dimensions_cache):
            continue
        candidates_after_python_filter += 1
        try:
            t_h0 = time.perf_counter()
            distance = _hamming_distance(asset.phash, candidate.phash)
            hamming_seconds_acc += time.perf_counter() - t_h0
            hamming_comparisons += 1
        except Exception:  # noqa: BLE001
            continue
        if distance > threshold:
            continue
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_match = candidate

    python_filter_seconds = (time.perf_counter() - t_f0) - hamming_seconds_acc

    # --- DB write ---
    t_w0 = time.perf_counter()
    if best_match is None:
        asset.duplicate_group_id = None
        asset.is_canonical = True
        db_session.flush()
        action = "standalone"
    else:
        group_id = _ensure_group_for_candidate(db_session, best_match)
        asset.duplicate_group_id = group_id
        # Flush before recompute so the new group assignment is visible to the
        # SELECT inside recompute_group_canonical. The session uses autoflush=False,
        # so without this flush the incoming asset is invisible to the query and
        # keeps its default is_canonical=True, producing two canonicals per group.
        db_session.flush()
        winner = recompute_group_canonical(db_session, group_id)
        db_session.flush()
        action = "promoted-canonical" if winner == asset.sha256 else "grouped-noncanonical"
    db_write_seconds = time.perf_counter() - t_w0

    t_end = time.perf_counter()
    return (
        AssetLineageUpdate(sha256=asset.sha256, action=action),
        AssetLineageMetrics(
            sha256=asset.sha256,
            mode=mode,
            phash_computed=phash_computed,
            candidates_queried=candidates_queried,
            candidates_after_python_filter=candidates_after_python_filter,
            hamming_comparisons=hamming_comparisons,
            match_found=best_match is not None,
            best_distance=best_distance,
            action=action,
            db_query_seconds=db_query_seconds,
            python_filter_seconds=python_filter_seconds,
            hamming_seconds=hamming_seconds_acc,
            db_write_seconds=db_write_seconds,
            total_seconds=t_end - t_start,
        ),
    )


def update_asset_lineage(db_session: Session, asset: Asset) -> AssetLineageUpdate:
    """Compute lineage fields for one asset and update canonical assignment as needed."""
    update, _ = update_asset_lineage_instrumented(db_session, asset, mode="optimized")
    return update


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

    # First pass: exact pHash equality is a strong duplicate signal.
    rows_by_phash: dict[int, list[_FeatureRow]] = {}
    for row in rows:
        rows_by_phash.setdefault(row.phash_int, []).append(row)

    for phash_rows in rows_by_phash.values():
        if len(phash_rows) < 2:
            continue
        anchor = phash_rows[0]
        for other in phash_rows[1:]:
            union(anchor.sha256, other.sha256)

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

                # Exact pHash matches should group even when size/time heuristics differ.
                if current.phash_int == candidate.phash_int:
                    union(current.sha256, candidate.sha256)
                    continue

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


def update_lineage_for_assets(
    db_session: Session,
    asset_sha256_list: list[str],
    *,
    dry_run: bool = False,
) -> DuplicateLineageSummary:
    """Update lineage fields and grouping only for the provided asset set."""
    if not asset_sha256_list:
        return DuplicateLineageSummary(processed=0, updated=0, skipped=0, failed=0)

    ordered_assets = list(
        db_session.scalars(
            select(Asset)
            .where(Asset.sha256.in_(asset_sha256_list))
            .order_by(Asset.created_at_utc.asc(), Asset.sha256.asc())
        ).all()
    )

    processed = 0
    updated = 0
    skipped = 0
    failed = 0

    for asset in ordered_assets:
        processed += 1
        if dry_run:
            skipped += 1
            continue

        try:
            update_asset_lineage(db_session, asset)
            db_session.commit()
            updated += 1
        except Exception:  # noqa: BLE001
            db_session.rollback()
            failed += 1

    return DuplicateLineageSummary(processed=processed, updated=updated, skipped=skipped, failed=failed)
