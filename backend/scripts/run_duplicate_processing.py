"""Run incremental duplicate lineage processing synchronously.

Usage:
    python scripts/run_duplicate_processing.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.duplicates.processing_service import (
    DuplicateProcessingAlreadyRunningError,
    DuplicateProcessingStatusSnapshot,
    run_duplicate_processing_sync,
)


def _snapshot_to_dict(snapshot: DuplicateProcessingStatusSnapshot) -> dict[str, object]:
    return {
        "run_id": snapshot.run_id,
        "status": snapshot.status,
        "started_at": snapshot.started_at.isoformat() if snapshot.started_at else None,
        "finished_at": snapshot.finished_at.isoformat() if snapshot.finished_at else None,
        "elapsed_seconds": snapshot.elapsed_seconds,
        "total_items": snapshot.total_items,
        "processed_items": snapshot.processed_items,
        "current_stage": snapshot.current_stage,
        "error_message": snapshot.error_message,
        "stop_requested": snapshot.stop_requested,
        "workset_cutoff": snapshot.workset_cutoff.isoformat() if snapshot.workset_cutoff else None,
        "last_successful_cutoff": (
            snapshot.last_successful_cutoff.isoformat() if snapshot.last_successful_cutoff else None
        ),
    }


def _print_progress(snapshot: DuplicateProcessingStatusSnapshot) -> None:
    if snapshot.run_id is None:
        return
    print(
        f"[progress] run={snapshot.run_id} "
        f"status={snapshot.status} "
        f"processed={snapshot.processed_items}/{snapshot.total_items}"
    )


def main() -> int:
    print("[run] Starting duplicate processing...")

    try:
        final_status = run_duplicate_processing_sync(created_by="manual_script", progress_callback=_print_progress)
    except DuplicateProcessingAlreadyRunningError as exc:
        print("[run] Cannot start: another duplicate-processing run is active.")
        print(json.dumps(_snapshot_to_dict(exc.status), indent=2))
        return 2

    print("[run] Final status:")
    print(json.dumps(_snapshot_to_dict(final_status), indent=2))

    if final_status.status in {"completed", "stopped"}:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
