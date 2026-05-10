"""Shared report helpers for Live Photo pairing runs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.services.live_photo.pairing_schema import LivePhotoPairingSchemaSummary
from app.services.live_photo.pairing_service import LivePhotoPairingResult


def report_dir() -> Path:
    return (Path(__file__).resolve().parents[4] / "storage" / "logs" / "live_photo_pairing_reports").resolve()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_report_payload(
    schema_summary: LivePhotoPairingSchemaSummary,
    result: LivePhotoPairingResult,
) -> dict[str, object]:
    return {
        "generated_at_utc": result.generated_at_utc,
        "schema": {
            "ensured_tables": schema_summary.ensured_tables,
        },
        "summary": {
            "scanned_rows": result.scanned_rows,
            "candidate_groups": result.candidate_groups,
            "inserted": result.inserted,
            "updated": result.updated,
            "unchanged": result.unchanged,
            "removed_stale": result.removed_stale,
            "skipped_missing_source": result.skipped_missing_source,
            "skipped_ambiguous": result.skipped_ambiguous,
            "ambiguous_skipped": result.skipped_ambiguous,
            "skipped_suspicious_delta": result.skipped_suspicious_delta,
            "pairs_created_simple_basename": result.pairs_created_simple_basename,
            "pairs_created_motion_suffix": result.pairs_created_motion_suffix,
            "motion_suffixes_seen": result.motion_suffixes_seen,
        },
        "sample_pairs": result.sample_pairs,
    }


def write_report(payload: dict[str, object]) -> Path:
    destination_dir = report_dir()
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"live_photo_pairing_{utc_stamp()}.json"
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return destination