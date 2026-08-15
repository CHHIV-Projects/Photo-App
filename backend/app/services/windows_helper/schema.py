"""Additive schema synchronization for Windows Helper trust state."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.models.windows_helper import (
    WindowsHelperCredential,
    WindowsHelperOperation,
    WindowsHelperPairingAuthorization,
)


@dataclass(frozen=True)
class WindowsHelperSchemaSummary:
    created_tables: list[str]


def ensure_windows_helper_schema(db_session: Session) -> WindowsHelperSchemaSummary:
    """Create only the additive credential/pairing tables, idempotently."""

    connection = db_session.connection()
    existing_tables = set(inspect(connection).get_table_names())
    if "access_nodes" not in existing_tables:
        raise RuntimeError("Expected 'access_nodes' before Windows Helper schema sync.")

    created_tables: list[str] = []
    for table in (
        WindowsHelperCredential.__table__,
        WindowsHelperPairingAuthorization.__table__,
        WindowsHelperOperation.__table__,
    ):
        if table.name not in existing_tables:
            table.create(bind=connection, checkfirst=True)
            created_tables.append(table.name)
        else:
            table.create(bind=connection, checkfirst=True)
        existing_tables.add(table.name)

    db_session.commit()
    return WindowsHelperSchemaSummary(created_tables=created_tables)
