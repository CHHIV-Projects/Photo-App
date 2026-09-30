"""Additive schema synchronization for generalized NAS registration."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.models.nas_registration import (
    NasApplianceRegistration,
    NasPendingRegistration,
    NasShareRegistration,
)


@dataclass(frozen=True)
class NasRegistrationSchemaSummary:
    created_tables: list[str]


def ensure_nas_registration_schema(db_session: Session) -> NasRegistrationSchemaSummary:
    """Create only the additive NAS registry tables, idempotently."""

    connection = db_session.connection()
    existing = set(inspect(connection).get_table_names())
    required = {"source_endpoints"}
    if not required.issubset(existing):
        raise RuntimeError("Expected Source Endpoint schema before NAS registration schema sync.")
    created: list[str] = []
    for table in (
        NasApplianceRegistration.__table__,
        NasShareRegistration.__table__,
        NasPendingRegistration.__table__,
    ):
        if table.name not in existing:
            table.create(bind=connection, checkfirst=True)
            created.append(table.name)
        else:
            table.create(bind=connection, checkfirst=True)
        existing.add(table.name)
    db_session.commit()
    return NasRegistrationSchemaSummary(created_tables=created)

