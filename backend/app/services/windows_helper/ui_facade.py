"""Small redacted facade over the accepted Windows Helper workflow authorities."""

from __future__ import annotations

import ntpath
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ingestion_source import IngestionSource
from app.models.source_acquisition import SourceAcquisitionRun
from app.models.source_endpoint import AccessNode, SourceEndpoint, SourceEndpointObservedPath
from app.models.source_intake_run import SourceIntakeRun
from app.models.windows_helper import WindowsHelperCredential
from app.schemas.admin import RunIngestionDispatchRequest, RunIngestionWindowsHelperOptions
from app.schemas.source_acquisition import CreateSourceAcquisitionPlanRequest
from app.schemas.windows_helper import CreateWindowsHelperProbeOperationRequest
from app.schemas.windows_source_ui import (
    WindowsSourceUiCandidateReview,
    WindowsSourceUiCreateConfirmRequest,
    WindowsSourceUiCreatePlan,
    WindowsSourceUiCreatePlanRequest,
    WindowsSourceUiCreateProbeRequest,
    WindowsSourceUiCreateResult,
    WindowsSourceUiOperation,
    WindowsSourceUiProfileStatus,
    WindowsSourceUiWorkflowStatus,
)
from app.services.admin.run_ingestion_dispatch_service import RunIngestionDispatchService
from app.services.source_acquisition.service import create_planned_run, get_run
from app.services.source_acquisition.workflow import advance_source_acquisition_workflow
from app.services.source_identity.creation_schema import (
    SourceCreationConfirmRequest,
    SourceCreationPlanRequest,
)
from app.services.source_identity.creation_service import SourceCreationService
from app.services.windows_helper.operations import (
    create_probe_operation,
    get_operation_status,
    helper_is_online,
    windows_helper_profile_binding,
)
from app.services.windows_helper.service import HELPER_PROVIDER_NAME, WindowsHelperServiceError
from app.windows_helper_shared.protocol import HelperCapabilityIdentity, ProbeMode, SourceType


def _helper_version(node: AccessNode) -> str | None:
    try:
        return HelperCapabilityIdentity.model_validate_json(node.capabilities_json or "").helper_version
    except (TypeError, ValueError):
        return None


def profile_status(db: Session, source_profile_id: int) -> WindowsSourceUiProfileStatus:
    source = db.get(IngestionSource, source_profile_id)
    if source is None or source.profile_status != "active" or source.endpoint_id is None:
        raise WindowsHelperServiceError(
            "source_profile_unavailable", "The requested Source Profile is unavailable.", http_status=404
        )
    endpoint = db.get(SourceEndpoint, source.endpoint_id)
    if endpoint is None or endpoint.status == "retired":
        raise WindowsHelperServiceError(
            "source_endpoint_unavailable", "The requested Source device is unavailable.", http_status=409
        )
    nodes = list(
        db.scalars(
            select(AccessNode)
            .join(SourceEndpointObservedPath, SourceEndpointObservedPath.access_node_id == AccessNode.id)
            .where(
                SourceEndpointObservedPath.source_endpoint_id == endpoint.id,
                AccessNode.provider_name == HELPER_PROVIDER_NAME,
                AccessNode.os_family == "windows",
                AccessNode.status == "active",
            )
            .distinct()
        )
    )
    if len(nodes) != 1:
        raise WindowsHelperServiceError(
            "source_access_node_ambiguous",
            "The Source does not have one configured Windows access device.",
            http_status=409,
        )
    node = nodes[0]
    credential = db.scalar(
        select(WindowsHelperCredential).where(
            WindowsHelperCredential.access_node_id == node.id,
            WindowsHelperCredential.status == "active",
            WindowsHelperCredential.revoked_at.is_(None),
        )
    )
    paired = credential is not None
    online = paired and helper_is_online(node)
    return WindowsSourceUiProfileStatus(
        source_profile_id=source.id,
        profile_name=source.source_label,
        device_alias=endpoint.alias,
        windows_root=source.source_root_path or "",
        windows_access="ready" if online else "not_available" if paired else "setup_required",
        paired=paired,
        online=online,
        helper_version=_helper_version(node),
    )


def create_profile_probe(db: Session, source_profile_id: int) -> WindowsSourceUiOperation:
    source, endpoint, node = windows_helper_profile_binding(db, source_profile_id)
    if not helper_is_online(node):
        raise WindowsHelperServiceError(
            "helper_offline", "Windows access is not currently available.", http_status=409
        )
    operation = create_probe_operation(
        db,
        CreateWindowsHelperProbeOperationRequest(
            access_node_id=UUID(node.access_node_uuid),
            source_type=SourceType(endpoint.source_type),
            provider_native_root=source.source_root_path or "",
            probe_mode=ProbeMode.READINESS,
            source_profile_id=source.id,
        ),
    )
    return WindowsSourceUiOperation(
        operation_token=operation.operation_id,
        stage="checking_source",
        safe_message="Checking the selected Windows Source.",
    )


def operation_status(db: Session, operation_id: UUID) -> WindowsSourceUiOperation:
    status = get_operation_status(db, operation_id)
    if status.state in {"failed", "expired"}:
        return WindowsSourceUiOperation(
            operation_token=operation_id,
            stage="failed",
            safe_message="Windows access could not complete the requested Source check.",
        )
    if status.state != "completed":
        return WindowsSourceUiOperation(
            operation_token=operation_id,
            stage="checking_source" if status.operation_type == "probe_source" else "preparing_files",
            safe_message=(
                "Checking the selected Windows Source."
                if status.operation_type == "probe_source"
                else "Preparing the bounded file list."
            ),
        )
    if status.operation_type == "probe_source":
        ready = bool(status.probe_result and status.probe_result.result_status.value == "success")
        return WindowsSourceUiOperation(
            operation_token=operation_id,
            stage="ready" if ready else "failed",
            source_ready=ready,
            safe_message="Source is ready." if ready else "The selected Source is not ready.",
        )
    if status.inventory_result is None or status.inventory_result.result_status.value != "success":
        return WindowsSourceUiOperation(
            operation_token=operation_id,
            stage="failed",
            safe_message="The bounded file list could not be prepared.",
        )
    return WindowsSourceUiOperation(
        operation_token=operation_id,
        stage="ready",
        source_ready=True,
        safe_message="The bounded file list is ready for review.",
    )


def prepare_inventory(
    db: Session, source_profile_id: int, probe_operation_id: UUID
) -> WindowsSourceUiOperation:
    result = RunIngestionDispatchService(db).dispatch(
        RunIngestionDispatchRequest(
            source_profile_id=source_profile_id,
            windows_helper_options=RunIngestionWindowsHelperOptions(
                helper_probe_operation_id=probe_operation_id,
                inventory_page_size=100,
            ),
        )
    )
    if result.action != "windows_helper_inventory_started":
        raise WindowsHelperServiceError(
            "windows_inventory_not_started", result.message, http_status=409
        )
    operation_id = UUID(str(result.workflow_payload["operation_id"]))
    return WindowsSourceUiOperation(
        operation_token=operation_id,
        stage="preparing_files",
        safe_message="Preparing the bounded file list.",
    )


def candidate_review(
    db: Session, source_profile_id: int, inventory_operation_id: UUID
) -> WindowsSourceUiCandidateReview:
    status = get_operation_status(db, inventory_operation_id)
    if (
        status.operation_type != "inventory_page"
        or status.source_profile_id != source_profile_id
        or status.state != "completed"
        or status.inventory_result is None
        or status.inventory_result.result_status.value != "success"
    ):
        raise WindowsHelperServiceError(
            "inventory_not_ready", "The bounded file list is not ready.", http_status=409
        )
    if status.inventory_result.next_cursor is not None:
        raise WindowsHelperServiceError(
            "inventory_ui_bound_exceeded",
            "This Source contains more than the bounded UI review limit.",
            http_status=409,
        )
    candidates = [item for item in status.inventory_candidates if item.eligibility == "eligible"]
    if not candidates:
        raise WindowsHelperServiceError(
            "no_eligible_candidates", "No eligible media files were found.", http_status=409
        )
    generation = str(status.inventory_result.inventory_generation)
    existing = db.scalar(
        select(SourceAcquisitionRun).where(
            SourceAcquisitionRun.source_profile_id == source_profile_id,
            SourceAcquisitionRun.inventory_generation == generation,
        )
    )
    acquisition = (
        get_run(db, UUID(existing.run_uuid))
        if existing is not None
        else create_planned_run(
            db,
            CreateSourceAcquisitionPlanRequest(
                idempotency_key=uuid4(),
                source_profile_id=source_profile_id,
                inventory_operation_ids=[inventory_operation_id],
                candidate_references=[item.candidate_reference for item in candidates],
            ),
        )
    )
    source = db.get(IngestionSource, source_profile_id)
    if source is None:
        raise WindowsHelperServiceError("source_profile_unavailable", "Source Profile unavailable.", http_status=404)
    return WindowsSourceUiCandidateReview(
        workflow_token=acquisition.acquisition_run_id,
        files_to_process=acquisition.selected_item_count,
        total_bytes=acquisition.expected_byte_count,
        profile_name=source.source_label,
        windows_root=source.source_root_path or "",
        safe_message="Review the exact bounded file set before starting ingestion.",
    )


def advance_workflow(db: Session, run_id: UUID, *, confirm: bool) -> WindowsSourceUiWorkflowStatus:
    acquisition = get_run(db, run_id)
    proposal_digest = acquisition.proposal_digest if confirm and acquisition.state == "planned" else None
    workflow = advance_source_acquisition_workflow(db, run_id, proposal_digest=proposal_digest)
    acquisition = workflow.acquisition
    failed = acquisition.failed_item_count
    new_items = 0
    if workflow.bridge and workflow.bridge.source_intake_run_id is not None:
        intake = db.get(SourceIntakeRun, workflow.bridge.source_intake_run_id)
        if intake is not None:
            new_items = int(intake.processed_new_unique or 0)
            failed += int(intake.failed_or_rejected or 0)
    if workflow.stage == "awaiting_approval":
        stage = "awaiting_confirmation"
    elif workflow.stage == "awaiting_helper":
        stage = "transferring_files"
    elif workflow.stage == "bridge_running":
        stage = "processing_library"
    elif workflow.stage == "completed":
        stage = "complete"
    else:
        stage = "failed"
    completed = acquisition.ready_item_count + acquisition.failed_item_count
    already = max(0, acquisition.selected_item_count - new_items - failed) if stage == "complete" else 0
    return WindowsSourceUiWorkflowStatus(
        workflow_token=run_id,
        stage=stage,
        files_total=acquisition.selected_item_count,
        files_completed=completed if stage != "complete" else acquisition.selected_item_count,
        expected_bytes=acquisition.expected_byte_count,
        transferred_bytes=acquisition.committed_byte_count,
        new_library_items=new_items,
        already_represented=already,
        failed_items=failed,
        safe_message=(
            "Run complete."
            if stage == "complete"
            else "Processing files in the common ingestion pipeline."
            if stage == "processing_library"
            else "Transferring verified files."
            if stage == "transferring_files"
            else "Review the bounded file set before starting ingestion."
            if stage == "awaiting_confirmation"
            else "Ingestion stopped safely and needs review."
        ),
    )


def _creation_binding(db: Session, device_alias: str) -> tuple[SourceEndpoint, AccessNode]:
    endpoints = list(db.scalars(select(SourceEndpoint).where(SourceEndpoint.status != "retired")))
    matches = [item for item in endpoints if item.alias.casefold() == device_alias.strip().casefold()]
    if len(matches) != 1:
        raise WindowsHelperServiceError(
            "windows_device_unavailable", "Select one known Windows device.", http_status=409
        )
    endpoint = matches[0]
    nodes = list(
        db.scalars(
            select(AccessNode)
            .join(SourceEndpointObservedPath, SourceEndpointObservedPath.access_node_id == AccessNode.id)
            .where(
                SourceEndpointObservedPath.source_endpoint_id == endpoint.id,
                AccessNode.provider_name == HELPER_PROVIDER_NAME,
                AccessNode.status == "active",
            )
            .distinct()
        )
    )
    if len(nodes) != 1:
        raise WindowsHelperServiceError(
            "windows_device_unavailable", "Windows access for this device is unavailable.", http_status=409
        )
    return endpoint, nodes[0]


def create_creation_probe(
    db: Session, request: WindowsSourceUiCreateProbeRequest
) -> WindowsSourceUiOperation:
    _, node = _creation_binding(db, request.device_alias)
    root = request.windows_root.strip()
    if not ntpath.isabs(root) or not ntpath.splitdrive(root)[0]:
        raise WindowsHelperServiceError(
            "invalid_windows_root", "Enter an absolute Windows folder path.", http_status=400
        )
    operation = create_probe_operation(
        db,
        CreateWindowsHelperProbeOperationRequest(
            access_node_id=UUID(node.access_node_uuid),
            source_type=SourceType.LOCAL,
            provider_native_root=root,
            probe_mode=ProbeMode.SETUP,
        ),
    )
    return WindowsSourceUiOperation(
        operation_token=operation.operation_id,
        stage="checking_source",
        safe_message="Checking the exact Windows folder and device identity.",
    )


def _creation_plan(db: Session, request: WindowsSourceUiCreatePlanRequest):
    endpoint, _ = _creation_binding(db, request.device_alias)
    return SourceCreationService(db).plan(
        SourceCreationPlanRequest(
            source_type="local",
            observed_path=request.windows_root.strip(),
            source_name=request.profile_name.strip(),
            device_name=endpoint.alias,
            selected_existing_endpoint_id=endpoint.id,
            helper_probe_operation_id=request.probe_operation_token,
        )
    )


def creation_plan(db: Session, request: WindowsSourceUiCreatePlanRequest) -> WindowsSourceUiCreatePlan:
    plan = _creation_plan(db, request)
    return WindowsSourceUiCreatePlan(
        plan_status=plan.plan_status,
        device_alias=plan.device_name,
        windows_root=plan.canonical_source_root_path,
        profile_name=plan.source_display_name,
        device_action=plan.endpoint_action,
        profile_action=plan.source_action,
        blockers=[item.message for item in plan.blockers],
        warnings=[item.message for item in plan.warnings],
    )


def confirm_creation(
    db: Session, request: WindowsSourceUiCreateConfirmRequest
) -> WindowsSourceUiCreateResult:
    endpoint, _ = _creation_binding(db, request.device_alias)
    plan = _creation_plan(db, request)
    result = SourceCreationService(db).confirm(
        SourceCreationConfirmRequest(
            source_type="local",
            observed_path=request.windows_root.strip(),
            source_name=request.profile_name.strip(),
            device_name=endpoint.alias,
            selected_existing_endpoint_id=endpoint.id,
            helper_probe_operation_id=request.probe_operation_token,
            operator_review_acknowledged=True,
            plan_fingerprint=plan.plan_fingerprint,
            operator_confirmed=request.operator_confirmed,
        )
    )
    return WindowsSourceUiCreateResult(
        status=result.creation_status,
        source_profile_id=result.source_profile_id,
        source_endpoint_id=result.source_endpoint_id,
        created_profile=result.created_source,
        reused_profile=result.reused_source,
        safe_message=(
            "Source saved."
            if result.creation_status == "completed"
            else result.blockers[0].message if result.blockers else "Source was not saved."
        ),
    )
