"""Pipeline orchestration script for batch ingest and processing."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import select

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.asset import Asset
from app.services.ingestion.deduplicator import DeduplicationResult, deduplicate
from app.services.ingestion.dropzone_manager import (
    DropzoneStageResult,
    build_dropzone_processing_records,
    stage_source_records_to_dropzone,
)
from app.services.ingestion.filter import FilterResult, filter_records
from app.services.ingestion.hasher import HashResult, hash_records
from app.services.ingestion.scanner import FileScanRecord, ScanResult, scan_folder
from app.services.ingestion.storage_manager import StorageResult, copy_unique_files_to_vault
from app.services.persistence.asset_repository import PersistenceResult, persist_copied_files


@dataclass
class PipelineContext:
    from_path: Path | None
    drop_zone_path: Path
    vault_path: Path
    quarantine_path: Path
    source_scan_result: ScanResult | None = None
    stage_result: DropzoneStageResult | None = None
    dropzone_scan_result: ScanResult | None = None
    processing_records: list[FileScanRecord] = field(default_factory=list)
    filter_result: FilterResult | None = None
    hash_result: HashResult | None = None
    dedup_result: DeduplicationResult | None = None
    storage_result: StorageResult | None = None
    persistence_result: PersistenceResult | None = None


@dataclass(frozen=True)
class StageDefinition:
    key: str
    label: str
    runner: Callable[[PipelineContext], dict[str, Any]]
    skip_flag: str | None = None
    skip_reason: str | None = None


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
    skip_event_clustering: bool
    skip_face_detection: bool
    skip_face_clustering: bool
    skip_crop_generation: bool


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
        "--from-path",
        type=Path,
        help="Optional source folder to stage into the Drop Zone before processing.",
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
        "--run-crop-generation",
        action="store_true",
        help="Run review crop generation (default aligns to face rebuild stages).",
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
            parsed.from_path is not None,
            parsed.dry_run,
            parsed.skip_exif_extraction,
            parsed.skip_metadata_normalization,
            parsed.skip_event_clustering,
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
    skip_event_clustering: bool,
    run_face_detection_rebuild: bool,
    run_face_clustering_rebuild: bool,
    run_crop_generation_override: bool,
) -> RuntimeArgs:
    any_face_rebuild = run_face_detection_rebuild or run_face_clustering_rebuild
    run_crop_generation = run_crop_generation_override or any_face_rebuild

    return RuntimeArgs(
        dry_run=dry_run,
        from_path=from_path,
        skip_exif_extraction=skip_exif_extraction,
        skip_metadata_normalization=skip_metadata_normalization,
        skip_event_clustering=skip_event_clustering,
        skip_face_detection=not run_face_detection_rebuild,
        skip_face_clustering=not run_face_clustering_rebuild,
        skip_crop_generation=not run_crop_generation,
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


def _prompt_yes_no(question: str) -> bool:
    """Prompt user for yes/no input."""
    while True:
        response = input(f"{question} (y/n): ").strip().lower()
        if response in ("y", "yes"):
            return True
        if response in ("n", "no"):
            return False
        print("  Please enter 'y' or 'n'")


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

    # Prompt 4: Source folder to ingest
    source_path = input("Source folder to ingest (leave blank for existing drop zone): ").strip()
    from_path = None
    if source_path:
        from_path = Path(source_path).expanduser().resolve()
        if not from_path.exists():
            print(f"  Warning: Path does not exist: {from_path}")
    print()

    confirmation_value = _maybe_confirm_rebuild_interactive(
        run_face_detection_rebuild or run_face_clustering_rebuild
    )
    _validate_rebuild_confirmation(
        run_face_detection_rebuild=run_face_detection_rebuild,
        run_face_clustering_rebuild=run_face_clustering_rebuild,
        confirmation_value=confirmation_value,
    )

    return _build_runtime_args(
        dry_run=dry_run,
        from_path=from_path,
        skip_exif_extraction=False,
        skip_metadata_normalization=False,
        skip_event_clustering=False,
        run_face_detection_rebuild=run_face_detection_rebuild,
        run_face_clustering_rebuild=run_face_clustering_rebuild,
        run_crop_generation_override=False,
    )


def _get_cli_input(parsed: argparse.Namespace) -> RuntimeArgs:
    """Build runtime args from CLI flags."""
    from_path = parsed.from_path.expanduser().resolve() if parsed.from_path else None

    _validate_rebuild_confirmation(
        run_face_detection_rebuild=parsed.run_face_detection_rebuild,
        run_face_clustering_rebuild=parsed.run_face_clustering_rebuild,
        confirmation_value=parsed.confirm_rebuild,
    )

    return _build_runtime_args(
        dry_run=parsed.dry_run,
        from_path=from_path,
        skip_exif_extraction=parsed.skip_exif_extraction,
        skip_metadata_normalization=parsed.skip_metadata_normalization,
        skip_event_clustering=parsed.skip_event_clustering,
        run_face_detection_rebuild=parsed.run_face_detection_rebuild,
        run_face_clustering_rebuild=parsed.run_face_clustering_rebuild,
        run_crop_generation_override=parsed.run_crop_generation,
    )


def _collect_input(ctx: PipelineContext) -> dict[str, Any]:
    if ctx.from_path is not None:
        source_scan_result = scan_folder(ctx.from_path)
        stage_result = stage_source_records_to_dropzone(
            source_scan_result.files,
            ctx.drop_zone_path,
            ctx.quarantine_path,
        )
        dropzone_scan_result = scan_folder(ctx.drop_zone_path)
        processing_records = build_dropzone_processing_records(
            dropzone_scan_result.files,
            stage_result.staged_files,
        )

        ctx.source_scan_result = source_scan_result
        ctx.stage_result = stage_result
        ctx.dropzone_scan_result = dropzone_scan_result
        ctx.processing_records = processing_records

        return {
            "input_mode": "from-path via drop zone staging",
            "source_path": str(ctx.from_path),
            "source_files_scanned": len(source_scan_result.files),
            "source_scan_errors": len(source_scan_result.errors),
            "files_staged": len(stage_result.staged_files),
            "stage_failures": len(stage_result.failures),
            "drop_zone_records": len(dropzone_scan_result.files),
            "processing_records": len(processing_records),
        }

    dropzone_scan_result = scan_folder(ctx.drop_zone_path)
    ctx.dropzone_scan_result = dropzone_scan_result
    ctx.processing_records = dropzone_scan_result.files

    return {
        "input_mode": "existing drop zone contents",
        "drop_zone_path": str(ctx.drop_zone_path),
        "drop_zone_records": len(dropzone_scan_result.files),
        "drop_zone_scan_errors": len(dropzone_scan_result.errors),
    }


def _filter_records_stage(ctx: PipelineContext) -> dict[str, Any]:
    result = filter_records(
        ctx.processing_records,
        approved_extensions=settings.approved_extensions,
        min_size_bytes=settings.minimum_file_size_bytes,
    )
    ctx.filter_result = result
    return {
        "accepted": len(result.accepted),
        "rejected": len(result.rejected),
        "approved_extensions": len(settings.approved_extensions),
        "minimum_size_bytes": settings.minimum_file_size_bytes,
    }


def _hash_stage(ctx: PipelineContext) -> dict[str, Any]:
    if ctx.filter_result is None:
        raise RuntimeError("Filter stage must run before hashing.")

    result = hash_records(ctx.filter_result.accepted)
    ctx.hash_result = result
    return {
        "hashed": len(result.hashed_files),
        "hash_errors": len(result.errors),
    }


def _deduplicate_stage(ctx: PipelineContext) -> dict[str, Any]:
    if ctx.hash_result is None:
        raise RuntimeError("Hash stage must run before deduplication.")

    result = deduplicate(ctx.hash_result.hashed_files)
    ctx.dedup_result = result
    return {
        "unique": len(result.unique_files),
        "duplicates": len(result.duplicate_files),
    }


def _storage_stage(ctx: PipelineContext) -> dict[str, Any]:
    if ctx.dedup_result is None:
        raise RuntimeError("Deduplication stage must run before storage.")

    result = copy_unique_files_to_vault(ctx.dedup_result, ctx.vault_path)
    ctx.storage_result = result
    return {
        "copied_to_vault": len(result.copied_files),
        "copy_failures": len(result.failed_files),
        "vault_path": str(ctx.vault_path),
    }


def _ingest_to_db_stage(ctx: PipelineContext) -> dict[str, Any]:
    if ctx.storage_result is None:
        raise RuntimeError("Storage stage must run before DB ingestion.")

    db_session = SessionLocal()
    try:
        result = persist_copied_files(db_session, ctx.storage_result.copied_files)
    finally:
        db_session.close()

    ctx.persistence_result = result
    return {
        "inserted": len(result.inserted_records),
        "skipped_existing": len(result.skipped_existing_records),
        "db_failures": len(result.failed_inserts),
    }


def _exif_extraction_stage(_: PipelineContext) -> dict[str, Any]:
    from app.services.metadata.exif_extractor import extract_exif_for_assets
    from app.services.metadata.exif_persistence import persist_exif_updates

    db_session = SessionLocal()
    try:
        assets = list(db_session.scalars(select(Asset)).all())
        extraction_result = extract_exif_for_assets(assets)
        persistence_result = persist_exif_updates(db_session, extraction_result.extracted)
    finally:
        db_session.close()

    return {
        "assets_checked": len(assets),
        "updated": len(persistence_result.updated_assets),
        "skipped": len(extraction_result.skipped) + len(persistence_result.skipped_assets),
        "failed": len(extraction_result.failed) + len(persistence_result.failed_assets),
    }


def _metadata_normalization_stage(_: PipelineContext) -> dict[str, Any]:
    from app.services.metadata.metadata_normalizer import normalize_assets, persist_normalized_metadata

    db_session = SessionLocal()
    try:
        assets = list(db_session.scalars(select(Asset)).all())
        normalization_result = normalize_assets(assets)
        persistence_result = persist_normalized_metadata(db_session, normalization_result.updated_records)
    finally:
        db_session.close()

    scans_detected = sum(1 for item in normalization_result.updated_records if item.is_scan)
    missing_dates = sum(1 for item in normalization_result.updated_records if item.needs_date_estimation)

    return {
        "assets_processed": len(assets),
        "updated_records": len(persistence_result.updated_records),
        "scans_detected": scans_detected,
        "missing_dates": missing_dates,
        "failed": len(normalization_result.failed_records) + len(persistence_result.failed_records),
    }


def _event_clustering_stage(_: PipelineContext) -> dict[str, Any]:
    from app.services.organization.event_clusterer import cluster_assets_into_events, persist_event_clusters

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
        "assets_considered": clustering_result.considered_assets,
        "assets_skipped_scans": clustering_result.skipped_scans,
        "events_created": persistence_result.events_created,
        "assigned_assets": persistence_result.assigned_assets,
    }


def _face_detection_stage(_: PipelineContext) -> dict[str, Any]:
    from app.services.vision.face_detector import YuNetFaceDetector, persist_face_detections, run_face_detection

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
        assets = list(db_session.scalars(select(Asset)).all())
        detection_result = run_face_detection(
            assets=assets,
            detector=detector,
            target_longest_side=settings.face_detection_resize_longest_side,
        )
        persistence_result = persist_face_detections(db_session, detection_result.detections)
    finally:
        db_session.close()

    return {
        "assets_processed": detection_result.total_assets_processed,
        "faces_detected": detection_result.total_faces_detected,
        "inserted_faces": persistence_result.inserted_faces,
        "failed": persistence_result.failed,
    }


def _face_clustering_stage(_: PipelineContext) -> dict[str, Any]:
    from app.services.vision.face_clusterer import (
        cluster_face_embeddings,
        load_faces_for_embedding,
        persist_face_clusters,
    )
    from app.services.vision.face_embedder import generate_face_embeddings

    db_session = SessionLocal()
    try:
        face_asset_rows = load_faces_for_embedding(db_session)
        embedding_result = generate_face_embeddings(
            face_asset_rows=face_asset_rows,
            model_name=settings.face_embedding_model,
            margin_ratio=settings.face_embedding_crop_margin_ratio,
        )
        clustering_result = cluster_face_embeddings(
            embedding_items=embedding_result.embedding_items,
            similarity_threshold=settings.face_cluster_similarity_threshold,
        )
        persistence_result = persist_face_clusters(db_session, clustering_result)
    finally:
        db_session.close()

    return {
        "faces_in_db": len(face_asset_rows),
        "embeddings_generated": embedding_result.embedded_faces,
        "clusters_created": clustering_result.clusters_created,
        "faces_assigned": persistence_result.faces_assigned,
        "failed": persistence_result.failed,
    }


def _crop_generation_stage(_: PipelineContext) -> dict[str, Any]:
    command = [sys.executable, str(BACKEND_ROOT / "scripts" / "generate_missing_face_crops.py")]
    completed = subprocess.run(command, cwd=str(BACKEND_ROOT), check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Crop generation exited with code {completed.returncode}.")

    return {
        "command": "generate_missing_face_crops.py",
        "status": "completed",
    }


def _build_stage_plan() -> list[StageDefinition]:
    return [
        StageDefinition(key="collect_input", label="collect input", runner=_collect_input),
        StageDefinition(key="filter", label="filter records", runner=_filter_records_stage),
        StageDefinition(key="hash", label="hash files", runner=_hash_stage),
        StageDefinition(key="deduplicate", label="deduplicate files", runner=_deduplicate_stage),
        StageDefinition(key="storage", label="store to vault", runner=_storage_stage),
        StageDefinition(key="ingest_db", label="ingest to database", runner=_ingest_to_db_stage),
        StageDefinition(
            key="exif_extraction",
            label="EXIF extraction",
            runner=_exif_extraction_stage,
            skip_flag="skip_exif_extraction",
            skip_reason="--skip-exif-extraction",
        ),
        StageDefinition(
            key="metadata_normalization",
            label="metadata normalization",
            runner=_metadata_normalization_stage,
            skip_flag="skip_metadata_normalization",
            skip_reason="--skip-metadata-normalization",
        ),
        StageDefinition(
            key="event_clustering",
            label="event clustering",
            runner=_event_clustering_stage,
            skip_flag="skip_event_clustering",
            skip_reason="--skip-event-clustering",
        ),
        StageDefinition(
            key="face_detection",
            label="face detection",
            runner=_face_detection_stage,
            skip_flag="skip_face_detection",
            skip_reason="safe default (use face rebuild prompt/flag)",
        ),
        StageDefinition(
            key="face_clustering",
            label="face embedding + clustering",
            runner=_face_clustering_stage,
            skip_flag="skip_face_clustering",
            skip_reason="safe default (use face rebuild prompt/flag)",
        ),
        StageDefinition(
            key="crop_generation",
            label="review crop generation",
            runner=_crop_generation_stage,
            skip_flag="skip_crop_generation",
            skip_reason="aligned safe default (runs with face rebuild)",
        ),
    ]


def _print_dry_run(stage_plan: list[StageDefinition], args: Any, ctx: PipelineContext) -> None:
    print("Pipeline dry-run")
    print(f"  Source mode: {'from-path' if ctx.from_path else 'existing drop zone'}")
    if ctx.from_path is not None:
        print(f"  Source path: {ctx.from_path}")
    print(f"  Drop zone path: {ctx.drop_zone_path}")
    print(f"  Vault path: {ctx.vault_path}")
    print()
    print("Planned stages:")
    for index, stage in enumerate(stage_plan, start=1):
        should_skip = bool(stage.skip_flag and getattr(args, stage.skip_flag))
        status = f"SKIP ({stage.skip_reason})" if should_skip else "RUN"
        print(f"  [{index}/{len(stage_plan)}] {status} - {stage.label}")
    print()
    print("Status: DRY RUN")


def _run_pipeline(stage_plan: list[StageDefinition], ctx: PipelineContext, args: Any) -> list[StageOutcome]:
    outcomes: list[StageOutcome] = []

    for index, stage in enumerate(stage_plan, start=1):
        should_skip = bool(stage.skip_flag and getattr(args, stage.skip_flag))
        if should_skip:
            _print_stage_skipped(index, len(stage_plan), stage.label, stage.skip_reason or "skipped")
            outcomes.append(
                StageOutcome(
                    key=stage.key,
                    label=stage.label,
                    status="skipped",
                    elapsed_seconds=0.0,
                    skip_reason=stage.skip_reason,
                )
            )
            continue

        _print_stage_header(index, len(stage_plan), stage.label)
        started_at = time.perf_counter()
        try:
            summary = stage.runner(ctx)
        except Exception as exc:  # noqa: BLE001
            elapsed_seconds = time.perf_counter() - started_at
            error = str(exc) or exc.__class__.__name__
            _print_stage_failed(elapsed_seconds, error)
            outcomes.append(
                StageOutcome(
                    key=stage.key,
                    label=stage.label,
                    status="failed",
                    elapsed_seconds=elapsed_seconds,
                    error=error,
                )
            )
            break

        elapsed_seconds = time.perf_counter() - started_at
        _print_stage_done(elapsed_seconds, summary)
        outcomes.append(
            StageOutcome(
                key=stage.key,
                label=stage.label,
                status="completed",
                elapsed_seconds=elapsed_seconds,
                summary=summary,
            )
        )

    return outcomes


def _print_summary(outcomes: list[StageOutcome], total_elapsed_seconds: float) -> int:
    completed = sum(1 for outcome in outcomes if outcome.status == "completed")
    skipped = sum(1 for outcome in outcomes if outcome.status == "skipped")
    failed = next((outcome for outcome in outcomes if outcome.status == "failed"), None)

    print("Pipeline summary")
    print(f"  Stages run: {completed}")
    print(f"  Stages skipped: {skipped}")
    print(f"  Total elapsed: {_format_duration(total_elapsed_seconds)}")

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
    )
    stage_plan = _build_stage_plan()

    if args.dry_run:
        _print_dry_run(stage_plan, args, ctx)
        return 0

    print("Pipeline start")
    print(f"  Source mode: {'from-path' if ctx.from_path else 'existing drop zone'}")
    if ctx.from_path is not None:
        print(f"  Source path: {ctx.from_path}")
    print(f"  Drop zone path: {ctx.drop_zone_path}")
    print(f"  Vault path: {ctx.vault_path}")
    print()

    started_at = time.perf_counter()
    outcomes = _run_pipeline(stage_plan, ctx, args)
    total_elapsed_seconds = time.perf_counter() - started_at
    return _print_summary(outcomes, total_elapsed_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
