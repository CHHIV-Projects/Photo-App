"""CLI entry point for HEIC preview generation.

Usage:
    python -m scripts.run_heic_preview_generation [--created-by NAME]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Ensure the backend package is importable when run directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.services.previews.heic_preview_processing_service import (
    HeicPreviewAlreadyRunningError,
    get_heic_preview_status,
    start_heic_preview_background,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate JPEG previews for HEIC assets.")
    parser.add_argument(
        "--created-by",
        default="cli",
        help="Label for the run record (default: cli).",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        status_view = get_heic_preview_status(db)
    finally:
        db.close()

    print(f"Pending HEIC previews: {status_view.pending_previews}")
    if status_view.pending_previews == 0:
        print("Nothing to do — all HEIC assets already have previews.")
        return

    try:
        result = start_heic_preview_background(created_by=args.created_by)
    except HeicPreviewAlreadyRunningError as exc:
        print(f"Already running: {exc}")
        sys.exit(1)

    print(f"Started run #{result.status.run_id}. Waiting for completion...")

    while True:
        time.sleep(3)
        db = SessionLocal()
        try:
            view = get_heic_preview_status(db)
        finally:
            db.close()

        snap = view.current
        print(
            f"  Status={snap.status}  processed={snap.assets_processed}/{snap.assets_pending}"
            f"  succeeded={snap.assets_succeeded}  failed={snap.assets_failed}"
        )

        if snap.status not in ("running", "stop_requested"):
            break

    print(f"Done. Final status: {view.current.status}")
    if view.current.last_error:
        print(f"Last error: {view.current.last_error}")


if __name__ == "__main__":
    main()
