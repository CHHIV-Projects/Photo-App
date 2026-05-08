"""CLI entry point for deterministic Live Photo still/motion pairing."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure the backend package is importable when run directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.services.live_photo.pairing_reporting import build_report_payload, write_report
from app.services.live_photo.pairing_schema import ensure_live_photo_pairing_schema
from app.services.live_photo.pairing_service import run_live_photo_pairing


def main() -> None:
    parser = argparse.ArgumentParser(description="Build deterministic Live Photo still<->motion pairs.")
    parser.add_argument(
        "--write-report",
        action="store_true",
        default=True,
        help="Write a JSON report under storage/logs/live_photo_pairing_reports (default: enabled).",
    )
    parser.add_argument(
        "--no-write-report",
        action="store_false",
        dest="write_report",
        help="Disable JSON report output.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        schema_summary = ensure_live_photo_pairing_schema(db)
        result = run_live_photo_pairing(db)
    finally:
        db.close()

    report_payload = build_report_payload(schema_summary, result)

    print("Live Photo pairing complete")
    print(json.dumps(report_payload["summary"], indent=2))

    if args.write_report:
        report_path = write_report(report_payload)
        print(f"Report written: {report_path}")


if __name__ == "__main__":
    main()
