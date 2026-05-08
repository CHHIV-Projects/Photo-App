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
    report_root,
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


def _scan_inventory(limit: int, username: str | None, cookie_directory: str | None) -> tuple[dict[str, Any], int]:
    api, auth = authenticate_interactive(username=username, cookie_directory=cookie_directory)

    extension_counts: dict[str, int] = {}
    extension_bytes: dict[str, int] = {}
    sample_metadata: list[dict[str, Any]] = []
    identifier_fields: set[str] = set()
    errors: list[str] = []
    error_details: list[dict[str, Any]] = []

    scanned = 0
    total_bytes = 0

    photos = api.photos.all
    for photo in photos:
        if scanned >= limit:
            break

        scanned += 1
        step = "init"
        filename: str | None = None
        extension = ""
        size: int | None = None
        created_iso: str | None = None
        item_type: str | None = None
        versions: list[str] = []
        id_candidates: dict[str, Any] = {}

        try:
            step = "filename"
            filename = getattr(photo, "filename", None)

            step = "extension"
            extension = extract_extension(filename)

            step = "size"
            size = _normalize_size(getattr(photo, "size", None))

            step = "created"
            created = getattr(photo, "created", None)

            step = "versions"
            versions = sorted(list((getattr(photo, "versions", {}) or {}).keys()))

            step = "identifiers"
            id_candidates = safe_identifier_candidates(photo)
            for key, value in id_candidates.items():
                if value is not None and value != []:
                    identifier_fields.add(key)

            step = "item_type"
            item_type = item_type_from_photo(photo)

            step = "totals"
            extension_counts[extension or ""] = extension_counts.get(extension or "", 0) + 1
            if size is not None:
                extension_bytes[extension or ""] = extension_bytes.get(extension or "", 0) + size
                total_bytes += size

            step = "record"
            created_iso = _safe_iso_datetime(created)

            sample_metadata.append(
                {
                    "index": scanned,
                    "filename": filename,
                    "extension": extension,
                    "size_bytes": size,
                    "created": created_iso,
                    "item_type": item_type,
                    "version_keys": versions,
                    "identifier_candidates": id_candidates,
                }
            )
        except Exception as exc:  # keep scanning remaining assets
            if item_type is None:
                item_type = item_type_from_photo(photo)

            if not id_candidates:
                try:
                    id_candidates = safe_identifier_candidates(photo)
                except Exception:
                    id_candidates = {}

            errors.append(f"item_{scanned} [{step}] {type(exc).__name__}: {exc}")
            error_details.append(
                {
                    "index": scanned,
                    "step": step,
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
        },
        "sample_metadata": sample_metadata,
        "errors": errors,
        "error_details": error_details,
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
        payload, scanned = _scan_inventory(limit, args.username, args.cookie_directory)
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
