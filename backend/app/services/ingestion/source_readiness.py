"""Source-readiness checks for cloud-export intake sessions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time

from app.services.ingestion.scanner import FileScanRecord


READINESS_STABILITY_CHECKS = 2
READINESS_STABILITY_INTERVAL_SECONDS = 5.0

_TEMP_ARTIFACT_SUFFIXES = (".tmp", ".partial", ".crdownload")


@dataclass(frozen=True)
class DeferredUnreadyRecord:
    record: FileScanRecord
    reason: str


@dataclass(frozen=True)
class ReadinessResult:
    ready_records: list[FileScanRecord]
    deferred_records: list[DeferredUnreadyRecord]
    deferred_reason_counts: dict[str, int]


def _count_reason(counter: dict[str, int], reason: str) -> None:
    counter[reason] = counter.get(reason, 0) + 1


def _is_temporary_partial_artifact(record: FileScanRecord) -> bool:
    file_name = record.file_name.lower()
    return file_name.startswith("~") or file_name.endswith(_TEMP_ARTIFACT_SUFFIXES)


def _safe_stat_size(path: Path) -> int | None:
    try:
        return path.stat().st_size
    except OSError:
        return None


def classify_source_readiness(
    records: list[FileScanRecord],
    *,
    approved_extensions: frozenset[str],
    stability_checks: int = READINESS_STABILITY_CHECKS,
    stability_interval_seconds: float = READINESS_STABILITY_INTERVAL_SECONDS,
) -> ReadinessResult:
    """
    Classify source files as ready vs deferred_unready.

    Unsupported extensions are passed through as ready so existing filter/rejection
    behavior remains in the downstream Drop Zone pipeline (12.27 scope).
    """
    if not records:
        return ReadinessResult(ready_records=[], deferred_records=[], deferred_reason_counts={})

    ready_records: list[FileScanRecord] = []
    deferred_records: list[DeferredUnreadyRecord] = []
    deferred_reason_counts: dict[str, int] = {}

    # Only apply readiness logic to potentially ingestible files.
    candidates = [r for r in records if r.extension in approved_extensions]
    passthrough = [r for r in records if r.extension not in approved_extensions]

    for record in passthrough:
        ready_records.append(record)

    if not candidates:
        return ReadinessResult(
            ready_records=ready_records,
            deferred_records=deferred_records,
            deferred_reason_counts=deferred_reason_counts,
        )

    candidate_by_path = {record.full_path: record for record in candidates}
    current_paths: set[str] = set(candidate_by_path.keys())
    reasons_by_path: dict[str, str] = {}

    for record in candidates:
        if _is_temporary_partial_artifact(record):
            reasons_by_path[record.full_path] = "partial_temp_artifact"
            current_paths.discard(record.full_path)
            continue

        if record.size_bytes <= 0:
            reasons_by_path[record.full_path] = "zero_byte"
            current_paths.discard(record.full_path)

    if current_paths and stability_checks > 1 and stability_interval_seconds > 0:
        previous_sizes: dict[str, int] = {}
        for path_str in list(current_paths):
            size = _safe_stat_size(Path(path_str))
            if size is None:
                reasons_by_path[path_str] = "unreadable"
                current_paths.discard(path_str)
                continue
            previous_sizes[path_str] = size

        for _ in range(1, stability_checks):
            if not current_paths:
                break
            time.sleep(stability_interval_seconds)
            for path_str in list(current_paths):
                size_now = _safe_stat_size(Path(path_str))
                if size_now is None:
                    reasons_by_path[path_str] = "unreadable"
                    current_paths.discard(path_str)
                    continue
                if size_now != previous_sizes[path_str]:
                    reasons_by_path[path_str] = "size_unstable"
                    current_paths.discard(path_str)
                    continue
                previous_sizes[path_str] = size_now

    for path_str in list(current_paths):
        path = Path(path_str)
        try:
            with path.open("rb") as handle:
                handle.read(1)
        except OSError:
            reasons_by_path[path_str] = "unreadable"
            current_paths.discard(path_str)

    for record in records:
        if record.extension not in approved_extensions:
            continue

        reason = reasons_by_path.get(record.full_path)
        if reason is None:
            ready_records.append(record)
            continue

        deferred_records.append(DeferredUnreadyRecord(record=record, reason=reason))
        _count_reason(deferred_reason_counts, reason)

    return ReadinessResult(
        ready_records=ready_records,
        deferred_records=deferred_records,
        deferred_reason_counts=deferred_reason_counts,
    )
