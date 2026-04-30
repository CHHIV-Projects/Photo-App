"""Diagnostic script: compare per-item vs batch ExifTool extraction.

Verifies that batch ExifTool extraction (12.20.2 optimization) produces
identical ExtractedMetadataObservation results to the original per-item
approach. Writes a JSON report to storage/logs/metadata_canonicalization_reports/.

Usage:
    python scripts/compare_metadata_canonicalization.py [--limit N]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.provenance import Provenance
from app.services.metadata.canonicalization_service import (
    ExtractedMetadataObservation,
    _batch_extract_metadata,
    _extract_observation_from_metadata,
    extract_metadata_observation_from_path,
)

REPORT_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "logs" / "metadata_canonicalization_reports"
FIELDS = [
    "exif_datetime_original",
    "exif_create_date",
    "captured_at_observed",
    "gps_latitude",
    "gps_longitude",
    "camera_make",
    "camera_model",
    "width",
    "height",
    "observed_extension",
]


def _obs_to_dict(obs: ExtractedMetadataObservation | None) -> dict:
    if obs is None:
        return {f: None for f in FIELDS}
    return {
        "exif_datetime_original": obs.exif_datetime_original.isoformat() if obs.exif_datetime_original else None,
        "exif_create_date": obs.exif_create_date.isoformat() if obs.exif_create_date else None,
        "captured_at_observed": obs.captured_at_observed.isoformat() if obs.captured_at_observed else None,
        "gps_latitude": obs.gps_latitude,
        "gps_longitude": obs.gps_longitude,
        "camera_make": obs.camera_make,
        "camera_model": obs.camera_model,
        "width": obs.width,
        "height": obs.height,
        "observed_extension": obs.observed_extension,
    }


def _compare_obs(
    baseline: ExtractedMetadataObservation | None,
    optimized: ExtractedMetadataObservation | None,
) -> list[dict]:
    mismatches = []
    bd = _obs_to_dict(baseline)
    od = _obs_to_dict(optimized)
    for field in FIELDS:
        if bd[field] != od[field]:
            mismatches.append({"field": field, "baseline": bd[field], "optimized": od[field]})
    return mismatches


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare per-item vs batch ExifTool extraction.")
    parser.add_argument("--limit", type=int, default=None, help="Max number of source paths to compare.")
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    with SessionLocal() as db_session:
        query = select(Provenance.source_path).where(Provenance.source_path.isnot(None)).distinct()
        all_paths: list[str] = list(db_session.scalars(query).all())

    if not all_paths:
        print("No provenance source paths found in DB. Nothing to compare.")
        return

    # Filter to existing files only
    all_paths = [p for p in all_paths if p and Path(p).exists() and Path(p).is_file()]

    if args.limit is not None:
        all_paths = all_paths[: args.limit]

    print(f"Comparing extraction for {len(all_paths)} source path(s)...")

    # --- Baseline: per-item ExifTool ---
    t0 = time.perf_counter()
    baseline_results: dict[str, ExtractedMetadataObservation | None] = {}
    for path in all_paths:
        baseline_results[path] = extract_metadata_observation_from_path(path)
    baseline_runtime = time.perf_counter() - t0
    print(f"  Baseline runtime:  {baseline_runtime:.3f}s")

    # --- Optimized: batch ExifTool ---
    t1 = time.perf_counter()
    batch_metadata = _batch_extract_metadata(all_paths)
    optimized_results: dict[str, ExtractedMetadataObservation | None] = {}
    for path in all_paths:
        raw = batch_metadata.get(path)
        if raw is not None:
            optimized_results[path] = _extract_observation_from_metadata(Path(path), raw)
        else:
            optimized_results[path] = None
    optimized_runtime = time.perf_counter() - t1
    print(f"  Optimized runtime: {optimized_runtime:.3f}s")

    improvement_seconds = baseline_runtime - optimized_runtime
    improvement_pct = (improvement_seconds / baseline_runtime * 100) if baseline_runtime > 0 else 0.0

    # --- Compare ---
    per_asset_mismatch_details = []
    total_mismatches = 0
    for path in all_paths:
        mismatches = _compare_obs(baseline_results[path], optimized_results[path])
        if mismatches:
            total_mismatches += len(mismatches)
            per_asset_mismatch_details.append({
                "source_path": path,
                "baseline": _obs_to_dict(baseline_results[path]),
                "optimized": _obs_to_dict(optimized_results[path]),
                "mismatched_fields": mismatches,
            })

    # --- Write report ---
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"meta_compare_{ts}.json"
    report = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "asset_count_compared": len(all_paths),
        "fields_compared": FIELDS,
        "total_mismatches": total_mismatches,
        "baseline_runtime_seconds": round(baseline_runtime, 3),
        "optimized_runtime_seconds": round(optimized_runtime, 3),
        "runtime_improvement_seconds": round(improvement_seconds, 3),
        "runtime_improvement_percent": round(improvement_pct, 2),
        "per_asset_mismatch_details": per_asset_mismatch_details,
    }
    report_path.write_text(json.dumps(report, indent=2, default=str))

    print(f"\n{'='*60}")
    print(f"Assets compared:     {len(all_paths)}")
    print(f"Total mismatches:    {total_mismatches}")
    print(f"Baseline runtime:    {baseline_runtime:.3f}s")
    print(f"Optimized runtime:   {optimized_runtime:.3f}s")
    print(f"Improvement:         {improvement_seconds:.3f}s ({improvement_pct:.1f}%)")
    print(f"Report:              {report_path}")
    if total_mismatches == 0:
        print("\nOUTCOME: PASS — outputs are identical.")
    else:
        print(f"\nOUTCOME: FAIL — {total_mismatches} field mismatch(es) detected.")
        sys.exit(1)


if __name__ == "__main__":
    main()
