"""Drop Zone staging service for ingestion workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil

from app.services.ingestion.scanner import FileScanRecord, ScanResult, scan_folder


@dataclass(frozen=True)
class StagedFile:
    """A source file successfully copied into the Drop Zone."""

    source_record: FileScanRecord
    dropzone_path: str


@dataclass(frozen=True)
class StageFailure:
    """A source file that failed to stage, with reason and quarantine hint."""

    source_record: FileScanRecord
    reason: str
    quarantine_target_path: str


@dataclass(frozen=True)
class DropzoneStageResult:
    """Structured result of staging source files into Drop Zone."""

    staged_files: list[StagedFile]
    failures: list[StageFailure]


def _resolve_dropzone_path(dropzone_dir: Path, source_name: str) -> Path:
    """Build a non-conflicting destination path using (1), (2), ... suffixes."""
    candidate = dropzone_dir / source_name
    if not candidate.exists():
        return candidate

    stem = Path(source_name).stem
    suffix = Path(source_name).suffix
    counter = 1

    while True:
        candidate = dropzone_dir / f"{stem}({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def stage_source_records_to_dropzone(
    source_records: list[FileScanRecord],
    drop_zone_path: str | Path,
    quarantine_path: str | Path,
) -> DropzoneStageResult:
    """Copy source records into Drop Zone without modifying source files."""
    dropzone_dir = Path(drop_zone_path).expanduser().resolve()
    quarantine_dir = Path(quarantine_path).expanduser().resolve()
    dropzone_dir.mkdir(parents=True, exist_ok=True)
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    staged_files: list[StagedFile] = []
    failures: list[StageFailure] = []

    for source_record in source_records:
        source_path = Path(source_record.full_path)
        quarantine_target = quarantine_dir / source_record.file_name

        try:
            destination_path = _resolve_dropzone_path(dropzone_dir, source_record.file_name)
            shutil.copy2(source_path, destination_path)

            source_size = source_path.stat().st_size
            destination_size = destination_path.stat().st_size
            if source_size != destination_size:
                destination_path.unlink(missing_ok=True)
                failures.append(
                    StageFailure(
                        source_record=source_record,
                        reason=(
                            "Staged file size mismatch: "
                            f"source={source_size}, destination={destination_size}."
                        ),
                        quarantine_target_path=str(quarantine_target),
                    )
                )
                continue

            staged_files.append(
                StagedFile(
                    source_record=source_record,
                    dropzone_path=str(destination_path),
                )
            )
        except OSError as error:
            failures.append(
                StageFailure(
                    source_record=source_record,
                    reason=str(error),
                    quarantine_target_path=str(quarantine_target),
                )
            )

    return DropzoneStageResult(staged_files=staged_files, failures=failures)


def stage_source_folder_to_dropzone(
    source_folder: str | Path,
    drop_zone_path: str | Path,
    quarantine_path: str | Path,
) -> tuple[ScanResult, DropzoneStageResult]:
    """Scan source folder then stage discovered files into Drop Zone."""
    source_scan = scan_folder(source_folder)
    stage_result = stage_source_records_to_dropzone(source_scan.files, drop_zone_path, quarantine_path)
    return source_scan, stage_result