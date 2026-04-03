"""SQLAlchemy engine and session setup for local development."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
	"""Base class for all SQLAlchemy models."""


engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db_session() -> Generator[Session, None, None]:
	"""Yield a SQLAlchemy session and ensure it closes after use."""
	db_session = SessionLocal()
	try:
		yield db_session
	finally:
		db_session.close()


def test_database_connection() -> None:
	"""Run a simple query to confirm the PostgreSQL connection works."""
	with engine.connect() as connection:
		connection.execute(text("SELECT 1"))


def create_all_tables() -> None:
	"""Create all registered SQLAlchemy tables for local development."""
	Base.metadata.create_all(bind=engine)


def drop_all_tables() -> None:
	"""Drop all registered SQLAlchemy tables for local development reset."""
	Base.metadata.drop_all(bind=engine)
