"""Pipeline orchestration script for batch ingest and processing.

This is a thin CLI wrapper. Core pipeline logic lives in:
    app/services/ingestion/pipeline_orchestrator.py
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.services.ingestion.pipeline_orchestrator import (
    PipelineContext,
    RuntimeArgs,
    StageOutcome,
    _format_duration,
    _run_pipeline,
    _write_ingestion_run_manifest,
    _write_source_intake_report,
    resolve_runtime_path,
)
from app.services.ingestion.scanner import scan_folder


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
        "--source-limit",
        type=int,
        dest="source_limit",
        help="Max new source files staged from --from-path per session (INGEST_SOURCE_LIMIT).",
    )
    parser.add_argument(
        "--ingest-total-limit",
        type=int,
        dest="ingest_total_limit",
        help="Deprecated alias for --source-limit. Use --source-limit instead.",
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
        help="Deprecated no-op. Duplicate lineage now runs separately via run_duplicate_processing.py.",
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
            getattr(parsed, "source_limit", None) is not None,
            getattr(parsed, "ingest_total_limit", None) is not None,
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
    ingest_source_limit: int | None,
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
        ingest_source_limit=ingest_source_limit,
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


def _validate_ingest_controls(ingest_batch_size: int, ingest_source_limit: int | None) -> None:
    if ingest_batch_size <= 0:
        raise ValueError("Ingest batch size must be greater than zero.")
    if ingest_source_limit is not None and ingest_source_limit <= 0:
        raise ValueError("INGEST_SOURCE_LIMIT must be greater than zero.")


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
    ingest_source_limit = None
    if source_path:
        from_path = Path(source_path).expanduser().resolve()
        if not from_path.exists():
            print(f"  Warning: Path does not exist: {from_path}")
        raw_label = input("Source label (stable name for this source, e.g. icloud_export_primary): ").strip()
        if not raw_label:
            raise ValueError("Source label is required when ingesting from a source folder.")
        source_label = raw_label
        source_type = "local_folder"
        ingest_source_limit = _prompt_optional_int(
            "Max new source files to stage this session (INGEST_SOURCE_LIMIT)?",
        )
    print()

    ingest_batch_size = _prompt_int_default(
        "Batch size for Drop Zone files per run?",
        settings.ingest_batch_size,
    )
    print()

    confirmation_value = _maybe_confirm_rebuild_interactive(
        run_face_detection_rebuild or run_face_clustering_rebuild
    )
    _validate_rebuild_confirmation(
        run_face_detection_rebuild=run_face_detection_rebuild,
        run_face_clustering_rebuild=run_face_clustering_rebuild,
        confirmation_value=confirmation_value,
    )
    _validate_ingest_controls(ingest_batch_size, ingest_source_limit)

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
        ingest_source_limit=ingest_source_limit,
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

    # --source-limit is primary; --ingest-total-limit is deprecated alias; env var INGEST_SOURCE_LIMIT as fallback
    cli_source_limit = getattr(parsed, "source_limit", None) or getattr(parsed, "ingest_total_limit", None)
    ingest_source_limit = cli_source_limit if cli_source_limit is not None else settings.ingest_source_limit

    source_label = parsed.source_label
    if from_path is not None and not source_label:
        raise ValueError(
            "--source-label is required when --from-path is provided.\n"
            "Use a stable, operator-defined label, e.g.: --source-label icloud_export_primary"
        )
    if from_path is None and parsed.source_type and not source_label:
        raise ValueError("--source-type requires --source-label when --from-path is not provided.")
    _validate_ingest_controls(ingest_batch_size, ingest_source_limit)

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
        ingest_source_limit=ingest_source_limit,
        source_label=source_label,
        source_type=parsed.source_type,
    )


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
    print("  [12] SKIP - duplicate lineage (decoupled; run scripts/run_duplicate_processing.py separately)")
    print(f"  [13] {'SKIP (--skip-face-processing)' if args.skip_face_processing else 'RUN'} - face detection + clustering (scope=batch unless rebuild)")
    print(f"  [14] {'SKIP (--skip-crop-generation)' if args.skip_crop_generation else 'RUN'} - review crop generation (scope=global)")
    print(f"  [15] {'SKIP (--skip-event-clustering)' if args.skip_event_clustering else 'RUN'} - event clustering (scope=global, intentional)")
    print()
    print("Status: DRY RUN")


def _print_summary(ctx: PipelineContext, outcomes: list[StageOutcome], total_elapsed_seconds: float) -> int:
    completed = sum(1 for outcome in outcomes if outcome.status == "completed")
    skipped = sum(1 for outcome in outcomes if outcome.status == "skipped")
    failed = next((outcome for outcome in outcomes if outcome.status == "failed"), None)
    remaining_dropzone_files = len(scan_folder(ctx.drop_zone_path).files)

    print("Pipeline summary")
    print(f"  Stages run: {completed}")
    print(f"  Stages skipped: {skipped}")
    print(f"  Total elapsed: {_format_duration(total_elapsed_seconds)}")
    print(f"  New unique assets ingested: {ctx.total_new_unique_ingested}")
    print(f"  Duplicates/already-known absorbed: {ctx.total_existing_or_duplicate_processed}")
    print(f"  Ingest batch size used: {ctx.ingest_batch_size}")
    if ctx.ingest_source_limit is not None:
        print(f"  Source intake limit: {ctx.ingest_source_limit}")
    print(f"  Batches run: {ctx.total_batches_run}")
    print(f"  Drop zone files cleaned: {ctx.total_dropzone_files_cleaned}")
    print(f"  Drop zone files remaining: {remaining_dropzone_files}")
    print(f"  Ingest failures path: {ctx.ingest_failures_path}")
    if ctx.manifest_path is not None:
        print(f"  Ingestion manifest: {ctx.manifest_path}")
    if ctx.from_path is not None:
        print(f"  Source files scanned: {ctx.source_files_scanned_total}")
        print(f"  Known files skipped: {ctx.source_files_skipped_known}")
        print(f"  Eligible unknown files: {ctx.source_files_eligible}")
        print(f"  Selected for this session: {ctx.source_files_selected}")
        print(f"  Remaining unknown eligible: {ctx.source_files_remaining_unknown}")
        print(f"  Source complete: {'Yes' if ctx.source_files_remaining_unknown == 0 else 'No'}")
    if ctx.source_intake_report_path is not None:
        print(f"  Source intake report: {ctx.source_intake_report_path}")
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
        drop_zone_path=resolve_runtime_path(settings.drop_zone_path),
        vault_path=resolve_runtime_path(settings.vault_path),
        quarantine_path=resolve_runtime_path(settings.quarantine_path),
        ingest_failures_path=resolve_runtime_path(settings.ingest_failures_path),
        ingest_batch_size=args.ingest_batch_size,
        ingest_source_limit=args.ingest_source_limit,
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
    if ctx.ingest_source_limit is not None:
        print(f"  Source intake limit: {ctx.ingest_source_limit}")
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
    try:
        _write_source_intake_report(ctx)
    except OSError as error:
        print(f"Warning: could not write source intake report: {error}")
    return _print_summary(ctx, outcomes, total_elapsed_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
