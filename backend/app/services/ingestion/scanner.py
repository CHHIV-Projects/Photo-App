"""Folder scanner for ingestion Milestone 1."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import os


@dataclass(frozen=True)
class FileScanRecord:
    """Structured metadata for a discovered file."""

    full_path: str
    file_name: str
    extension: str
    size_bytes: int
    modified_timestamp_utc: str
    original_source_path: str
    original_filename: str


@dataclass(frozen=True)
class ScanResult:
    """Scanner output including successful records and non-fatal errors."""

    files: list[FileScanRecord]
    errors: list[str]


def _build_record(file_path: Path) -> FileScanRecord:
    """Create one file record from a filesystem path."""
    file_stat = file_path.stat()
    modified_utc = datetime.fromtimestamp(file_stat.st_mtime, tz=timezone.utc)

    return FileScanRecord(
        full_path=str(file_path.resolve()),
        file_name=file_path.name,
        extension=file_path.suffix.lower(),
        size_bytes=file_stat.st_size,
        modified_timestamp_utc=modified_utc.isoformat(),
        original_source_path=str(file_path.resolve()),
        original_filename=file_path.name,
    )


def scan_folder(folder_path: str | Path) -> ScanResult:
    """Recursively scan a folder and return file records.

    Directories are skipped automatically because only discovered files are
    converted into records.
    """
    root_path = Path(folder_path).expanduser().resolve()

    if not root_path.exists():
        raise FileNotFoundError(f"Folder not found: {root_path}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {root_path}")

    files: list[FileScanRecord] = []
    errors: list[str] = []

    def _on_walk_error(error: OSError) -> None:
        errors.append(f"{error.filename}: {error.strerror}")

    for current_root, _, file_names in os.walk(root_path, onerror=_on_walk_error):
        current_path = Path(current_root)
        for file_name in file_names:
            file_path = current_path / file_name
            try:
                files.append(_build_record(file_path))
            except OSError as error:
                errors.append(f"{file_path}: {error}")

    files.sort(key=lambda record: record.full_path.lower())
    errors.sort()

    return ScanResult(files=files, errors=errors)


def scan_folder_as_dicts(folder_path: str | Path) -> dict[str, list[dict[str, Any]] | list[str]]:
    """Return scan output in plain dict format for easy API serialization."""
    result = scan_folder(folder_path)
    return {
        "files": [asdict(record) for record in result.files],
        "errors": result.errors,
    }
