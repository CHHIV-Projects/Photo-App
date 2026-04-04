"""File filter for ingestion Milestone 1.

Accepts scanner output records and separates them into accepted and rejected
based on file extension and minimum size rules.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.core.config import settings
from app.services.ingestion.scanner import FileScanRecord

# ---------------------------------------------------------------------------
# Default configuration
# ---------------------------------------------------------------------------

DEFAULT_APPROVED_EXTENSIONS: frozenset[str] = settings.approved_extensions
DEFAULT_MIN_SIZE_BYTES: int = settings.minimum_file_size_bytes


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RejectedFile:
    """A file record that did not pass the filter, with a reason."""

    record: FileScanRecord
    reason: str


@dataclass(frozen=True)
class FilterResult:
    """Output of a filter pass: accepted and rejected file lists."""

    accepted: list[FileScanRecord]
    rejected: list[RejectedFile]


# ---------------------------------------------------------------------------
# Core filter logic
# ---------------------------------------------------------------------------


def filter_records(
    records: list[FileScanRecord],
    approved_extensions: frozenset[str] = DEFAULT_APPROVED_EXTENSIONS,
    min_size_bytes: int = DEFAULT_MIN_SIZE_BYTES,
) -> FilterResult:
    """Filter scanned file records by extension and minimum size.

    Files that do not match an approved extension or are below the minimum
    size are moved to the rejected list with a plain-text reason.
    """
    accepted: list[FileScanRecord] = []
    rejected: list[RejectedFile] = []

    for record in records:
        if record.extension not in approved_extensions:
            rejected.append(
                RejectedFile(
                    record=record,
                    reason=f"Extension '{record.extension}' is not approved.",
                )
            )
        elif record.size_bytes < min_size_bytes:
            rejected.append(
                RejectedFile(
                    record=record,
                    reason=(
                        f"File size {record.size_bytes} bytes is below "
                        f"minimum {min_size_bytes} bytes."
                    ),
                )
            )
        else:
            accepted.append(record)

    return FilterResult(accepted=accepted, rejected=rejected)


def filter_records_as_dicts(
    records: list[FileScanRecord],
    approved_extensions: frozenset[str] = DEFAULT_APPROVED_EXTENSIONS,
    min_size_bytes: int = DEFAULT_MIN_SIZE_BYTES,
) -> dict[str, list[dict[str, Any]]]:
    """Return filter output as plain dicts for easy serialization."""
    result = filter_records(records, approved_extensions, min_size_bytes)
    return {
        "accepted": [asdict(record) for record in result.accepted],
        "rejected": [
            {"record": asdict(r.record), "reason": r.reason}
            for r in result.rejected
        ],
    }
