"""Initialize PostgreSQL tables for local development."""

from __future__ import annotations

import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
	sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import create_all_tables, test_database_connection
from app.models.asset import Asset


def main() -> int:
	_ = Asset
	test_database_connection()
	create_all_tables()
	print("Database connection successful. Tables created or already present.")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
