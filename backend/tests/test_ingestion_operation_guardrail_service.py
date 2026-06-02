from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.admin.ingestion_operation_guardrail_service import get_ingestion_operation_guardrail_snapshot


class IngestionOperationGuardrailServiceTests(unittest.TestCase):
    def test_returns_blocking_reasons_for_active_operations(self) -> None:
        db = MagicMock()

        with patch(
            "app.services.admin.ingestion_operation_guardrail_service._latest_active_acquisition",
            return_value=SimpleNamespace(id=1),
        ), patch(
            "app.services.admin.ingestion_operation_guardrail_service._latest_active_source_intake",
            return_value=SimpleNamespace(id=2, ingestion_source_id=7),
        ), patch(
            "app.services.admin.ingestion_operation_guardrail_service._latest_active_cleanup",
            return_value=None,
        ):
            snapshot = get_ingestion_operation_guardrail_snapshot(db, source_id=7)

        self.assertTrue(snapshot.blocked)
        self.assertTrue(snapshot.operation_conflicts.icloud_acquisition_active)
        self.assertTrue(snapshot.operation_conflicts.source_intake_active)
        self.assertFalse(snapshot.operation_conflicts.icloud_cleanup_active)
        self.assertTrue(snapshot.operation_conflicts.source_intake_active_for_this_source)
        self.assertIsNone(snapshot.operation_conflicts.icloud_cleanup_active_for_this_source)
        self.assertEqual(snapshot.active_operation, "icloud_acquisition")
        self.assertEqual(
            [reason.code for reason in snapshot.blocking_reasons],
            ["ICLOUD_ACQUISITION_ACTIVE", "SOURCE_INTAKE_ACTIVE"],
        )

    def test_source_specific_conflict_is_null_when_source_context_unknown(self) -> None:
        db = MagicMock()

        with patch(
            "app.services.admin.ingestion_operation_guardrail_service._latest_active_acquisition",
            return_value=None,
        ), patch(
            "app.services.admin.ingestion_operation_guardrail_service._latest_active_source_intake",
            return_value=SimpleNamespace(id=2, ingestion_source_id=11),
        ), patch(
            "app.services.admin.ingestion_operation_guardrail_service._latest_active_cleanup",
            return_value=SimpleNamespace(id=3, ingestion_source_id=None),
        ):
            snapshot = get_ingestion_operation_guardrail_snapshot(db, source_id=None)

        self.assertIsNone(snapshot.operation_conflicts.source_intake_active_for_this_source)
        self.assertIsNone(snapshot.operation_conflicts.icloud_cleanup_active_for_this_source)


if __name__ == "__main__":
    unittest.main()
