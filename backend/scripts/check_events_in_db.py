"""Read-only database checker for Event records and assignments."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import func, select

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.models.asset import Asset
from app.models.event import Event

DEFAULT_LIMIT = 10


def _parse_limit(argv: list[str]) -> int:
    """Parse optional limit argument from CLI."""
    if len(argv) < 2:
        return DEFAULT_LIMIT

    try:
        parsed = int(argv[1])
        return parsed if parsed > 0 else DEFAULT_LIMIT
    except ValueError:
        return DEFAULT_LIMIT


def _event_to_dict(event: Event, assigned_count: int) -> dict[str, object]:
    """Convert one Event row into a JSON-friendly dictionary."""
    return {
        "id": event.id,
        "start_at": event.start_at.isoformat() if event.start_at else None,
        "end_at": event.end_at.isoformat() if event.end_at else None,
        "asset_count": event.asset_count,
        "assigned_asset_count": assigned_count,
        "label": event.label,
        "created_at_utc": event.created_at_utc.isoformat() if event.created_at_utc else None,
    }


def main() -> int:
    limit = _parse_limit(sys.argv)

    db_session = SessionLocal()
    try:
        total_events = db_session.scalar(select(func.count()).select_from(Event)) or 0
        total_assets_with_event = db_session.scalar(
            select(func.count()).select_from(Asset).where(Asset.event_id.is_not(None))
        ) or 0
        total_assets_without_event = db_session.scalar(
            select(func.count()).select_from(Asset).where(Asset.event_id.is_(None))
        ) or 0

        sample_events = list(db_session.scalars(select(Event).order_by(Event.start_at).limit(limit)).all())

        sample_records: list[dict[str, object]] = []
        for event in sample_events:
            assigned_count = db_session.scalar(
                select(func.count()).select_from(Asset).where(Asset.event_id == event.id)
            ) or 0
            sample_records.append(_event_to_dict(event, assigned_count))
    finally:
        db_session.close()

    output = {
        "total_events": total_events,
        "total_assets_with_event": total_assets_with_event,
        "total_assets_without_event": total_assets_without_event,
        "sample_limit": limit,
        "sample_count": len(sample_records),
        "sample_events": sample_records,
    }

    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
