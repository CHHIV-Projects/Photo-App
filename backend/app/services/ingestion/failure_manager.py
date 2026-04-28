"""Helpers for relocating failed ingestion inputs for operator review."""

from __future__ import annotations

from pathlib import Path
import shutil

from app.services.ingestion.scanner import FileScanRecord


def _resolve_collision_safe_path(destination_path: Path) -> Path:
    if not destination_path.exists():
        return destination_path

    stem = destination_path.stem
    suffix = destination_path.suffix
    counter = 1

    while True:
        candidate = destination_path.with_name(f"{stem}({counter}){suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def _relative_failure_path(record: FileScanRecord, source_root: Path | None) -> Path:
    if source_root is not None:
        source_path = Path(record.original_source_path).expanduser().resolve()
        try:
            return source_path.relative_to(source_root)
        except ValueError:
            pass

    return Path(record.original_filename)


def move_record_to_ingest_failures(
    record: FileScanRecord,
    failures_root: str | Path,
    *,
    source_root: str | Path | None = None,
) -> str:
    """Move one failed Drop Zone file into the operator review area."""

    failures_dir = Path(failures_root).expanduser().resolve()
    failures_dir.mkdir(parents=True, exist_ok=True)

    normalized_source_root = None
    if source_root is not None:
        normalized_source_root = Path(source_root).expanduser().resolve()

    relative_path = _relative_failure_path(record, normalized_source_root)
    destination_path = _resolve_collision_safe_path(failures_dir / relative_path)
    destination_path.parent.mkdir(parents=True, exist_ok=True)

    source_path = Path(record.full_path).expanduser().resolve()
    shutil.move(str(source_path), str(destination_path))
    return str(destination_path)