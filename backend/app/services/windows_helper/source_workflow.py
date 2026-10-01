"""Durable whole-source inventory and bounded-child Windows orchestration."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import ntpath
from pathlib import Path, PureWindowsPath
import shutil
import threading
import time
from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.ingestion_source import IngestionSource
from app.models.source_acquisition import SourceAcquisitionRun
from app.models.source_endpoint import AccessNode, SourceEndpoint
from app.models.source_intake_run import SourceIntakeRun
from app.models.windows_helper import WindowsHelperOperation
from app.models.windows_source_workflow import (
    WindowsSourceWorkflow,
    WindowsSourceWorkflowCandidate,
    WindowsSourceWorkflowChild,
    WindowsSourceWorkflowPage,
)
from app.schemas.windows_helper import CreateWindowsHelperInventoryOperationRequest
from app.schemas.windows_source_ui import (
    WindowsSourceUiCandidateReview,
    WindowsSourceUiOperation,
    WindowsSourceUiWorkflowStatus,
)
from app.services.source_acquisition.service import (
    create_planned_child_run,
)
from app.services.source_acquisition.workflow import advance_source_acquisition_workflow
from app.services.windows_helper.operations import (
    completed_inventory_attestation,
    create_known_source_attestation_operation,
    create_inventory_operation,
    get_operation_status,
)
from app.services.windows_helper.service import WindowsHelperServiceError
from app.windows_helper_shared.protocol import HelperInventoryPageRequest


CHILD_CANDIDATE_LIMIT = 100
_workers_lock = threading.Lock()
_workers: dict[str, threading.Thread] = {}


def acquisition_chunk_sizes(candidate_count: int) -> list[int]:
    """Return the exact bounded child shape for one approved parent."""
    if candidate_count < 0:
        raise ValueError("candidate_count must not be negative")
    return [
        min(CHILD_CANDIDATE_LIMIT, candidate_count - start)
        for start in range(0, candidate_count, CHILD_CANDIDATE_LIMIT)
    ]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _proposal_digest(
    row: WindowsSourceWorkflow,
    candidates: list[WindowsSourceWorkflowCandidate],
) -> str:
    return _digest(
        {
            "domain": "photo-organizer-windows-whole-source-proposal-v1",
            "workflow_id": row.workflow_uuid,
            "inventory_chain_digest": row.inventory_chain_digest,
            "observed_item_count": row.observed_item_count,
            "eligible_item_count": row.eligible_item_count,
            "rejected_item_count": row.rejected_item_count,
            "expected_byte_count": row.expected_byte_count,
            "expected_child_count": (
                row.eligible_item_count + CHILD_CANDIDATE_LIMIT - 1
            ) // CHILD_CANDIDATE_LIMIT,
            "candidate_evidence": [
                {
                    "reference": item.candidate_reference,
                    "relative_path": item.normalized_path,
                    "size": item.size_bytes,
                    "mtime_ns": item.modified_time_ns,
                    "file_id": item.stable_file_id_digest,
                    "local_residency": item.local_residency,
                    "windows_file_attributes": item.windows_file_attributes,
                }
                for item in candidates
            ],
        }
    )


def _workflow(db: Session, workflow_id: UUID, *, lock: bool = False) -> WindowsSourceWorkflow:
    statement = select(WindowsSourceWorkflow).where(
        WindowsSourceWorkflow.workflow_uuid == str(workflow_id)
    )
    if lock:
        statement = statement.with_for_update()
    row = db.scalar(statement)
    if row is None:
        raise WindowsHelperServiceError(
            "windows_workflow_not_found", "The Windows ingestion workflow was not found.", http_status=404
        )
    return row


def create_inventory_workflow(
    db: Session,
    *,
    source_profile_id: int,
    probe_operation_id: UUID,
    first_inventory_operation_id: UUID,
) -> WindowsSourceUiOperation:
    operation = db.scalar(
        select(WindowsHelperOperation).where(
            WindowsHelperOperation.operation_uuid == str(first_inventory_operation_id)
        )
    )
    source = db.get(IngestionSource, source_profile_id)
    endpoint = db.get(SourceEndpoint, source.endpoint_id) if source is not None and source.endpoint_id else None
    if (
        operation is None
        or operation.operation_type != "inventory_page"
        or operation.source_profile_id != source_profile_id
        or operation.source_endpoint_id is None
        or source is None
        or endpoint is None
        or not endpoint.identity_fingerprint_hash
        or not source.source_root_path
    ):
        raise WindowsHelperServiceError(
            "inventory_workflow_binding_invalid",
            "The Windows inventory workflow binding is invalid.",
            http_status=409,
        )
    inventory_request = HelperInventoryPageRequest.model_validate_json(operation.request_json)
    row = WindowsSourceWorkflow(
        workflow_uuid=(
            str(inventory_request.parent_workflow_id)
            if inventory_request.parent_workflow_id is not None
            else str(uuid5(first_inventory_operation_id, "legacy-inventory-workflow-v1"))
        ),
        source_profile_id=source.id,
        source_endpoint_id=endpoint.id,
        access_node_id=operation.access_node_id,
        probe_operation_uuid=str(probe_operation_id),
        state="inventorying",
        source_fingerprint=endpoint.identity_fingerprint_hash,
        provider_native_root=inventory_request.provider_native_path.provider_native_root,
        max_observed_entries=max(1, settings.windows_inventory_max_entries),
        safe_status="Preparing the complete point-in-time file proposal.",
    )
    db.add(row)
    db.flush()
    db.add(
        WindowsSourceWorkflowPage(
            workflow_id=row.id,
            page_index=1,
            operation_uuid=str(first_inventory_operation_id),
        )
    )
    db.commit()
    start_or_resume_worker(UUID(row.workflow_uuid))
    return WindowsSourceUiOperation(
        operation_token=UUID(row.workflow_uuid),
        stage="preparing_files",
        safe_message="Preparing the complete point-in-time file proposal.",
    )


def workflow_operation_status(db: Session, workflow_id: UUID) -> WindowsSourceUiOperation | None:
    row = db.scalar(
        select(WindowsSourceWorkflow).where(
            WindowsSourceWorkflow.workflow_uuid == str(workflow_id)
        )
    )
    if row is None:
        return None
    if row.state == "inventorying":
        start_or_resume_worker(workflow_id)
        stage = "preparing_files"
    elif row.state == "awaiting_confirmation":
        stage = "ready"
    else:
        stage = "failed"
    return WindowsSourceUiOperation(
        operation_token=workflow_id,
        stage=stage,
        source_ready=stage == "ready",
        safe_message=row.safe_status or "Windows Source workflow status is available.",
    )


def review_inventory_workflow(
    db: Session, source_profile_id: int, workflow_id: UUID
) -> WindowsSourceUiCandidateReview:
    row = _workflow(db, workflow_id)
    if row.source_profile_id != source_profile_id or row.state != "awaiting_confirmation":
        raise WindowsHelperServiceError(
            "inventory_not_ready", "The complete file proposal is not ready.", http_status=409
        )
    source = db.get(IngestionSource, source_profile_id)
    if source is None:
        raise WindowsHelperServiceError("source_profile_unavailable", "Source Profile unavailable.", http_status=404)
    return WindowsSourceUiCandidateReview(
        workflow_token=workflow_id,
        files_to_process=row.eligible_item_count,
        inventory_candidates=row.observed_item_count,
        predictable_rejections=row.rejected_item_count,
        expected_chunks=(row.eligible_item_count + CHILD_CANDIDATE_LIMIT - 1) // CHILD_CANDIDATE_LIMIT,
        total_bytes=row.expected_byte_count,
        profile_name=source.source_label,
        windows_root=row.provider_native_root,
        safe_message="Review the complete point-in-time file set before starting ingestion.",
    )


def approve_or_resume_workflow(
    db: Session, workflow_id: UUID, *, confirm: bool
) -> WindowsSourceUiWorkflowStatus:
    row = _workflow(db, workflow_id, lock=True)
    if confirm:
        if row.state in {"running", "processing", "completed", "failed"}:
            return workflow_status(db, workflow_id)
        if row.state == "blocked":
            row.state = "running"
            row.failure_code = None
            row.safe_status = "Resuming the approved Source run from durable progress."
            db.commit()
            start_or_resume_worker(workflow_id)
            return workflow_status(db, workflow_id)
        if row.state != "awaiting_confirmation" or not row.proposal_digest:
            raise WindowsHelperServiceError(
                "workflow_not_awaiting_confirmation",
                "The complete proposal is not awaiting approval.",
                http_status=409,
            )
        candidates = list(
            db.scalars(
                select(WindowsSourceWorkflowCandidate)
                .where(
                    WindowsSourceWorkflowCandidate.workflow_id == row.id,
                    WindowsSourceWorkflowCandidate.eligibility == "eligible",
                )
                .order_by(WindowsSourceWorkflowCandidate.ordinal)
            )
        )
        if row.proposal_digest != _proposal_digest(row, candidates):
            raise WindowsHelperServiceError(
                "workflow_proposal_changed",
                "The complete Source proposal changed and must be prepared again.",
                http_status=409,
            )
        row.state = "running"
        row.approved_at = _now()
        row.safe_status = "The approved Source run is continuing in the background."
        chunk_sizes = acquisition_chunk_sizes(row.eligible_item_count)
        first_ordinal = 1
        for index, chunk_size in enumerate(chunk_sizes, start=1):
            db.add(
                WindowsSourceWorkflowChild(
                    workflow_id=row.id,
                    child_index=index,
                    first_candidate_ordinal=first_ordinal,
                    candidate_count=chunk_size,
                    state="pending",
                )
            )
            first_ordinal += chunk_size
        row.child_count = len(chunk_sizes)
        db.commit()
    elif row.state == "blocked":
        row.state = "running"
        row.failure_code = None
        row.safe_status = "Resuming the approved Source run from durable progress."
        db.commit()
    elif row.state not in {"running", "processing", "completed", "failed"}:
        raise WindowsHelperServiceError(
            "workflow_resume_invalid", "This Windows workflow cannot be resumed.", http_status=409
        )
    if row.state == "running":
        start_or_resume_worker(workflow_id)
    return workflow_status(db, workflow_id)


def workflow_status(db: Session, workflow_id: UUID) -> WindowsSourceUiWorkflowStatus:
    row = _workflow(db, workflow_id)
    source = db.get(IngestionSource, row.source_profile_id)
    if row.state == "running":
        start_or_resume_worker(workflow_id)
    stage = {
        "inventorying": "inventorying",
        "awaiting_confirmation": "awaiting_confirmation",
        "running": "transferring_files",
        "processing": "processing_library",
        "completed": "complete",
        "blocked": "paused",
        "failed": "failed",
    }.get(row.state, "failed")
    files_completed = row.completed_item_count
    transferred_bytes = row.transferred_byte_count
    active_child = db.scalar(
        select(WindowsSourceWorkflowChild)
        .where(
            WindowsSourceWorkflowChild.workflow_id == row.id,
            WindowsSourceWorkflowChild.state == "running",
            WindowsSourceWorkflowChild.acquisition_run_id.is_not(None),
        )
        .order_by(WindowsSourceWorkflowChild.child_index)
        .limit(1)
    )
    if active_child is not None and active_child.acquisition_run_id is not None:
        active_acquisition = db.get(SourceAcquisitionRun, active_child.acquisition_run_id)
        if active_acquisition is not None:
            files_completed += active_acquisition.ready_item_count
            transferred_bytes += active_acquisition.committed_byte_count
            if (
                row.state == "running"
                and active_acquisition.state == "completed"
                and active_acquisition.bridge_state == "running"
            ):
                stage = "processing_library"
    return WindowsSourceUiWorkflowStatus(
        workflow_token=workflow_id,
        source_profile_id=row.source_profile_id,
        source_label=source.source_label if source is not None else None,
        started_at=row.approved_at or row.created_at,
        finished_at=row.completed_at,
        stage=stage,
        files_total=row.eligible_item_count,
        files_completed=files_completed,
        inventory_candidates=row.observed_item_count,
        predictable_rejections=row.rejected_item_count,
        chunks_completed=row.completed_child_count,
        chunks_total=row.child_count,
        files_remaining=max(0, row.eligible_item_count - files_completed),
        expected_bytes=row.expected_byte_count,
        transferred_bytes=transferred_bytes,
        new_library_items=row.new_library_items,
        already_represented=row.already_represented,
        failed_items=row.failed_item_count,
        safe_message=row.safe_status or "Windows Source workflow status is available.",
    )


def latest_workflow_status(
    db: Session, source_profile_id: int
) -> WindowsSourceUiWorkflowStatus | None:
    row = db.scalar(
        select(WindowsSourceWorkflow)
        .where(WindowsSourceWorkflow.source_profile_id == source_profile_id)
        .order_by(WindowsSourceWorkflow.id.desc())
        .limit(1)
    )
    if row is None:
        return None
    return workflow_status(db, UUID(row.workflow_uuid))


def reset_interrupted_workflows(db: Session) -> None:
    """Fail inventory restarts closed; make approved work explicitly resumable."""
    rows = list(
        db.scalars(
            select(WindowsSourceWorkflow).where(
                WindowsSourceWorkflow.state.in_(("inventorying", "running", "processing"))
            )
        )
    )
    for row in rows:
        if row.state == "inventorying":
            row.state = "failed"
            row.failure_code = "inventory_process_restarted"
            row.safe_status = "Inventory was interrupted. Prepare a fresh proposal and approve it again."
        else:
            row.state = "blocked"
            row.failure_code = "backend_process_restarted"
            row.safe_status = "The approved run was paused by a backend restart. Resume from durable progress."
    if rows:
        db.commit()


def start_or_resume_worker(workflow_id: UUID) -> None:
    key = str(workflow_id)
    with _workers_lock:
        current = _workers.get(key)
        if current is not None and current.is_alive():
            return
        worker = threading.Thread(
            target=_worker_main,
            args=(workflow_id,),
            daemon=True,
            name=f"windows-source-{key}",
        )
        _workers[key] = worker
        worker.start()


def _worker_main(workflow_id: UUID) -> None:
    key = str(workflow_id)
    try:
        while True:
            with SessionLocal() as db:
                row = _workflow(db, workflow_id)
                if row.state == "inventorying":
                    waiting = _advance_inventory(db, row)
                elif row.state == "running":
                    waiting = _advance_execution(db, row)
                else:
                    return
            time.sleep(0.5 if waiting else 0.05)
    except WindowsHelperServiceError as exc:
        with SessionLocal() as db:
            row = db.scalar(select(WindowsSourceWorkflow).where(WindowsSourceWorkflow.workflow_uuid == key))
            if row is not None and row.state not in {"completed", "failed"}:
                resumable = exc.code in {
                    "helper_offline",
                    "source_intake_already_running",
                    "acquisition_operation_active",
                }
                row.state = "blocked" if resumable and row.approved_at is not None else "failed"
                row.failure_code = exc.code
                row.safe_status = (
                    "The approved run is paused. Reconnect the same Source device and resume."
                    if row.state == "blocked"
                    else exc.message
                )
                db.commit()
    except Exception:
        with SessionLocal() as db:
            row = db.scalar(select(WindowsSourceWorkflow).where(WindowsSourceWorkflow.workflow_uuid == key))
            if row is not None and row.state not in {"completed", "failed"}:
                row.state = "failed"
                row.failure_code = "windows_workflow_internal_error"
                row.safe_status = "The Windows Source workflow stopped safely and requires review."
                db.commit()
    finally:
        with _workers_lock:
            _workers.pop(key, None)


def _advance_inventory(db: Session, row: WindowsSourceWorkflow) -> bool:
    page = db.scalar(
        select(WindowsSourceWorkflowPage)
        .where(WindowsSourceWorkflowPage.workflow_id == row.id)
        .order_by(WindowsSourceWorkflowPage.page_index.desc())
        .limit(1)
    )
    if page is None:
        raise WindowsHelperServiceError("inventory_chain_incomplete", "The inventory chain is incomplete.", http_status=409)
    status = get_operation_status(db, UUID(page.operation_uuid))
    if status.state in {"pending", "claimed"}:
        return True
    if status.operation_type == "attest_inventory":
        if status.state != "completed":
            raise WindowsHelperServiceError(
                "inventory_chain_interrupted",
                "The inventory attestation stopped. Prepare a fresh proposal.",
                http_status=409,
            )
        operation, attestation = completed_inventory_attestation(
            db,
            UUID(page.operation_uuid),
            require_fresh=True,
            expected_source_profile_id=row.source_profile_id,
        )
        inventory = create_inventory_operation(
            db,
            CreateWindowsHelperInventoryOperationRequest(
                source_profile_id=row.source_profile_id,
                probe_operation_id=UUID(operation.operation_uuid),
                page_size=100,
                inventory_generation=attestation.inventory_generation,
                cursor=attestation.continuation_cursor,
            ),
        )
        page.operation_uuid = str(inventory.operation_id)
        db.add(page)
        db.commit()
        return True
    if status.state != "completed" or status.inventory_result is None or not status.result_digest:
        raise WindowsHelperServiceError(
            "inventory_chain_interrupted",
            "The inventory continuation stopped. Start a fresh inventory and approve it again.",
            http_status=409,
        )
    result = status.inventory_result
    if result.result_status.value == "attestation_required":
        inventory_operation = db.scalar(
            select(WindowsHelperOperation).where(
                WindowsHelperOperation.operation_uuid == page.operation_uuid
            )
        )
        if inventory_operation is None:
            raise WindowsHelperServiceError(
                "inventory_chain_interrupted", "The inventory operation is unavailable.", http_status=409
            )
        inventory_request = HelperInventoryPageRequest.model_validate_json(
            inventory_operation.request_json
        )
        node = db.get(AccessNode, row.access_node_id)
        if node is None or inventory_request.parent_workflow_id is None:
            raise WindowsHelperServiceError(
                "inventory_chain_interrupted", "The inventory authority is unavailable.", http_status=409
            )
        refresh = create_known_source_attestation_operation(
            db,
            row.source_profile_id,
            node,
            parent_workflow_id=inventory_request.parent_workflow_id,
            inventory_generation=result.inventory_generation,
            continuation_cursor=inventory_request.cursor,
        )
        page.operation_uuid = str(refresh.operation_id)
        db.add(page)
        db.commit()
        return True
    if result.result_status.value != "success":
        raise WindowsHelperServiceError(
            "inventory_chain_interrupted",
            "The inventory continuation is no longer valid. Prepare a fresh proposal and approve it again.",
            http_status=409,
        )
    if page.result_digest is None:
        if row.inventory_generation is None:
            row.inventory_generation = str(result.inventory_generation)
        elif row.inventory_generation != str(result.inventory_generation):
            raise WindowsHelperServiceError(
                "inventory_generation_changed", "The inventory generation changed unexpectedly.", http_status=409
            )
        next_total = row.observed_item_count + len(result.items)
        if next_total > row.max_observed_entries:
            raise WindowsHelperServiceError(
                "inventory_source_limit_exceeded",
                f"This Source exceeds the configured {row.max_observed_entries} entry safety limit; no truncated proposal was created.",
                http_status=409,
            )
        classifications = {item.candidate_reference: item for item in status.inventory_candidates}
        existing_candidates = list(
            db.scalars(
                select(WindowsSourceWorkflowCandidate).where(
                    WindowsSourceWorkflowCandidate.workflow_id == row.id
                )
            )
        )
        seen_references = {item.candidate_reference for item in existing_candidates}
        seen_paths = {item.normalized_path for item in existing_candidates}
        for item in result.items:
            normalized = ntpath.normcase(item.provider_native_path.provider_native_relative_path)
            if item.candidate_reference in seen_references or normalized in seen_paths:
                raise WindowsHelperServiceError(
                    "inventory_chain_ambiguous",
                    "The inventory chain contains a duplicate candidate or relative path.",
                    http_status=409,
                )
            seen_references.add(item.candidate_reference)
            seen_paths.add(normalized)
            classification = classifications[item.candidate_reference]
            eligible = (
                classification.eligibility == "eligible"
                and item.local_residency == "resident"
            )
            effective_eligibility = "eligible" if eligible else "rejected"
            effective_reason = (
                classification.eligibility_reason
                if classification.eligibility != "eligible" or eligible
                else "not_locally_resident"
            )
            db.add(
                WindowsSourceWorkflowCandidate(
                    workflow_id=row.id,
                    ordinal=row.observed_item_count + 1,
                    candidate_reference=item.candidate_reference,
                    relative_path=item.provider_native_path.provider_native_relative_path,
                    normalized_path=normalized,
                    normalized_path_digest=_digest(normalized),
                    full_path=item.provider_native_path.provider_native_full_path,
                    filename=item.filename,
                    safe_extension=PureWindowsPath(item.filename).suffix.casefold(),
                    size_bytes=item.size_bytes,
                    modified_time_ns=item.modified_time_ns,
                    stable_file_id_digest=item.stable_file_id_digest,
                    windows_file_attributes=item.windows_file_attributes,
                    local_residency=item.local_residency,
                    eligibility=effective_eligibility,
                    eligibility_reason=effective_reason,
                )
            )
            row.observed_item_count += 1
            if eligible:
                row.eligible_item_count += 1
                row.expected_byte_count += int(item.size_bytes or 0)
            else:
                row.rejected_item_count += 1
        page.result_digest = status.result_digest
        page.item_count = len(result.items)
        page.next_cursor = result.next_cursor
        page.completed_at = _now()
        db.commit()
    if result.next_cursor is not None:
        page_rows = list(
            db.scalars(
                select(WindowsSourceWorkflowPage).where(
                    WindowsSourceWorkflowPage.workflow_id == row.id
                )
            )
        )
        request_cursors: set[str] = set()
        for prior_page in page_rows:
            prior_operation = db.scalar(
                select(WindowsHelperOperation).where(
                    WindowsHelperOperation.operation_uuid == prior_page.operation_uuid
                )
            )
            if prior_operation is not None:
                prior_request = HelperInventoryPageRequest.model_validate_json(
                    prior_operation.request_json
                )
                if prior_request.cursor is not None:
                    request_cursors.add(prior_request.cursor)
        if result.next_cursor in request_cursors:
            raise WindowsHelperServiceError(
                "inventory_cursor_loop",
                "The inventory continuation repeated a prior cursor; prepare a fresh proposal.",
                http_status=409,
            )
        existing_next = db.scalar(
            select(WindowsSourceWorkflowPage).where(
                WindowsSourceWorkflowPage.workflow_id == row.id,
                WindowsSourceWorkflowPage.page_index == page.page_index + 1,
            )
        )
        if existing_next is None:
            try:
                operation = create_inventory_operation(
                    db,
                    CreateWindowsHelperInventoryOperationRequest(
                        source_profile_id=row.source_profile_id,
                        probe_operation_id=UUID(row.probe_operation_uuid),
                        page_size=100,
                        inventory_generation=UUID(row.inventory_generation or ""),
                        cursor=result.next_cursor,
                    ),
                )
            except WindowsHelperServiceError as exc:
                if exc.code != "inventory_attestation_expired":
                    raise
                node = db.get(AccessNode, row.access_node_id)
                if node is None:
                    raise
                operation = create_known_source_attestation_operation(
                    db,
                    row.source_profile_id,
                    node,
                    parent_workflow_id=UUID(row.workflow_uuid),
                    inventory_generation=UUID(row.inventory_generation or ""),
                    continuation_cursor=result.next_cursor,
                )
            db.add(
                WindowsSourceWorkflowPage(
                    workflow_id=row.id,
                    page_index=page.page_index + 1,
                    operation_uuid=str(operation.operation_id),
                )
            )
            db.commit()
        return False
    pages = list(db.scalars(select(WindowsSourceWorkflowPage).where(WindowsSourceWorkflowPage.workflow_id == row.id).order_by(WindowsSourceWorkflowPage.page_index)))
    if (
        [item.page_index for item in pages] != list(range(1, len(pages) + 1))
        or any(not item.result_digest for item in pages)
    ):
        raise WindowsHelperServiceError(
            "inventory_chain_incomplete",
            "The inventory chain is incomplete.",
            http_status=409,
        )
    candidates = list(db.scalars(select(WindowsSourceWorkflowCandidate).where(WindowsSourceWorkflowCandidate.workflow_id == row.id, WindowsSourceWorkflowCandidate.eligibility == "eligible").order_by(WindowsSourceWorkflowCandidate.ordinal)))
    row.inventory_chain_digest = _digest(
        {
            "domain": "photo-organizer-source-acquisition-inventory-chain-v1",
            "access_node_id": row.access_node_id,
            "source_endpoint_id": row.source_endpoint_id,
            "source_profile_id": row.source_profile_id,
            "provider_native_root": ntpath.normcase(row.provider_native_root),
            "source_fingerprint": row.source_fingerprint,
            "inventory_generation": row.inventory_generation,
            "pages": [{"operation_id": item.operation_uuid, "result_digest": item.result_digest} for item in pages],
        }
    )
    row.proposal_digest = _proposal_digest(row, candidates)
    base = Path(settings.acquisition_receiving_path)
    if not base.is_absolute():
        raise WindowsHelperServiceError("receiving_root_not_absolute", "Acquisition storage is not configured safely.", http_status=500)
    base.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(base).free < row.expected_byte_count + settings.acquisition_disk_reserve_bytes:
        raise WindowsHelperServiceError("receiving_capacity_insufficient", "Receiving storage lacks the required safety reserve.", http_status=409)
    row.state = "awaiting_confirmation"
    row.safe_status = "The complete point-in-time proposal is ready for review."
    db.commit()
    return False


def _advance_execution(db: Session, row: WindowsSourceWorkflow) -> bool:
    child = db.scalar(
        select(WindowsSourceWorkflowChild)
        .where(
            WindowsSourceWorkflowChild.workflow_id == row.id,
            WindowsSourceWorkflowChild.state != "completed",
        )
        .order_by(WindowsSourceWorkflowChild.child_index)
        .limit(1)
    )
    if child is None:
        row.state = "completed"
        row.completed_at = _now()
        row.safe_status = "Run complete."
        db.commit()
        return False
    if child.acquisition_run_id is None:
        eligible = list(
            db.scalars(
                select(WindowsSourceWorkflowCandidate)
                .where(
                    WindowsSourceWorkflowCandidate.workflow_id == row.id,
                    WindowsSourceWorkflowCandidate.eligibility == "eligible",
                )
                .order_by(WindowsSourceWorkflowCandidate.ordinal)
                .offset(child.first_candidate_ordinal - 1)
                .limit(child.candidate_count)
            )
        )
        acquisition = create_planned_child_run(
            db,
            idempotency_key=uuid5(UUID(row.workflow_uuid), f"child:{child.child_index}"),
            source_profile_id=row.source_profile_id,
            inventory_generation=UUID(row.inventory_generation or ""),
            inventory_chain_digest=row.inventory_chain_digest or "",
            runtime_root=row.provider_native_root,
            candidates=eligible,
            access_node_db_id=row.access_node_id,
        )
        child.acquisition_run_id = db.scalar(
            select(SourceAcquisitionRun.id).where(
                SourceAcquisitionRun.run_uuid == str(acquisition.acquisition_run_id)
            )
        )
        child.state = "running"
        db.commit()
    acquisition_row = db.get(SourceAcquisitionRun, child.acquisition_run_id)
    if acquisition_row is None:
        raise WindowsHelperServiceError("acquisition_run_not_found", "A bounded acquisition child is missing.", http_status=409)
    child_workflow = advance_source_acquisition_workflow(
        db,
        UUID(acquisition_row.run_uuid),
        proposal_digest=(
            acquisition_row.proposal_digest
            if acquisition_row.state == "planned"
            else None
        ),
    )
    if child_workflow.stage == "failed":
        row.state = "failed"
        row.failure_code = acquisition_row.failure_code or "acquisition_child_failed"
        row.failed_item_count += acquisition_row.failed_item_count
        row.safe_status = "A bounded child failed verification or Source Intake; the approved run stopped safely."
        db.commit()
        return False
    if child_workflow.stage != "completed":
        return True
    db.expire_all()
    acquisition_row = db.get(SourceAcquisitionRun, child.acquisition_run_id)
    if acquisition_row is None:
        raise WindowsHelperServiceError("acquisition_run_not_found", "A bounded acquisition child is missing.", http_status=409)
    intake = (
        db.get(SourceIntakeRun, acquisition_row.bridge_source_intake_run_id)
        if acquisition_row.bridge_source_intake_run_id is not None
        else None
    )
    child_new = int(intake.processed_new_unique or 0) if intake is not None else 0
    child_failed = int(intake.failed_or_rejected or 0) if intake is not None else 0
    child_already = max(0, acquisition_row.selected_item_count - child_new - child_failed)
    child.state = "completed"
    child.completed_at = _now()
    row.completed_child_count += 1
    row.completed_item_count += acquisition_row.ready_item_count
    row.transferred_byte_count += acquisition_row.committed_byte_count
    row.new_library_items += child_new
    row.already_represented += child_already
    row.failed_item_count += child_failed
    row.safe_status = f"Transferred chunk {row.completed_child_count} of {row.child_count}."
    db.commit()
    return False
