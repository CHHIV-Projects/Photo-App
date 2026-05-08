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
        required=True,
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


def _safe_filename(filename: str | None, fallback_id: str | None, index: int) -> str:
    if filename and filename.strip():
        return filename.strip()
    if fallback_id and fallback_id.strip():
        return f"icloud_{fallback_id.strip()}.bin"
    return f"icloud_item_{index}.bin"


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
    api: Any,
    *,
    scan_limit: int,
    retry_attempts: int,
    source_label: str,
    staging_root: Path,
    authentication: dict[str, Any],
    report_path: Path,
) -> dict[str, Any]:
    extension_counts: dict[str, int] = {}
    extension_bytes: dict[str, int] = {}
    errors: list[str] = []
    error_details: list[dict[str, Any]] = []
    retry_events: list[dict[str, Any]] = []
    scanned = 0
    total_bytes = 0

    sample_metadata: list[dict[str, Any]] = []
    photos = api.photos.all
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

        sample_metadata.append(
            {
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
        )

    payload = {
        "generated_at_utc": now_utc_iso(),
        "mode": "staging_adapter_inventory",
        "source_label": source_label,
        "staging_root": str(staging_root),
        "authentication": authentication,
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
    return payload


def _run_download(
    api: Any,
    *,
    download_limit: int,
    retry_attempts: int,
    source_label: str,
    staging_root: Path,
    existing_policy: str,
    version: str,
    authentication: dict[str, Any],
    report_path: Path,
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

    photos = api.photos.all
    for photo in photos:
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
                    "retries_used": retries_used,
                }
            )
        except Exception as exc:
            failures += 1
            errors.append(f"item_{attempted}: {type(exc).__name__}: {exc}")

    payload = {
        "generated_at_utc": now_utc_iso(),
        "mode": "staging_adapter_download",
        "source_label": source_label,
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
    if not source_label:
        print("Error: --source-label is required and cannot be empty.")
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

    staging_root = (
        Path(args.output_root).expanduser().resolve()
        if args.output_root
        else default_staging_root(source_label).resolve()
    )
    staging_root.mkdir(parents=True, exist_ok=True)

    inventory_report_path, download_report_path, summary_report_path = _report_paths(now_stamp())

    print(EXPERIMENTAL_NOTICE)
    print(f"Source label: {source_label}")
    print(f"Staging root (absolute): {staging_root}")
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

    registration = _check_source_registration(source_label, staging_root)

    inventory_payload = _run_inventory(
        api,
        scan_limit=scan_limit,
        retry_attempts=max(1, int(args.retry_attempts)),
        source_label=source_label,
        staging_root=staging_root,
        authentication=auth_data,
        report_path=inventory_report_path,
    )

    download_payload = _run_download(
        api,
        download_limit=effective_download_limit,
        retry_attempts=max(1, int(args.retry_attempts)),
        source_label=source_label,
        staging_root=staging_root,
        existing_policy=args.existing_policy,
        version=args.version,
        authentication=auth_data,
        report_path=download_report_path,
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
        "existing_policy": args.existing_policy,
        "source_registration": registration,
        "inventory_report_path": str(inventory_report_path),
        "download_report_path": str(download_report_path),
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
