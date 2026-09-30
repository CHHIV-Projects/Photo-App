"""Thin, stateless orchestration over existing durable acquisition authorities."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.source_acquisition import SourceAcquisitionItem, SourceAcquisitionRun
from app.models.windows_helper import WindowsHelperOperation
from app.schemas.source_acquisition import SourceAcquisitionWorkflowResponse
from app.services.source_acquisition.service import (
    activate_run,
    execute_acquisition_bridge,
    get_run,
    plan_acquisition_bridge,
)
from app.services.windows_helper.operations import create_acquire_operation
from app.services.windows_helper.service import WindowsHelperServiceError
from app.windows_helper_shared.protocol import HelperAcquireItemRequest


def _active_acquire_operation(
    db: Session, run_id: UUID
) -> WindowsHelperOperation | None:
    matching: list[WindowsHelperOperation] = []
    operations = list(
        db.scalars(
            select(WindowsHelperOperation).where(
                WindowsHelperOperation.operation_type == "acquire_item",
                WindowsHelperOperation.state.in_(("pending", "claimed")),
            )
        )
    )
    for operation in operations:
        request = HelperAcquireItemRequest.model_validate_json(operation.request_json)
        if request.acquisition_run_id == run_id:
            matching.append(operation)
    if len(matching) > 1:
        raise WindowsHelperServiceError(
            "acquisition_operation_ambiguous",
            "More than one active acquire operation exists for this acquisition run.",
            http_status=409,
        )
    return matching[0] if matching else None


def advance_source_acquisition_workflow(
    db: Session,
    run_id: UUID,
    *,
    proposal_digest: str | None,
) -> SourceAcquisitionWorkflowResponse:
    """Advance one safe asynchronous step under an already-approved proposal."""
    acquisition = get_run(db, run_id)
    if acquisition.state == "planned":
        if proposal_digest is None:
            return SourceAcquisitionWorkflowResponse(
                acquisition_run_id=run_id,
                stage="awaiting_approval",
                acquisition=acquisition,
                message="The exact acquisition proposal is awaiting Run Ingestion approval.",
            )
        acquisition = activate_run(db, run_id, proposal_digest)
    elif proposal_digest is not None and proposal_digest != acquisition.proposal_digest:
        raise WindowsHelperServiceError(
            "acquisition_proposal_mismatch",
            "The approved acquisition proposal digest does not match the durable run.",
            http_status=409,
        )

    if acquisition.state in {"failed", "cancelled"}:
        return SourceAcquisitionWorkflowResponse(
            acquisition_run_id=run_id,
            stage="failed",
            acquisition=acquisition,
            message="The acquisition did not complete and requires bounded review.",
        )

    if acquisition.state == "active":
        active_operation = _active_acquire_operation(db, run_id)
        if active_operation is not None:
            return SourceAcquisitionWorkflowResponse(
                acquisition_run_id=run_id,
                stage="awaiting_helper",
                acquisition=acquisition,
                helper_operation_id=UUID(active_operation.operation_uuid),
                helper_operation_state=active_operation.state,
                message="The exact acquisition item operation is awaiting the Helper.",
            )
        run = db.scalar(
            select(SourceAcquisitionRun).where(SourceAcquisitionRun.run_uuid == str(run_id))
        )
        if run is None:
            raise WindowsHelperServiceError(
                "acquisition_run_not_found", "The acquisition run was not found.", http_status=404
            )
        items = list(
            db.scalars(
                select(SourceAcquisitionItem)
                .where(SourceAcquisitionItem.run_id == run.id)
                .order_by(SourceAcquisitionItem.ordinal)
            )
        )
        next_item = next(
            (item for item in items if item.state in {"pending", "transferring"}), None
        )
        if next_item is None:
            raise WindowsHelperServiceError(
                "acquisition_state_inconsistent",
                "The active acquisition has no safely transferable next item.",
                http_status=409,
            )
        operation = create_acquire_operation(db, UUID(next_item.item_uuid))
        return SourceAcquisitionWorkflowResponse(
            acquisition_run_id=run_id,
            stage="awaiting_helper",
            acquisition=get_run(db, run_id),
            helper_operation_id=operation.operation_id,
            helper_operation_state=operation.state,
            message="The next exact acquisition item operation was authorized for the Helper.",
        )

    bridge = plan_acquisition_bridge(db, run_id)
    if bridge.bridge_state == "not_started":
        bridge = execute_acquisition_bridge(db, run_id, bridge.bridge_plan_digest)
    if bridge.bridge_state == "failed":
        stage = "failed"
    elif bridge.bridge_state == "completed":
        stage = "completed"
    else:
        stage = "bridge_running"
    return SourceAcquisitionWorkflowResponse(
        acquisition_run_id=run_id,
        stage=stage,
        acquisition=get_run(db, run_id),
        bridge=bridge,
        message=(
            "The approved Windows Source workflow completed."
            if stage == "completed"
            else "The common Source Intake bridge is running."
            if stage == "bridge_running"
            else "The bridge failed closed and requires bounded review."
        ),
    )
