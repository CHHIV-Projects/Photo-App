"""Dry-run comparison of baseline vs optimized duplicate candidate sets.

Usage:
    python scripts/compare_duplicate_processing_candidates.py [--limit N] [--output PATH]

This script:
- Loads all phash-populated assets (up to --limit if specified)
- For each asset, queries BOTH baseline and optimized candidate sets
- Computes ALL pairs under the Hamming threshold for each mode (pair-level recall)
- Does NOT mutate duplicate_group_id, is_canonical, or any other DB state
- Writes a JSON comparison report to storage/logs/duplicate_processing_reports/

Pair-level recall is the primary quality metric per milestone 12.20.1.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy.orm import Session

from app.core.config import BACKEND_ROOT as CONFIG_BACKEND_ROOT, settings
from app.db.session import SessionLocal
from app.models.asset import Asset
from app.services.duplicates.lineage import (
    _candidate_query_baseline,
    _candidate_query_optimized,
    _hamming_distance,
    _is_candidate_match,
)

REPORT_DIR: Path = CONFIG_BACKEND_ROOT.parent / "storage" / "logs" / "duplicate_processing_reports"


def _all_pairs_under_threshold(
    db_session: Session,
    asset: Asset,
    candidates: list[Asset],
    threshold: int,
    dimensions_cache: dict[str, tuple[int, int] | None],
) -> set[frozenset[str]]:
    """Return all (asset, candidate) pairs that pass Python filter and are under threshold.

    Uses frozenset keys so (a, b) and (b, a) are the same pair.
    Does not mutate any DB state.
    """
    pairs: set[frozenset[str]] = set()
    for candidate in candidates:
        if not candidate.phash:
            continue
        if not _is_candidate_match(asset, candidate, dimensions_cache):
            continue
        try:
            distance = _hamming_distance(asset.phash, candidate.phash)
        except Exception:  # noqa: BLE001
            continue
        if distance <= threshold:
            pairs.add(frozenset({asset.sha256, candidate.sha256}))
    return pairs


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare baseline vs optimized duplicate candidate sets (dry-run, non-mutating)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of assets to evaluate (default: all)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON report path (default: auto-named in storage/logs/duplicate_processing_reports/)",
    )
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    db_session = SessionLocal()
    try:
        from sqlalchemy import select

        query = (
            select(Asset)
            .where(Asset.phash.is_not(None))
            .order_by(Asset.created_at_utc.asc(), Asset.sha256.asc())
        )
        if args.limit:
            query = query.limit(args.limit)

        assets = list(db_session.scalars(query).all())
        print(f"Loaded {len(assets)} phash-populated assets for comparison")

        threshold = max(0, settings.duplicate_hamming_threshold)
        print(f"Hamming threshold: {threshold}")
        print(f"Resolution band: {settings.duplicate_resolution_band_ratio}")
        print(f"Capture window enabled: {settings.duplicate_capture_window_enabled} ({settings.duplicate_capture_window_hours}h)")
        print()

        baseline_pairs: set[frozenset[str]] = set()
        optimized_pairs: set[frozenset[str]] = set()
        dimensions_cache: dict[str, tuple[int, int] | None] = {}

        baseline_candidates_total = 0
        optimized_candidates_total = 0
        baseline_query_seconds = 0.0
        optimized_query_seconds = 0.0

        t_run_start = time.perf_counter()

        for i, asset in enumerate(assets, 1):
            if i % 50 == 0 or i == len(assets):
                print(f"  [{i}/{len(assets)}] baseline_pairs={len(baseline_pairs)} optimized_pairs={len(optimized_pairs)}")

            # Baseline: unfiltered broad query
            t0 = time.perf_counter()
            baseline_candidates = list(db_session.scalars(_candidate_query_baseline(asset.sha256)).all())
            baseline_query_seconds += time.perf_counter() - t0
            baseline_candidates_total += len(baseline_candidates)
            baseline_pairs.update(
                _all_pairs_under_threshold(db_session, asset, baseline_candidates, threshold, dimensions_cache)
            )

            # Optimized: SQL-prefiltered query
            t0 = time.perf_counter()
            optimized_candidates = list(db_session.scalars(_candidate_query_optimized(asset)).all())
            optimized_query_seconds += time.perf_counter() - t0
            optimized_candidates_total += len(optimized_candidates)
            optimized_pairs.update(
                _all_pairs_under_threshold(db_session, asset, optimized_candidates, threshold, dimensions_cache)
            )

        t_run_elapsed = time.perf_counter() - t_run_start

        # --- Pair comparison ---
        both = baseline_pairs & optimized_pairs
        only_baseline = baseline_pairs - optimized_pairs
        only_optimized = optimized_pairs - baseline_pairs
        recall = (len(both) / len(baseline_pairs) * 100.0) if baseline_pairs else 100.0

        candidate_reduction_pct = round(
            (1.0 - optimized_candidates_total / max(1, baseline_candidates_total)) * 100.0, 2
        )

        report = {
            "report_type": "duplicate_candidate_comparison",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "config": {
                "hamming_threshold": threshold,
                "resolution_band_ratio": settings.duplicate_resolution_band_ratio,
                "capture_window_enabled": settings.duplicate_capture_window_enabled,
                "capture_window_hours": settings.duplicate_capture_window_hours,
                "assets_evaluated": len(assets),
                "limit_applied": args.limit,
                "total_run_seconds": round(t_run_elapsed, 2),
            },
            "pair_comparison": {
                "baseline_pairs_found": len(baseline_pairs),
                "optimized_pairs_found": len(optimized_pairs),
                "pairs_found_by_both": len(both),
                "pairs_found_only_by_baseline": len(only_baseline),
                "pairs_found_only_by_optimized": len(only_optimized),
                "recall_vs_baseline_pct": round(recall, 4),
            },
            "performance_comparison": {
                "baseline_total_candidates_queried": baseline_candidates_total,
                "optimized_total_candidates_queried": optimized_candidates_total,
                "candidate_reduction_pct": candidate_reduction_pct,
                "baseline_db_query_seconds": round(baseline_query_seconds, 3),
                "optimized_db_query_seconds": round(optimized_query_seconds, 3),
                "db_query_speedup_seconds": round(baseline_query_seconds - optimized_query_seconds, 3),
            },
            "pairs_found_only_by_baseline": [sorted(pair) for pair in sorted(only_baseline)],
            "pairs_found_only_by_optimized": [sorted(pair) for pair in sorted(only_optimized)],
        }

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        out_path = Path(args.output) if args.output else REPORT_DIR / f"candidate_comparison_{ts}Z.json"
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        print()
        print("=== Results ===")
        print(f"Baseline pairs found:   {len(baseline_pairs)}")
        print(f"Optimized pairs found:  {len(optimized_pairs)}")
        print(f"Pairs in both:          {len(both)}")
        print(f"Only in baseline:       {len(only_baseline)}  ← missed by optimized")
        print(f"Only in optimized:      {len(only_optimized)}  ← new finds")
        print(f"Recall vs baseline:     {recall:.2f}%")
        print()
        print("=== Performance ===")
        print(f"Baseline candidates:    {baseline_candidates_total}")
        print(f"Optimized candidates:   {optimized_candidates_total}")
        print(f"Candidate reduction:    {candidate_reduction_pct}%")
        print(f"Baseline query time:    {baseline_query_seconds:.3f}s")
        print(f"Optimized query time:   {optimized_query_seconds:.3f}s")
        print(f"Total elapsed:          {t_run_elapsed:.1f}s")
        print()
        print(f"Report written: {out_path}")

    finally:
        db_session.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
