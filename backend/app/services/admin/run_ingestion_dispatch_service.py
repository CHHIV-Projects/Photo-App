"""Selected-source Run Ingestion dispatch service.

This is the thin Step 3 integration seam. It revalidates Source Selection,
then routes to the existing filesystem Source Intake or iCloud Intake
authorities without creating new selected-source persistence.
"""

from __future__ import annotations

import ntpath
import re
from dataclasses import asdict, is_dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models.ingestion_source import IngestionSource
from app.models.source_endpoint import SourceEndpoint
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
from app.services.source_identity.identity_fingerprint import (
    CURRENT_OPTICAL_MEDIA_FINGERPRINT_VERSION,
    OPTICAL_MEDIA_FINGERPRINT_VERSION,
    parse_unc_server_share,
)
from app.services.source_identity.readiness_service import SourceProfileReadinessService
from app.services.source_identity.source_selection_schema import SourceSelectionResponse


DEFAULT_FILESYSTEM_BATCH_SIZE = 500
DEFAULT_ICLOUD_INTERNAL_BATCH_SIZE = 100
ICLOUD_PREPARE_SCAN_CAP = 10000
_ENABLED_FILESYSTEM_FRIENDLY_TYPES = {"Local", "External", "Removable", "NAS", "Optical"}


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
        self._probe_service = probe_service
        self._source_selection_service = source_selection_service or SourceSelectionService(
            db_session=db_session,
            probe_service=probe_service,
        )

    def dispatch(self, request: RunIngestionDispatchRequest) -> RunIngestionDispatchResponse:
        filesystem_options = request.filesystem_options
        acknowledged = bool(
            filesystem_options.acknowledge_legacy_or_review
        ) if filesystem_options is not None else False
        selection = self._source_selection_service.select_source(
            SourceSelectionRequest(source_profile_id=request.source_profile_id),
            operator_acknowledged=acknowledged,
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

        if context.friendly_source_type == "NAS":
            nas_blocked = self._validate_nas_runtime_root(request, selection)
            if nas_blocked is not None:
                return nas_blocked
        if context.friendly_source_type == "Optical":
            optical_blocked = self._validate_optical_runtime_root(request, selection)
            if optical_blocked is not None:
                return optical_blocked

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
        readiness_service = SourceProfileReadinessService(
            self._db,
            probe_service=self._probe_service,
            runtime_source_root_overrides={request.source_profile_id: runtime_root},
            operator_acknowledged=acknowledged,
        )

        try:
            snapshot = start_source_intake(
                self._db,
                ingestion_source_id=request.source_profile_id,
                source_intake_limit=limit,
                ingest_batch_size=batch_size,
                readiness_acknowledged=acknowledged,
                created_by="run_ingestion_dispatch",
                readiness_service=readiness_service,
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

    def _validate_nas_runtime_root(
        self,
        request: RunIngestionDispatchRequest,
        selection: SourceSelectionResponse,
    ) -> RunIngestionDispatchResponse | None:
        context = selection.selected_source_context
        assert context is not None

        source = self._db.get(IngestionSource, request.source_profile_id)
        if source is None:
            raise LookupError("Source profile not found.")
        if source.profile_status != "active":
            return _nas_blocked(
                request.source_profile_id,
                selection,
                message="Only active NAS Sources can run ingestion.",
                next_action="Review the Source status, then select it again.",
                status="source_profile_inactive",
            )
        if source.endpoint_id is None:
            return _nas_blocked(
                request.source_profile_id,
                selection,
                message="NAS Run Ingestion requires a linked Source Endpoint.",
                next_action="Create or repair the NAS Source through the normal Source workflow.",
                status="nas_endpoint_missing",
            )
        if context.source_endpoint_id != source.endpoint_id:
            return _nas_blocked(
                request.source_profile_id,
                selection,
                message="The selected NAS endpoint changed after Source Selection.",
                next_action="Select Source again before running ingestion.",
                status="nas_endpoint_stale",
            )

        endpoint = self._db.get(SourceEndpoint, source.endpoint_id)
        if endpoint is None:
            return _nas_blocked(
                request.source_profile_id,
                selection,
                message="The linked NAS Source Endpoint was not found.",
                next_action="Review or repair the Source endpoint link.",
                status="nas_endpoint_not_found",
            )
        if endpoint.status != "active":
            return _nas_blocked(
                request.source_profile_id,
                selection,
                message="Only active NAS Source Endpoints can run ingestion.",
                next_action="Review the NAS endpoint status, then select the Source again.",
                status="nas_endpoint_inactive",
            )
        if endpoint.source_type != "nas":
            return _nas_blocked(
                request.source_profile_id,
                selection,
                message="The linked endpoint is not a NAS endpoint.",
                next_action="Review or repair the Source endpoint link before running ingestion.",
                status="nas_endpoint_type_mismatch",
            )
        if context.identity_match_status != "matched":
            return _nas_blocked(
                request.source_profile_id,
                selection,
                message="NAS identity must be matched before running ingestion.",
                next_action="Select Source again after confirming the NAS share is available.",
                status="nas_identity_not_matched",
            )

        endpoint_root = _canonical_unc_share(context.resolved_endpoint_path)
        runtime_root = _normalize_unc_path(context.resolved_source_root)
        if endpoint_root is None:
            return _nas_blocked(
                request.source_profile_id,
                selection,
                message="The selected NAS endpoint did not resolve to a valid UNC server/share.",
                next_action="Confirm the NAS Source uses a canonical UNC share, then select it again.",
                status="nas_endpoint_unc_invalid",
            )
        if runtime_root is None:
            return _nas_blocked(
                request.source_profile_id,
                selection,
                message="The selected NAS Source Root did not resolve to a valid UNC path.",
                next_action="Confirm the NAS Source Root is a UNC path and select it again.",
                status="nas_runtime_root_unc_invalid",
            )

        expected_root = _join_unc_root(endpoint_root, source.endpoint_relative_root or "")
        if expected_root is None:
            return _nas_blocked(
                request.source_profile_id,
                selection,
                message="The NAS Source Root would leave the endpoint share boundary.",
                next_action="Review the Source endpoint-relative root before running ingestion.",
                status="nas_runtime_root_outside_share",
            )
        if not _same_unc_path(runtime_root, expected_root):
            return _nas_blocked(
                request.source_profile_id,
                selection,
                message="The selected NAS Source Root no longer matches the linked endpoint and relative root.",
                next_action="Select Source again after confirming the NAS Source details.",
                status="nas_runtime_root_mismatch",
            )
        if not _is_within_unc_share(runtime_root, endpoint_root):
            return _nas_blocked(
                request.source_profile_id,
                selection,
                message="The NAS Source Root is outside the linked server/share boundary.",
                next_action="Review the NAS Source root before running ingestion.",
                status="nas_runtime_root_outside_share",
            )

        return None

    def _validate_optical_runtime_root(
        self,
        request: RunIngestionDispatchRequest,
        selection: SourceSelectionResponse,
    ) -> RunIngestionDispatchResponse | None:
        context = selection.selected_source_context
        assert context is not None

        source = self._db.get(IngestionSource, request.source_profile_id)
        if source is None:
            raise LookupError("Source profile not found.")
        if source.profile_status != "active":
            return _optical_blocked(
                request.source_profile_id,
                selection,
                message="Only active Optical Sources can run ingestion.",
                next_action="Review the Source status, then select it again.",
                status="source_profile_inactive",
            )
        if source.endpoint_id is None:
            return _optical_blocked(
                request.source_profile_id,
                selection,
                message="Optical Run Ingestion requires a linked Optical Source Endpoint.",
                next_action="Create or repair the Optical Source through the normal Source workflow.",
                status="optical_endpoint_missing",
            )
        if source.endpoint_relative_root is None:
            return _optical_blocked(
                request.source_profile_id,
                selection,
                message="This linked legacy Optical Source needs identity review before it can run ingestion.",
                next_action="Create a current-format Optical Source through the normal Source workflow.",
                status="optical_legacy_source",
            )
        if context.source_endpoint_id != source.endpoint_id:
            return _optical_blocked(
                request.source_profile_id,
                selection,
                message="The selected Optical endpoint changed after Source Selection.",
                next_action="Select Source again before running ingestion.",
                status="optical_endpoint_stale",
            )

        endpoint = self._db.get(SourceEndpoint, source.endpoint_id)
        if endpoint is None:
            return _optical_blocked(
                request.source_profile_id,
                selection,
                message="The linked Optical Source Endpoint was not found.",
                next_action="Review or repair the Source endpoint link.",
                status="optical_endpoint_not_found",
            )
        if endpoint.status != "active":
            return _optical_blocked(
                request.source_profile_id,
                selection,
                message="Only active Optical Source Endpoints can run ingestion.",
                next_action="Review the Optical endpoint status, then select the Source again.",
                status="optical_endpoint_inactive",
            )
        if endpoint.source_type != "optical_media":
            return _optical_blocked(
                request.source_profile_id,
                selection,
                message="The linked endpoint is not an Optical media endpoint.",
                next_action="Review or repair the Source endpoint link before running ingestion.",
                status="optical_endpoint_type_mismatch",
            )
        if endpoint.identity_fingerprint_version == OPTICAL_MEDIA_FINGERPRINT_VERSION:
            return _optical_blocked(
                request.source_profile_id,
                selection,
                message="This Optical Source uses the earlier v1 identity format. Recreate the Optical Source to use the stable v2 identity.",
                next_action="Recreate this Optical Source using the current Optical workflow.",
                status="optical_fingerprint_v1_legacy",
            )
        if not endpoint.identity_fingerprint_hash or endpoint.identity_fingerprint_version != CURRENT_OPTICAL_MEDIA_FINGERPRINT_VERSION:
            return _optical_blocked(
                request.source_profile_id,
                selection,
                message="The linked Optical endpoint does not have a complete current optical media fingerprint.",
                next_action="Create or re-enroll the Optical Source through the normal Source workflow.",
                status="optical_fingerprint_incomplete",
            )
        if context.identity_match_status != "matched" or context.durable_identity_status != "verified":
            return _optical_blocked(
                request.source_profile_id,
                selection,
                message="The inserted Optical disc identity must be completely verified before running ingestion.",
                next_action="Insert the correct Optical disc and select Source again.",
                status="optical_identity_not_matched",
            )

        media_root = _normalize_drive_root(context.resolved_endpoint_path)
        runtime_root = _normalize_local_path(context.resolved_source_root)
        if media_root is None:
            return _optical_blocked(
                request.source_profile_id,
                selection,
                message="The selected Optical media root did not resolve to a valid drive root.",
                next_action="Insert the correct Optical disc and select Source again.",
                status="optical_media_root_invalid",
            )
        if runtime_root is None:
            return _optical_blocked(
                request.source_profile_id,
                selection,
                message="The selected Optical Source Root did not resolve to a valid local path.",
                next_action="Insert the correct Optical disc and select Source again.",
                status="optical_runtime_root_invalid",
            )

        expected_root = _join_local_root(media_root, source.endpoint_relative_root)
        if expected_root is None:
            return _optical_blocked(
                request.source_profile_id,
                selection,
                message="The Optical Source Root would leave the inserted media boundary.",
                next_action="Review the Optical Source endpoint-relative root before running ingestion.",
                status="optical_runtime_root_outside_media",
            )
        if not _same_local_path(runtime_root, expected_root):
            return _optical_blocked(
                request.source_profile_id,
                selection,
                message="The selected Optical Source Root no longer matches the linked media and relative root.",
                next_action="Select Source again after confirming the correct disc is inserted.",
                status="optical_runtime_root_mismatch",
            )
        if not _is_within_local_root(runtime_root, media_root):
            return _optical_blocked(
                request.source_profile_id,
                selection,
                message="The Optical Source Root is outside the inserted media boundary.",
                next_action="Review the Optical Source root before running ingestion.",
                status="optical_runtime_root_outside_media",
            )

        return None

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


def _nas_blocked(
    source_profile_id: int,
    selection: SourceSelectionResponse,
    *,
    message: str,
    next_action: str,
    status: str,
) -> RunIngestionDispatchResponse:
    return RunIngestionDispatchResponse(
        result="blocked",
        workflow_kind="filesystem_source_intake",
        action="none",
        message=message,
        next_action=next_action,
        source_profile_id=source_profile_id,
        status=status,
        workflow_payload={"selection": _safe_payload(selection)},
    )


def _optical_blocked(
    source_profile_id: int,
    selection: SourceSelectionResponse,
    *,
    message: str,
    next_action: str,
    status: str,
) -> RunIngestionDispatchResponse:
    return RunIngestionDispatchResponse(
        result="blocked",
        workflow_kind="filesystem_source_intake",
        action="none",
        message=message,
        next_action=next_action,
        source_profile_id=source_profile_id,
        status=status,
        workflow_payload={"selection": _safe_payload(selection)},
    )


def _canonical_unc_share(path: str | None) -> str | None:
    server_share = parse_unc_server_share(path)
    if server_share is None:
        return None
    server, share = server_share
    return f"\\\\{server}\\{share}"


def _normalize_unc_path(path: str | None) -> str | None:
    if parse_unc_server_share(path) is None:
        return None
    normalized = ntpath.normpath((path or "").replace("/", "\\"))
    if parse_unc_server_share(normalized) is None:
        return None
    return normalized.rstrip("\\")


def _join_unc_root(endpoint_root: str, endpoint_relative_root: str) -> str | None:
    endpoint = _canonical_unc_share(endpoint_root)
    if endpoint is None:
        return None
    relative = (endpoint_relative_root or "").strip("\\/")
    if not relative:
        return endpoint
    if any(part == ".." for part in re.split(r"[\\/]+", relative)):
        return None
    joined = _normalize_unc_path(f"{endpoint}\\{relative}")
    if joined is None or not _is_within_unc_share(joined, endpoint):
        return None
    return joined


def _is_within_unc_share(path: str, endpoint_root: str) -> bool:
    normalized_path = _normalize_unc_path(path)
    normalized_endpoint = _canonical_unc_share(endpoint_root)
    if normalized_path is None or normalized_endpoint is None:
        return False
    left = normalized_path.casefold()
    right = normalized_endpoint.rstrip("\\").casefold()
    return left == right or left.startswith(f"{right}\\")


def _same_unc_path(left: str, right: str) -> bool:
    normalized_left = _normalize_unc_path(left)
    normalized_right = _normalize_unc_path(right)
    if normalized_left is None or normalized_right is None:
        return False
    return normalized_left.casefold() == normalized_right.casefold()


def _normalize_drive_root(path: str | None) -> str | None:
    normalized = _normalize_local_path(path)
    if normalized is None:
        return None
    drive, tail = ntpath.splitdrive(normalized)
    if not drive or tail not in {"\\", ""}:
        return None
    return f"{drive.upper()}\\"


def _normalize_local_path(path: str | None) -> str | None:
    if not path:
        return None
    normalized = ntpath.normpath(path.replace("/", "\\"))
    drive, _tail = ntpath.splitdrive(normalized)
    if not drive or drive.startswith("\\\\"):
        return None
    return normalized.rstrip("\\") if normalized.rstrip("\\") else normalized


def _join_local_root(root: str, endpoint_relative_root: str) -> str | None:
    media_root = _normalize_drive_root(root)
    if media_root is None:
        return None
    relative = (endpoint_relative_root or "").strip("\\/")
    if not relative:
        return media_root
    if any(part == ".." for part in re.split(r"[\\/]+", relative)):
        return None
    joined = _normalize_local_path(f"{media_root}{relative}")
    if joined is None or not _is_within_local_root(joined, media_root):
        return None
    return joined


def _is_within_local_root(path: str, root: str) -> bool:
    normalized_path = _normalize_local_path(path)
    normalized_root = _normalize_drive_root(root)
    if normalized_path is None or normalized_root is None:
        return False
    left = normalized_path.casefold()
    right = normalized_root.rstrip("\\").casefold()
    return left == right or left.startswith(f"{right}\\")


def _same_local_path(left: str, right: str) -> bool:
    normalized_left = _normalize_local_path(left)
    normalized_right = _normalize_local_path(right)
    if normalized_left is None or normalized_right is None:
        return False
    return normalized_left.casefold() == normalized_right.casefold()


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
