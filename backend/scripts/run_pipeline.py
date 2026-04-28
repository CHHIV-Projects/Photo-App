"""Pipeline orchestration script for batch ingest and processing."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.asset import Asset
from app.models.face import Face
from app.models.place import Place
from app.services.duplicates.lineage import ProvenanceContext
from app.services.ingestion.deduplicator import DeduplicationResult, DuplicateFile
from app.services.ingestion.ingestion_context_schema import ensure_ingestion_context_schema
from app.services.ingestion.ingestion_context_service import ResolvedIngestionContext, resolve_ingestion_context
from app.services.location.geocoding_service import enrich_places_with_reverse_geocoding
from app.services.metadata.canonicalization_service import (
    create_ingest_observations_for_batch,
    recompute_canonical_metadata_for_assets,
)
from app.services.metadata.metadata_canonicalization_schema import ensure_metadata_canonicalization_schema
from app.services.places.grouping import assign_assets_to_places
from app.services.places.place_schema import ensure_place_schema
from app.services.ingestion.dropzone_manager import (
    DropzoneStageResult,
    build_dropzone_processing_records,
    stage_source_records_to_dropzone,
)
from app.services.ingestion.failure_manager import move_record_to_ingest_failures
from app.services.ingestion.filter import FilterResult, filter_records
from app.services.ingestion.hasher import HashResult, HashedFile, hash_records
from app.services.ingestion.scanner import FileScanRecord, ScanResult, scan_folder
from app.services.ingestion.storage_manager import StorageResult, copy_unique_files_to_vault
from app.services.persistence.asset_repository import (
    DuplicateProvenanceResult,
    PersistenceResult,
    persist_copied_files,
    persist_duplicate_provenance,
)


@dataclass
class PipelineContext:
    from_path: Path | None
    drop_zone_path: Path
    vault_path: Path
    quarantine_path: Path
    ingest_failures_path: Path
    ingest_batch_size: int
    ingest_total_limit: int | None
    source_label: str | None
    source_type: str | None
    source_scan_result: ScanResult | None = None
    source_selected_records: list[FileScanRecord] = field(default_factory=list)
    stage_result: DropzoneStageResult | None = None
    dropzone_scan_result: ScanResult | None = None
    processing_records: list[FileScanRecord] = field(default_factory=list)
    filter_result: FilterResult | None = None
    hash_result: HashResult | None = None
    dedup_result: DeduplicationResult | None = None
    storage_result: StorageResult | None = None
    persistence_result: PersistenceResult | None = None
    duplicate_provenance_result: DuplicateProvenanceResult | None = None
    known_asset_sha256: set[str] = field(default_factory=set)
    current_batch_records: list[FileScanRecord] = field(default_factory=list)
    current_batch_new_asset_sha256: list[str] = field(default_factory=list)
    total_batches_run: int = 0
    total_new_unique_ingested: int = 0
    total_existing_or_duplicate_processed: int = 0
    total_dropzone_files_cleaned: int = 0
    cleaned_dropzone_paths: list[str] = field(default_factory=list)
    moved_to_ingest_failures: list[dict[str, str]] = field(default_factory=list)
    failed_move_paths: list[str] = field(default_factory=list)
    manifest_path: Path | None = None
    run_face_detection_rebuild: bool = False
    run_face_clustering_rebuild: bool = False
    resolved_ingestion_context: ResolvedIngestionContext | None = None


@dataclass(frozen=True)
class StageOutcome:
    key: str
    label: str
    status: str
    elapsed_seconds: float
    summary: dict[str, Any] | None = None
    error: str | None = None
    skip_reason: str | None = None


@dataclass(frozen=True)
class RuntimeArgs:
    """Normalized runtime options for interactive and CLI execution."""

    dry_run: bool
    from_path: Path | None
    skip_exif_extraction: bool
    skip_metadata_normalization: bool
    skip_duplicate_lineage: bool
    skip_event_clustering: bool
    skip_face_processing: bool
    run_face_detection_rebuild: bool
    run_face_clustering_rebuild: bool
    skip_crop_generation: bool
    ingest_batch_size: int
    ingest_total_limit: int | None
    source_label: str | None
    source_type: str | None


@dataclass(frozen=True)
class IngestionBatch:
    records: list[FileScanRecord]
    filter_result: FilterResult
    hash_result: HashResult
    dedup_result: DeduplicationResult
    prospective_new_unique: int


def _resolve_runtime_path(path_setting: str) -> Path:
    return (BACKEND_ROOT / path_setting).resolve()


def _format_duration(total_seconds: float) -> str:
    if total_seconds < 60:
        return f"{total_seconds:.1f}s"

    total_whole_seconds = int(round(total_seconds))
    hours, remainder = divmod(total_whole_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def _print_stage_header(index: int, total: int, label: str) -> None:
    print(f"[{index}/{total}] Running {label}...")


def _print_stage_done(elapsed_seconds: float, summary: dict[str, Any] | None) -> None:
    print(f"Done in {_format_duration(elapsed_seconds)}")
    if summary:
        for key, value in summary.items():
            print(f"  - {key}: {value}")
    print()


def _print_stage_skipped(index: int, total: int, label: str, reason: str) -> None:
    print(f"[{index}/{total}] Skipping {label} ({reason})")
    print()


def _print_stage_failed(elapsed_seconds: float, error: str) -> None:
    print(f"Failed in {_format_duration(elapsed_seconds)}")
    print(f"  Error: {error}")
    print()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the AI Photo Organizer pipeline in the correct order.",
    )
    parser.add_argument(
        "--ingest-batch-size",
        type=int,
        help="Batch size for newly ingested unique assets.",
    )
    parser.add_argument(
        "--ingest-total-limit",
        type=int,
        help="Optional total limit for newly ingested unique assets in this run.",
    )
    parser.add_argument(
        "--from-path",
        type=Path,
        help="Optional source folder to stage into the Drop Zone before processing.",
    )
    parser.add_argument(
        "--source-label",
        type=str,
        help="Optional human-readable source label for this ingestion run.",
    )
    parser.add_argument(
        "--source-type",
        type=str,
        choices=["local_folder", "external_drive", "cloud_export", "scan_batch", "other"],
        help="Optional source type label for this ingestion run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the stage plan without executing it.",
    )
    parser.add_argument(
        "--skip-exif-extraction",
        action="store_true",
        help="Skip EXIF extraction stage.",
    )
    parser.add_argument(
        "--skip-metadata-normalization",
        action="store_true",
        help="Skip metadata normalization stage.",
    )
    parser.add_argument(
        "--skip-duplicate-lineage",
        action="store_true",
        help="Skip duplicate-lineage backfill/grouping stage.",
    )
    parser.add_argument(
        "--skip-event-clustering",
        action="store_true",
        help="Skip event clustering stage.",
    )
    parser.add_argument(
        "--run-face-detection-rebuild",
        action="store_true",
        help="Run global destructive face detection rebuild.",
    )
    parser.add_argument(
        "--run-face-clustering-rebuild",
        action="store_true",
        help="Run global destructive face embedding + clustering rebuild.",
    )
    parser.add_argument(
        "--skip-face-processing",
        action="store_true",
        help="Skip incremental face detection/embedding/clustering stages.",
    )
    parser.add_argument(
        "--skip-crop-generation",
        action="store_true",
        help="Skip review crop generation stage.",
    )
    parser.add_argument(
        "--run-crop-generation",
        action="store_true",
        help="Force crop generation even when face processing is skipped.",
    )
    parser.add_argument(
        "--confirm-rebuild",
        type=str,
        default="",
        help="Required value REBUILD when running destructive face rebuild stages.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Force interactive prompts even when CLI flags are provided.",
    )
    return parser


def _has_non_interactive_flags(parsed: argparse.Namespace) -> bool:
    return any(
        [
            parsed.ingest_batch_size is not None,
            parsed.ingest_total_limit is not None,
            parsed.from_path is not None,
            bool(parsed.source_label),
            bool(parsed.source_type),
            parsed.dry_run,
            parsed.skip_exif_extraction,
            parsed.skip_metadata_normalization,
            parsed.skip_duplicate_lineage,
            parsed.skip_event_clustering,
            parsed.skip_face_processing,
            parsed.skip_crop_generation,
            parsed.run_face_detection_rebuild,
            parsed.run_face_clustering_rebuild,
            parsed.run_crop_generation,
            bool(parsed.confirm_rebuild),
        ]
    )


def _prompt_yes_no_default_no(question: str) -> bool:
    """Prompt user for yes/no with default no."""
    while True:
        response = input(f"{question} (y/n, default n): ").strip().lower()
        if response == "":
            return False
        if response in ("y", "yes"):
            return True
        if response in ("n", "no"):
            return False
        print("  Please enter 'y' or 'n'.")


def _maybe_confirm_rebuild_interactive(rebuild_requested: bool) -> str:
    if not rebuild_requested:
        return ""

    print("WARNING: Global face rebuild can reset reviewed identity work.")
    return input("Type REBUILD to confirm destructive face stages: ").strip()


def _build_runtime_args(
    *,
    dry_run: bool,
    from_path: Path | None,
    skip_exif_extraction: bool,
    skip_metadata_normalization: bool,
    skip_duplicate_lineage: bool,
    skip_event_clustering: bool,
    skip_face_processing: bool,
    skip_crop_generation: bool,
    run_face_detection_rebuild: bool,
    run_face_clustering_rebuild: bool,
    run_crop_generation_override: bool,
    ingest_batch_size: int,
    ingest_total_limit: int | None,
    source_label: str | None,
    source_type: str | None,
) -> RuntimeArgs:
    any_face_rebuild = run_face_detection_rebuild or run_face_clustering_rebuild
    run_crop_generation = run_crop_generation_override or (not skip_face_processing)
    effective_skip_crop_generation = not run_crop_generation or skip_crop_generation

    return RuntimeArgs(
        dry_run=dry_run,
        from_path=from_path,
        skip_exif_extraction=skip_exif_extraction,
        skip_metadata_normalization=skip_metadata_normalization,
        skip_duplicate_lineage=skip_duplicate_lineage,
        skip_event_clustering=skip_event_clustering,
        skip_face_processing=skip_face_processing or any_face_rebuild,
        run_face_detection_rebuild=run_face_detection_rebuild,
        run_face_clustering_rebuild=run_face_clustering_rebuild,
        skip_crop_generation=effective_skip_crop_generation,
        ingest_batch_size=ingest_batch_size,
        ingest_total_limit=ingest_total_limit,
        source_label=source_label,
        source_type=source_type,
    )


def _validate_rebuild_confirmation(
    *,
    run_face_detection_rebuild: bool,
    run_face_clustering_rebuild: bool,
    confirmation_value: str,
) -> None:
    if not (run_face_detection_rebuild or run_face_clustering_rebuild):
        return

    if confirmation_value != "REBUILD":
        raise ValueError(
            "Destructive face rebuild requested. Provide REBUILD confirmation. "
            "Interactive mode: type REBUILD when prompted. "
            "CLI mode: pass --confirm-rebuild REBUILD."
        )


def _validate_ingest_controls(ingest_batch_size: int, ingest_total_limit: int | None) -> None:
    if ingest_batch_size <= 0:
        raise ValueError("Ingest batch size must be greater than zero.")
    if ingest_total_limit is not None:
        raise ValueError("INGEST_TOTAL_LIMIT is not supported in milestone 12.19. Use INGEST_BATCH_SIZE only.")


def _prompt_yes_no(question: str) -> bool:
    """Prompt user for yes/no input."""
    while True:
        response = input(f"{question} (y/n): ").strip().lower()
        if response in ("y", "yes"):
            return True
        if response in ("n", "no"):
            return False
        print("  Please enter 'y' or 'n'")


def _prompt_int_default(question: str, default: int) -> int:
    while True:
        response = input(f"{question} (default {default}): ").strip()
        if response == "":
            return default
        try:
            value = int(response)
        except ValueError:
            print("  Please enter a whole number.")
            continue
        if value <= 0:
            print("  Please enter a value greater than zero.")
            continue
        return value


def _prompt_optional_int(question: str) -> int | None:
    while True:
        response = input(f"{question} (leave blank for no limit): ").strip()
        if response == "":
            return None
        try:
            value = int(response)
        except ValueError:
            print("  Please enter a whole number or leave blank.")
            continue
        if value <= 0:
            print("  Please enter a value greater than zero.")
            continue
        return value


def _get_user_input() -> Any:
    """Interactively get pipeline configuration from user."""
    print()
    print("=" * 60)
    print("AI Photo Organizer - Pipeline Configuration")
    print("=" * 60)
    print()

    # Prompt 1: Dry run?
    dry_run = _prompt_yes_no("Run in dry-run mode (plan only, no changes)?")
    print()

    # Prompt 2: destructive face detection rebuild
    run_face_detection_rebuild = _prompt_yes_no_default_no("Run global face detection rebuild?")
    print()

    # Prompt 3: destructive face clustering rebuild
    run_face_clustering_rebuild = _prompt_yes_no_default_no("Run global face clustering rebuild?")
    print()

    # Prompt 4: skip incremental face processing
    skip_face_processing = _prompt_yes_no_default_no("Skip incremental face processing stages?")
    print()

    # Prompt 5: Source folder to ingest
    source_path = input("Source folder to ingest (leave blank for existing drop zone): ").strip()
    from_path = None
    source_label = None
    source_type = None
    if source_path:
        from_path = Path(source_path).expanduser().resolve()
        if not from_path.exists():
            print(f"  Warning: Path does not exist: {from_path}")
        source_label = input(
            "Source label for this ingestion run? (examples: Chuck PC, External Drive 1, iCloud Export): "
        ).strip()
        source_type = "local_folder"
    print()

    ingest_batch_size = _prompt_int_default(
        "Batch size for Drop Zone files per run?",
        settings.ingest_batch_size,
    )
    print()

    ingest_total_limit = None

    confirmation_value = _maybe_confirm_rebuild_interactive(
        run_face_detection_rebuild or run_face_clustering_rebuild
    )
    _validate_rebuild_confirmation(
        run_face_detection_rebuild=run_face_detection_rebuild,
        run_face_clustering_rebuild=run_face_clustering_rebuild,
        confirmation_value=confirmation_value,
    )
    _validate_ingest_controls(ingest_batch_size, ingest_total_limit)

    return _build_runtime_args(
        dry_run=dry_run,
        from_path=from_path,
        skip_exif_extraction=False,
        skip_metadata_normalization=False,
        skip_duplicate_lineage=False,
        skip_event_clustering=False,
        skip_face_processing=skip_face_processing,
        skip_crop_generation=False,
        run_face_detection_rebuild=run_face_detection_rebuild,
        run_face_clustering_rebuild=run_face_clustering_rebuild,
        run_crop_generation_override=False,
        ingest_batch_size=ingest_batch_size,
        ingest_total_limit=ingest_total_limit,
        source_label=source_label,
        source_type=source_type,
    )


def _get_cli_input(parsed: argparse.Namespace) -> RuntimeArgs:
    """Build runtime args from CLI flags."""
    from_path = parsed.from_path.expanduser().resolve() if parsed.from_path else None

    _validate_rebuild_confirmation(
        run_face_detection_rebuild=parsed.run_face_detection_rebuild,
        run_face_clustering_rebuild=parsed.run_face_clustering_rebuild,
        confirmation_value=parsed.confirm_rebuild,
    )
    ingest_batch_size = parsed.ingest_batch_size or settings.ingest_batch_size
    ingest_total_limit = parsed.ingest_total_limit if parsed.ingest_total_limit is not None else settings.ingest_total_limit
    if from_path is None and parsed.source_type and not parsed.source_label:
        raise ValueError("--source-type requires --source-label when --from-path is not provided.")
    _validate_ingest_controls(ingest_batch_size, ingest_total_limit)

    return _build_runtime_args(
        dry_run=parsed.dry_run,
        from_path=from_path,
        skip_exif_extraction=parsed.skip_exif_extraction,
        skip_metadata_normalization=parsed.skip_metadata_normalization,
        skip_duplicate_lineage=parsed.skip_duplicate_lineage,
        skip_event_clustering=parsed.skip_event_clustering,
        skip_face_processing=parsed.skip_face_processing,
        skip_crop_generation=parsed.skip_crop_generation,
        run_face_detection_rebuild=parsed.run_face_detection_rebuild,
        run_face_clustering_rebuild=parsed.run_face_clustering_rebuild,
        run_crop_generation_override=parsed.run_crop_generation,
        ingest_batch_size=ingest_batch_size,
        ingest_total_limit=ingest_total_limit,
        source_label=parsed.source_label,
        source_type=parsed.source_type,
    )


def _collect_input(ctx: PipelineContext) -> dict[str, Any]:
    if ctx.from_path is not None:
        existing_dropzone_scan = scan_folder(ctx.drop_zone_path)
        if existing_dropzone_scan.files:
            raise RuntimeError(
                "Drop Zone already contains an active batch. Process or clear it before using --from-path."
            )

        source_scan_result = scan_folder(ctx.from_path)
        selected_source_records = list(source_scan_result.files[: ctx.ingest_batch_size])
        stage_result = stage_source_records_to_dropzone(
            selected_source_records,
            ctx.drop_zone_path,
            ctx.quarantine_path,
        )
        dropzone_scan_result = scan_folder(ctx.drop_zone_path)
        processing_records = build_dropzone_processing_records(
            dropzone_scan_result.files,
            stage_result.staged_files,
        )

        ctx.source_scan_result = source_scan_result
        ctx.source_selected_records = selected_source_records
        ctx.stage_result = stage_result
        ctx.dropzone_scan_result = dropzone_scan_result
        ctx.processing_records = processing_records

        return {
            "scope": "batch",
            "input_mode": "from-path via drop zone staging",
            "source_path": str(ctx.from_path),
            "source_files_scanned": len(source_scan_result.files),
            "source_scan_errors": len(source_scan_result.errors),
            "source_files_selected_for_batch": len(selected_source_records),
            "source_files_deferred": max(0, len(source_scan_result.files) - len(selected_source_records)),
            "files_staged": len(stage_result.staged_files),
            "stage_failures": len(stage_result.failures),
            "drop_zone_records_total": len(dropzone_scan_result.files),
            "drop_zone_records_frozen": len(processing_records),
        }

    dropzone_scan_result = scan_folder(ctx.drop_zone_path)
    ctx.dropzone_scan_result = dropzone_scan_result
    ctx.processing_records = dropzone_scan_result.files

    return {
        "scope": "batch",
        "input_mode": "existing drop zone contents",
        "drop_zone_path": str(ctx.drop_zone_path),
        "drop_zone_records_frozen": len(dropzone_scan_result.files),
        "drop_zone_scan_errors": len(dropzone_scan_result.errors),
    }


def _load_known_asset_sha256(ctx: PipelineContext) -> None:
    db_session = SessionLocal()
    try:
        ctx.known_asset_sha256 = set(db_session.scalars(select(Asset.sha256)).all())
    finally:
        db_session.close()


def _load_assets_by_sha256(asset_sha256_list: list[str]) -> list[Asset]:
    if not asset_sha256_list:
        return []

    order = {sha256: index for index, sha256 in enumerate(asset_sha256_list)}
    db_session = SessionLocal()
    try:
        assets = list(
            db_session.scalars(select(Asset).where(Asset.sha256.in_(asset_sha256_list))).all()
        )
    finally:
        db_session.close()

    assets.sort(key=lambda asset: order.get(asset.sha256, len(order)))
    return assets


def _load_place_ids_for_assets(asset_sha256_list: list[str]) -> list[int]:
    if not asset_sha256_list:
        return []

    db_session = SessionLocal()
    try:
        rows = db_session.execute(
            select(Asset.place_id)
            .where(
                Asset.sha256.in_(dict.fromkeys(asset_sha256_list)),
                Asset.place_id.is_not(None),
            )
            .order_by(Asset.created_at_utc.asc(), Asset.sha256.asc())
        ).all()
    finally:
        db_session.close()

    return [int(row.place_id) for row in rows if row.place_id is not None]


def _remaining_new_asset_slots(ctx: PipelineContext) -> int | None:
    if ctx.ingest_total_limit is None:
        return None
    return max(0, ctx.ingest_total_limit - ctx.total_new_unique_ingested)


def _select_next_batch(ctx: PipelineContext) -> IngestionBatch | None:
    if not ctx.processing_records:
        return None

    batch_records = list(ctx.processing_records[: ctx.ingest_batch_size])
    accepted: list[FileScanRecord] = []
    rejected = []
    hashed_files: list[HashedFile] = []
    hash_errors = []
    unique_files: list[HashedFile] = []
    duplicate_files: list[DuplicateFile] = []
    seen_sha256_in_batch: dict[str, HashedFile] = {}
    prospective_new_unique = 0

    for record in batch_records:
        single_filter_result = filter_records(
            [record],
            approved_extensions=settings.approved_extensions,
            min_size_bytes=settings.minimum_file_size_bytes,
        )
        accepted.extend(single_filter_result.accepted)
        rejected.extend(single_filter_result.rejected)

        if not single_filter_result.accepted:
            continue

        single_hash_result = hash_records(single_filter_result.accepted)
        hashed_files.extend(single_hash_result.hashed_files)
        hash_errors.extend(single_hash_result.errors)

        for hashed_file in single_hash_result.hashed_files:
            original = seen_sha256_in_batch.get(hashed_file.sha256)
            if original is not None:
                duplicate_files.append(DuplicateFile(duplicate=hashed_file, original=original))
                continue

            seen_sha256_in_batch[hashed_file.sha256] = hashed_file
            unique_files.append(hashed_file)
            if hashed_file.sha256 not in ctx.known_asset_sha256:
                prospective_new_unique += 1

    return IngestionBatch(
        records=batch_records,
        filter_result=FilterResult(accepted=accepted, rejected=rejected),
        hash_result=HashResult(hashed_files=hashed_files, errors=hash_errors),
        dedup_result=DeduplicationResult(unique_files=unique_files, duplicate_files=duplicate_files),
        prospective_new_unique=prospective_new_unique,
    )


def _remove_vault_copy_for_failed_insert(destination_path: str) -> None:
    path = Path(destination_path)
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def _resolve_failure_source_root(ctx: PipelineContext) -> Path | None:
    if ctx.from_path is None:
        return None
    return ctx.from_path.expanduser().resolve()


def _move_failed_batch_records(ctx: PipelineContext) -> tuple[int, list[str]]:
    failed_records_by_path: dict[str, tuple[FileScanRecord, str]] = {}
    failed_moves: list[str] = []

    if ctx.filter_result is not None:
        for item in ctx.filter_result.rejected:
            failed_records_by_path[item.record.full_path] = (item.record, item.reason)
    if ctx.hash_result is not None:
        for item in ctx.hash_result.errors:
            failed_records_by_path[item.record.full_path] = (item.record, item.reason)
    if ctx.storage_result is not None:
        for item in ctx.storage_result.failed_files:
            failed_records_by_path[item.hashed_file.record.full_path] = (item.hashed_file.record, item.reason)
    if ctx.persistence_result is not None:
        for item in ctx.persistence_result.failed_inserts:
            failed_records_by_path[item.copied_file.hashed_file.record.full_path] = (
                item.copied_file.hashed_file.record,
                item.reason,
            )
            if item.should_remove_vault_copy:
                _remove_vault_copy_for_failed_insert(item.copied_file.destination_path)
    if ctx.duplicate_provenance_result is not None:
        for item, _ in ctx.duplicate_provenance_result.failed_duplicates:
            failed_records_by_path[item.duplicate.record.full_path] = (
                item.duplicate.record,
                "duplicate_provenance_persist_failed",
            )

    moved = 0
    moved_entries: list[dict[str, str]] = []
    failure_source_root = _resolve_failure_source_root(ctx)
    for raw_path in sorted(failed_records_by_path):
        record, reason = failed_records_by_path[raw_path]
        try:
            moved_target = move_record_to_ingest_failures(
                record,
                ctx.ingest_failures_path,
                source_root=failure_source_root,
            )
            moved += 1
            moved_entries.append(
                {
                    "source_path": raw_path,
                    "moved_to": moved_target,
                    "reason": reason,
                }
            )
        except FileNotFoundError:
            moved += 1
            moved_entries.append(
                {
                    "source_path": raw_path,
                    "moved_to": "already_missing",
                    "reason": reason,
                }
            )
        except OSError:
            failed_moves.append(raw_path)

    ctx.moved_to_ingest_failures = moved_entries
    ctx.failed_move_paths = failed_moves
    return moved, failed_moves


def _filter_records_stage(ctx: PipelineContext) -> dict[str, Any]:
    if ctx.filter_result is None:
        raise RuntimeError("Batch filter result missing.")
    result = ctx.filter_result
    return {
        "scope": "batch",
        "records_considered": len(ctx.current_batch_records),
        "accepted": len(result.accepted),
        "rejected": len(result.rejected),
        "approved_extensions": len(settings.approved_extensions),
        "minimum_size_bytes": settings.minimum_file_size_bytes,
    }


def _hash_stage(ctx: PipelineContext) -> dict[str, Any]:
    if ctx.hash_result is None:
        raise RuntimeError("Batch hash result missing.")
    result = ctx.hash_result
    return {
        "scope": "batch",
        "hashed": len(result.hashed_files),
        "hash_errors": len(result.errors),
    }


def _deduplicate_stage(ctx: PipelineContext) -> dict[str, Any]:
    if ctx.dedup_result is None:
        raise RuntimeError("Batch dedup result missing.")
    result = ctx.dedup_result
    return {
        "scope": "batch",
        "unique": len(result.unique_files),
        "duplicates": len(result.duplicate_files),
        "new_unique_candidates": sum(1 for item in result.unique_files if item.sha256 not in ctx.known_asset_sha256),
    }


def _storage_stage(ctx: PipelineContext) -> dict[str, Any]:
    if ctx.dedup_result is None:
        raise RuntimeError("Deduplication stage must run before storage.")

    result = copy_unique_files_to_vault(ctx.dedup_result, ctx.vault_path)
    ctx.storage_result = result
    return {
        "scope": "batch",
        "copied_to_vault": len(result.copied_files),
        "copy_failures": len(result.failed_files),
        "vault_path": str(ctx.vault_path),
    }


def _ingest_to_db_stage(ctx: PipelineContext) -> dict[str, Any]:
    if ctx.storage_result is None:
        raise RuntimeError("Storage stage must run before DB ingestion.")

    provenance_context = None
    if ctx.resolved_ingestion_context is not None:
        provenance_context = ProvenanceContext(
            ingestion_source_id=ctx.resolved_ingestion_context.ingestion_source_id,
            ingestion_run_id=ctx.resolved_ingestion_context.ingestion_run_id,
            source_label=ctx.resolved_ingestion_context.source_label,
            source_type=ctx.resolved_ingestion_context.source_type,
            source_root_path=ctx.resolved_ingestion_context.source_root_path,
        )

    db_session = SessionLocal()
    try:
        result = persist_copied_files(
            db_session,
            ctx.storage_result.copied_files,
            provenance_context=provenance_context,
        )
        duplicate_provenance_result = (
            persist_duplicate_provenance(
                db_session,
                ctx.dedup_result.duplicate_files,
                provenance_context=provenance_context,
            )
            if ctx.dedup_result is not None
            else None
        )
    finally:
        db_session.close()

    ctx.persistence_result = result
    ctx.duplicate_provenance_result = duplicate_provenance_result
    ctx.current_batch_new_asset_sha256 = [
        item.copied_file.hashed_file.sha256
        for item in result.inserted_records
    ]
    ctx.total_new_unique_ingested += len(result.inserted_records)
    ctx.total_existing_or_duplicate_processed += len(result.skipped_existing_records)
    if duplicate_provenance_result is not None:
        ctx.total_existing_or_duplicate_processed += (
            duplicate_provenance_result.added + duplicate_provenance_result.already_present
        )
    ctx.known_asset_sha256.update(ctx.current_batch_new_asset_sha256)

    return {
        "scope": "batch",
        "inserted": len(result.inserted_records),
        "skipped_existing": len(result.skipped_existing_records),
        "db_failures": len(result.failed_inserts),
        "duplicate_provenance_added": duplicate_provenance_result.added if duplicate_provenance_result else 0,
        "duplicate_provenance_existing": duplicate_provenance_result.already_present if duplicate_provenance_result else 0,
        "duplicate_provenance_failed": duplicate_provenance_result.failed if duplicate_provenance_result else 0,
    }


def _cleanup_drop_zone_stage(ctx: PipelineContext) -> dict[str, Any]:
    if ctx.persistence_result is None:
        raise RuntimeError("DB ingestion must complete before drop zone cleanup.")

    successful_paths: set[str] = set()
    failed_cleanup: list[str] = []

    for item in ctx.persistence_result.inserted_records:
        successful_paths.add(item.copied_file.hashed_file.record.full_path)
    for item in ctx.persistence_result.skipped_existing_records:
        successful_paths.add(item.copied_file.hashed_file.record.full_path)
    if ctx.duplicate_provenance_result is not None:
        for item in ctx.duplicate_provenance_result.successful_duplicates:
            successful_paths.add(item.duplicate.record.full_path)

    cleaned = 0
    cleaned_paths: list[str] = []
    for raw_path in sorted(successful_paths):
        try:
            Path(raw_path).unlink(missing_ok=False)
            cleaned += 1
            cleaned_paths.append(raw_path)
        except FileNotFoundError:
            cleaned += 1
            cleaned_paths.append(raw_path)
        except OSError:
            failed_cleanup.append(raw_path)

    failed_moved, failed_move_errors = _move_failed_batch_records(ctx)

    ctx.total_dropzone_files_cleaned += cleaned
    ctx.cleaned_dropzone_paths = cleaned_paths
    remaining_selected_paths = 0
    for record in ctx.current_batch_records:
        if Path(record.full_path).exists():
            remaining_selected_paths += 1

    return {
        "scope": "batch",
        "cleaned_files": cleaned,
        "failed_files_relocated": failed_moved,
        "cleanup_failures": len(failed_cleanup) + len(failed_move_errors),
        "left_in_drop_zone": remaining_selected_paths,
    }


def _build_ingestion_run_manifest(
    ctx: PipelineContext,
    outcomes: list[StageOutcome],
    total_elapsed_seconds: float,
    status: str,
) -> dict[str, Any]:
    selected_from_source = [record.full_path for record in ctx.source_selected_records]
    staged_into_drop_zone = [item.dropzone_path for item in (ctx.stage_result.staged_files if ctx.stage_result else [])]
    frozen_for_processing = [record.full_path for record in ctx.processing_records]

    inserted_sources = [
        item.copied_file.hashed_file.record.original_source_path
        for item in (ctx.persistence_result.inserted_records if ctx.persistence_result else [])
    ]
    existing_sources = [
        item.copied_file.hashed_file.record.original_source_path
        for item in (ctx.persistence_result.skipped_existing_records if ctx.persistence_result else [])
    ]
    duplicate_sources = [
        item.duplicate.record.original_source_path
        for item in (
            ctx.duplicate_provenance_result.successful_duplicates
            if ctx.duplicate_provenance_result is not None
            else []
        )
    ]

    persisted_unique = sorted(
        {
            *inserted_sources,
            *existing_sources,
            *duplicate_sources,
        }
    )

    failures_with_reasons: list[dict[str, str]] = []
    if ctx.stage_result is not None:
        failures_with_reasons.extend(
            {
                "source_path": item.source_record.full_path,
                "reason": item.reason,
                "phase": "staging",
            }
            for item in ctx.stage_result.failures
        )
    if ctx.filter_result is not None:
        failures_with_reasons.extend(
            {
                "source_path": item.record.full_path,
                "reason": item.reason,
                "phase": "filter",
            }
            for item in ctx.filter_result.rejected
        )
    if ctx.hash_result is not None:
        failures_with_reasons.extend(
            {
                "source_path": item.record.full_path,
                "reason": item.reason,
                "phase": "hash",
            }
            for item in ctx.hash_result.errors
        )
    if ctx.storage_result is not None:
        failures_with_reasons.extend(
            {
                "source_path": item.hashed_file.record.full_path,
                "reason": item.reason,
                "phase": "storage",
            }
            for item in ctx.storage_result.failed_files
        )
    if ctx.persistence_result is not None:
        failures_with_reasons.extend(
            {
                "source_path": item.copied_file.hashed_file.record.full_path,
                "reason": item.reason,
                "phase": "persistence",
            }
            for item in ctx.persistence_result.failed_inserts
        )
    if ctx.duplicate_provenance_result is not None:
        failures_with_reasons.extend(
            {
                "source_path": item.duplicate.record.full_path,
                "reason": reason,
                "phase": "duplicate_provenance",
            }
            for item, reason in ctx.duplicate_provenance_result.failed_duplicates
        )

    return {
        "run_metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "elapsed_seconds": round(total_elapsed_seconds, 3),
            "source_path": str(ctx.from_path) if ctx.from_path is not None else None,
            "drop_zone_path": str(ctx.drop_zone_path),
            "ingest_failures_path": str(ctx.ingest_failures_path),
            "ingest_batch_size": ctx.ingest_batch_size,
            "ingestion_run_id": (
                ctx.resolved_ingestion_context.ingestion_run_id
                if ctx.resolved_ingestion_context is not None
                else None
            ),
            "ingestion_source_id": (
                ctx.resolved_ingestion_context.ingestion_source_id
                if ctx.resolved_ingestion_context is not None
                else None
            ),
        },
        "files": {
            "selected_from_source": selected_from_source,
            "staged_into_drop_zone": staged_into_drop_zone,
            "frozen_for_processing": frozen_for_processing,
            "successfully_persisted": persisted_unique,
            "cleaned_from_drop_zone": list(ctx.cleaned_dropzone_paths),
            "moved_to_ingest_failures": list(ctx.moved_to_ingest_failures),
            "failed_to_move_to_ingest_failures": list(ctx.failed_move_paths),
        },
        "failures_with_reasons": failures_with_reasons,
        "counts": {
            "source_files_scanned": len(ctx.source_scan_result.files) if ctx.source_scan_result is not None else None,
            "source_files_selected_for_batch": len(selected_from_source),
            "files_staged": len(staged_into_drop_zone),
            "files_frozen": len(frozen_for_processing),
            "files_successfully_persisted": len(persisted_unique),
            "files_cleaned_from_drop_zone": len(ctx.cleaned_dropzone_paths),
            "files_moved_to_ingest_failures": len(ctx.moved_to_ingest_failures),
            "failed_to_move_to_ingest_failures": len(ctx.failed_move_paths),
            "stage_outcomes": [
                {
                    "key": outcome.key,
                    "label": outcome.label,
                    "status": outcome.status,
                    "elapsed_seconds": round(outcome.elapsed_seconds, 3),
                    "error": outcome.error,
                    "skip_reason": outcome.skip_reason,
                    "summary": outcome.summary,
                }
                for outcome in outcomes
            ],
        },
    }


def _write_ingestion_run_manifest(
    ctx: PipelineContext,
    outcomes: list[StageOutcome],
    total_elapsed_seconds: float,
    status: str,
) -> Path | None:
    manifest_root = _resolve_runtime_path("../storage/logs/ingestion_manifests")
    manifest_root.mkdir(parents=True, exist_ok=True)

    run_id = (
        str(ctx.resolved_ingestion_context.ingestion_run_id)
        if ctx.resolved_ingestion_context is not None
        else datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    )
    manifest_path = manifest_root / f"ingestion_run_{run_id}.json"

    manifest_payload = _build_ingestion_run_manifest(
        ctx,
        outcomes,
        total_elapsed_seconds,
        status,
    )
    manifest_path.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")
    ctx.manifest_path = manifest_path
    return manifest_path


def _exif_extraction_stage(ctx: PipelineContext) -> dict[str, Any]:
    from app.services.metadata.exif_extractor import extract_exif_for_assets
    from app.services.metadata.exif_persistence import persist_exif_updates

    assets = _load_assets_by_sha256(ctx.current_batch_new_asset_sha256)
    if not assets:
        return {
            "scope": "batch",
            "assets_checked": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
        }

    db_session = SessionLocal()
    try:
        extraction_result = extract_exif_for_assets(assets)
        persistence_result = persist_exif_updates(db_session, extraction_result.extracted)
    finally:
        db_session.close()

    return {
        "scope": "batch",
        "assets_checked": len(assets),
        "updated": len(persistence_result.updated_assets),
        "skipped": len(extraction_result.skipped) + len(persistence_result.skipped_assets),
        "failed": len(extraction_result.failed) + len(persistence_result.failed_assets),
    }


def _metadata_normalization_stage(ctx: PipelineContext) -> dict[str, Any]:
    from app.services.metadata.metadata_normalizer import normalize_assets, persist_normalized_metadata

    assets = _load_assets_by_sha256(ctx.current_batch_new_asset_sha256)
    if not assets:
        return {
            "scope": "batch",
            "assets_processed": 0,
            "updated_records": 0,
            "scans_detected": 0,
            "low_trust_dates": 0,
            "failed": 0,
        }

    db_session = SessionLocal()
    try:
        normalization_result = normalize_assets(assets)
        persistence_result = persist_normalized_metadata(db_session, normalization_result.updated_records)
    finally:
        db_session.close()

    scans_detected = sum(1 for item in normalization_result.updated_records if item.capture_type == "scan")
    low_trust_dates = sum(1 for item in normalization_result.updated_records if item.capture_time_trust == "low")

    return {
        "scope": "batch",
        "assets_processed": len(assets),
        "updated_records": len(persistence_result.updated_records),
        "scans_detected": scans_detected,
        "low_trust_dates": low_trust_dates,
        "failed": len(normalization_result.failed_records) + len(persistence_result.failed_records),
    }


def _metadata_observation_and_canonicalization_stage(ctx: PipelineContext) -> dict[str, Any]:
    if ctx.persistence_result is None:
        raise RuntimeError("DB ingestion must complete before metadata observation stage.")

    inserted_records = ctx.persistence_result.inserted_records
    duplicate_files = (
        ctx.duplicate_provenance_result.successful_duplicates
        if ctx.duplicate_provenance_result is not None
        else []
    )
    if not inserted_records and not duplicate_files:
        return {
            "scope": "batch",
            "observations_inserted": 0,
            "observations_skipped": 0,
            "observations_failed": 0,
            "assets_canonical_processed": 0,
            "assets_canonical_updated": 0,
            "assets_canonical_failed": 0,
        }

    provenance_context = None
    if ctx.resolved_ingestion_context is not None:
        provenance_context = ProvenanceContext(
            ingestion_source_id=ctx.resolved_ingestion_context.ingestion_source_id,
            ingestion_run_id=ctx.resolved_ingestion_context.ingestion_run_id,
            source_label=ctx.resolved_ingestion_context.source_label,
            source_type=ctx.resolved_ingestion_context.source_type,
            source_root_path=ctx.resolved_ingestion_context.source_root_path,
        )

    db_session = SessionLocal()
    try:
        ingest_summary = create_ingest_observations_for_batch(
            db_session,
            inserted_records=inserted_records,
            duplicate_files=duplicate_files,
            provenance_context=provenance_context,
        )
        canonical_summary = recompute_canonical_metadata_for_assets(
            db_session,
            ingest_summary.affected_asset_sha256,
        )
    finally:
        db_session.close()

    return {
        "scope": "batch",
        "observations_inserted": ingest_summary.inserted,
        "observations_skipped": ingest_summary.skipped,
        "observations_failed": ingest_summary.failed,
        "assets_canonical_processed": canonical_summary.processed,
        "assets_canonical_updated": canonical_summary.updated,
        "assets_canonical_failed": canonical_summary.failed,
    }


def _event_clustering_stage(ctx: PipelineContext) -> dict[str, Any]:
    from app.services.organization.event_clusterer import cluster_assets_into_events, persist_event_clusters

    if ctx.total_new_unique_ingested == 0:
        return {
            "scope": "global",
            "mode": "intentional_global",
            "status": "skipped_no_new_assets",
            "assets_considered": 0,
            "assets_skipped_scans": 0,
            "events_created": 0,
            "assigned_assets": 0,
        }

    db_session = SessionLocal()
    try:
        clustering_result = cluster_assets_into_events(
            db_session=db_session,
            gap_seconds=settings.event_cluster_gap_seconds,
        )
        persistence_result = persist_event_clusters(db_session, clustering_result)
    finally:
        db_session.close()

    return {
        "scope": "global",
        "mode": "intentional_global",
        "assets_considered": clustering_result.considered_assets,
        "assets_skipped_scans": clustering_result.skipped_scans,
        "events_created": persistence_result.events_created,
        "assigned_assets": persistence_result.assigned_assets,
    }


def _place_grouping_stage(ctx: PipelineContext) -> dict[str, Any]:
    db_session = SessionLocal()
    try:
        summary = assign_assets_to_places(
            db_session,
            asset_sha256_list=ctx.current_batch_new_asset_sha256,
        )
    finally:
        db_session.close()

    return {
        "scope": "batch",
        "assets_considered": summary.considered_assets,
        "assigned_assets": summary.assigned_assets,
        "created_places": summary.created_places,
        "matched_existing_places": summary.matched_existing_places,
        "skipped_without_gps": summary.skipped_without_gps,
        "skipped_already_assigned": summary.skipped_already_assigned,
        "skipped_invalid_gps": summary.skipped_invalid_gps,
    }


def _place_geocoding_stage(ctx: PipelineContext) -> dict[str, Any]:
    place_ids = _load_place_ids_for_assets(ctx.current_batch_new_asset_sha256)

    db_session = SessionLocal()
    try:
        total_candidate_places = (
            db_session.query(Place)
            .filter(Place.place_id.in_(place_ids), Place.geocode_status == "never_tried")
            .count()
            if place_ids
            else 0
        )
        summary = enrich_places_with_reverse_geocoding(
            db_session,
            place_ids=place_ids,
            include_failed=False,
            max_calls=settings.place_geocode_max_calls_per_run,
        )
    finally:
        db_session.close()

    return {
        "scope": "batch",
        "candidate_places": total_candidate_places,
        "eligible_places": summary.eligible_places,
        "attempted_calls": summary.attempted_calls,
        "successful": summary.successful,
        "failed": summary.failed,
        "skipped_due_to_cap": summary.skipped_due_to_cap,
        "max_calls_per_run": settings.place_geocode_max_calls_per_run,
    }


def _duplicate_lineage_stage(ctx: PipelineContext) -> dict[str, Any]:
    from app.services.duplicates.lineage import update_lineage_for_assets

    db_session = SessionLocal()
    try:
        summary = update_lineage_for_assets(db_session, ctx.current_batch_new_asset_sha256, dry_run=False)
    finally:
        db_session.close()

    return {
        "scope": "batch",
        "assets_processed": summary.processed,
        "assets_updated": summary.updated,
        "assets_skipped": summary.skipped,
        "failed": summary.failed,
    }


def _face_schema_sync_stage(_: PipelineContext) -> dict[str, Any]:
    from app.services.vision.face_incremental_schema import ensure_face_incremental_schema

    db_session = SessionLocal()
    try:
        summary = ensure_face_incremental_schema(db_session)
    finally:
        db_session.close()

    return {
        "scope": "global",
        "added_columns": len(summary.added_columns),
        "added_indexes": len(summary.added_indexes),
        "backfilled_detection_completed": summary.backfilled_asset_detection_completed,
        "backfilled_reviewed_clusters": summary.backfilled_reviewed_clusters,
    }


def _ingestion_context_schema_sync_stage(_: PipelineContext) -> dict[str, Any]:
    db_session = SessionLocal()
    try:
        summary = ensure_ingestion_context_schema(db_session)
    finally:
        db_session.close()

    return {
        "scope": "global",
        "added_tables": len(summary.added_tables),
        "added_columns": len(summary.added_columns),
        "added_indexes": len(summary.added_indexes),
        "constraints_added": len(summary.added_constraints),
        "constraints_dropped": len(summary.dropped_constraints),
    }


def _metadata_canonicalization_schema_sync_stage(_: PipelineContext) -> dict[str, Any]:
    db_session = SessionLocal()
    try:
        summary = ensure_metadata_canonicalization_schema(db_session)
    finally:
        db_session.close()

    return {
        "scope": "global",
        "added_tables": len(summary.ensured_tables),
        "added_columns": len(summary.added_columns),
    }


def _place_schema_sync_stage(_: PipelineContext) -> dict[str, Any]:
    db_session = SessionLocal()
    try:
        summary = ensure_place_schema(db_session)
    finally:
        db_session.close()

    return {
        "scope": "global",
        "added_tables": len(summary.created_tables),
        "added_columns": len(summary.added_columns),
        "added_indexes": len(summary.created_indexes),
    }


def _resolve_ingestion_context_stage(ctx: PipelineContext) -> dict[str, Any]:
    db_session = SessionLocal()
    try:
        resolved = resolve_ingestion_context(
            db_session,
            from_path=ctx.from_path,
            source_label=ctx.source_label,
            source_type=ctx.source_type,
        )
    finally:
        db_session.close()

    ctx.resolved_ingestion_context = resolved
    if resolved is None:
        return {
            "scope": "global",
            "status": "not_set",
            "reason": "no_source_context_requested",
        }

    return {
        "scope": "global",
        "ingestion_source_id": resolved.ingestion_source_id,
        "ingestion_run_id": resolved.ingestion_run_id,
        "source_label": resolved.source_label,
        "source_type": resolved.source_type,
        "source_root_path": resolved.source_root_path,
    }


def _face_detection_stage(ctx: PipelineContext) -> dict[str, Any]:
    from app.services.vision.face_detector import (
        YuNetFaceDetector,
        load_assets_for_incremental_face_detection,
        persist_face_detections_rebuild,
        persist_incremental_face_detections,
        run_face_detection,
    )

    # Resolve model path relative to BACKEND_ROOT if it's relative
    model_path = settings.face_detector_model_path
    if not Path(model_path).is_absolute():
        model_path = str(_resolve_runtime_path(model_path))

    detector = YuNetFaceDetector(
        model_path=model_path,
        score_threshold=settings.face_detection_confidence_threshold,
    )

    db_session = SessionLocal()
    try:
        if ctx.run_face_detection_rebuild:
            assets = list(db_session.scalars(select(Asset)).all())
        else:
            assets = list(
                db_session.scalars(
                    select(Asset)
                    .where(Asset.sha256.in_(ctx.current_batch_new_asset_sha256))
                    .order_by(Asset.created_at_utc.asc(), Asset.sha256.asc())
                ).all()
            )

        detection_result = run_face_detection(
            assets=assets,
            detector=detector,
            target_longest_side=settings.face_detection_resize_longest_side,
        )

        if ctx.run_face_detection_rebuild:
            persistence_result = persist_face_detections_rebuild(
                db_session,
                detection_result.detections,
                detection_result.successful_asset_sha256,
            )
        else:
            persistence_result = persist_incremental_face_detections(
                db_session,
                detection_result.detections,
                detection_result.successful_asset_sha256,
            )
    finally:
        db_session.close()

    return {
        "scope": "global" if ctx.run_face_detection_rebuild else "batch",
        "mode": "rebuild" if ctx.run_face_detection_rebuild else "incremental",
        "assets_processed": detection_result.total_assets_processed,
        "assets_failed": len(detection_result.failed_asset_sha256),
        "faces_detected": detection_result.total_faces_detected,
        "inserted_faces": persistence_result.inserted_faces,
        "assets_marked_detection_complete": persistence_result.assets_marked_detection_complete,
        "failed": persistence_result.failed,
    }


def _face_clustering_stage(ctx: PipelineContext) -> dict[str, Any]:
    from app.services.vision.face_clusterer import (
        assign_selected_faces_incrementally,
        assign_faces_incrementally,
        cluster_face_embeddings,
        load_faces_for_embedding,
        persist_face_clusters,
    )
    from app.services.vision.face_embedder import (
        generate_face_embeddings,
        load_faces_missing_embeddings,
        persist_generated_embeddings,
    )

    db_session = SessionLocal()
    try:
        if ctx.run_face_clustering_rebuild:
            face_asset_rows = load_faces_for_embedding(db_session)
        else:
            face_asset_rows = [
                (row[0], row[1])
                for row in db_session.execute(
                    select(Face, Asset)
                    .join(Asset, Asset.sha256 == Face.asset_sha256)
                    .where(Face.embedding_json.is_(None), Face.asset_sha256.in_(ctx.current_batch_new_asset_sha256))
                    .order_by(Face.id.asc())
                ).all()
            ]

        embedding_result = generate_face_embeddings(
            face_asset_rows=face_asset_rows,
            model_name=settings.face_embedding_model,
            margin_ratio=settings.face_embedding_crop_margin_ratio,
        )
        embeddings_persisted = persist_generated_embeddings(db_session, embedding_result.embedding_items)

        if ctx.run_face_clustering_rebuild:
            clustering_result = cluster_face_embeddings(
                embedding_items=embedding_result.embedding_items,
                similarity_threshold=settings.face_cluster_similarity_threshold,
            )
            persistence_result = persist_face_clusters(db_session, clustering_result)
            assignment_summary = None
        else:
            faces_to_assign = list(
                db_session.scalars(
                    select(Face)
                    .where(
                        Face.cluster_id.is_(None),
                        Face.embedding_json.is_not(None),
                        Face.asset_sha256.in_(ctx.current_batch_new_asset_sha256),
                    )
                    .order_by(Face.id.asc())
                ).all()
            )
            assignment_summary = assign_selected_faces_incrementally(
                db_session,
                faces_to_assign=faces_to_assign,
                similarity_threshold=settings.face_cluster_similarity_threshold,
                ambiguity_margin=settings.face_cluster_ambiguity_margin,
            )
            clustering_result = None
            persistence_result = None
    finally:
        db_session.close()

    if ctx.run_face_clustering_rebuild:
        return {
            "scope": "global",
            "mode": "rebuild",
            "faces_in_db": len(face_asset_rows),
            "embeddings_generated": embedding_result.embedded_faces,
            "embeddings_persisted": embeddings_persisted,
            "clusters_created": clustering_result.clusters_created,
            "faces_assigned": persistence_result.faces_assigned,
            "failed": persistence_result.failed,
        }

    return {
        "scope": "batch",
        "mode": "incremental",
        "faces_needing_embeddings": len(face_asset_rows),
        "embeddings_generated": embedding_result.embedded_faces,
        "embeddings_persisted": embeddings_persisted,
        "faces_considered_for_assignment": assignment_summary.faces_considered if assignment_summary else 0,
        "assigned_to_existing_clusters": assignment_summary.assigned_to_existing_clusters if assignment_summary else 0,
        "new_clusters_created": assignment_summary.new_clusters_created if assignment_summary else 0,
        "invalid_embeddings_skipped": assignment_summary.invalid_embeddings_skipped if assignment_summary else 0,
        "failed": assignment_summary.failed if assignment_summary else 1,
    }


def _crop_generation_stage(_: PipelineContext) -> dict[str, Any]:
    command = [sys.executable, str(BACKEND_ROOT / "scripts" / "generate_missing_face_crops.py")]
    completed = subprocess.run(command, cwd=str(BACKEND_ROOT), check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Crop generation exited with code {completed.returncode}.")

    return {
        "scope": "global",
        "command": "generate_missing_face_crops.py",
        "status": "completed",
    }


def _print_dry_run(args: RuntimeArgs, ctx: PipelineContext) -> None:
    print("Pipeline dry-run")
    print(f"  Source mode: {'from-path' if ctx.from_path else 'existing drop zone'}")
    if ctx.from_path is not None:
        print(f"  Source path: {ctx.from_path}")
    if args.source_label:
        print(f"  Source label: {args.source_label}")
    if args.source_type:
        print(f"  Source type: {args.source_type}")
    print(f"  Drop zone path: {ctx.drop_zone_path}")
    print(f"  Vault path: {ctx.vault_path}")
    print(f"  Ingest failures path: {ctx.ingest_failures_path}")
    print(f"  Ingest batch size: {args.ingest_batch_size}")
    print()
    print("Planned stages:")
    print("  [1] RUN - collect input (scope=batch)")
    print("  [2] RUN - ingestion context schema sync (scope=global)")
    print("  [3] RUN - metadata canonicalization schema sync (scope=global)")
    print("  [4] RUN - place schema sync (scope=global)")
    print("  [5] RUN - ingestion context resolve (scope=global)")
    print("  [6] RUN - face schema sync (scope=global)")
    print("  [7] RUN - ingestion batches: filter, hash, deduplicate, storage, ingest, cleanup (scope=batch)")
    print(f"  [7] {'SKIP (--skip-exif-extraction)' if args.skip_exif_extraction else 'RUN'} - EXIF extraction (scope=batch)")
    print(f"  [8] {'SKIP (--skip-metadata-normalization)' if args.skip_metadata_normalization else 'RUN'} - metadata normalization (scope=batch)")
    print("  [9] RUN - metadata observations + canonicalization (scope=batch)")
    print("  [10] RUN - place grouping (scope=batch)")
    print("  [11] RUN - place geocoding enrichment (scope=batch)")
    print(f"  [12] {'SKIP (--skip-duplicate-lineage)' if args.skip_duplicate_lineage else 'RUN'} - duplicate lineage (scope=batch)")
    print(f"  [13] {'SKIP (--skip-face-processing)' if args.skip_face_processing else 'RUN'} - face detection + clustering (scope=batch unless rebuild)")
    print(f"  [14] {'SKIP (--skip-crop-generation)' if args.skip_crop_generation else 'RUN'} - review crop generation (scope=global)")
    print(f"  [15] {'SKIP (--skip-event-clustering)' if args.skip_event_clustering else 'RUN'} - event clustering (scope=global, intentional)")
    print()
    print("Status: DRY RUN")


def _execute_stage(
    *,
    key: str,
    index: int,
    total: int,
    label: str,
    runner,
    outcomes: list[StageOutcome],
) -> dict[str, Any]:
    _print_stage_header(index, total, label)
    started_at = time.perf_counter()
    try:
        summary = runner()
    except Exception as exc:  # noqa: BLE001
        elapsed_seconds = time.perf_counter() - started_at
        error = str(exc) or exc.__class__.__name__
        _print_stage_failed(elapsed_seconds, error)
        outcomes.append(
            StageOutcome(
                key=key,
                label=label,
                status="failed",
                elapsed_seconds=elapsed_seconds,
                error=error,
            )
        )
        raise

    elapsed_seconds = time.perf_counter() - started_at
    _print_stage_done(elapsed_seconds, summary)
    outcomes.append(
        StageOutcome(
            key=key,
            label=label,
            status="completed",
            elapsed_seconds=elapsed_seconds,
            summary=summary,
        )
    )
    return summary


def _skip_stage(*, key: str, index: int, total: int, label: str, reason: str, outcomes: list[StageOutcome]) -> None:
    _print_stage_skipped(index, total, label, reason)
    outcomes.append(
        StageOutcome(
            key=key,
            label=label,
            status="skipped",
            elapsed_seconds=0.0,
            skip_reason=reason,
        )
    )


def _run_batch_stages(ctx: PipelineContext, args: RuntimeArgs, outcomes: list[StageOutcome]) -> None:
    next_batch = _select_next_batch(ctx)
    if next_batch is None:
        return

    ctx.total_batches_run = 1
    ctx.current_batch_records = next_batch.records
    ctx.filter_result = next_batch.filter_result
    ctx.hash_result = next_batch.hash_result
    ctx.dedup_result = next_batch.dedup_result
    ctx.storage_result = None
    ctx.persistence_result = None
    ctx.duplicate_provenance_result = None
    ctx.current_batch_new_asset_sha256 = []

    batch_label_prefix = f"batch {ctx.total_batches_run}"
    _execute_stage(
        key=f"{batch_label_prefix}_filter",
        index=1,
        total=6,
        label=f"{batch_label_prefix}: filter records",
        runner=lambda: _filter_records_stage(ctx),
        outcomes=outcomes,
    )
    _execute_stage(
        key=f"{batch_label_prefix}_hash",
        index=2,
        total=6,
        label=f"{batch_label_prefix}: hash files",
        runner=lambda: _hash_stage(ctx),
        outcomes=outcomes,
    )
    _execute_stage(
        key=f"{batch_label_prefix}_deduplicate",
        index=3,
        total=6,
        label=f"{batch_label_prefix}: deduplicate files",
        runner=lambda: _deduplicate_stage(ctx),
        outcomes=outcomes,
    )
    _execute_stage(
        key=f"{batch_label_prefix}_storage",
        index=4,
        total=6,
        label=f"{batch_label_prefix}: store to vault",
        runner=lambda: _storage_stage(ctx),
        outcomes=outcomes,
    )
    _execute_stage(
        key=f"{batch_label_prefix}_ingest",
        index=5,
        total=6,
        label=f"{batch_label_prefix}: ingest to database",
        runner=lambda: _ingest_to_db_stage(ctx),
        outcomes=outcomes,
    )
    _execute_stage(
        key=f"{batch_label_prefix}_cleanup",
        index=6,
        total=6,
        label=f"{batch_label_prefix}: clean drop zone",
        runner=lambda: _cleanup_drop_zone_stage(ctx),
        outcomes=outcomes,
    )

    if args.skip_exif_extraction:
        _skip_stage(
            key=f"{batch_label_prefix}_exif",
            index=1,
            total=5,
            label=f"{batch_label_prefix}: EXIF extraction",
            reason="--skip-exif-extraction",
            outcomes=outcomes,
        )
    else:
        _execute_stage(
            key=f"{batch_label_prefix}_exif",
            index=1,
            total=5,
            label=f"{batch_label_prefix}: EXIF extraction",
            runner=lambda: _exif_extraction_stage(ctx),
            outcomes=outcomes,
        )

    if args.skip_metadata_normalization:
        _skip_stage(
            key=f"{batch_label_prefix}_metadata",
            index=2,
            total=5,
            label=f"{batch_label_prefix}: metadata normalization",
            reason="--skip-metadata-normalization",
            outcomes=outcomes,
        )
    else:
        _execute_stage(
            key=f"{batch_label_prefix}_metadata",
                index=2,
                total=5,
                label=f"{batch_label_prefix}: metadata normalization",
                runner=lambda: _metadata_normalization_stage(ctx),
                outcomes=outcomes,
            )

        _execute_stage(
            key=f"{batch_label_prefix}_metadata_canonicalization",
            index=3,
            total=7,
            label=f"{batch_label_prefix}: metadata observations + canonicalization",
            runner=lambda: _metadata_observation_and_canonicalization_stage(ctx),
            outcomes=outcomes,
        )

        _execute_stage(
            key=f"{batch_label_prefix}_place_grouping",
            index=4,
            total=7,
            label=f"{batch_label_prefix}: place grouping",
            runner=lambda: _place_grouping_stage(ctx),
            outcomes=outcomes,
        )

        _execute_stage(
            key=f"{batch_label_prefix}_place_geocoding",
            index=5,
            total=7,
            label=f"{batch_label_prefix}: place geocoding enrichment",
            runner=lambda: _place_geocoding_stage(ctx),
            outcomes=outcomes,
        )

        if args.skip_duplicate_lineage:
            _skip_stage(
                key=f"{batch_label_prefix}_lineage",
                index=6,
                total=7,
                label=f"{batch_label_prefix}: duplicate lineage",
                reason="--skip-duplicate-lineage",
                outcomes=outcomes,
            )
        else:
            _execute_stage(
                key=f"{batch_label_prefix}_lineage",
                index=6,
                total=7,
                label=f"{batch_label_prefix}: duplicate lineage",
                runner=lambda: _duplicate_lineage_stage(ctx),
                outcomes=outcomes,
            )

        if args.skip_face_processing:
            _skip_stage(
                key=f"{batch_label_prefix}_faces",
                index=7,
                total=7,
                label=f"{batch_label_prefix}: face detection + clustering",
                reason="--skip-face-processing",
                outcomes=outcomes,
            )
        else:
            _execute_stage(
                key=f"{batch_label_prefix}_face_detection",
                index=7,
                total=7,
                label=f"{batch_label_prefix}: face detection",
                runner=lambda: _face_detection_stage(ctx),
                outcomes=outcomes,
            )
            _execute_stage(
                key=f"{batch_label_prefix}_face_clustering",
                index=8,
                total=8,
                label=f"{batch_label_prefix}: face embedding + clustering",
                runner=lambda: _face_clustering_stage(ctx),
                outcomes=outcomes,
            )


def _run_pipeline(ctx: PipelineContext, args: RuntimeArgs) -> list[StageOutcome]:
    outcomes: list[StageOutcome] = []
    try:
        _execute_stage(
            key="collect_input",
            index=1,
            total=1,
            label="collect input",
            runner=lambda: _collect_input(ctx),
            outcomes=outcomes,
        )
        _execute_stage(
            key="ingestion_context_schema_sync",
            index=1,
            total=1,
            label="ingestion context schema sync",
            runner=lambda: _ingestion_context_schema_sync_stage(ctx),
            outcomes=outcomes,
        )
        _execute_stage(
            key="metadata_canonicalization_schema_sync",
            index=1,
            total=1,
            label="metadata canonicalization schema sync",
            runner=lambda: _metadata_canonicalization_schema_sync_stage(ctx),
            outcomes=outcomes,
        )
        _execute_stage(
            key="place_schema_sync",
            index=1,
            total=1,
            label="place schema sync",
            runner=lambda: _place_schema_sync_stage(ctx),
            outcomes=outcomes,
        )
        _execute_stage(
            key="ingestion_context_resolve",
            index=1,
            total=1,
            label="ingestion context resolve",
            runner=lambda: _resolve_ingestion_context_stage(ctx),
            outcomes=outcomes,
        )
        _load_known_asset_sha256(ctx)

        _execute_stage(
            key="face_schema_sync",
            index=1,
            total=1,
            label="face schema sync",
            runner=lambda: _face_schema_sync_stage(ctx),
            outcomes=outcomes,
        )

        _run_batch_stages(ctx, args, outcomes)

        if args.skip_crop_generation:
            _skip_stage(
                key="crop_generation",
                index=1,
                total=2,
                label="review crop generation",
                reason="--skip-crop-generation",
                outcomes=outcomes,
            )
        else:
            _execute_stage(
                key="crop_generation",
                index=1,
                total=2,
                label="review crop generation",
                runner=lambda: _crop_generation_stage(ctx),
                outcomes=outcomes,
            )

        if args.skip_event_clustering:
            _skip_stage(
                key="event_clustering",
                index=2,
                total=2,
                label="event clustering",
                reason="--skip-event-clustering",
                outcomes=outcomes,
            )
        else:
            _execute_stage(
                key="event_clustering",
                index=2,
                total=2,
                label="event clustering",
                runner=lambda: _event_clustering_stage(ctx),
                outcomes=outcomes,
            )
    except Exception:
        return outcomes

    return outcomes


def _print_summary(ctx: PipelineContext, outcomes: list[StageOutcome], total_elapsed_seconds: float) -> int:
    completed = sum(1 for outcome in outcomes if outcome.status == "completed")
    skipped = sum(1 for outcome in outcomes if outcome.status == "skipped")
    failed = next((outcome for outcome in outcomes if outcome.status == "failed"), None)
    remaining_dropzone_files = len(scan_folder(ctx.drop_zone_path).files)

    print("Pipeline summary")
    print(f"  Stages run: {completed}")
    print(f"  Stages skipped: {skipped}")
    print(f"  Total elapsed: {_format_duration(total_elapsed_seconds)}")
    print(f"  Source files scanned: {len(ctx.processing_records)}")
    print(f"  New unique assets ingested: {ctx.total_new_unique_ingested}")
    print(f"  Duplicates/already-known absorbed: {ctx.total_existing_or_duplicate_processed}")
    print(f"  Ingest batch size used: {ctx.ingest_batch_size}")
    print(f"  Batches run: {ctx.total_batches_run}")
    print(f"  Drop zone files cleaned: {ctx.total_dropzone_files_cleaned}")
    print(f"  Drop zone files remaining: {remaining_dropzone_files}")
    print(f"  Ingest failures path: {ctx.ingest_failures_path}")
    if ctx.manifest_path is not None:
        print(f"  Ingestion manifest: {ctx.manifest_path}")
    if ctx.resolved_ingestion_context is not None:
        print(f"  Source label: {ctx.resolved_ingestion_context.source_label}")
        print(f"  Source type: {ctx.resolved_ingestion_context.source_type}")
        if ctx.resolved_ingestion_context.source_root_path:
            print(f"  Source root path: {ctx.resolved_ingestion_context.source_root_path}")
        print(f"  Ingestion source ID: {ctx.resolved_ingestion_context.ingestion_source_id}")
        print(f"  Ingestion run ID: {ctx.resolved_ingestion_context.ingestion_run_id}")

    if failed is None:
        print("  Status: SUCCESS")
        return 0

    print(f"  Pipeline stopped at: {failed.key}")
    print("  Status: FAILED")
    return 1


def main() -> int:
    parser = _build_parser()
    parsed = parser.parse_args()

    use_interactive = parsed.interactive or (not _has_non_interactive_flags(parsed) and sys.stdin.isatty())

    try:
        args = _get_user_input() if use_interactive else _get_cli_input(parsed)
    except ValueError as exc:
        print(f"Configuration error: {exc}")
        return 2

    from_path = args.from_path
    ctx = PipelineContext(
        from_path=from_path,
        drop_zone_path=_resolve_runtime_path(settings.drop_zone_path),
        vault_path=_resolve_runtime_path(settings.vault_path),
        quarantine_path=_resolve_runtime_path(settings.quarantine_path),
        ingest_failures_path=_resolve_runtime_path(settings.ingest_failures_path),
        ingest_batch_size=args.ingest_batch_size,
        ingest_total_limit=args.ingest_total_limit,
        source_label=args.source_label,
        source_type=args.source_type,
        run_face_detection_rebuild=args.run_face_detection_rebuild,
        run_face_clustering_rebuild=args.run_face_clustering_rebuild,
    )

    if args.dry_run:
        _print_dry_run(args, ctx)
        return 0

    print("Pipeline start")
    print(f"  Source mode: {'from-path' if ctx.from_path else 'existing drop zone'}")
    if ctx.from_path is not None:
        print(f"  Source path: {ctx.from_path}")
    if args.source_label:
        print(f"  Source label: {args.source_label.strip()}")
    if args.source_type:
        print(f"  Source type: {args.source_type}")
    print(f"  Drop zone path: {ctx.drop_zone_path}")
    print(f"  Vault path: {ctx.vault_path}")
    print(f"  Ingest failures path: {ctx.ingest_failures_path}")
    print(f"  Ingest batch size: {ctx.ingest_batch_size}")
    print()

    started_at = time.perf_counter()
    outcomes = _run_pipeline(ctx, args)
    total_elapsed_seconds = time.perf_counter() - started_at
    failed = next((outcome for outcome in outcomes if outcome.status == "failed"), None)
    status = "FAILED" if failed is not None else "SUCCESS"
    try:
        _write_ingestion_run_manifest(ctx, outcomes, total_elapsed_seconds, status)
    except OSError as error:
        print(f"Warning: could not write ingestion manifest: {error}")
    return _print_summary(ctx, outcomes, total_elapsed_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
