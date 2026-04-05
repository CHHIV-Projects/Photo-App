"""Run event clustering for existing assets in the database."""

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
from app.services.organization.event_clusterer import (
    cluster_assets_into_events,
    persist_event_clusters,
)


def main() -> int:
    db_session = SessionLocal()
    try:
        clustering_result = cluster_assets_into_events(
            db_session=db_session,
            gap_seconds=settings.event_cluster_gap_seconds,
        )
        persistence_result = persist_event_clusters(db_session, clustering_result)
    finally:
        db_session.close()

    output = {
        "event_gap_seconds": settings.event_cluster_gap_seconds,
        "total_assets_considered": clustering_result.considered_assets,
        "assets_skipped_missing_captured_at": clustering_result.skipped_missing_captured_at,
        "assets_skipped_scans": clustering_result.skipped_scans,
        "total_events_created": persistence_result.events_created,
        "assigned_assets": persistence_result.assigned_assets,
        "largest_event_size": persistence_result.largest_event_size,
        "smallest_event_size": persistence_result.smallest_event_size,
        "failed": persistence_result.failed,
    }

    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
