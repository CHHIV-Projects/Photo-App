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
    parser.add_argument(
        "--existing-policy",
        type=str,
        choices=["skip", "rename"],
        default="skip",
        help="Behavior when destination file already exists (default: skip).",
    )
    parser.add_argument(
        "--retry-attempts",
        type=int,
        default=DEFAULT_RETRY_ATTEMPTS,
        help=f"Retry attempts for fragile metadata/download operations (default: {DEFAULT_RETRY_ATTEMPTS}).",
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
        "skipped_existing_downloads": 0,
        "renamed_for_collision": 0,
        "downloaded_files": [],
        "skipped_files": [],
        "errors": [str(error)],
        "retry_policy": {
            "attempts": max(1, int(args.retry_attempts)),
            "backoff_seconds": list(DEFAULT_RETRY_DELAYS_SECONDS),
        },
        "retry_events": [],
        "recommended_source_intake_command": source_intake_command_hint(
            (Path(args.output_root).expanduser().resolve() if args.output_root else default_staging_root(args.source_label).resolve()),
            args.source_label,
            limit=min(max(1, int(args.limit)), max(1, int(args.max_limit))),
            batch_size=min(max(1, int(args.limit)), max(1, int(args.max_limit))),
        ),
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
    skipped_existing = 0
    renamed_for_collision = 0
    retry_events: list[dict[str, Any]] = []
    downloaded_files: list[dict[str, Any]] = []
    skipped_files: list[dict[str, Any]] = []
    errors: list[str] = []

    photos = api.photos.all
    for photo in photos:
        if attempted >= limited_count:
            break

        attempted += 1
        try:
            id_outcome = retry_call(
                "identifier_candidates",
                lambda: safe_identifier_candidates(photo),
                attempts=max(1, int(args.retry_attempts)),
                delays_seconds=DEFAULT_RETRY_DELAYS_SECONDS,
            )
            identifier_candidates = id_outcome.value
            version_outcome = retry_call(
                "versions",
                lambda: getattr(photo, "versions", {}) or {},
                attempts=max(1, int(args.retry_attempts)),
                delays_seconds=DEFAULT_RETRY_DELAYS_SECONDS,
            )
            version_keys = sorted(list(version_outcome.value.keys()))

            fallback_id = identifier_candidates.get("id")
            filename = _safe_filename(getattr(photo, "filename", None), fallback_id, attempted)
            base_destination = staging_root / filename

            destination = base_destination
            was_renamed_for_collision = False
            if base_destination.exists():
                if args.existing_policy == "skip":
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
                lambda: photo.download(version=args.version),
                attempts=max(1, int(args.retry_attempts)),
                delays_seconds=DEFAULT_RETRY_DELAYS_SECONDS,
            )
            blob = download_outcome.value
            if blob is None:
                failures += 1
                errors.append(f"item_{attempted}: no download bytes for requested version '{args.version}'")
                continue

            destination.write_bytes(blob)
            written_size = destination.stat().st_size
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
                    "version_requested": args.version,
                    "version_keys": version_keys,
                    "identifier_candidates": identifier_candidates,
                    "retries_used": retries_used,
                }
            )
        except Exception as exc:
            failures += 1
            errors.append(f"item_{attempted}: {type(exc).__name__}: {exc}")

    hint_limit = min(limited_count, 10)
    source_intake_hint = source_intake_command_hint(
        staging_root,
        args.source_label,
        limit=hint_limit,
        batch_size=hint_limit,
    )

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
        "skipped_existing_downloads": skipped_existing,
        "renamed_for_collision": renamed_for_collision,
        "existing_policy": args.existing_policy,
        "downloaded_files": downloaded_files,
        "skipped_files": skipped_files,
        "retry_policy": {
            "attempts": max(1, int(args.retry_attempts)),
            "backoff_seconds": list(DEFAULT_RETRY_DELAYS_SECONDS),
        },
        "retry_events": retry_events,
        "recommended_source_intake_command": source_intake_hint,
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
    print(
        f"Attempted: {attempted} | Succeeded: {successes} | Failed: {failures} "
        f"| Skipped Existing: {skipped_existing} | Renamed For Collision: {renamed_for_collision}"
    )
    print("Recommended Source Intake command:")
    print(source_intake_hint)
    print(f"Report written: {report_path}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
