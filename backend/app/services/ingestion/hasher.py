"""SHA-256 hasher for ingestion Milestone 1."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.services.ingestion.scanner import FileScanRecord

DEFAULT_CHUNK_SIZE_BYTES: int = 1024 * 1024


@dataclass(frozen=True)
class HashedFile:
    """A scanned file record paired with its SHA-256 hash."""

    record: FileScanRecord
    sha256: str


@dataclass(frozen=True)
class HashError:
    """A file that could not be hashed, with a plain-text reason."""

    record: FileScanRecord
    reason: str


@dataclass(frozen=True)
class HashResult:
    """Output of a hashing pass: successful hashes and non-fatal errors."""

    hashed_files: list[HashedFile]
    errors: list[HashError]


def _compute_sha256(file_path: Path, chunk_size_bytes: int) -> str:
    """Compute SHA-256 for a file using chunked reads."""
    sha256_hasher = hashlib.sha256()

    with file_path.open("rb") as source_file:
        while True:
            chunk = source_file.read(chunk_size_bytes)
            if not chunk:
                break
            sha256_hasher.update(chunk)

    return sha256_hasher.hexdigest()


def hash_records(
    records: list[FileScanRecord],
    chunk_size_bytes: int = DEFAULT_CHUNK_SIZE_BYTES,
) -> HashResult:
    """Compute SHA-256 hashes for scanned file records."""
    hashed_files: list[HashedFile] = []
    errors: list[HashError] = []

    for record in records:
        file_path = Path(record.full_path)
        try:
            hashed_files.append(
                HashedFile(
                    record=record,
                    sha256=_compute_sha256(file_path, chunk_size_bytes),
                )
            )
        except OSError as error:
            errors.append(HashError(record=record, reason=str(error)))

    hashed_files.sort(key=lambda item: item.record.full_path.lower())
    errors.sort(key=lambda item: item.record.full_path.lower())

    return HashResult(hashed_files=hashed_files, errors=errors)


def hash_records_as_dicts(
    records: list[FileScanRecord],
    chunk_size_bytes: int = DEFAULT_CHUNK_SIZE_BYTES,
) -> dict[str, list[dict[str, Any]]]:
    """Return hash output as plain dicts for easy serialization."""
    result = hash_records(records, chunk_size_bytes)
    return {
        "hashed_files": [
            {"record": asdict(item.record), "sha256": item.sha256}
            for item in result.hashed_files
        ],
        "errors": [
            {"record": asdict(item.record), "reason": item.reason}
            for item in result.errors
        ],
    }
