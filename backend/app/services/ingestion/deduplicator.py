"""SHA-256 deduplicator for ingestion Milestone 1.

Classifies a list of HashedFile objects into unique files and duplicates.
First-seen wins: the first file encountered with a given SHA-256 is the
original; any later file with the same SHA-256 is a duplicate.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.services.ingestion.hasher import HashedFile


@dataclass(frozen=True)
class DuplicateFile:
    """A file that shares its SHA-256 with an earlier file in the batch."""

    duplicate: HashedFile
    original: HashedFile


@dataclass(frozen=True)
class DeduplicationResult:
    """Output of a deduplication pass."""

    unique_files: list[HashedFile]
    duplicate_files: list[DuplicateFile]


def deduplicate(hashed_files: list[HashedFile]) -> DeduplicationResult:
    """Classify hashed files into unique and duplicate groups.

    First-seen wins: the first occurrence of a SHA-256 in the list is the
    original. All later occurrences of the same SHA-256 are duplicates.
    """
    seen: dict[str, HashedFile] = {}
    unique_files: list[HashedFile] = []
    duplicate_files: list[DuplicateFile] = []

    for hashed_file in hashed_files:
        if hashed_file.sha256 not in seen:
            seen[hashed_file.sha256] = hashed_file
            unique_files.append(hashed_file)
        else:
            duplicate_files.append(
                DuplicateFile(
                    duplicate=hashed_file,
                    original=seen[hashed_file.sha256],
                )
            )

    return DeduplicationResult(
        unique_files=unique_files,
        duplicate_files=duplicate_files,
    )


def deduplicate_as_dicts(
    hashed_files: list[HashedFile],
) -> dict[str, list[dict[str, Any]]]:
    """Return deduplication output as plain dicts for easy serialization."""
    result = deduplicate(hashed_files)
    return {
        "unique_files": [
            {"record": asdict(item.record), "sha256": item.sha256}
            for item in result.unique_files
        ],
        "duplicate_files": [
            {
                "duplicate": {"record": asdict(item.duplicate.record), "sha256": item.duplicate.sha256},
                "original": {"record": asdict(item.original.record), "sha256": item.original.sha256},
            }
            for item in result.duplicate_files
        ],
    }
