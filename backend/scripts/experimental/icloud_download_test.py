"""Small controlled iCloud original-download spike for Milestone 12.33.

Safety:
- Download-only
- No direct Drop Zone/Vault writes
- Writes into staging root: storage/exports/icloud/<source_label>/
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
    DEFAULT_SOURCE_LABEL,
    authenticate_interactive,
    default_staging_root,
    ensure_unique_path,
    extract_extension,
    item_type_from_photo,
    now_stamp,
    now_utc_iso,
    report_root,
    safe_identifier_candidates,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run small controlled iCloud download feasibility test.")
    parser.add_argument("--limit", type=int, default=10, help="Max assets to attempt (default: 10).")
    parser.add_argument(
        "--source-label",
        type=str,
        default=DEFAULT_SOURCE_LABEL,
        help=f"Source label used for staging path (default: {DEFAULT_SOURCE_LABEL}).",
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default=None,
        help="Optional explicit staging folder root override.",
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
        help="Requested pyicloud asset version (default: original).",
    )
    parser.add_argument(
        "--max-limit",
        type=int,
        default=25,
        help="Hard ceiling for this spike run (default: 25).",
    )
    return parser.parse_args()


def _safe_filename(filename: str | None, fallback_id: str | None, index: int) -> str:
    if filename and filename.strip():
        return filename.strip()
    if fallback_id and fallback_id.strip():
        return f"icloud_{fallback_id.strip()}.bin"
    return f"icloud_item_{index}.bin"


def _default_report_path() -> Path:
    root = report_root()
    root.mkdir(parents=True, exist_ok=True)
    return root / f"icloud_download_{now_stamp()}.json"


def _write_failure_report(report_path: Path, args: argparse.Namespace, error: Exception) -> None:
    payload = {
        "generated_at_utc": now_utc_iso(),
        "source_label": args.source_label,
        "download_target_folder": str(Path(args.output_root).expanduser().resolve()) if args.output_root else None,
        "requested_limit": int(args.limit),
        "hard_limit": int(args.max_limit),
        "attempted_downloads": 0,
        "successful_downloads": 0,
        "failed_downloads": 0,
        "downloaded_files": [],
        "errors": [str(error)],
        "authentication": {
            "authenticated": False,
            "requires_2fa": False,
            "requires_2sa": False,
            "trusted_session": False,
            "cookie_directory": args.cookie_directory,
        },
    }
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    args = _parse_args()
    hard_limit = max(1, int(args.max_limit))
    requested_limit = max(1, int(args.limit))
    limited_count = min(requested_limit, hard_limit)

    staging_root = (
        Path(args.output_root).expanduser().resolve()
        if args.output_root
        else default_staging_root(args.source_label).resolve()
    )
    staging_root.mkdir(parents=True, exist_ok=True)

    report_path = _default_report_path()

    try:
        api, auth = authenticate_interactive(username=args.username, cookie_directory=args.cookie_directory)
    except Exception as exc:
        _write_failure_report(report_path, args, exc)
        print("Authentication failed.")
        print(f"Report written: {report_path}")
        return 1

    attempted = 0
    successes = 0
    failures = 0
    downloaded_files: list[dict[str, Any]] = []
    errors: list[str] = []

    photos = api.photos.all
    for photo in photos:
        if attempted >= limited_count:
            break

        attempted += 1
        try:
            identifier_candidates = safe_identifier_candidates(photo)
            fallback_id = identifier_candidates.get("id")
            filename = _safe_filename(getattr(photo, "filename", None), fallback_id, attempted)
            destination = ensure_unique_path(staging_root / filename)

            blob = photo.download(version=args.version)
            if blob is None:
                failures += 1
                errors.append(f"item_{attempted}: no download bytes for requested version '{args.version}'")
                continue

            destination.write_bytes(blob)
            written_size = destination.stat().st_size
            successes += 1

            downloaded_files.append(
                {
                    "index": attempted,
                    "filename": filename,
                    "saved_path": str(destination),
                    "extension": extract_extension(filename),
                    "size_bytes": written_size,
                    "item_type": item_type_from_photo(photo),
                    "version_requested": args.version,
                    "version_keys": sorted(list((getattr(photo, "versions", {}) or {}).keys())),
                    "identifier_candidates": identifier_candidates,
                }
            )
        except Exception as exc:
            failures += 1
            errors.append(f"item_{attempted}: {exc}")

    payload = {
        "generated_at_utc": now_utc_iso(),
        "source_label": args.source_label,
        "download_target_folder": str(staging_root),
        "requested_limit": requested_limit,
        "hard_limit": hard_limit,
        "effective_limit": limited_count,
        "attempted_downloads": attempted,
        "successful_downloads": successes,
        "failed_downloads": failures,
        "downloaded_files": downloaded_files,
        "errors": errors,
        "authentication": {
            "authenticated": auth.authenticated,
            "requires_2fa": auth.requires_2fa,
            "requires_2sa": auth.requires_2sa,
            "trusted_session": auth.trusted_session,
            "cookie_directory": auth.cookie_directory,
        },
    }

    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("iCloud download feasibility test complete.")
    print(f"Staging folder: {staging_root}")
    print(f"Attempted: {attempted} | Succeeded: {successes} | Failed: {failures}")
    print(f"Report written: {report_path}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
