"""Add account_username field to ingestion_sources table for 12.44.0.

This migration adds a non-secret field to track the associated Apple ID username
for iCloud sources, enabling safer source/account matching and operator guidance.
"""

import sys
from pathlib import Path

# Add backend to path for imports
CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import Column, String, text

from app.db.session import engine, SessionLocal
from app.models.ingestion_source import IngestionSource


def migrate_add_account_username():
    """Add account_username column to ingestion_sources table if not present."""
    db_session = SessionLocal()
    try:
        # Check if column already exists by querying
        inspector_result = db_session.execute(
            text(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'ingestion_sources' AND column_name = 'account_username'
                """
            )
        ).fetchall()

        if inspector_result:
            print("✓ Column 'account_username' already exists. Migration skipped.")
            return True

        # Add the column
        print("Adding 'account_username' column to ingestion_sources table...")
        db_session.execute(
            text(
                """
                ALTER TABLE ingestion_sources
                ADD COLUMN account_username VARCHAR(255) NULL
                """
            )
        )
        db_session.commit()
        print("✓ Column 'account_username' added successfully.")
        return True

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        db_session.rollback()
        return False

    finally:
        db_session.close()


if __name__ == "__main__":
    success = migrate_add_account_username()
    sys.exit(0 if success else 1)
