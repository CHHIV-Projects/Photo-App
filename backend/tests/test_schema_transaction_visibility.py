"""Regression tests for same-transaction PostgreSQL schema visibility."""

from __future__ import annotations

from collections.abc import Callable
import re
import unittest
from unittest.mock import patch

from sqlalchemy.exc import NoSuchTableError

from app.services.albums import album_schema
from app.services.context_labels import schema as context_label_schema


class _Connection:
    """Identity object representing the Session's active connection."""


class _TransactionState:
    def __init__(self, initial_tables: set[str]) -> None:
        self.committed_tables = set(initial_tables)
        self.pending_tables: set[str] = set()
        self.committed_indexes: dict[str, set[str]] = {}
        self.pending_indexes: dict[str, set[str]] = {}

    def visible_tables(self, *, include_pending: bool) -> set[str]:
        tables = set(self.committed_tables)
        if include_pending:
            tables.update(self.pending_tables)
        return tables

    def visible_indexes(self, table_name: str, *, include_pending: bool) -> set[str]:
        indexes = set(self.committed_indexes.get(table_name, set()))
        if include_pending:
            indexes.update(self.pending_indexes.get(table_name, set()))
        return indexes

    def commit(self) -> None:
        self.committed_tables.update(self.pending_tables)
        for table_name, indexes in self.pending_indexes.items():
            self.committed_indexes.setdefault(table_name, set()).update(indexes)
        self.pending_tables.clear()
        self.pending_indexes.clear()

    def rollback(self) -> None:
        self.pending_tables.clear()
        self.pending_indexes.clear()


class _Inspector:
    def __init__(self, state: _TransactionState, *, include_pending: bool) -> None:
        self.state = state
        self.include_pending = include_pending

    def get_table_names(self) -> list[str]:
        return sorted(self.state.visible_tables(include_pending=self.include_pending))

    def get_columns(self, table_name: str) -> list[dict[str, str]]:
        if table_name not in self.state.visible_tables(include_pending=self.include_pending):
            raise NoSuchTableError(table_name)
        known_columns = {
            "assets": {"sha256"},
            "collections": {"grouping_type"},
            "place_observations": {"id"},
            "asset_context_labels": {"id"},
        }
        return [{"name": name} for name in sorted(known_columns.get(table_name, {"id"}))]

    def get_indexes(self, table_name: str) -> list[dict[str, str]]:
        if table_name not in self.state.visible_tables(include_pending=self.include_pending):
            raise NoSuchTableError(table_name)
        return [
            {"name": name}
            for name in sorted(
                self.state.visible_indexes(
                    table_name,
                    include_pending=self.include_pending,
                )
            )
        ]


class _Session:
    """Small harness modeling PostgreSQL visibility before transaction commit."""

    def __init__(
        self,
        initial_tables: set[str],
        *,
        fail_on_sql_fragment: str | None = None,
    ) -> None:
        self.state = _TransactionState(initial_tables)
        self.active_connection = _Connection()
        self.connection_calls = 0
        self.get_bind_calls = 0
        self.commit_calls = 0
        self.rollback_calls = 0
        self.inspection_targets: list[object] = []
        self.fail_on_sql_fragment = fail_on_sql_fragment

    def connection(self) -> _Connection:
        self.connection_calls += 1
        return self.active_connection

    def get_bind(self) -> object:
        self.get_bind_calls += 1
        raise AssertionError(
            "Schema inspection must use the Session connection that performed "
            "the uncommitted PostgreSQL DDL."
        )

    def inspect(self, target: object) -> _Inspector:
        self.inspection_targets.append(target)
        return _Inspector(
            self.state,
            include_pending=target is self.active_connection,
        )

    def execute(self, statement: object) -> None:
        sql = " ".join(str(statement).split())
        if self.fail_on_sql_fragment and self.fail_on_sql_fragment in sql:
            raise RuntimeError("injected schema failure")

        table_match = re.match(r"CREATE TABLE ([a-z_]+)", sql, re.IGNORECASE)
        if table_match:
            self.state.pending_tables.add(table_match.group(1).lower())
            return

        index_match = re.match(
            r"CREATE (?:UNIQUE )?INDEX ([a-z0-9_]+) ON ([a-z0-9_]+)",
            sql,
            re.IGNORECASE,
        )
        if index_match:
            index_name, table_name = (value.lower() for value in index_match.groups())
            self.state.pending_indexes.setdefault(table_name, set()).add(index_name)

    def commit(self) -> None:
        self.commit_calls += 1
        self.state.commit()

    def rollback(self) -> None:
        self.rollback_calls += 1
        self.state.rollback()


def _run_with_transaction_inspector(
    session: _Session,
    module: object,
    operation: Callable[[_Session], object],
) -> object:
    with patch.object(module, "inspect", side_effect=session.inspect):
        return operation(session)


class SchemaTransactionVisibilityTests(unittest.TestCase):
    def test_album_schema_creates_and_inspects_first_pass_on_session_connection(self) -> None:
        session = _Session({"assets"})

        summary = _run_with_transaction_inspector(
            session,
            album_schema,
            album_schema.ensure_album_schema,
        )

        self.assertEqual(
            summary.created_tables,
            ["collections", "collection_assets", "collection_albums"],
        )
        self.assertEqual(set(summary.created_indexes), set(album_schema.INDEX_DDLS))
        self.assertEqual(session.get_bind_calls, 0)
        self.assertGreaterEqual(session.connection_calls, 1)
        self.assertTrue(
            all(target is session.active_connection for target in session.inspection_targets)
        )
        self.assertEqual(session.commit_calls, 1)
        self.assertTrue(
            {"collections", "collection_assets", "collection_albums"}.issubset(
                session.state.committed_tables
            )
        )

    def test_context_label_schema_creates_first_pass_indexes_on_session_connection(self) -> None:
        session = _Session({"assets", "place_observations"})

        summary = _run_with_transaction_inspector(
            session,
            context_label_schema,
            context_label_schema.ensure_asset_context_label_schema,
        )

        self.assertEqual(summary.created_tables, ["asset_context_labels"])
        self.assertEqual(
            set(summary.created_indexes),
            set(context_label_schema.INDEX_DDLS),
        )
        self.assertEqual(session.get_bind_calls, 0)
        self.assertTrue(
            all(target is session.active_connection for target in session.inspection_targets)
        )
        self.assertEqual(
            session.state.committed_indexes["asset_context_labels"],
            set(context_label_schema.INDEX_DDLS),
        )

    def test_album_schema_failure_has_no_intermediate_commit_and_rolls_back(self) -> None:
        session = _Session(
            {"assets"},
            fail_on_sql_fragment="CREATE INDEX ix_collections_updated_at_utc",
        )

        with self.assertRaisesRegex(RuntimeError, "injected schema failure"):
            _run_with_transaction_inspector(
                session,
                album_schema,
                album_schema.ensure_album_schema,
            )

        self.assertEqual(session.commit_calls, 0)
        session.rollback()
        self.assertEqual(session.rollback_calls, 1)
        self.assertEqual(session.state.committed_tables, {"assets"})
        self.assertEqual(session.state.pending_tables, set())
        self.assertEqual(session.state.pending_indexes, {})

    def test_context_label_failure_has_no_intermediate_commit_and_rolls_back(self) -> None:
        session = _Session(
            {"assets", "place_observations"},
            fail_on_sql_fragment="CREATE INDEX ix_asset_context_labels_status",
        )

        with self.assertRaisesRegex(RuntimeError, "injected schema failure"):
            _run_with_transaction_inspector(
                session,
                context_label_schema,
                context_label_schema.ensure_asset_context_label_schema,
            )

        self.assertEqual(session.commit_calls, 0)
        session.rollback()
        self.assertEqual(
            session.state.committed_tables,
            {"assets", "place_observations"},
        )
        self.assertEqual(session.state.pending_tables, set())
        self.assertEqual(session.state.pending_indexes, {})

    def test_already_created_schemas_remain_idempotent(self) -> None:
        album_session = _Session({"assets"})
        context_session = _Session({"assets", "place_observations"})

        _run_with_transaction_inspector(
            album_session,
            album_schema,
            album_schema.ensure_album_schema,
        )
        second_album = _run_with_transaction_inspector(
            album_session,
            album_schema,
            album_schema.ensure_album_schema,
        )

        _run_with_transaction_inspector(
            context_session,
            context_label_schema,
            context_label_schema.ensure_asset_context_label_schema,
        )
        second_context = _run_with_transaction_inspector(
            context_session,
            context_label_schema,
            context_label_schema.ensure_asset_context_label_schema,
        )

        self.assertEqual(second_album.created_tables, [])
        self.assertEqual(second_album.created_indexes, [])
        self.assertEqual(second_context.created_tables, [])
        self.assertEqual(second_context.created_indexes, [])


if __name__ == "__main__":
    unittest.main()
