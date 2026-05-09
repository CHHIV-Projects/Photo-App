"""Experimental direct iCloud staging adapter workflow (Milestone 12.35).

This wrapper provides a repeatable operator flow:
1) Inventory scan (report)
2) Controlled download to staging (report)
3) Source Intake command guidance (manual handoff)

Safety:
- Download-only from iCloud
- No direct Drop Zone/Vault/DB/provenance writes
- Staging target is storage/exports/icloud/<source_label> by default
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import select

# Ensure backend root is importable when running script file directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.db.session import SessionLocal
from app.models.ingestion_source import IngestionSource
from app.services.ingestion.ingestion_context_service import (
    coerce_source_type,
    normalize_source_label,
    normalize_source_root_path,
)
from scripts.experimental.icloud_common import (
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_DELAYS_SECONDS,
    authenticate_interactive,
    default_staging_root,
    ensure_unique_path,
    extract_extension,
    item_type_from_photo,
    now_stamp,
    now_utc_iso,
    report_root,
    retry_call,
    safe_identifier_candidates,
    source_intake_command_hint,
)

EXPERIMENTAL_NOTICE = "Experimental direct iCloud connector. Download-only. Does not modify iCloud."


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run direct iCloud staging adapter workflow (experimental).")
    parser.add_argument(
        "--source-label",
        type=str,
        required=False,
        help="Required source label used for staging folder/report metadata.",
    )
    parser.add_argument("--scan-limit", type=int, default=25, help="Inventory scan limit (default: 25).")
    parser.add_argument("--download-limit", type=int, default=10, help="Download limit (default: 10).")
    parser.add_argument(
        "--hard-max-download-limit",
        type=int,
        default=25,
        help="Hard max download limit unless --allow-large-test is provided (default: 25).",
    )
    parser.add_argument(
        "--allow-large-test",
        action="store_true",
        help="Allow download limits above --hard-max-download-limit.",
    )
    parser.add_argument(
        "--existing-policy",
        type=str,
        choices=["skip", "rename"],
        default="skip",
        help="When destination exists: skip (default) or rename.",
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default=None,
        help="Optional explicit staging root override.",
    )
    parser.add_argument("--username", type=str, default=None, help="Apple ID email (optional; prompts if omitted).")
    parser.add_argument(
        "--cookie-directory",
        type=str,
        default=None,
        help="Optional pyicloud session/cookie directory override.",
    )
    parser.add_argument(
        "--version",
        type=str,
        default="original",
        help="Requested download version (default: original).",
    )
    parser.add_argument(
        "--retry-attempts",
        type=int,
        default=DEFAULT_RETRY_ATTEMPTS,
        help=f"Retry attempts for fragile connector operations (default: {DEFAULT_RETRY_ATTEMPTS}).",
    )
    parser.add_argument(
        "--order-by",
        type=str,
        choices=["default", "newest", "oldest"],
        default="default",
        help="Sort order for assets: default (iCloud library order), newest, or oldest (default: default).",
    )
    parser.add_argument(
        "--list-albums",
        action="store_true",
        help="Read-only mode: list iCloud albums/collections and exit.",
    )
    parser.add_argument(
        "--include-album-samples",
        action="store_true",
        help="Include sample filenames in album reports (off by default for privacy).",
    )
    parser.add_argument(
        "--album",
        type=str,
        default=None,
        help="Optional album/collection name to use as candidate pool (case-insensitive exact match).",
    )
    parser.add_argument(
        "--require-empty-staging",
        action="store_true",
        help="Fail if staging folder already contains files.",
    )
    parser.add_argument(
        "--diagnose-library-order",
        action="store_true",
        help="Read-only mode: inspect Library ordering and added_date availability.",
    )
    parser.add_argument(
        "--diagnostic-limit",
        type=int,
        default=100,
        help="Max items to inspect in --diagnose-library-order mode (default: 100).",
    )
    return parser.parse_args()


def _safe_iso_datetime(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    return str(value)


def _extract_date_for_sorting(photo: Any, retry_attempts: int) -> tuple[Any, str | None, str]:
    """Extract the best available date from a photo for sorting.
    
    Returns: (date_value, date_iso, date_field_name)
    
    If date extraction fails or is unavailable, returns (None, None, 'unavailable')
    Date value is returned for sorting; date_iso for reporting.
    """
    # Prefer added_date for acquisition semantics (recently added to iCloud).
    try:
        added_outcome = retry_call(
            "added_date",
            lambda: getattr(photo, "added_date", None),
            attempts=retry_attempts,
            delays_seconds=DEFAULT_RETRY_DELAYS_SECONDS,
        )
        if added_outcome.value is not None:
            return added_outcome.value, _safe_iso_datetime(added_outcome.value), "added_date"
    except Exception:
        pass

    # Try created (capture date) as fallback only.
    try:
        created_outcome = retry_call(
            "created",
            lambda: getattr(photo, "created", None),
            attempts=retry_attempts,
            delays_seconds=DEFAULT_RETRY_DELAYS_SECONDS,
        )
        if created_outcome.value is not None:
            return created_outcome.value, _safe_iso_datetime(created_outcome.value), "created"
    except Exception:
        pass

    # Fallback: unavailable
    return None, None, "unavailable"


def _safe_filename(filename: str | None, fallback_id: str | None, index: int) -> str:
    if filename and filename.strip():
        return filename.strip()
    if fallback_id and fallback_id.strip():
        return f"icloud_{fallback_id.strip()}.bin"
    return f"icloud_item_{index}.bin"


def _safe_album_count(album: Any) -> int | None:
    try:
        return len(album)
    except Exception:
        return None


def _iter_album_entries(photos_api: Any) -> list[tuple[str, Any]]:
    """Return album entries as (album_name, album_obj) across pyicloud album container shapes."""
    albums_obj = getattr(photos_api, "albums", None)
    if not albums_obj:
        return []

    try:
        items = albums_obj.items()
        return [(str(name), obj) for name, obj in items]
    except Exception:
        pass

    try:
        keys = albums_obj.keys()
        return [(str(name), albums_obj[name]) for name in keys]
    except Exception:
        pass

    entries: list[tuple[str, Any]] = []
    try:
        for idx, album_obj in enumerate(albums_obj):
            album_name = getattr(album_obj, "name", None) or getattr(album_obj, "title", None) or f"album_{idx}"
            entries.append((str(album_name), album_obj))
    except Exception:
        return []
    return entries


def _resolve_album(photos_api: Any, requested_name: str) -> tuple[str, Any] | None:
    """Resolve album by case-insensitive exact name from pyicloud photos.albums mapping."""
    requested_norm = requested_name.strip().casefold()
    for album_name, album_obj in _iter_album_entries(photos_api):
        if str(album_name).strip().casefold() == requested_norm:
            return str(album_name), album_obj
    return None


def _list_albums_payload(
    api: Any,
    *,
    authentication: dict[str, Any],
    include_samples: bool,
) -> dict[str, Any]:
    photos_api = api.photos
    album_entries = _iter_album_entries(photos_api)

    albums: list[dict[str, Any]] = []
    errors: list[str] = []
    for album_name, album_obj in album_entries:
        count = _safe_album_count(album_obj)
        entry: dict[str, Any] = {
            "album_name": str(album_name),
            "album_count": count,
        }
        if include_samples:
            sample_names: list[str] = []
            try:
                for idx, photo in enumerate(album_obj):
                    if idx >= 5:
                        break
                    sample_names.append(str(getattr(photo, "filename", None) or ""))
            except Exception as exc:
                errors.append(f"album={album_name} sample_enumeration_error={type(exc).__name__}: {exc}")
            entry["album_sample_filenames"] = sample_names
        albums.append(entry)

    albums = sorted(albums, key=lambda row: row["album_name"].casefold())
    payload = {
        "generated_at_utc": now_utc_iso(),
        "mode": "staging_adapter_list_albums",
        "status": "SUCCESS",
        "selection_mode": "list_albums",
        "authentication": authentication,
        "include_album_samples": include_samples,
        "albums": albums,
        "album_count_total": len(albums),
        "errors": errors,
    }
    return payload


def _run_library_order_diagnostic(
    api: Any,
    *,
    authentication: dict[str, Any],
    diagnostic_limit: int,
) -> dict[str, Any]:
    resolved_album = _resolve_album(api.photos, "Library")
    if resolved_album is None:
        available_album_names = sorted(
            [name for name, _ in _iter_album_entries(api.photos)],
            key=lambda name: name.casefold(),
        )
        return {
            "generated_at_utc": now_utc_iso(),
            "mode": "staging_adapter_library_order_diagnostic",
            "status": "FAILED",
            "reason": "library_album_not_found",
            "selection_mode": "diagnostic_library_order",
            "album_requested": "Library",
            "available_albums": available_album_names,
            "authentication": authentication,
        }

    album_name, album_obj = resolved_album
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    added_date_available_count = 0
    added_date_values_sample: list[str] = []

    for idx, photo in enumerate(album_obj, start=1):
        if idx > max(1, int(diagnostic_limit)):
            break

        filename: str | None = None
        extension = ""
        size_bytes: int | None = None
        created_iso: str | None = None
        added_iso: str | None = None
        identifier_candidates: dict[str, Any] = {}

        try:
            filename = getattr(photo, "filename", None)
        except Exception as exc:
            errors.append(f"item_{idx} [filename] {type(exc).__name__}: {exc}")
        extension = extract_extension(filename)

        try:
            size_value = getattr(photo, "size", None)
            size_bytes = int(size_value) if size_value is not None else None
        except Exception as exc:
            errors.append(f"item_{idx} [size] {type(exc).__name__}: {exc}")

        try:
            created_iso = _safe_iso_datetime(getattr(photo, "created", None))
        except Exception as exc:
            errors.append(f"item_{idx} [created] {type(exc).__name__}: {exc}")

        try:
            added_iso = _safe_iso_datetime(getattr(photo, "added_date", None))
            if added_iso is not None:
                added_date_available_count += 1
                if len(added_date_values_sample) < 10:
                    added_date_values_sample.append(added_iso)
        except Exception as exc:
            errors.append(f"item_{idx} [added_date] {type(exc).__name__}: {exc}")

        try:
            identifier_candidates = safe_identifier_candidates(photo)
        except Exception as exc:
            errors.append(f"item_{idx} [identifier_candidates] {type(exc).__name__}: {exc}")

        rows.append(
            {
                "index": idx,
                "filename": filename,
                "added_date": added_iso,
                "asset_date": created_iso,
                "created": created_iso,
                "size_bytes": size_bytes,
                "extension": extension,
                "identifier_candidates": identifier_candidates,
            }
        )

    added_date_available = added_date_available_count > 0
    selection_date_field = "added_date" if added_date_available else "library_order"
    payload = {
        "generated_at_utc": now_utc_iso(),
        "mode": "staging_adapter_library_order_diagnostic",
        "status": "SUCCESS",
        "selection_mode": "diagnostic_library_order",
        "album_requested": "Library",
        "album_found": album_name,
        "album_item_count": _safe_album_count(album_obj),
        "diagnostic_limit": max(1, int(diagnostic_limit)),
        "items_inspected": len(rows),
        "added_date_available": added_date_available,
        "added_date_available_count": added_date_available_count,
        "added_date_values_sample": added_date_values_sample,
        "library_order_observation": {
            "first_filenames_in_iteration_order": [r.get("filename") for r in rows[:10] if r.get("filename")],
            "first_added_dates_in_iteration_order": [r.get("added_date") for r in rows[:10]],
        },
        "selection_date_field": selection_date_field,
        "diagnostic_rows": rows,
        "errors": errors,
        "authentication": authentication,
    }
    return payload


def _report_paths(stamp: str) -> tuple[Path, Path, Path]:
    root = report_root()
    root.mkdir(parents=True, exist_ok=True)
    inventory = root / f"icloud_adapter_inventory_{stamp}.json"
    download = root / f"icloud_adapter_download_{stamp}.json"
    summary = root / f"icloud_staging_adapter_{stamp}.json"
    return inventory, download, summary


def _check_source_registration(source_label: str, staging_root: Path) -> dict[str, Any]:
    normalized_label = normalize_source_label(source_label)
    normalized_type = coerce_source_type("cloud_export")
    normalized_root = normalize_source_root_path(str(staging_root))

    db_session = SessionLocal()
    try:
        source = db_session.scalar(
            select(IngestionSource).where(
                IngestionSource.source_label_normalized == normalized_label,
                IngestionSource.source_type == normalized_type,
                IngestionSource.source_root_path_normalized == normalized_root,
            )
        )
    finally:
        db_session.close()

    if source is None:
        return {
            "registered": False,
            "message": "Register this source in Admin before running intake.",
            "source_label": source_label,
            "source_type": "cloud_export",
            "source_root_path": str(staging_root),
        }

    return {
        "registered": True,
        "message": "Registered source found.",
        "ingestion_source_id": source.id,
        "source_label": source.source_label,
        "source_type": source.source_type,
        "source_root_path": source.source_root_path,
    }


def _run_inventory(
    photos: Any,
    *,
    scan_limit: int,
    retry_attempts: int,
    source_label: str,
    staging_root: Path,
    authentication: dict[str, Any],
    report_path: Path,
    order_by: str = "default",
    selection_mode: str = "library_all",
    album_requested: str | None = None,
    album_found: str | None = None,
    album_item_count: int | None = None,
    include_album_samples: bool = False,
) -> tuple[dict[str, Any], list[Any]]:
    extension_counts: dict[str, int] = {}
    extension_bytes: dict[str, int] = {}
    errors: list[str] = []
    error_details: list[dict[str, Any]] = []
    retry_events: list[dict[str, Any]] = []
    scanned = 0
    total_bytes = 0
    date_extraction_errors = 0
    items_with_date = 0
    items_without_date = 0

    sample_metadata: list[dict[str, Any]] = []
    collected_photos: list[tuple[Any, dict[str, Any]]] = []  # (photo, metadata)
    album_sample_filenames: list[str] = []
    for photo in photos:
        if scanned >= scan_limit:
            break

        scanned += 1
        filename: str | None = None
        extension = ""
        size_bytes: int | None = None
        created_iso: str | None = None
        item_type: str | None = None
        version_keys: list[str] = []
        identifier_candidates: dict[str, Any] = {}
        item_retries = 0

        try:
            filename_outcome = retry_call(
                "filename",
                lambda: getattr(photo, "filename", None),
                attempts=retry_attempts,
                delays_seconds=DEFAULT_RETRY_DELAYS_SECONDS,
            )
            filename = filename_outcome.value
            item_retries += filename_outcome.retries_used
        except Exception as exc:
            errors.append(f"item_{scanned} [filename] {type(exc).__name__}: {exc}")

        extension = extract_extension(filename)

        try:
            size_outcome = retry_call(
                "size",
                lambda: getattr(photo, "size", None),
                attempts=retry_attempts,
                delays_seconds=DEFAULT_RETRY_DELAYS_SECONDS,
            )
            value = size_outcome.value
            size_bytes = int(value) if value is not None else None
            item_retries += size_outcome.retries_used
        except Exception as exc:
            errors.append(f"item_{scanned} [size] {type(exc).__name__}: {exc}")
            error_details.append(
                {
                    "index": scanned,
                    "field": "size",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "filename": filename,
                }
            )

        try:
            created_outcome = retry_call(
                "created",
                lambda: getattr(photo, "created", None),
                attempts=retry_attempts,
                delays_seconds=DEFAULT_RETRY_DELAYS_SECONDS,
            )
            created_iso = _safe_iso_datetime(created_outcome.value)
            item_retries += created_outcome.retries_used
        except Exception as exc:
            created_iso = None
            errors.append(f"item_{scanned} [created] {type(exc).__name__}: {exc}")
            error_details.append(
                {
                    "index": scanned,
                    "field": "created",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "filename": filename,
                    "created": None,
                }
            )

        try:
            versions_outcome = retry_call(
                "versions",
                lambda: getattr(photo, "versions", {}) or {},
                attempts=retry_attempts,
                delays_seconds=DEFAULT_RETRY_DELAYS_SECONDS,
            )
            version_keys = sorted(list(versions_outcome.value.keys()))
            item_retries += versions_outcome.retries_used
        except Exception as exc:
            errors.append(f"item_{scanned} [versions] {type(exc).__name__}: {exc}")

        try:
            type_outcome = retry_call(
                "item_type",
                lambda: item_type_from_photo(photo),
                attempts=retry_attempts,
                delays_seconds=DEFAULT_RETRY_DELAYS_SECONDS,
            )
            item_type = type_outcome.value
            item_retries += type_outcome.retries_used
        except Exception as exc:
            errors.append(f"item_{scanned} [item_type] {type(exc).__name__}: {exc}")

        try:
            id_outcome = retry_call(
                "identifier_candidates",
                lambda: safe_identifier_candidates(photo),
                attempts=retry_attempts,
                delays_seconds=DEFAULT_RETRY_DELAYS_SECONDS,
            )
            identifier_candidates = id_outcome.value
            item_retries += id_outcome.retries_used
        except Exception as exc:
            errors.append(f"item_{scanned} [identifier_candidates] {type(exc).__name__}: {exc}")

        if item_retries > 0:
            retry_events.append({"index": scanned, "filename": filename, "retries_used": item_retries})

        extension_counts[extension or ""] = extension_counts.get(extension or "", 0) + 1
        if size_bytes is not None:
            total_bytes += size_bytes
            extension_bytes[extension or ""] = extension_bytes.get(extension or "", 0) + size_bytes

        photo_metadata = {
            "index": scanned,
            "filename": filename,
            "extension": extension,
            "size_bytes": size_bytes,
            "created": created_iso,
            "item_type": item_type,
            "version_keys": version_keys,
            "identifier_candidates": identifier_candidates,
            "downloadable_original_available": "original" in [k.lower() for k in version_keys],
            "is_video_like": (item_type or "").lower() in {"movie", "video"}
            or extension.lower() in {".mov", ".mp4", ".m4v"},
            "retries_used": item_retries,
        }
        sample_metadata.append(photo_metadata)
        collected_photos.append((photo, photo_metadata))
        if include_album_samples and len(album_sample_filenames) < 5:
            album_sample_filenames.append(str(filename or ""))

    # Selection ordering: prefer date-based ordering when available, even in default mode.
    # This aligns ongoing acquisition with recently added assets.
    sorted_photos = collected_photos
    ordering_metadata = {"order_by": order_by}

    items_with_dates: list[tuple[Any, dict[str, Any], Any, str | None, str]] = []
    items_without_dates: list[tuple[Any, dict[str, Any]]] = []
    date_field_counts: dict[str, int] = {}
    for photo, metadata in collected_photos:
        date_value, date_iso, date_field = _extract_date_for_sorting(photo, retry_attempts)
        metadata["selection_date"] = date_iso
        metadata["selection_date_field"] = date_field
        metadata["added_date"] = date_iso if date_field == "added_date" else None

        if date_value is not None:
            items_with_dates.append((photo, metadata, date_value, date_iso, date_field))
            items_with_date += 1
            date_field_counts[date_field] = date_field_counts.get(date_field, 0) + 1
        else:
            items_without_dates.append((photo, metadata))
            items_without_date += 1
            date_extraction_errors += 1

    has_sortable_dates = len(items_with_dates) > 0
    reverse_order = (order_by != "oldest")

    if has_sortable_dates:
        sorted_items = sorted(items_with_dates, key=lambda x: x[2], reverse=reverse_order)
        sorted_photos = [(item[0], item[1]) for item in sorted_items] + items_without_dates

        newest_candidate_date = sorted_items[0][3] if reverse_order else sorted_items[-1][3]
        oldest_candidate_date = sorted_items[-1][3] if reverse_order else sorted_items[0][3]
        primary_date_field = "added_date" if date_field_counts.get("added_date", 0) > 0 else sorted_items[0][4]
        ordering_metadata.update({
            "date_field_used": primary_date_field,
            "selection_date_field": primary_date_field,
            "selection_strategy": "date_desc" if reverse_order else "date_asc",
            "items_with_date": items_with_date,
            "items_without_date": items_without_date,
            "date_field_counts": date_field_counts,
            "newest_candidate_date": newest_candidate_date,
            "oldest_candidate_date": oldest_candidate_date,
        })
    else:
        ordering_metadata.update({
            "date_field_used": "unavailable",
            "selection_date_field": "library_order",
            "selection_strategy": "pool_iteration_order",
            "items_with_date": items_with_date,
            "items_without_date": items_without_date,
            "date_field_counts": date_field_counts,
        })

    payload = {
        "generated_at_utc": now_utc_iso(),
        "mode": "staging_adapter_inventory",
        "source_label": source_label,
        "staging_root": str(staging_root),
        "selection_mode": selection_mode,
        "selected_from_album": selection_mode == "album",
        "album_requested": album_requested,
        "album_found": album_found,
        "album_item_count": album_item_count,
        "album_sample_filenames": album_sample_filenames if include_album_samples else [],
        "album_order_observation": {
            "first_filenames_in_iteration_order": [
                row.get("filename") for row in sample_metadata[:5] if row.get("filename")
            ]
        },
        "date_extraction_errors": date_extraction_errors,
        "authentication": authentication,
        "ordering": ordering_metadata,
        "scan": {
            "limit_requested": scan_limit,
            "items_scanned": scanned,
            "total_bytes": total_bytes,
            "extension_counts": extension_counts,
            "extension_bytes": extension_bytes,
            "retry_policy": {
                "attempts": retry_attempts,
                "backoff_seconds": list(DEFAULT_RETRY_DELAYS_SECONDS),
            },
        },
        "sample_metadata": sample_metadata,
        "errors": errors,
        "error_details": error_details,
        "retry_events": retry_events,
    }
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    # Return payload + sorted photos (photos can't be JSON serialized, so return separately)
    return payload, sorted_photos


def _run_download(
    photos: Any,
    *,
    download_limit: int,
    retry_attempts: int,
    source_label: str,
    staging_root: Path,
    existing_policy: str,
    version: str,
    authentication: dict[str, Any],
    report_path: Path,
    sorted_photos: list[Any] | None = None,
    selection_mode: str = "library_all",
    album_requested: str | None = None,
    album_found: str | None = None,
    album_item_count: int | None = None,
) -> dict[str, Any]:
    attempted = 0
    successes = 0
    failures = 0
    skipped_existing = 0
    renamed_for_collision = 0
    total_downloaded_bytes = 0
    errors: list[str] = []
    retry_events: list[dict[str, Any]] = []
    downloaded_files: list[dict[str, Any]] = []
    skipped_files: list[dict[str, Any]] = []
    downloaded_selection_dates: list[str] = []

    candidate_photos = sorted_photos if sorted_photos is not None else photos
    for photo in candidate_photos:
        if attempted >= download_limit:
            break

        attempted += 1
        try:
            id_outcome = retry_call(
                "identifier_candidates",
                lambda: safe_identifier_candidates(photo),
                attempts=retry_attempts,
                delays_seconds=DEFAULT_RETRY_DELAYS_SECONDS,
            )
            identifier_candidates = id_outcome.value

            version_outcome = retry_call(
                "versions",
                lambda: getattr(photo, "versions", {}) or {},
                attempts=retry_attempts,
                delays_seconds=DEFAULT_RETRY_DELAYS_SECONDS,
            )
            version_keys = sorted(list(version_outcome.value.keys()))

            fallback_id = identifier_candidates.get("id")
            filename = _safe_filename(getattr(photo, "filename", None), fallback_id, attempted)
            base_destination = staging_root / filename

            destination = base_destination
            was_renamed_for_collision = False
            if base_destination.exists():
                if existing_policy == "skip":
                    skipped_existing += 1
                    skipped_files.append(
                        {
                            "index": attempted,
                            "filename": filename,
                            "existing_path": str(base_destination),
                            "reason": "already_exists_skip_policy",
                            "identifier_candidates": identifier_candidates,
                        }
                    )
                    continue

                destination = ensure_unique_path(base_destination)
                was_renamed_for_collision = destination != base_destination
                if was_renamed_for_collision:
                    renamed_for_collision += 1

            download_outcome = retry_call(
                "download",
                lambda: photo.download(version=version),
                attempts=retry_attempts,
                delays_seconds=DEFAULT_RETRY_DELAYS_SECONDS,
            )
            blob = download_outcome.value
            if blob is None:
                failures += 1
                errors.append(f"item_{attempted}: no download bytes for requested version '{version}'")
                continue

            destination.write_bytes(blob)
            written_size = destination.stat().st_size
            total_downloaded_bytes += written_size
            successes += 1

            retries_used = id_outcome.retries_used + version_outcome.retries_used + download_outcome.retries_used
            if retries_used > 0:
                retry_events.append(
                    {
                        "index": attempted,
                        "filename": filename,
                        "retries_used": retries_used,
                    }
                )

            downloaded_files.append(
                {
                    "index": attempted,
                    "filename": filename,
                    "saved_path": str(destination),
                    "destination_filename": destination.name,
                    "renamed_for_collision": was_renamed_for_collision,
                    "extension": extract_extension(filename),
                    "size_bytes": written_size,
                    "item_type": item_type_from_photo(photo),
                    "version_requested": version,
                    "version_keys": version_keys,
                    "identifier_candidates": identifier_candidates,
                    "added_date": _safe_iso_datetime(getattr(photo, "added_date", None)),
                    "created": _safe_iso_datetime(getattr(photo, "created", None)),
                    "retries_used": retries_used,
                }
            )
            added_or_created = downloaded_files[-1].get("added_date") or downloaded_files[-1].get("created")
            if added_or_created:
                downloaded_selection_dates.append(str(added_or_created))
        except Exception as exc:
            failures += 1
            errors.append(f"item_{attempted}: {type(exc).__name__}: {exc}")

    payload = {
        "generated_at_utc": now_utc_iso(),
        "mode": "staging_adapter_download",
        "source_label": source_label,
        "selection_mode": selection_mode,
        "selected_from_album": selection_mode == "album",
        "album_requested": album_requested,
        "album_found": album_found,
        "album_item_count": album_item_count,
        "download_target_folder": str(staging_root),
        "requested_limit": download_limit,
        "attempted_downloads": attempted,
        "successful_downloads": successes,
        "failed_downloads": failures,
        "skipped_existing_downloads": skipped_existing,
        "renamed_for_collision": renamed_for_collision,
        "total_downloaded_bytes": total_downloaded_bytes,
        "existing_policy": existing_policy,
        "downloaded_files": downloaded_files,
        "downloaded_filenames": [row.get("filename") for row in downloaded_files],
        "downloaded_identifier_candidates": [row.get("identifier_candidates") for row in downloaded_files],
        "created_dates_if_available": [row.get("created") for row in downloaded_files if row.get("created")],
        "added_dates_if_available": [row.get("added_date") for row in downloaded_files if row.get("added_date")],
        "selection_dates_if_available": downloaded_selection_dates,
        "skipped_files": skipped_files,
        "retry_policy": {
            "attempts": retry_attempts,
            "backoff_seconds": list(DEFAULT_RETRY_DELAYS_SECONDS),
        },
        "retry_events": retry_events,
        "errors": errors,
        "authentication": authentication,
    }
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    args = _parse_args()

    source_label = (args.source_label or "").strip()
    if not args.list_albums and not args.diagnose_library_order and not source_label:
        print("Error: --source-label is required and cannot be empty unless --list-albums is used.")
        return 2

    scan_limit = max(1, int(args.scan_limit))
    requested_download_limit = max(1, int(args.download_limit))
    hard_max = max(1, int(args.hard_max_download_limit))

    if not args.allow_large_test and requested_download_limit > hard_max:
        print(
            f"Error: requested download limit {requested_download_limit} exceeds hard max {hard_max}. "
            "Use --allow-large-test to override intentionally."
        )
        return 2

    effective_download_limit = requested_download_limit if args.allow_large_test else min(requested_download_limit, hard_max)

    inventory_report_path, download_report_path, summary_report_path = _report_paths(now_stamp())

    print(EXPERIMENTAL_NOTICE)
    if source_label:
        print(f"Source label: {source_label}")
    print(f"Scan limit: {scan_limit}")
    print(f"Download limit requested: {requested_download_limit}")
    print(f"Download limit effective: {effective_download_limit}")
    print(f"Hard max without override: {hard_max}")

    try:
        api, auth = authenticate_interactive(username=args.username, cookie_directory=args.cookie_directory)
    except Exception as exc:
        failure = {
            "generated_at_utc": now_utc_iso(),
            "status": "AUTH_FAILED",
            "source_label": source_label,
            "staging_root": str(staging_root),
            "scan_limit": scan_limit,
            "download_limit_requested": requested_download_limit,
            "download_limit_effective": effective_download_limit,
            "error": str(exc),
        }
        summary_report_path.write_text(json.dumps(failure, indent=2), encoding="utf-8")
        print("Authentication failed.")
        print(f"Summary report: {summary_report_path}")
        return 1

    auth_data = {
        "authenticated": auth.authenticated,
        "requires_2fa": auth.requires_2fa,
        "requires_2sa": auth.requires_2sa,
        "trusted_session": auth.trusted_session,
        "cookie_directory": auth.cookie_directory,
    }

    if args.list_albums:
        albums_payload = _list_albums_payload(
            api,
            authentication=auth_data,
            include_samples=bool(args.include_album_samples),
        )
        summary_report_path.write_text(json.dumps(albums_payload, indent=2), encoding="utf-8")
        print("\nAvailable albums/collections:")
        albums = albums_payload.get("albums", [])
        if not albums:
            print("- No albums returned by pyicloud.")
        else:
            for album in albums:
                count = album.get("album_count")
                count_display = str(count) if count is not None else "unknown"
                print(f"- {album.get('album_name')} (count={count_display})")
        print(f"\nAlbum report: {summary_report_path}")
        return 0

    if args.diagnose_library_order:
        diagnostic_payload = _run_library_order_diagnostic(
            api,
            authentication=auth_data,
            diagnostic_limit=max(1, int(args.diagnostic_limit)),
        )
        summary_report_path.write_text(json.dumps(diagnostic_payload, indent=2), encoding="utf-8")

        if diagnostic_payload.get("status") != "SUCCESS":
            print("Library-order diagnostic failed.")
            print(f"Reason: {diagnostic_payload.get('reason')}")
            print(f"Summary report: {summary_report_path}")
            return 1

        print("\nLibrary-order diagnostic complete.")
        print(f"Album: {diagnostic_payload.get('album_found')}")
        print(f"Items inspected: {diagnostic_payload.get('items_inspected')}")
        print(f"added_date available: {diagnostic_payload.get('added_date_available')}")
        print(f"selection_date_field: {diagnostic_payload.get('selection_date_field')}")
        print(f"Summary report: {summary_report_path}")
        return 0

    staging_root = (
        Path(args.output_root).expanduser().resolve()
        if args.output_root
        else default_staging_root(source_label).resolve()
    )
    staging_root.mkdir(parents=True, exist_ok=True)
    print(f"Staging root (absolute): {staging_root}")

    if args.require_empty_staging:
        existing_files = [p for p in staging_root.iterdir() if p.is_file()]
        if existing_files:
            failure = {
                "generated_at_utc": now_utc_iso(),
                "status": "FAILED",
                "reason": "staging_not_empty",
                "source_label": source_label,
                "staging_root": str(staging_root),
                "existing_file_count": len(existing_files),
                "existing_sample_files": [p.name for p in existing_files[:10]],
            }
            summary_report_path.write_text(json.dumps(failure, indent=2), encoding="utf-8")
            print("Error: staging folder is not empty and --require-empty-staging was set.")
            print(f"Summary report: {summary_report_path}")
            return 2

    registration = _check_source_registration(source_label, staging_root)

    selection_mode = "library_all"
    album_requested = args.album.strip() if args.album else None
    album_found: str | None = None
    album_item_count: int | None = None
    candidate_photos = api.photos.all

    if album_requested:
        resolved_album = _resolve_album(api.photos, album_requested)
        if resolved_album is None:
            available_album_names = sorted(
                [name for name, _ in _iter_album_entries(api.photos)],
                key=lambda name: name.casefold(),
            )
            failure = {
                "generated_at_utc": now_utc_iso(),
                "status": "FAILED",
                "reason": "album_not_found",
                "selection_mode": "album",
                "album_requested": album_requested,
                "available_albums": available_album_names,
                "source_label": source_label,
                "staging_root": str(staging_root),
            }
            summary_report_path.write_text(json.dumps(failure, indent=2), encoding="utf-8")
            print(f"Error: album '{album_requested}' not found.")
            print("Available albums:")
            for name in available_album_names:
                print(f"- {name}")
            print(f"Summary report: {summary_report_path}")
            return 1

        album_found, album_obj = resolved_album
        album_item_count = _safe_album_count(album_obj)
        selection_mode = "album"
        candidate_photos = album_obj

        if album_item_count == 0:
            completed = {
                "generated_at_utc": now_utc_iso(),
                "status": "COMPLETED",
                "warning": "album_empty",
                "selection_mode": "album",
                "selected_from_album": True,
                "album_requested": album_requested,
                "album_found": album_found,
                "album_item_count": 0,
                "source_label": source_label,
                "staging_root": str(staging_root),
                "download_summary": {
                    "attempted_downloads": 0,
                    "successful_downloads": 0,
                    "skipped_existing_downloads": 0,
                    "failed_downloads": 0,
                },
            }
            summary_report_path.write_text(json.dumps(completed, indent=2), encoding="utf-8")
            print(f"Album '{album_found}' is empty. No downloads performed.")
            print(f"Summary report: {summary_report_path}")
            return 0

    inventory_payload, sorted_photos = _run_inventory(
        candidate_photos,
        scan_limit=scan_limit,
        retry_attempts=max(1, int(args.retry_attempts)),
        source_label=source_label,
        staging_root=staging_root,
        authentication=auth_data,
        report_path=inventory_report_path,
        order_by=args.order_by,
        selection_mode=selection_mode,
        album_requested=album_requested,
        album_found=album_found,
        album_item_count=album_item_count,
        include_album_samples=bool(args.include_album_samples),
    )

    # sorted_photos is already returned from _run_inventory as list of (photo, metadata) tuples
    if sorted_photos:
        sorted_photos = [photo for photo, _ in sorted_photos]  # Extract just the photo objects

    effective_sorted_photos = sorted_photos if sorted_photos else None

    download_payload = _run_download(
        candidate_photos,
        download_limit=effective_download_limit,
        retry_attempts=max(1, int(args.retry_attempts)),
        source_label=source_label,
        staging_root=staging_root,
        existing_policy=args.existing_policy,
        version=args.version,
        authentication=auth_data,
        report_path=download_report_path,
        sorted_photos=effective_sorted_photos,
        selection_mode=selection_mode,
        album_requested=album_requested,
        album_found=album_found,
        album_item_count=album_item_count,
    )

    intake_hint = source_intake_command_hint(
        staging_root,
        source_label,
        limit=min(effective_download_limit, 10),
        batch_size=min(effective_download_limit, 10),
    )

    summary_payload = {
        "generated_at_utc": now_utc_iso(),
        "status": "SUCCESS" if download_payload.get("failed_downloads", 0) == 0 else "PARTIAL_FAILURE",
        "experimental_notice": EXPERIMENTAL_NOTICE,
        "source_label": source_label,
        "staging_root": str(staging_root),
        "scan_limit": scan_limit,
        "download_limit_requested": requested_download_limit,
        "download_limit_effective": effective_download_limit,
        "selection_mode": selection_mode,
        "selected_from_album": selection_mode == "album",
        "album_requested": album_requested,
        "album_found": album_found,
        "album_item_count": album_item_count,
        "order_by": args.order_by,
        "existing_policy": args.existing_policy,
        "source_registration": registration,
        "inventory_report_path": str(inventory_report_path),
        "download_report_path": str(download_report_path),
        "ordering_metadata": inventory_payload.get("ordering", {}),
        "inventory_summary": {
            "items_scanned": inventory_payload.get("scan", {}).get("items_scanned", 0),
            "extension_counts": inventory_payload.get("scan", {}).get("extension_counts", {}),
            "errors": len(inventory_payload.get("errors", [])),
        },
        "download_summary": {
            "attempted_downloads": download_payload.get("attempted_downloads", 0),
            "successful_downloads": download_payload.get("successful_downloads", 0),
            "skipped_existing_downloads": download_payload.get("skipped_existing_downloads", 0),
            "failed_downloads": download_payload.get("failed_downloads", 0),
            "renamed_for_collision": download_payload.get("renamed_for_collision", 0),
            "total_downloaded_bytes": download_payload.get("total_downloaded_bytes", 0),
        },
        "recommended_source_intake_command": intake_hint,
        "recommended_source_registration": {
            "source_label": source_label,
            "source_type": "cloud_export",
            "source_root_path": str(staging_root),
        },
    }

    summary_report_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")

    print("\nStaging adapter run complete.")
    print(f"Inventory report: {inventory_report_path}")
    print(f"Download report: {download_report_path}")
    print(f"Summary report: {summary_report_path}")

    print("\nSource registration check:")
    print(registration.get("message"))
    if registration.get("registered"):
        print(f"Ingestion source ID: {registration.get('ingestion_source_id')}")
    else:
        print(f"Source Label: {source_label}")
        print("Source Type: cloud_export")
        print(f"Source Root Path: {staging_root}")

    print("\nRecommended Source Intake command:")
    print(intake_hint)

    return 0 if download_payload.get("failed_downloads", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
