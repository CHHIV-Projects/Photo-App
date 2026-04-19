"""Backfill metadata observations and recompute canonical metadata for image assets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.services.metadata.canonicalization_service import backfill_observations_and_canonicalize
from app.services.metadata.metadata_canonicalization_schema import ensure_metadata_canonicalization_schema


def main() -> int:
    db_session = SessionLocal()
    try:
        schema_summary = ensure_metadata_canonicalization_schema(db_session)
        summary = backfill_observations_and_canonicalize(db_session)
    finally:
        db_session.close()

    payload = {
        "schema_added_tables": schema_summary.ensured_tables,
        "schema_added_columns": schema_summary.added_columns,
        "assets_considered": summary.assets_considered,
        "observations_inserted": summary.observations_inserted,
        "observations_skipped": summary.observations_skipped,
        "observations_failed": summary.observations_failed,
        "legacy_seeded": summary.legacy_seeded,
        "limited_coverage_assets": summary.limited_coverage_assets,
        "canonical_updated": summary.canonical_updated,
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
