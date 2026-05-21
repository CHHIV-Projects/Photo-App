"""Add person_aliases table for Milestone 12.56 (idempotent)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import inspect

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.models.person import Person  # noqa: F401
from app.models.person_alias import PersonAlias


def main() -> int:
    db_session = SessionLocal()
    ensured_table = False

    try:
        bind = db_session.get_bind()
        existing_tables = set(inspect(bind).get_table_names())
        if "person_aliases" not in existing_tables:
            PersonAlias.__table__.create(bind=bind, checkfirst=True)
            ensured_table = True
        else:
            PersonAlias.__table__.create(bind=bind, checkfirst=True)

        db_session.commit()
    finally:
        db_session.close()

    print(json.dumps({"table": "person_aliases", "created": ensured_table}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
