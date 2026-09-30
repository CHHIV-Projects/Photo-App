from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from app.schemas.source_acquisition import (
    SourceAcquisitionBridgePlanResponse,
    SourceAcquisitionRunResponse,
)
from app.services.source_acquisition.workflow import advance_source_acquisition_workflow


class SourceAcquisitionWorkflowTests(unittest.TestCase):
    def _acquisition(self, *, state: str) -> SourceAcquisitionRunResponse:
        return SourceAcquisitionRunResponse.model_construct(
            acquisition_run_id=uuid4(),
            proposal_digest="sha256:" + "a" * 64,
            state=state,
        )

    def test_approved_planned_run_activates_and_authorizes_one_item(self) -> None:
        run_id = uuid4()
        planned = self._acquisition(state="planned")
        active = self._acquisition(state="active")
        item_id = uuid4()
        db = Mock()
        db.scalar.return_value = SimpleNamespace(id=7)
        db.scalars.return_value = [SimpleNamespace(item_uuid=str(item_id), state="pending")]
        operation_id = uuid4()

        with patch(
            "app.services.source_acquisition.workflow.get_run",
            side_effect=[planned, active],
        ), patch(
            "app.services.source_acquisition.workflow.activate_run",
            return_value=active,
        ) as activate, patch(
            "app.services.source_acquisition.workflow._active_acquire_operation",
            return_value=None,
        ), patch(
            "app.services.source_acquisition.workflow.create_acquire_operation",
            return_value=SimpleNamespace(operation_id=operation_id, state="pending"),
        ) as create:
            result = advance_source_acquisition_workflow(
                db,
                run_id,
                proposal_digest=planned.proposal_digest,
            )

        self.assertEqual(result.stage, "awaiting_helper")
        self.assertEqual(result.helper_operation_id, operation_id)
        activate.assert_called_once_with(db, run_id, planned.proposal_digest)
        create.assert_called_once_with(db, item_id)

    def test_completed_acquisition_plans_and_executes_bridge(self) -> None:
        run_id = uuid4()
        completed = self._acquisition(state="completed")
        planned_bridge = SourceAcquisitionBridgePlanResponse.model_construct(
            bridge_state="not_started",
            bridge_plan_digest="sha256:" + "b" * 64,
        )
        completed_bridge = SourceAcquisitionBridgePlanResponse.model_construct(
            bridge_state="completed",
            bridge_plan_digest=planned_bridge.bridge_plan_digest,
        )
        db = Mock()

        with patch(
            "app.services.source_acquisition.workflow.get_run",
            side_effect=[completed, completed],
        ), patch(
            "app.services.source_acquisition.workflow.plan_acquisition_bridge",
            return_value=planned_bridge,
        ), patch(
            "app.services.source_acquisition.workflow.execute_acquisition_bridge",
            return_value=completed_bridge,
        ) as execute:
            result = advance_source_acquisition_workflow(
                db, run_id, proposal_digest=None
            )

        self.assertEqual(result.stage, "completed")
        self.assertIs(result.bridge, completed_bridge)
        execute.assert_called_once_with(db, run_id, planned_bridge.bridge_plan_digest)


if __name__ == "__main__":
    unittest.main()
