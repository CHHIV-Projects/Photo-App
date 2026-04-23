"""Backfill stable place assignments for all canonical-GPS assets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.services.places.grouping import assign_assets_to_places
from app.services.places.place_schema import ensure_place_schema


def main() -> int:
    db_session = SessionLocal()
    try:
        schema_summary = ensure_place_schema(db_session)
        grouping_summary = assign_assets_to_places(db_session, asset_sha256_list=None)
    finally:
        db_session.close()

    payload = {
        "schema_created_tables": schema_summary.created_tables,
        "schema_added_columns": schema_summary.added_columns,
        "schema_created_indexes": schema_summary.created_indexes,
        "considered_assets": grouping_summary.considered_assets,
        "assigned_assets": grouping_summary.assigned_assets,
        "created_places": grouping_summary.created_places,
        "matched_existing_places": grouping_summary.matched_existing_places,
        "skipped_without_gps": grouping_summary.skipped_without_gps,
        "skipped_already_assigned": grouping_summary.skipped_already_assigned,
        "skipped_invalid_gps": grouping_summary.skipped_invalid_gps,
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
