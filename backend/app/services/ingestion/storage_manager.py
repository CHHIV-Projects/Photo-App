"""Vault storage manager for ingestion Milestone 1.

Stores files using SHA-256 as canonical filename with 2-char hex prefix folders.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import shutil

from app.services.ingestion.deduplicator import DeduplicationResult
from app.services.ingestion.hasher import HashedFile


@dataclass(frozen=True)
class CopiedFile:
    """A successfully copied unique file."""

    hashed_file: HashedFile
    destination_path: str


@dataclass(frozen=True)
class CopyFailure:
    """A file that failed to copy with a plain-text reason."""

    hashed_file: HashedFile
    reason: str


@dataclass(frozen=True)
class StorageResult:
    """Output of vault copy operation."""

    copied_files: list[CopiedFile]
    failed_files: list[CopyFailure]


def _build_hash_based_vault_path(vault_root: Path, sha256_hash: str, original_extension: str) -> Path:
    """Build vault path from SHA-256 hash with 2-char hex prefix subfolder.

    Example: vault/32/3266ff1d665fa274...7e43347.jpg
    """
    hex_prefix = sha256_hash[:2]
    lowercase_ext = original_extension.lower()
    filename = f"{sha256_hash}{lowercase_ext}"
    return vault_root / hex_prefix / filename


def copy_unique_files_to_vault(
    deduplication_result: DeduplicationResult,
    destination_vault_path: str | Path,
) -> StorageResult:
    """Copy unique files to hash-based vault with 2-char hex prefix structure."""
    vault_root = Path(destination_vault_path).expanduser().resolve()

    copied_files: list[CopiedFile] = []
    failed_files: list[CopyFailure] = []

    for unique_file in deduplication_result.unique_files:
        source_path = Path(unique_file.record.full_path)

        try:
            destination_path = _build_hash_based_vault_path(
                vault_root,
                unique_file.sha256,
                unique_file.record.extension,
            )

            if destination_path.exists():
                copied_files.append(
                    CopiedFile(
                        hashed_file=unique_file,
                        destination_path=str(destination_path),
                    )
                )
                continue

            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination_path)

            source_size = source_path.stat().st_size
            destination_size = destination_path.stat().st_size
            if source_size != destination_size:
                destination_path.unlink(missing_ok=True)
                failed_files.append(
                    CopyFailure(
                        hashed_file=unique_file,
                        reason=(
                            "Copied file size mismatch: "
                            f"source={source_size}, destination={destination_size}."
                        ),
                    )
                )
                continue

            copied_files.append(
                CopiedFile(
                    hashed_file=unique_file,
                    destination_path=str(destination_path),
                )
            )
        except OSError as error:
            failed_files.append(CopyFailure(hashed_file=unique_file, reason=str(error)))

    return StorageResult(copied_files=copied_files, failed_files=failed_files)


def copy_unique_files_to_vault_as_dicts(
    deduplication_result: DeduplicationResult,
    destination_vault_path: str | Path,
) -> dict[str, list[dict[str, Any]]]:
    """Return vault copy output in plain dict format for serialization."""
    result = copy_unique_files_to_vault(deduplication_result, destination_vault_path)
    return {
        "copied_files": [
            {
                "hashed_file": {
                    "record": asdict(item.hashed_file.record),
                    "sha256": item.hashed_file.sha256,
                },
                "destination_path": item.destination_path,
            }
            for item in result.copied_files
        ],
        "failed_files": [
            {
                "hashed_file": {
                    "record": asdict(item.hashed_file.record),
                    "sha256": item.hashed_file.sha256,
                },
                "reason": item.reason,
            }
            for item in result.failed_files
        ],
    }
