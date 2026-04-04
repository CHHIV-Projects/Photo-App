"""Run Drop Zone based ingestion and persist results to PostgreSQL."""

from __future__ import annotations

import json
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.ingestion.deduplicator import deduplicate
from app.services.ingestion.dropzone_manager import (
    build_dropzone_processing_records,
    stage_source_folder_to_dropzone,
)
from app.services.ingestion.filter import filter_records
from app.services.ingestion.hasher import hash_records
from app.services.ingestion.scanner import scan_folder
from app.services.ingestion.storage_manager import copy_unique_files_to_vault
from app.services.persistence.asset_repository import persist_copied_files


def _resolve_runtime_path(path_setting: str) -> Path:
    """Resolve config-relative path from backend folder to absolute path."""
    return (BACKEND_ROOT / path_setting).resolve()


def main() -> int:
    if len(sys.argv) >= 2:
        source_folder = Path(sys.argv[1]).expanduser().resolve()
    else:
        folder_input = input("Enter source folder path for Drop Zone ingestion: ").strip()
        if not folder_input:
            print("No source folder path provided. Exiting.")
            return 1
        source_folder = Path(folder_input).expanduser().resolve()

    drop_zone_path = _resolve_runtime_path(settings.drop_zone_path)
    vault_path = _resolve_runtime_path(settings.vault_path)
    quarantine_path = _resolve_runtime_path(settings.quarantine_path)

    source_scan_result, stage_result = stage_source_folder_to_dropzone(
        source_folder,
        drop_zone_path,
        quarantine_path,
    )

    dropzone_scan_result = scan_folder(drop_zone_path)
    processing_records = build_dropzone_processing_records(
        dropzone_scan_result.files,
        stage_result.staged_files,
    )
    filter_result = filter_records(
        processing_records,
        approved_extensions=settings.approved_extensions,
        min_size_bytes=settings.minimum_file_size_bytes,
    )
    hash_result = hash_records(filter_result.accepted)
    dedup_result = deduplicate(hash_result.hashed_files)
    storage_result = copy_unique_files_to_vault(dedup_result, vault_path)

    db_session = SessionLocal()
    try:
        persistence_result = persist_copied_files(db_session, storage_result.copied_files)
    finally:
        db_session.close()

    rejected_for_quarantine = [
        {
            "file": rejected.record.full_path,
            "reason": rejected.reason,
            "quarantine_target_path": str(quarantine_path / rejected.record.file_name),
        }
        for rejected in filter_result.rejected
    ]

    output = {
        "config": {
            "approved_extensions": sorted(settings.approved_extensions),
            "minimum_file_size_bytes": settings.minimum_file_size_bytes,
            "drop_zone_path": str(drop_zone_path),
            "vault_path": str(vault_path),
            "quarantine_path": str(quarantine_path),
        },
        "source_files_scanned": len(source_scan_result.files),
        "files_copied_to_drop_zone": len(stage_result.staged_files),
        "drop_zone_scan_count": len(dropzone_scan_result.files),
        "drop_zone_processed_count": len(processing_records),
        "accepted": len(filter_result.accepted),
        "rejected": len(filter_result.rejected),
        "unique": len(dedup_result.unique_files),
        "duplicates": len(dedup_result.duplicate_files),
        "copied_to_vault": len(storage_result.copied_files),
        "inserted_into_db": len(persistence_result.inserted_records),
        "skipped_existing": len(persistence_result.skipped_existing_records),
        "failures_by_stage": {
            "source_scan_errors": source_scan_result.errors,
            "dropzone_stage_failures": [failure.reason for failure in stage_result.failures],
            "dropzone_scan_errors": dropzone_scan_result.errors,
            "hash_failures": [failure.reason for failure in hash_result.errors],
            "vault_copy_failures": [failure.reason for failure in storage_result.failed_files],
            "database_failures": [failure.reason for failure in persistence_result.failed_inserts],
        },
        "quarantine_report_only": {
            "path": str(quarantine_path),
            "rejected_files": rejected_for_quarantine,
            "stage_failures": [
                {
                    "file": failure.source_record.full_path,
                    "reason": failure.reason,
                    "quarantine_target_path": failure.quarantine_target_path,
                }
                for failure in stage_result.failures
            ],
        },
    }

    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())