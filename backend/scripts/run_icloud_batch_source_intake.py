"""Run internal Source Intake handoff for one durable iCloud acquisition batch."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal  # noqa: E402
from app.services.icloud_acquisition.batch_source_intake_service import (  # noqa: E402
    BatchSourceIntakeError,
    run_batch_source_intake,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Internal/non-UI handoff from a durable exact-selection iCloud "
            "acquisition batch to Source Intake."
        )
    )
    parser.add_argument("--batch-id", type=int, required=True)
    parser.add_argument("--source-id", type=int, default=None)
    parser.add_argument("--created-by", default="internal_script")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        with SessionLocal() as db_session:
            result = run_batch_source_intake(
                db_session,
                batch_id=args.batch_id,
                source_id=args.source_id,
                created_by=args.created_by,
            )
            payload = result.to_dict()
    except BatchSourceIntakeError as exc:
        payload = {
            "status": "blocked",
            "stop_reason": exc.code,
            "next_safe_action": exc.next_safe_action,
            "message": str(exc),
        }
    except Exception as exc:  # noqa: BLE001
        payload = {
            "status": "failed",
            "stop_reason": "unexpected_error",
            "next_safe_action": "Inspect backend logs and retry only after the cause is clear.",
            "message": str(exc)[:500],
        }

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("status") == "intake_completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
