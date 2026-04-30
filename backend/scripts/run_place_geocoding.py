"""Manual CLI entry point for place geocoding processing."""

from __future__ import annotations

import json
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.services.location.place_geocoding_schema import ensure_place_geocoding_schema
from app.services.location.place_geocoding_service import start_place_geocoding_background


def main() -> int:
    """Start place geocoding in the background."""
    db_session = SessionLocal()
    try:
        schema_summary = ensure_place_geocoding_schema(db_session.connection())

        result = start_place_geocoding_background(created_by="manual_script")

        payload = {
            "status": result.status.status,
            "run_id": result.status.run_id,
            "message": result.message,
            "total_places": result.status.total_places,
            "pending_places": result.status.total_places,  # At start, all are pending
            "schema_created_tables": schema_summary.created_tables,
        }

        print(json.dumps(payload, indent=2))
        return 0

    except Exception as exc:  # noqa: BLE001
        error_payload = {
            "status": "failed",
            "error": str(exc),
            "message": f"Failed to start place geocoding: {exc}",
        }
        print(json.dumps(error_payload, indent=2), file=sys.stderr)
        return 1
    finally:
        db_session.close()


if __name__ == "__main__":
    raise SystemExit(main())
