"""Backfill reverse geocoding data for existing places."""

from __future__ import annotations

import json
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.location.geocoding_service import enrich_places_with_reverse_geocoding
from app.services.places.place_schema import ensure_place_schema


def main() -> int:
    db_session = SessionLocal()
    try:
        schema_summary = ensure_place_schema(db_session)
        geocode_summary = enrich_places_with_reverse_geocoding(
            db_session,
            place_ids=None,
            include_failed=True,
            max_calls=settings.place_geocode_max_calls_per_run,
        )
    finally:
        db_session.close()

    payload = {
        "schema_created_tables": schema_summary.created_tables,
        "schema_added_columns": schema_summary.added_columns,
        "schema_created_indexes": schema_summary.created_indexes,
        "eligible_places": geocode_summary.eligible_places,
        "attempted_calls": geocode_summary.attempted_calls,
        "successful": geocode_summary.successful,
        "failed": geocode_summary.failed,
        "skipped_due_to_cap": geocode_summary.skipped_due_to_cap,
        "max_calls_per_run": settings.place_geocode_max_calls_per_run,
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
