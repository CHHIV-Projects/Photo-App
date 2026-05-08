"""Inventory-only iCloud feasibility scan for Milestone 12.33.

Safety:
- Read/list only (no download)
- Prompts for credentials interactively
- Writes diagnostic report under storage/logs/icloud_connector_reports/
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Ensure backend root is importable when running script file directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.experimental.icloud_common import (
    extract_extension,
    authenticate_interactive,
    item_type_from_photo,
    now_stamp,
    now_utc_iso,
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_DELAYS_SECONDS,
    report_root,
    retry_call,
    safe_identifier_candidates,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run iCloud inventory-only feasibility scan.")
    parser.add_argument("--limit", type=int, default=25, help="Maximum assets to inspect (default: 25).")
    parser.add_argument("--username", type=str, default=None, help="Apple ID email (optional; prompts if omitted).")
    parser.add_argument(
        "--cookie-directory",
        type=str,
        default=None,
        help="Optional pyicloud session/cookie directory override.",
    )
    parser.add_argument(
        "--report-path",
        type=str,
        default=None,
        help="Optional full report path override.",
    )
    parser.add_argument(
        "--retry-attempts",
        type=int,
        default=DEFAULT_RETRY_ATTEMPTS,
        help=f"Retry attempts for fragile metadata fields (default: {DEFAULT_RETRY_ATTEMPTS}).",
    )
    return parser.parse_args()


def _normalize_size(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


def _safe_iso_datetime(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    return str(value)


def _version_key_flags(version_keys: list[str]) -> dict[str, bool]:
    lowered = [key.lower() for key in version_keys]
    has_original = "original" in lowered
    likely_video_resource = any(
        token in key
        for key in lowered
        for token in ("video", "mov", "movie")
    )
    likely_live_photo_resource = any(
        token in key
        for key in lowered
        for token in ("paired", "live", "video")
    )
    return {
        "downloadable_original_available": has_original,
        "has_video_resource_keys": likely_video_resource,
        "has_live_photo_companion_hints": likely_live_photo_resource,
    }


def _scan_inventory(
    limit: int,
    username: str | None,
    cookie_directory: str | None,
    *,
    retry_attempts: int,
) -> tuple[dict[str, Any], int]:
    api, auth = authenticate_interactive(username=username, cookie_directory=cookie_directory)

    extension_counts: dict[str, int] = {}
    extension_bytes: dict[str, int] = {}
    sample_metadata: list[dict[str, Any]] = []
    identifier_fields: set[str] = set()
    errors: list[str] = []
    error_details: list[dict[str, Any]] = []
    retry_events: list[dict[str, Any]] = []
    retry_totals = {
        "filename": 0,
        "size": 0,
        "created": 0,
        "versions": 0,
        "item_type": 0,
        "identifier_candidates": 0,
    }

    scanned = 0
    total_bytes = 0

    photos = api.photos.all
    for photo in photos:
        if scanned >= limit:
            break

        scanned += 1
        filename: str | None = None
        extension = ""
        size: int | None = None
        created_iso: str | None = None
        item_type: str | None = None
        versions: list[str] = []
        id_candidates: dict[str, Any] = {}
        field_errors: list[dict[str, Any]] = []
        item_retry_count = 0

        def _record_failure(field: str, exc: Exception) -> None:
            error_line = f"item_{scanned} [{field}] {type(exc).__name__}: {exc}"
            errors.append(error_line)
            detail = {
                "index": scanned,
                "field": field,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "filename": filename,
                "extension": extension,
                "size_bytes": size,
                "created": created_iso,
                "item_type": item_type,
                "version_keys": versions,
                "identifier_candidates": id_candidates,
            }
            error_details.append(detail)
            field_errors.append(detail)

        try:
            filename_outcome = retry_call(
                "filename",
                lambda: getattr(photo, "filename", None),
                attempts=retry_attempts,
                delays_seconds=DEFAULT_RETRY_DELAYS_SECONDS,
            )
            filename = filename_outcome.value
            retry_totals["filename"] += filename_outcome.retries_used
            item_retry_count += filename_outcome.retries_used
        except Exception as exc:
            _record_failure("filename", exc)

        extension = extract_extension(filename)

        try:
            size_outcome = retry_call(
                "size",
                lambda: getattr(photo, "size", None),
                attempts=retry_attempts,
                delays_seconds=DEFAULT_RETRY_DELAYS_SECONDS,
            )
            size = _normalize_size(size_outcome.value)
            retry_totals["size"] += size_outcome.retries_used
            item_retry_count += size_outcome.retries_used
        except Exception as exc:
            _record_failure("size", exc)

        try:
            created_outcome = retry_call(
                "created",
                lambda: getattr(photo, "created", None),
                attempts=retry_attempts,
                delays_seconds=DEFAULT_RETRY_DELAYS_SECONDS,
            )
            created_iso = _safe_iso_datetime(created_outcome.value)
            retry_totals["created"] += created_outcome.retries_used
            item_retry_count += created_outcome.retries_used
        except Exception as exc:
            created_iso = None
            _record_failure("created", exc)

        try:
            versions_outcome = retry_call(
                "versions",
                lambda: getattr(photo, "versions", {}) or {},
                attempts=retry_attempts,
                delays_seconds=DEFAULT_RETRY_DELAYS_SECONDS,
            )
            versions = sorted(list(versions_outcome.value.keys()))
            retry_totals["versions"] += versions_outcome.retries_used
            item_retry_count += versions_outcome.retries_used
        except Exception as exc:
            versions = []
            _record_failure("versions", exc)

        try:
            item_type_outcome = retry_call(
                "item_type",
                lambda: item_type_from_photo(photo),
                attempts=retry_attempts,
                delays_seconds=DEFAULT_RETRY_DELAYS_SECONDS,
            )
            item_type = item_type_outcome.value
            retry_totals["item_type"] += item_type_outcome.retries_used
            item_retry_count += item_type_outcome.retries_used
        except Exception as exc:
            item_type = None
            _record_failure("item_type", exc)

        try:
            id_outcome = retry_call(
                "identifier_candidates",
                lambda: safe_identifier_candidates(photo),
                attempts=retry_attempts,
                delays_seconds=DEFAULT_RETRY_DELAYS_SECONDS,
            )
            id_candidates = id_outcome.value
            retry_totals["identifier_candidates"] += id_outcome.retries_used
            item_retry_count += id_outcome.retries_used
            for key, value in id_candidates.items():
                if value is not None and value != []:
                    identifier_fields.add(key)
        except Exception as exc:
            id_candidates = {}
            _record_failure("identifier_candidates", exc)

        extension_counts[extension or ""] = extension_counts.get(extension or "", 0) + 1
        if size is not None:
            extension_bytes[extension or ""] = extension_bytes.get(extension or "", 0) + size
            total_bytes += size

        if item_retry_count > 0:
            retry_events.append(
                {
                    "index": scanned,
                    "filename": filename,
                    "retries_used": item_retry_count,
                }
            )

        version_flags = _version_key_flags(versions)
        looks_like_video = bool(
            (item_type or "").lower() in {"movie", "video"}
            or (extension or "").lower() in {".mov", ".mp4", ".m4v"}
            or version_flags["has_video_resource_keys"]
        )

        sample_metadata.append(
            {
                "index": scanned,
                "filename": filename,
                "extension": extension,
                "size_bytes": size,
                "created": created_iso,
                "item_type": item_type,
                "version_keys": versions,
                "resource_key_names": versions,
                "identifier_candidates": id_candidates,
                "is_video_like": looks_like_video,
                "downloadable_original_available": version_flags["downloadable_original_available"],
                "has_live_photo_companion_hints": version_flags["has_live_photo_companion_hints"],
                "retries_used": item_retry_count,
                "field_errors": [
                    {
                        "field": entry["field"],
                        "error_type": entry["error_type"],
                        "error_message": entry["error_message"],
                    }
                    for entry in field_errors
                ],
            }
        )

    payload: dict[str, Any] = {
        "generated_at_utc": now_utc_iso(),
        "mode": "inventory_only",
        "authentication": {
            "authenticated": auth.authenticated,
            "requires_2fa": auth.requires_2fa,
            "requires_2sa": auth.requires_2sa,
            "trusted_session": auth.trusted_session,
            "cookie_directory": auth.cookie_directory,
        },
        "scan": {
            "limit_requested": limit,
            "items_scanned": scanned,
            "total_bytes": total_bytes,
            "extension_counts": extension_counts,
            "extension_bytes": extension_bytes,
            "available_identifier_fields": sorted(identifier_fields),
            "retry_policy": {
                "attempts": retry_attempts,
                "backoff_seconds": list(DEFAULT_RETRY_DELAYS_SECONDS),
            },
            "retry_totals_by_field": retry_totals,
        },
        "sample_metadata": sample_metadata,
        "raw_keys_sample": {
            "sample_identifier_fields": sorted(identifier_fields),
            "sample_version_key_names": sorted({key for item in sample_metadata for key in item.get("version_keys", [])}),
        },
        "errors": errors,
        "error_details": error_details,
        "retry_events": retry_events,
    }
    return payload, scanned


def _default_report_path() -> Path:
    root = report_root()
    root.mkdir(parents=True, exist_ok=True)
    return root / f"icloud_inventory_{now_stamp()}.json"


def main() -> int:
    args = _parse_args()
    limit = max(1, min(int(args.limit), 200))

    report_path = Path(args.report_path).expanduser().resolve() if args.report_path else _default_report_path()
    report_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        payload, scanned = _scan_inventory(
            limit,
            args.username,
            args.cookie_directory,
            retry_attempts=max(1, int(args.retry_attempts)),
        )
    except Exception as exc:
        failure_payload = {
            "generated_at_utc": now_utc_iso(),
            "mode": "inventory_only",
            "authentication": {
                "authenticated": False,
                "requires_2fa": False,
                "requires_2sa": False,
                "trusted_session": False,
                "cookie_directory": args.cookie_directory,
            },
            "scan": {
                "limit_requested": limit,
                "items_scanned": 0,
                "total_bytes": 0,
                "extension_counts": {},
                "extension_bytes": {},
                "available_identifier_fields": [],
            },
            "sample_metadata": [],
            "errors": [str(exc)],
            "error_details": [],
        }
        report_path.write_text(json.dumps(failure_payload, indent=2), encoding="utf-8")
        print("Authentication/listing failed.")
        print(f"Report written: {report_path}")
        return 1

    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("iCloud inventory scan complete.")
    print(f"Scanned items: {scanned}")
    print(f"Report written: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
