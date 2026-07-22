"""Selected-source Run Ingestion dispatch service.

This is the thin Step 3 integration seam. It revalidates Source Selection,
then routes to the existing filesystem Source Intake or iCloud Intake
authorities without creating new selected-source persistence.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.schemas.admin import (
    RunIngestionDispatchRequest,
    RunIngestionDispatchResponse,
)
from app.services.admin.ingestion_operation_guardrail_service import get_ingestion_operation_guardrail_snapshot
from app.services.admin.source_intake_execution_service import (
    SourceIntakeAlreadyRunningError,
    SourceIntakeReadinessBlockedError,
    start_source_intake,
)
from app.services.icloud_historical_routine_service import (
    IcloudHistoricalRoutineError,
    advance_icloud_intake_import,
    get_icloud_intake_import_status,
    refresh_historical_inventory,
    resume_icloud_intake_import,
    start_icloud_intake_import,
)
from app.services.source_identity import SourceIdentityProbeService, SourceSelectionRequest, SourceSelectionService
from app.services.source_identity.source_selection_schema import SourceSelectionResponse


DEFAULT_FILESYSTEM_BATCH_SIZE = 500
DEFAULT_ICLOUD_INTERNAL_BATCH_SIZE = 100
ICLOUD_PREPARE_SCAN_CAP = 10000
_ENABLED_FILESYSTEM_FRIENDLY_TYPES = {"Local", "External", "Removable"}


class RunIngestionDispatchError(ValueError):
    """Raised for invalid selected-source dispatch requests."""

    def __init__(self, message: str, *, code: str = "RUN_INGESTION_DISPATCH_INVALID") -> None:
        super().__init__(message)
        self.code = code


class RunIngestionDispatchService:
    """Revalidate selected Source state and dispatch one safe Step 3 action."""

    def __init__(
        self,
        db_session: Session,
        *,
        source_selection_service: SourceSelectionService | None = None,
        probe_service: SourceIdentityProbeService | None = None,
    ) -> None:
        self._db = db_session
        self._source_selection_service = source_selection_service or SourceSelectionService(
            db_session=db_session,
            probe_service=probe_service,
        )

    def dispatch(self, request: RunIngestionDispatchRequest) -> RunIngestionDispatchResponse:
        selection = self._source_selection_service.select_source(
            SourceSelectionRequest(source_profile_id=request.source_profile_id)
        )
        blocked = self._blocked_for_unselected(request.source_profile_id, selection)
        if blocked is not None:
            return blocked

        context = selection.selected_source_context
        if context is None or selection.workflow_kind is None:
            return RunIngestionDispatchResponse(
                result="blocked",
                workflow_kind=None,
                action="none",
                message="Select and verify a Source before running ingestion.",
                next_action="Select Source again.",
                source_profile_id=request.source_profile_id,
                status=selection.availability,
                workflow_payload={"selection": _safe_payload(selection)},
            )

        if request.selection_fingerprint and request.selection_fingerprint != context.selection_fingerprint:
            return RunIngestionDispatchResponse(
                result="stale_selection",
                workflow_kind=selection.workflow_kind,
                action="none",
                message="The selected Source changed after it was selected.",
                next_action="Select Source again before running ingestion.",
                source_profile_id=request.source_profile_id,
                status="stale_selection",
                workflow_payload={"selection": _safe_payload(selection)},
            )

        if selection.workflow_kind == "filesystem_source_intake":
            if request.icloud_options is not None:
                raise RunIngestionDispatchError(
                    "iCloud options are not valid for filesystem Source Intake.",
                    code="ICLOUD_OPTIONS_FOR_FILESYSTEM_WORKFLOW",
                )
            return self._dispatch_filesystem(request, selection)

        if selection.workflow_kind == "icloud_intake":
            if request.filesystem_options is not None:
                raise RunIngestionDispatchError(
                    "Filesystem options are not valid for iCloud Intake.",
                    code="FILESYSTEM_OPTIONS_FOR_ICLOUD_WORKFLOW",
                )
            return self._dispatch_icloud(request, selection)

        return RunIngestionDispatchResponse(
            result="blocked",
            workflow_kind=selection.workflow_kind,
            action="none",
            message="This selected Source workflow is not supported by Run Ingestion.",
            next_action="Use the appropriate recovery or provider-specific workflow.",
            source_profile_id=request.source_profile_id,
            status="unsupported_workflow",
            workflow_payload={"selection": _safe_payload(selection)},
        )

    def _blocked_for_unselected(
        self,
        source_profile_id: int,
        selection: SourceSelectionResponse,
    ) -> RunIngestionDispatchResponse | None:
        if (
            selection.result == "selected"
            and selection.availability == "available"
            and selection.workflow_kind is not None
            and selection.selected_source_context is not None
        ):
            return None
        return RunIngestionDispatchResponse(
            result="blocked",
            workflow_kind=selection.workflow_kind,
            action="none",
            message=selection.message,
            next_action=selection.retry_guidance or "Select Source again when it is available.",
            source_profile_id=source_profile_id,
            status=selection.availability,
            workflow_payload={"selection": _safe_payload(selection)},
        )

    def _dispatch_filesystem(
        self,
        request: RunIngestionDispatchRequest,
        selection: SourceSelectionResponse,
    ) -> RunIngestionDispatchResponse:
        context = selection.selected_source_context
        assert context is not None

        if context.friendly_source_type == "NAS":
            return RunIngestionDispatchResponse(
                result="blocked",
                workflow_kind="filesystem_source_intake",
                action="none",
                message="NAS Run Ingestion is not enabled in the normal Step 3 workflow yet.",
                next_action="Use an approved management or future NAS validation workflow.",
                source_profile_id=request.source_profile_id,
                status="nas_not_enabled",
                workflow_payload={"selection": _safe_payload(selection)},
            )
        if context.friendly_source_type == "Optical":
            return RunIngestionDispatchResponse(
                result="blocked",
                workflow_kind="filesystem_source_intake",
                action="none",
                message="Optical Run Ingestion is not enabled in the normal Step 3 workflow yet.",
                next_action="Use a future Optical execution workflow after validation.",
                source_profile_id=request.source_profile_id,
                status="optical_not_enabled",
                workflow_payload={"selection": _safe_payload(selection)},
            )
        if context.friendly_source_type not in _ENABLED_FILESYSTEM_FRIENDLY_TYPES and context.source_endpoint_id is not None:
            return RunIngestionDispatchResponse(
                result="blocked",
                workflow_kind="filesystem_source_intake",
                action="none",
                message="This filesystem Source type is not enabled in normal Run Ingestion yet.",
                next_action="Use an approved management or recovery workflow.",
                source_profile_id=request.source_profile_id,
                status="source_type_not_enabled",
                workflow_payload={"selection": _safe_payload(selection)},
            )

        runtime_root = context.resolved_source_root
        if not runtime_root:
            return RunIngestionDispatchResponse(
                result="blocked",
                workflow_kind="filesystem_source_intake",
                action="none",
                message="The selected Source did not provide a resolved runtime Source Root.",
                next_action="Select Source again.",
                source_profile_id=request.source_profile_id,
                status="runtime_root_missing",
                workflow_payload={"selection": _safe_payload(selection)},
            )

        guardrail = get_ingestion_operation_guardrail_snapshot(self._db, source_id=request.source_profile_id)
        if guardrail.blocked:
            return RunIngestionDispatchResponse(
                result="blocked",
                workflow_kind="filesystem_source_intake",
                action="none",
                message="Another ingestion-related operation is active.",
                next_action="Wait for the active operation to finish or stop it before running ingestion.",
                source_profile_id=request.source_profile_id,
                status="operation_conflict",
                workflow_payload={"operation_conflicts": _safe_payload(guardrail)},
            )

        options = request.filesystem_options
        limit = options.source_intake_limit if options is not None else None
        batch_size = options.ingest_batch_size if options is not None and options.ingest_batch_size is not None else DEFAULT_FILESYSTEM_BATCH_SIZE
        acknowledged = bool(options.acknowledge_legacy_or_review) if options is not None else False
        selection_verified_identity = context.source_endpoint_id is not None and context.identity_match_status == "matched"

        try:
            snapshot = start_source_intake(
                self._db,
                ingestion_source_id=request.source_profile_id,
                source_intake_limit=limit,
                ingest_batch_size=batch_size,
                readiness_acknowledged=acknowledged,
                created_by="run_ingestion_dispatch",
                runtime_source_root_path=runtime_root,
                selection_verified_identity=selection_verified_identity,
            )
        except SourceIntakeReadinessBlockedError as exc:
            return RunIngestionDispatchResponse(
                result="blocked",
                workflow_kind="filesystem_source_intake",
                action="none",
                message=exc.detail,
                next_action=exc.readiness.recommended_next_action,
                source_profile_id=request.source_profile_id,
                status=exc.error_code,
                workflow_payload={"readiness": _safe_payload(exc.readiness)},
            )
        except SourceIntakeAlreadyRunningError as exc:
            return RunIngestionDispatchResponse(
                result="blocked",
                workflow_kind="filesystem_source_intake",
                action="none",
                message="A Source Intake run is already active.",
                next_action="Wait for the active Source Intake run to finish or stop it.",
                source_profile_id=request.source_profile_id,
                underlying_run_id=exc.snapshot.run_id,
                status=exc.snapshot.status,
                workflow_payload={"current": _safe_payload(exc.snapshot)},
            )
        except ValueError as exc:
            return RunIngestionDispatchResponse(
                result="blocked",
                workflow_kind="filesystem_source_intake",
                action="none",
                message=str(exc),
                next_action="Review the Source and select it again.",
                source_profile_id=request.source_profile_id,
                status="launch_blocked",
                workflow_payload={"selection": _safe_payload(selection)},
            )

        return RunIngestionDispatchResponse(
            result="started",
            workflow_kind="filesystem_source_intake",
            action="source_intake_started",
            message="Source Intake started.",
            next_action=None,
            source_profile_id=request.source_profile_id,
            underlying_run_id=snapshot.run_id,
            status=snapshot.status,
            workflow_payload={"current": _safe_payload(snapshot), "selection": _safe_payload(selection)},
        )

    def _dispatch_icloud(
        self,
        request: RunIngestionDispatchRequest,
        selection: SourceSelectionResponse,
    ) -> RunIngestionDispatchResponse:
        guardrail = get_ingestion_operation_guardrail_snapshot(self._db, source_id=request.source_profile_id)
        if guardrail.blocked:
            return RunIngestionDispatchResponse(
                result="blocked",
                workflow_kind="icloud_intake",
                action="none",
                message="Another ingestion-related operation is active.",
                next_action="Wait for the active operation to finish or stop it before running iCloud Intake.",
                source_profile_id=request.source_profile_id,
                status="operation_conflict",
                workflow_payload={"operation_conflicts": _safe_payload(guardrail)},
            )

        target = request.icloud_options.target_logical_items if request.icloud_options is not None else None
        try:
            current = get_icloud_intake_import_status(self._db, source_id=request.source_profile_id)
            if current.can_resume_import:
                next_status = resume_icloud_intake_import(
                    self._db,
                    source_id=request.source_profile_id,
                    import_run_id=current.import_run_id,
                )
                return _icloud_response(
                    request.source_profile_id,
                    action="icloud_import_resumed",
                    message=next_status.import_operator_message,
                    status=next_status.import_status or "resumed",
                    payload=next_status,
                )
            if current.can_advance_import:
                next_status = advance_icloud_intake_import(
                    self._db,
                    source_id=request.source_profile_id,
                    import_run_id=current.import_run_id,
                )
                return _icloud_response(
                    request.source_profile_id,
                    action="icloud_import_advanced",
                    message=next_status.import_operator_message,
                    status=next_status.import_status or "advanced",
                    payload=next_status,
                )
            if current.can_start_import:
                next_status = start_icloud_intake_import(
                    self._db,
                    source_id=request.source_profile_id,
                    target_logical_assets=target or current.target_logical_candidates,
                    internal_batch_size=DEFAULT_ICLOUD_INTERNAL_BATCH_SIZE,
                )
                return _icloud_response(
                    request.source_profile_id,
                    action="icloud_import_started",
                    message=next_status.import_operator_message,
                    status=next_status.import_status or "created",
                    payload=next_status,
                )
            if current.logical_candidates_ready <= 0 and current.available_inventory != "no":
                refresh = refresh_historical_inventory(
                    self._db,
                    source_id=request.source_profile_id,
                    max_candidates=ICLOUD_PREPARE_SCAN_CAP,
                )
                return RunIngestionDispatchResponse(
                    result="action_completed",
                    workflow_kind="icloud_intake",
                    action="icloud_prepare_started",
                    message=refresh.operator_message,
                    next_action="Review prepared iCloud inventory, then import when candidates are available.",
                    source_profile_id=request.source_profile_id,
                    underlying_run_id=refresh.prepare_run_id,
                    status=refresh.status,
                    workflow_payload={"current": _safe_payload(refresh), "selection": _safe_payload(selection)},
                )
        except IcloudHistoricalRoutineError as exc:
            return RunIngestionDispatchResponse(
                result="blocked",
                workflow_kind="icloud_intake",
                action="none",
                message=str(exc),
                next_action="Review iCloud readiness and try again.",
                source_profile_id=request.source_profile_id,
                status=exc.code,
            )

        return RunIngestionDispatchResponse(
            result="no_action_available",
            workflow_kind="icloud_intake",
            action="none",
            message=current.import_operator_message,
            next_action="Review iCloud Intake status and deferred/needs-policy items.",
            source_profile_id=request.source_profile_id,
            underlying_run_id=current.import_run_id,
            status=current.import_status or current.available_inventory,
            workflow_payload={"current": _safe_payload(current), "selection": _safe_payload(selection)},
        )


def _icloud_response(
    source_profile_id: int,
    *,
    action: str,
    message: str,
    status: str,
    payload: Any,
) -> RunIngestionDispatchResponse:
    return RunIngestionDispatchResponse(
        result="started" if action in {"icloud_import_started", "icloud_import_resumed", "icloud_import_advanced"} else "action_completed",
        workflow_kind="icloud_intake",
        action=action,  # type: ignore[arg-type]
        message=message,
        next_action=None,
        source_profile_id=source_profile_id,
        underlying_run_id=getattr(payload, "import_run_id", None),
        status=status,
        workflow_payload={"current": _safe_payload(payload)},
    )


def _safe_payload(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return value
    return dict(vars(value))
