"""Backfill missing duplicate-lineage fields (pHash, quality score) deterministically."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.services.duplicates.lineage import backfill_missing_lineage_fields, recompute_near_duplicate_groups


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backfill duplicate-lineage fields")
    parser.add_argument("--dry-run", action="store_true", help="Report assets that would be backfilled without updating rows")
    parser.add_argument("--chunk-size", type=int, default=100, help="Commit every N assets (default: 100)")
    parser.add_argument(
        "--stage",
        choices=["all", "fields", "groups"],
        default="all",
        help="Run fields-only, groups-only, or both (default: all)",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    db_session = SessionLocal()
    try:
        field_summary = None
        grouping_summary = None

        if args.stage in {"all", "fields"}:
            field_summary = backfill_missing_lineage_fields(
                db_session,
                chunk_size=max(1, args.chunk_size),
                dry_run=args.dry_run,
            )

        if args.stage in {"all", "groups"}:
            grouping_summary = recompute_near_duplicate_groups(db_session, dry_run=args.dry_run)
    finally:
        db_session.close()

    print(
        json.dumps(
            {
                "dry_run": args.dry_run,
                "chunk_size": max(1, args.chunk_size),
                "stage": args.stage,
                "field_backfill": (
                    {
                        "processed": field_summary.processed,
                        "updated": field_summary.updated,
                        "skipped": field_summary.skipped,
                        "failed": field_summary.failed,
                    }
                    if field_summary is not None
                    else None
                ),
                "grouping": (
                    {
                        "processed": grouping_summary.processed,
                        "near_groups_created": grouping_summary.updated,
                        "failed": grouping_summary.failed,
                    }
                    if grouping_summary is not None
                    else None
                ),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
