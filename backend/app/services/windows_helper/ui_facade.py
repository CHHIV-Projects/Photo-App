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
from app.schemas.windows_helper import (
    CreateWindowsHelperPairingRequest,
    CreateWindowsHelperProbeOperationRequest,
    WindowsHelperPairingAuthorizationResponse,
)
from app.schemas.windows_source_ui import (
    WindowsSourceUiCandidateReview,
    WindowsSourceUiCreateConfirmRequest,
    WindowsSourceUiCreatePlan,
    WindowsSourceUiCreatePlanRequest,
    WindowsSourceUiCreateProbeRequest,
    WindowsSourceUiCreateResult,
    WindowsSourceUiComputer,
    WindowsSourceUiComputerList,
    WindowsSourceUiOperation,
    WindowsSourceUiPortableCandidate,
    WindowsSourceUiPortableDiscovery,
    WindowsSourceUiPortableDiscoveryRequest,
    WindowsSourceUiPortableDiscoveryResolveRequest,
    WindowsSourceUiProfileStatus,
    WindowsSourceUiRoute,
    WindowsSourceUiRouteCheck,
    WindowsSourceUiRouteResolveRequest,
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
from app.services.source_identity.identity_fingerprint import fingerprint_from_probe
from app.services.windows_helper.operations import (
    completed_probe,
    completed_volume_observation,
    create_probe_operation,
    create_resolved_profile_probe_operation,
    create_volume_observation_for_access_node,
    create_volume_observation_operation,
    get_operation_status,
    helper_is_online,
    windows_helper_profile_binding,
)
from app.services.windows_helper.service import (
    ACCESS_NODE_LABEL,
    HELPER_PROVIDER_NAME,
    WindowsHelperServiceError,
    create_pairing_authorization,
)
from app.windows_helper_shared.protocol import HelperCapabilityIdentity, ProbeMode, SourceType


def _helper_version(node: AccessNode) -> str | None:
    try:
        return HelperCapabilityIdentity.model_validate_json(node.capabilities_json or "").helper_version
    except (TypeError, ValueError):
        return None


def list_computers(db: Session) -> WindowsSourceUiComputerList:
    """Project AccessNodes separately from the Source devices they can observe."""
    nodes = list(
        db.scalars(
            select(AccessNode)
            .where(
                AccessNode.os_family == "windows",
                AccessNode.provider_name == HELPER_PROVIDER_NAME,
                AccessNode.status != "retired",
            )
            .order_by(AccessNode.id)
        )
    )
    computers: list[WindowsSourceUiComputer] = []
    for node in nodes:
        endpoints = list(
            db.scalars(
                select(SourceEndpoint)
                .join(
                    SourceEndpointObservedPath,
                    SourceEndpointObservedPath.source_endpoint_id == SourceEndpoint.id,
                )
                .where(
                    SourceEndpointObservedPath.access_node_id == node.id,
                    SourceEndpoint.status != "retired",
                )
                .distinct()
                .order_by(SourceEndpoint.id)
            )
        )
        device_aliases = sorted({endpoint.alias for endpoint in endpoints}, key=str.casefold)
        local_aliases = [endpoint.alias for endpoint in endpoints if endpoint.source_type == "local"]
        display_alias = (
            local_aliases[0]
            if node.label == ACCESS_NODE_LABEL and len(local_aliases) == 1
            else node.label
        )
        credential = db.scalar(
            select(WindowsHelperCredential).where(
                WindowsHelperCredential.access_node_id == node.id,
                WindowsHelperCredential.status == "active",
                WindowsHelperCredential.revoked_at.is_(None),
            )
        )
        paired = credential is not None
        computers.append(
            WindowsSourceUiComputer(
                access_node_id=UUID(node.access_node_uuid),
                computer_alias=display_alias,
                paired=paired,
                online=paired and helper_is_online(node),
                helper_version=_helper_version(node),
                source_device_aliases=device_aliases,
            )
        )
    return WindowsSourceUiComputerList(computers=computers)


def create_computer_pairing(
    db: Session,
    request: CreateWindowsHelperPairingRequest,
) -> WindowsHelperPairingAuthorizationResponse:
    alias = request.computer_alias or ""
    for computer in list_computers(db).computers:
        if computer.paired and computer.computer_alias.casefold() == alias.strip().casefold():
            raise WindowsHelperServiceError(
                "access_node_already_paired",
                "That Windows computer is already paired. Select it instead.",
                http_status=409,
            )
    return create_pairing_authorization(db, request.computer_alias)


def begin_portable_discovery(
    db: Session, request: WindowsSourceUiPortableDiscoveryRequest
) -> WindowsSourceUiPortableDiscovery:
    nodes = list(
        db.scalars(
            select(AccessNode).where(
                AccessNode.provider_name == HELPER_PROVIDER_NAME,
                AccessNode.os_family == "windows",
                AccessNode.status == "active",
            ).order_by(AccessNode.id)
        )
    )
    tokens: list[UUID] = []
    for node in nodes:
        try:
            tokens.append(create_volume_observation_for_access_node(db, node).operation_id)
        except WindowsHelperServiceError as exc:
            if exc.code in {
                "helper_offline",
                "helper_credential_unavailable",
                "volume_observation_capability_unavailable",
            }:
                continue
            raise
    return WindowsSourceUiPortableDiscovery(
        stage="checking_devices" if tokens else "unavailable",
        observation_tokens=tokens,
        safe_message=(
            "Checking connected Source devices."
            if tokens
            else "No registered computer is currently available to detect devices."
        ),
    )


def resolve_portable_discovery(
    db: Session, request: WindowsSourceUiPortableDiscoveryResolveRequest
) -> WindowsSourceUiPortableDiscovery:
    rows: dict[tuple[str, str], list[tuple[UUID, int, object]]] = {}
    for token in request.observation_tokens:
        status = get_operation_status(db, token)
        if status.source_endpoint_id is not None or status.source_profile_id is not None:
            raise WindowsHelperServiceError(
                "portable_discovery_binding_invalid",
                "A device-discovery observation has an unexpected Source binding.",
                http_status=409,
            )
        if status.state in {"pending", "claimed"}:
            return WindowsSourceUiPortableDiscovery(
                stage="checking_devices",
                observation_tokens=request.observation_tokens,
                safe_message="Checking connected Source devices.",
            )
        if status.state != "completed":
            continue
        operation, result = completed_volume_observation(db, token, require_fresh=True)
        for index, item in enumerate(result.volumes):
            expected_drive_type = "removable" if request.source_type == "removable" else "fixed"
            if item.drive_type != expected_drive_type:
                continue
            key = (item.identity_fingerprint_version, item.identity_fingerprint_hash)
            rows.setdefault(key, []).append((token, index, item))
    candidates: list[WindowsSourceUiPortableCandidate] = []
    endpoint_type = "external_device" if request.source_type == "external" else "removable_media"
    for (version, fingerprint), observations in sorted(rows.items(), key=lambda row: row[0]):
        endpoints = list(
            db.scalars(
                select(SourceEndpoint).where(
                    SourceEndpoint.identity_fingerprint_version == version,
                    SourceEndpoint.identity_fingerprint_hash == fingerprint,
                    SourceEndpoint.status != "retired",
                )
            )
        )
        if len(endpoints) > 1:
            raise WindowsHelperServiceError(
                "portable_identity_ambiguous",
                "More than one Source device has the detected durable identity.",
                http_status=409,
            )
        endpoint = endpoints[0] if endpoints else None
        if endpoint is not None and endpoint.source_type != endpoint_type:
            continue
        # Helper 0.5.1 can distinguish native Windows drive types, but it does
        # not carry physical-device backing evidence in observe_volumes.  An
        # unknown fixed drive may therefore be internal or virtual/cloud-backed.
        # Fail closed for unknown External drives while continuing to expose a
        # previously enrolled External Endpoint by its durable fingerprint.
        if request.source_type == "external" and endpoint is None:
            continue
        token, index, item = observations[0]
        candidates.append(
            WindowsSourceUiPortableCandidate(
                candidate_token=f"{token}:{index}",
                device_alias=endpoint.alias if endpoint is not None else None,
                known_device=endpoint is not None,
                current_root=item.provider_native_root,  # type: ignore[attr-defined]
                drive_type=item.drive_type,  # type: ignore[attr-defined]
                current_route_count=len({entry[0] for entry in observations}),
            )
        )
    return WindowsSourceUiPortableDiscovery(
        stage="ready" if candidates else "unavailable",
        observation_tokens=request.observation_tokens,
        candidates=candidates,
        safe_message=(
            "Select a detected Source device."
            if candidates
            else "No matching connected Source devices were detected."
        ),
    )


def _resolve_discovery_candidate(db: Session, request):
    if not request.discovery_candidate_token:
        return request
    try:
        raw_token, raw_index = request.discovery_candidate_token.rsplit(":", 1)
        token = UUID(raw_token)
        index = int(raw_index)
    except (ValueError, TypeError) as exc:
        raise WindowsHelperServiceError(
            "portable_candidate_invalid", "The selected device candidate is invalid.", http_status=400
        ) from exc
    operation, result = completed_volume_observation(db, token, require_fresh=True)
    if operation.source_endpoint_id is not None or operation.source_profile_id is not None:
        raise WindowsHelperServiceError(
            "portable_candidate_binding_invalid", "The selected device candidate is invalid.", http_status=409
        )
    if index < 0 or index >= len(result.volumes):
        raise WindowsHelperServiceError(
            "portable_candidate_invalid", "The selected device candidate is invalid.", http_status=400
        )
    item = result.volumes[index]
    expected_drive_type = "removable" if request.source_type == "removable" else "fixed"
    if item.drive_type != expected_drive_type:
        raise WindowsHelperServiceError(
            "portable_candidate_type_mismatch", "The selected device type does not match this Source flow.", http_status=409
        )
    if ntpath.normcase(ntpath.splitdrive(request.windows_root)[0]) != ntpath.normcase(
        ntpath.splitdrive(item.provider_native_root)[0]
    ):
        raise WindowsHelperServiceError(
            "portable_candidate_root_mismatch",
            "The selected folder is not on the detected Source device.",
            http_status=409,
        )
    endpoints = list(
        db.scalars(
            select(SourceEndpoint).where(
                SourceEndpoint.identity_fingerprint_version == item.identity_fingerprint_version,
                SourceEndpoint.identity_fingerprint_hash == item.identity_fingerprint_hash,
                SourceEndpoint.status != "retired",
            )
        )
    )
    if len(endpoints) > 1:
        raise WindowsHelperServiceError(
            "portable_identity_ambiguous", "The selected device identity is ambiguous.", http_status=409
        )
    if request.source_type == "external" and not endpoints:
        raise WindowsHelperServiceError(
            "external_physical_identity_unverified",
            "Windows Helper 0.5.1 cannot safely distinguish this unknown fixed drive from virtual storage.",
            http_status=409,
        )
    alias = endpoints[0].alias if endpoints else request.device_alias
    if not alias or not alias.strip():
        raise WindowsHelperServiceError(
            "device_name_required", "Enter a Device name for this new physical device.", http_status=400
        )
    node = db.get(AccessNode, operation.access_node_id)
    if node is None:
        raise WindowsHelperServiceError(
            "windows_computer_unavailable", "The observing computer is unavailable.", http_status=409
        )
    return request.model_copy(
        update={
            "access_node_id": UUID(node.access_node_uuid),
            "device_alias": alias,
        }
    )


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
    if not nodes:
        raise WindowsHelperServiceError(
            "source_access_node_unavailable",
            "The Source has no registered Windows access route.",
            http_status=409,
        )
    states: list[tuple[AccessNode, bool, bool]] = []
    for candidate in nodes:
        credential = db.scalar(
            select(WindowsHelperCredential).where(
                WindowsHelperCredential.access_node_id == candidate.id,
                WindowsHelperCredential.status == "active",
                WindowsHelperCredential.revoked_at.is_(None),
            )
        )
        paired_candidate = credential is not None
        states.append((candidate, paired_candidate, paired_candidate and helper_is_online(candidate)))
    node = next((item[0] for item in states if item[2]), states[0][0])
    paired = any(item[1] for item in states)
    online = any(item[2] for item in states)
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


def begin_profile_route_check(db: Session, source_profile_id: int) -> WindowsSourceUiRouteCheck:
    source = db.get(IngestionSource, source_profile_id)
    endpoint = db.get(SourceEndpoint, source.endpoint_id) if source is not None and source.endpoint_id else None
    if source is None or source.profile_status != "active" or endpoint is None or endpoint.status == "retired":
        raise WindowsHelperServiceError(
            "source_profile_unavailable", "The requested Source Profile is unavailable.", http_status=404
        )
    if endpoint.source_type not in {"external_device", "removable_media"}:
        raise WindowsHelperServiceError(
            "portable_route_not_required", "This Source does not use portable route discovery.", http_status=409
        )
    nodes = list(
        db.scalars(
            select(AccessNode).where(
                AccessNode.provider_name == HELPER_PROVIDER_NAME,
                AccessNode.os_family == "windows",
                AccessNode.status == "active",
            )
            .order_by(AccessNode.id)
        )
    )
    tokens: list[UUID] = []
    for node in nodes:
        try:
            operation = create_volume_observation_for_access_node(
                db,
                node,
                source_endpoint_id=endpoint.id,
                source_profile_id=source.id,
            )
        except WindowsHelperServiceError as exc:
            if exc.code in {
                "helper_offline",
                "helper_credential_unavailable",
                "volume_observation_capability_unavailable",
            }:
                continue
            raise
        tokens.append(operation.operation_id)
    if not tokens:
        return WindowsSourceUiRouteCheck(
            stage="unavailable",
            safe_message="Device not connected.",
        )
    return WindowsSourceUiRouteCheck(
        stage="checking_routes",
        observation_tokens=tokens,
        safe_message="Checking currently available computers for this device.",
    )


def resolve_profile_route(
    db: Session,
    source_profile_id: int,
    request: WindowsSourceUiRouteResolveRequest,
) -> WindowsSourceUiRouteCheck:
    source = db.get(IngestionSource, source_profile_id)
    endpoint = db.get(SourceEndpoint, source.endpoint_id) if source is not None and source.endpoint_id else None
    if source is None or endpoint is None or source.profile_status != "active" or endpoint.status == "retired":
        raise WindowsHelperServiceError(
            "source_profile_unavailable", "The requested Source Profile is unavailable.", http_status=404
        )
    matching: list[tuple[UUID, AccessNode]] = []
    pending = False
    for token in request.observation_tokens:
        status = get_operation_status(db, token)
        if status.source_profile_id != source.id or status.source_endpoint_id != endpoint.id:
            raise WindowsHelperServiceError(
                "portable_route_binding_mismatch",
                "A route observation is not bound to the selected Source.",
                http_status=409,
            )
        if status.state in {"pending", "claimed"}:
            pending = True
            continue
        if status.state != "completed":
            continue
        operation, result = completed_volume_observation(db, token, require_fresh=True)
        matches = [
            item for item in result.volumes
            if item.identity_fingerprint_hash == endpoint.identity_fingerprint_hash
            and item.identity_fingerprint_version == endpoint.identity_fingerprint_version
        ]
        if len(matches) > 1:
            return WindowsSourceUiRouteCheck(
                stage="failed",
                observation_tokens=request.observation_tokens,
                safe_message="Windows reported more than one matching device on one computer.",
            )
        if len(matches) == 1:
            node = db.get(AccessNode, operation.access_node_id)
            if node is not None and helper_is_online(node):
                matching.append((token, node))
    if pending:
        return WindowsSourceUiRouteCheck(
            stage="checking_routes",
            observation_tokens=request.observation_tokens,
            safe_message="Checking currently available computers for this device.",
        )
    by_node = {node.id: (token, node) for token, node in matching}
    candidates = list(by_node.values())
    if not candidates:
        return WindowsSourceUiRouteCheck(
            stage="unavailable",
            observation_tokens=request.observation_tokens,
            safe_message="Device not connected.",
        )
    routes = [
        WindowsSourceUiRoute(
            access_node_id=UUID(node.access_node_uuid),
            computer_alias=next(
                (item.computer_alias for item in list_computers(db).computers if item.access_node_id == UUID(node.access_node_uuid)),
                node.label,
            ),
        )
        for _, node in candidates
    ]
    selected: tuple[UUID, AccessNode] | None = None
    if len(candidates) == 1:
        selected = candidates[0]
    elif request.selected_access_node_id is not None:
        selected = next(
            (item for item in candidates if item[1].access_node_uuid == str(request.selected_access_node_id)),
            None,
        )
        if selected is None:
            raise WindowsHelperServiceError(
                "portable_route_selection_invalid",
                "The selected computer is not a current verified route for this device.",
                http_status=409,
            )
    if selected is None:
        return WindowsSourceUiRouteCheck(
            stage="ambiguous",
            observation_tokens=request.observation_tokens,
            routes=routes,
            safe_message="This device is available through more than one computer. Choose one for this run.",
        )
    probe_token = create_resolved_profile_probe_operation(db, selected[0])
    return WindowsSourceUiRouteCheck(
        stage="checking_source",
        observation_tokens=request.observation_tokens,
        probe_operation_token=probe_token,
        routes=routes,
        safe_message="Verifying the selected Windows Source root.",
    )


def create_profile_probe(db: Session, source_profile_id: int) -> WindowsSourceUiOperation:
    source, endpoint, node = windows_helper_profile_binding(db, source_profile_id)
    if not helper_is_online(node):
        raise WindowsHelperServiceError(
            "helper_offline", "Windows access is not currently available.", http_status=409
        )
    operation = (
        create_volume_observation_operation(db, source.id)
        if endpoint.source_type in {"external_device", "removable_media"}
        else create_probe_operation(
            db,
            CreateWindowsHelperProbeOperationRequest(
                access_node_id=UUID(node.access_node_uuid),
                source_type=SourceType(endpoint.source_type),
                provider_native_root=source.source_root_path or "",
                probe_mode=ProbeMode.READINESS,
                source_profile_id=source.id,
            ),
        )
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
            stage=(
                "checking_source"
                if status.operation_type in {"probe_source", "observe_volumes"}
                else "preparing_files"
            ),
            safe_message=(
                "Checking the selected Windows Source."
                if status.operation_type in {"probe_source", "observe_volumes"}
                else "Preparing the bounded file list."
            ),
        )
    if status.operation_type == "observe_volumes":
        try:
            probe_operation_id = create_resolved_profile_probe_operation(db, operation_id)
        except WindowsHelperServiceError as exc:
            safe_message = {
                "mounted_volume_not_connected": "Device not connected.",
                "mounted_volume_identity_mismatch": "A different device is using this Source's prior drive letter.",
                "mounted_volume_identity_ambiguous": "Windows reported more than one matching device.",
            }.get(exc.code, "The selected Source is not ready.")
            return WindowsSourceUiOperation(
                operation_token=operation_id,
                stage="failed",
                safe_message=safe_message,
            )
        return WindowsSourceUiOperation(
            operation_token=probe_operation_id,
            stage="checking_source",
            safe_message="Verifying the selected Windows Source root.",
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
        windows_root=acquisition.provider_native_root,
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


def _creation_binding(
    db: Session,
    access_node_id: UUID,
    device_alias: str,
) -> tuple[SourceEndpoint | None, AccessNode]:
    node = db.scalar(
        select(AccessNode).where(
            AccessNode.access_node_uuid == str(access_node_id),
            AccessNode.os_family == "windows",
            AccessNode.provider_name == HELPER_PROVIDER_NAME,
            AccessNode.status == "active",
        )
    )
    if node is None:
        raise WindowsHelperServiceError(
            "windows_computer_unavailable",
            "Select one paired Windows computer.",
            http_status=409,
        )
    endpoints = list(
        db.scalars(
            select(SourceEndpoint)
            .join(
                SourceEndpointObservedPath,
                SourceEndpointObservedPath.source_endpoint_id == SourceEndpoint.id,
            )
            .where(
                SourceEndpointObservedPath.access_node_id == node.id,
                SourceEndpoint.status != "retired",
            )
            .distinct()
        )
    )
    matches = [
        endpoint
        for endpoint in endpoints
        if endpoint.alias.casefold() == device_alias.strip().casefold()
    ]
    if len(matches) > 1:
        raise WindowsHelperServiceError(
            "windows_device_ambiguous",
            "More than one Source device uses that name on this computer.",
            http_status=409,
        )
    if not matches:
        global_match = db.scalar(
            select(SourceEndpoint).where(
                SourceEndpoint.alias_normalized == device_alias.strip().casefold(),
                SourceEndpoint.status != "retired",
            )
        )
        if global_match is not None:
            matches = [global_match]
    return (matches[0] if matches else None), node


def _helper_source_type(source_type: str) -> SourceType:
    return {
        "local": SourceType.LOCAL,
        "external": SourceType.EXTERNAL,
        "removable": SourceType.REMOVABLE,
    }[source_type]


def _normalized_creation_request(
    db: Session,
    request: WindowsSourceUiCreateProbeRequest | WindowsSourceUiCreatePlanRequest | WindowsSourceUiCreateConfirmRequest,
):
    request = _resolve_discovery_candidate(db, request)
    if request.source_type != "local":
        return request
    computer = next(
        (item for item in list_computers(db).computers if item.access_node_id == request.access_node_id),
        None,
    )
    if computer is None:
        raise WindowsHelperServiceError(
            "windows_computer_unavailable", "Select one paired Windows computer.", http_status=409
        )
    return request.model_copy(update={"device_alias": computer.computer_alias})


def _enforce_local_endpoint_invariant(
    db: Session,
    request: WindowsSourceUiCreatePlanRequest | WindowsSourceUiCreateConfirmRequest,
    *,
    lock_access_node: bool,
) -> None:
    if request.source_type != "local":
        return
    probe_operation, probe = completed_probe(
        db,
        request.probe_operation_token,
        require_fresh=True,
    )
    statement = select(AccessNode).where(
        AccessNode.access_node_uuid == str(request.access_node_id),
        AccessNode.provider_name == HELPER_PROVIDER_NAME,
        AccessNode.os_family == "windows",
        AccessNode.status == "active",
    )
    if lock_access_node:
        statement = statement.with_for_update()
    node = db.scalar(statement)
    if node is None or probe_operation.access_node_id != node.id:
        raise WindowsHelperServiceError(
            "local_access_node_mismatch",
            "The Local Source check does not belong to the selected computer.",
            http_status=409,
        )
    endpoints = list(
        db.scalars(
            select(SourceEndpoint)
            .join(SourceEndpointObservedPath, SourceEndpointObservedPath.source_endpoint_id == SourceEndpoint.id)
            .where(
                SourceEndpointObservedPath.access_node_id == node.id,
                SourceEndpoint.source_type == "local",
                SourceEndpoint.status == "active",
            )
            .distinct()
            .order_by(SourceEndpoint.id)
        )
    )
    if len(endpoints) > 1:
        raise WindowsHelperServiceError(
            "local_endpoint_ambiguous",
            "This computer has more than one active Local device and requires operator review.",
            http_status=409,
        )
    fingerprint = fingerprint_from_probe(probe)
    if len(endpoints) == 1 and (
        fingerprint.strength != "strong"
        or not fingerprint.hash_value
        or endpoints[0].identity_fingerprint_hash != fingerprint.hash_value
    ):
        raise WindowsHelperServiceError(
            "additional_local_volume_not_supported",
            "Additional local volumes are not supported in this version.",
            http_status=409,
        )


def create_creation_probe(
    db: Session, request: WindowsSourceUiCreateProbeRequest
) -> WindowsSourceUiOperation:
    request = _normalized_creation_request(db, request)
    if request.access_node_id is None:
        raise WindowsHelperServiceError(
            "windows_computer_unavailable", "No current Windows access route is available.", http_status=409
        )
    _, node = _creation_binding(db, request.access_node_id, request.device_alias)
    root = request.windows_root.strip()
    if not ntpath.isabs(root) or not ntpath.splitdrive(root)[0]:
        raise WindowsHelperServiceError(
            "invalid_windows_root", "Enter an absolute Windows folder path.", http_status=400
        )
    operation = create_probe_operation(
        db,
        CreateWindowsHelperProbeOperationRequest(
            access_node_id=UUID(node.access_node_uuid),
            source_type=_helper_source_type(request.source_type),
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
    request = _normalized_creation_request(db, request)
    if request.access_node_id is None:
        raise WindowsHelperServiceError(
            "windows_computer_unavailable", "No current Windows access route is available.", http_status=409
        )
    _enforce_local_endpoint_invariant(db, request, lock_access_node=False)
    endpoint, _ = _creation_binding(db, request.access_node_id, request.device_alias)
    return SourceCreationService(db).plan(
        SourceCreationPlanRequest(
            source_type=request.source_type,
            observed_path=request.windows_root.strip(),
            source_name=request.profile_name.strip(),
            device_name=request.device_alias.strip(),
            naming_action="use_existing" if endpoint is not None else "create_new",
            selected_existing_endpoint_id=endpoint.id if endpoint is not None else None,
            helper_probe_operation_id=request.probe_operation_token,
        )
    )


def creation_plan(db: Session, request: WindowsSourceUiCreatePlanRequest) -> WindowsSourceUiCreatePlan:
    request = _normalized_creation_request(db, request)
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
    request = _normalized_creation_request(db, request)
    if request.access_node_id is None:
        raise WindowsHelperServiceError(
            "windows_computer_unavailable", "No current Windows access route is available.", http_status=409
        )
    _enforce_local_endpoint_invariant(db, request, lock_access_node=True)
    endpoint, _ = _creation_binding(db, request.access_node_id, request.device_alias)
    plan = _creation_plan(db, request)
    result = SourceCreationService(db).confirm(
        SourceCreationConfirmRequest(
            source_type=request.source_type,
            observed_path=request.windows_root.strip(),
            source_name=request.profile_name.strip(),
            device_name=request.device_alias.strip(),
            naming_action="use_existing" if endpoint is not None else "create_new",
            selected_existing_endpoint_id=endpoint.id if endpoint is not None else None,
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
