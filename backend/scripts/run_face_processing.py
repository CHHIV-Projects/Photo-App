"""Manual CLI entry point for background face processing.

Runs all four face processing stages in order:
  1. Face detection
  2. Face embedding
  3. Face clustering (incremental only)
  4. Crop generation

Usage:
    python scripts/run_face_processing.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.services.face.face_processing_schema import ensure_face_processing_schema
from app.services.face.face_processing_service import (
    FaceProcessingAlreadyRunningError,
    get_face_processing_status,
    start_face_processing_background,
)


def main() -> int:
    """Start face processing and wait for completion."""
    db_session = SessionLocal()
    try:
        schema_summary = ensure_face_processing_schema(db_session)

        result = start_face_processing_background(created_by="manual_script")

        payload = {
            "status": result.status.status,
            "run_id": result.status.run_id,
            "message": f"{result.message} Waiting for completion...",
            "schema_created_tables": schema_summary.created_tables,
            "face_incremental_columns_added": schema_summary.face_incremental_columns_added,
        }

        print(json.dumps(payload, indent=2))

        while True:
            time.sleep(3)
            poll_db = SessionLocal()
            try:
                status_view = get_face_processing_status(poll_db)
            finally:
                poll_db.close()

            snap = status_view.current
            print(
                json.dumps(
                    {
                        "run_id": snap.run_id,
                        "status": snap.status,
                        "current_stage": snap.current_stage,
                        "assets_processed_detection": snap.assets_processed_detection,
                        "assets_pending_detection": snap.assets_pending_detection,
                        "faces_processed_embedding": snap.faces_processed_embedding,
                        "faces_pending_embedding": snap.faces_pending_embedding,
                        "faces_processed_clustering": snap.faces_processed_clustering,
                        "faces_pending_clustering": snap.faces_pending_clustering,
                        "crops_generated": snap.crops_generated,
                        "crops_pending": snap.crops_pending,
                    }
                )
            )

            if snap.status not in ("running", "stop_requested"):
                return 0 if snap.status == "completed" else 1

    except FaceProcessingAlreadyRunningError as exc:
        error_payload = {
            "status": exc.status.status,
            "run_id": exc.status.run_id,
            "message": "A face processing run is already active. Use Admin stop or wait for completion.",
        }
        print(json.dumps(error_payload, indent=2), file=sys.stderr)
        return 1

    except Exception as exc:  # noqa: BLE001
        error_payload = {
            "status": "failed",
            "error": str(exc),
            "message": f"Failed to start face processing: {exc}",
        }
        print(json.dumps(error_payload, indent=2), file=sys.stderr)
        return 1

    finally:
        db_session.close()


if __name__ == "__main__":
    raise SystemExit(main())
