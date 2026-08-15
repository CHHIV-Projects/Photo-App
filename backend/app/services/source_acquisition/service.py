"""Immutable inventory selection and durable Source acquisition lifecycle."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import ntpath
import os
from pathlib import Path, PureWindowsPath
import shutil
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ingestion_source import IngestionSource
from app.models.source_acquisition import SourceAcquisitionItem, SourceAcquisitionRun
from app.models.source_endpoint import AccessNode, SourceEndpoint, SourceEndpointObservedPath
from app.models.windows_helper import WindowsHelperOperation
from app.schemas.source_acquisition import (
    CreateSourceAcquisitionPlanRequest,
    SourceAcquisitionItemSummary,
    SourceAcquisitionRunResponse,
)
from app.services.windows_helper.service import WindowsHelperServiceError
from app.windows_helper_shared.protocol import (
    HelperInventoryPageRequest,
    HelperInventoryPageResponse,
    canonical_protocol_digest,
)


PROVIDER = "windows_helper"
RUN_STATES = {"planned", "active", "completed", "failed", "cancelled"}
ITEM_STATES = {"pending", "transferring", "verifying", "ready", "failed"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _receiving_base() -> Path:
    base = Path(settings.acquisition_receiving_path)
    if not base.is_absolute():
        raise WindowsHelperServiceError(
            "receiving_root_not_absolute", "Acquisition receiving storage is not configured safely.", http_status=500
        )
    if base.exists() and (base.is_symlink() or not base.is_dir()):
        raise WindowsHelperServiceError(
            "receiving_root_unsafe", "Acquisition receiving storage is not a safe directory.", http_status=500
        )
    base.mkdir(parents=True, mode=0o700, exist_ok=True)
    if base.is_symlink():
        raise WindowsHelperServiceError(
            "receiving_root_unsafe", "Acquisition receiving storage changed unexpectedly.", http_status=500
        )
    os.chmod(base, 0o700)
    return base.resolve(strict=True)


def _load_profile(db: Session, source_profile_id: int) -> tuple[IngestionSource, SourceEndpoint, AccessNode]:
    source = db.get(IngestionSource, source_profile_id)
    if source is None or source.endpoint_id is None or not source.source_root_path:
        raise WindowsHelperServiceError("source_profile_unavailable", "The Source Profile is unavailable.", http_status=404)
    endpoint = db.get(SourceEndpoint, source.endpoint_id)
    if endpoint is None or not endpoint.identity_fingerprint_hash:
        raise WindowsHelperServiceError("source_endpoint_unavailable", "The Source Endpoint is unavailable.", http_status=409)
    nodes = list(
        db.scalars(
            select(AccessNode)
            .join(SourceEndpointObservedPath, SourceEndpointObservedPath.access_node_id == AccessNode.id)
            .where(
                SourceEndpointObservedPath.source_endpoint_id == endpoint.id,
                AccessNode.provider_name == "windows_helper_v1",
                AccessNode.status == "active",
                AccessNode.os_family == "windows",
            )
            .distinct()
        )
    )
    if len(nodes) != 1:
        raise WindowsHelperServiceError(
            "source_access_node_ambiguous", "The Source does not have one exact active Helper Access Node.", http_status=409
        )
    return source, endpoint, nodes[0]


def _validated_inventory_chain(
    db: Session,
    request: CreateSourceAcquisitionPlanRequest,
    source: IngestionSource,
    endpoint: SourceEndpoint,
    node: AccessNode,
) -> tuple[UUID, str, list[object], str]:
    if len(request.inventory_operation_ids) != len(set(request.inventory_operation_ids)):
        raise WindowsHelperServiceError("inventory_chain_ambiguous", "Inventory operation IDs must be unique.", http_status=409)
    pages: list[tuple[WindowsHelperOperation, HelperInventoryPageRequest, HelperInventoryPageResponse]] = []
    expected_cursor: str | None = None
    generation: UUID | None = None
    chain_parts: list[dict[str, str]] = []
    all_items: list[object] = []
    for index, operation_id in enumerate(request.inventory_operation_ids):
        operation = db.scalar(
            select(WindowsHelperOperation).where(WindowsHelperOperation.operation_uuid == str(operation_id))
        )
        if (
            operation is None
            or operation.operation_type != "inventory_page"
            or operation.state != "completed"
            or not operation.result_json
            or not operation.result_digest
        ):
            raise WindowsHelperServiceError("inventory_chain_incomplete", "The inventory chain is incomplete.", http_status=409)
        if (
            operation.access_node_id != node.id
            or operation.source_endpoint_id != endpoint.id
            or operation.source_profile_id != source.id
        ):
            raise WindowsHelperServiceError("inventory_chain_binding_mismatch", "Inventory binding does not match the Source.", http_status=409)
        page_request = HelperInventoryPageRequest.model_validate_json(operation.request_json)
        result = HelperInventoryPageResponse.model_validate_json(operation.result_json)
        identity_hashes = {
            evidence.fingerprint_hash
            for evidence in result.identity_probe.evidence_items
            if evidence.fingerprint_hash and evidence.fingerprint_version
        }
        if (
            page_request.request_id != operation_id
            or page_request.intended_access_node_id != UUID(node.access_node_uuid)
            or page_request.source_endpoint_id != endpoint.id
            or page_request.source_profile_id != source.id
            or page_request.source_type.value != endpoint.source_type
            or page_request.provider_native_path.provider_native_relative_path
            or ntpath.normcase(page_request.provider_native_path.provider_native_root)
            != ntpath.normcase(source.source_root_path)
            or ntpath.normcase(page_request.provider_native_path.provider_native_full_path)
            != ntpath.normcase(source.source_root_path)
            or result.request_id != operation_id
            or result.source_endpoint_id != endpoint.id
            or result.source_profile_id != source.id
            or result.source_type != page_request.source_type
            or result.provider_native_path != page_request.provider_native_path
            or identity_hashes != {endpoint.identity_fingerprint_hash}
            or any(
                ntpath.normcase(item.provider_native_path.provider_native_root)
                != ntpath.normcase(source.source_root_path)
                for item in result.items
            )
        ):
            raise WindowsHelperServiceError(
                "inventory_chain_binding_mismatch",
                "Inventory evidence does not match the exact Source authority.",
                http_status=409,
            )
        if canonical_protocol_digest(page_request) != operation.request_digest or canonical_protocol_digest(result) != operation.result_digest:
            raise WindowsHelperServiceError("inventory_chain_integrity_error", "Inventory evidence failed digest validation.", http_status=409)
        if result.result_status.value != "success":
            raise WindowsHelperServiceError("inventory_chain_failed", "Inventory did not complete successfully.", http_status=409)
        if index == 0:
            if page_request.inventory_generation is not None or page_request.cursor is not None:
                raise WindowsHelperServiceError("inventory_chain_missing_start", "Inventory chain does not begin at page one.", http_status=409)
            generation = result.inventory_generation
        else:
            if expected_cursor is None or page_request.inventory_generation != generation or page_request.cursor != expected_cursor:
                raise WindowsHelperServiceError("inventory_chain_disconnected", "Inventory continuation is not exact.", http_status=409)
        if (
            result.inventory_generation != generation
            or page_request.expected_identity_fingerprint != endpoint.identity_fingerprint_hash
            or ntpath.normcase(result.provider_native_path.provider_native_root)
            != ntpath.normcase(source.source_root_path)
        ):
            raise WindowsHelperServiceError("inventory_chain_binding_mismatch", "Inventory identity or root changed.", http_status=409)
        expected_cursor = result.next_cursor
        pages.append((operation, page_request, result))
        all_items.extend(result.items)
        chain_parts.append({"operation_id": operation.operation_uuid, "result_digest": operation.result_digest})
    if not pages or expected_cursor is not None or generation is None:
        raise WindowsHelperServiceError("inventory_chain_not_terminal", "Inventory chain lacks a terminal page.", http_status=409)
    normalized_paths = [ntpath.normcase(item.provider_native_path.provider_native_relative_path) for item in all_items]
    references = [item.candidate_reference for item in all_items]
    if len(normalized_paths) != len(set(normalized_paths)) or len(references) != len(set(references)):
        raise WindowsHelperServiceError("inventory_chain_ambiguous", "Inventory chain contains duplicate candidates.", http_status=409)
    if normalized_paths != sorted(normalized_paths):
        raise WindowsHelperServiceError("inventory_chain_not_ordered", "Inventory chain is not globally ordered.", http_status=409)
    chain_digest = _digest(
        {
            "domain": "photo-organizer-source-acquisition-inventory-chain-v1",
            "access_node_id": node.access_node_uuid,
            "source_endpoint_id": endpoint.id,
            "source_profile_id": source.id,
            "provider_native_root": ntpath.normcase(source.source_root_path),
            "source_fingerprint": endpoint.identity_fingerprint_hash,
            "inventory_generation": str(generation),
            "pages": chain_parts,
        }
    )
    return generation, chain_digest, all_items, endpoint.identity_fingerprint_hash


def create_planned_run(db: Session, request: CreateSourceAcquisitionPlanRequest) -> SourceAcquisitionRunResponse:
    source, endpoint, node = _load_profile(db, request.source_profile_id)
    generation, chain_digest, inventory_items, fingerprint = _validated_inventory_chain(db, request, source, endpoint, node)
    if len(request.candidate_references) != len(set(request.candidate_references)):
        raise WindowsHelperServiceError("candidate_selection_ambiguous", "Selected candidates must be unique.", http_status=409)
    by_reference = {item.candidate_reference: item for item in inventory_items}
    try:
        selected = [by_reference[reference] for reference in request.candidate_references]
    except KeyError as exc:
        raise WindowsHelperServiceError("candidate_not_in_inventory", "A selected candidate is not in the reviewed inventory.", http_status=409) from exc
    selected.sort(key=lambda item: ntpath.normcase(item.provider_native_path.provider_native_relative_path))
    for item in selected:
        extension = PureWindowsPath(item.filename).suffix.casefold()
        if (
            item.entry_kind.value != "regular_file"
            or extension not in settings.approved_extensions
            or item.size_bytes is None
            or item.size_bytes < settings.minimum_file_size_bytes
            or item.modified_time_ns is None
        ):
            raise WindowsHelperServiceError("candidate_not_eligible", "A selected candidate is not acquisition eligible.", http_status=409)
        if item.local_residency != "resident":
            raise WindowsHelperServiceError("candidate_not_local", "A selected candidate is not confirmed locally resident.", http_status=409)
    existing = db.scalar(select(SourceAcquisitionRun).where(SourceAcquisitionRun.idempotency_key == str(request.idempotency_key)))
    if existing is not None:
        existing_refs = [item.candidate_reference for item in existing.items]
        if existing.source_profile_id != source.id or existing.inventory_chain_digest != chain_digest or existing_refs != [item.candidate_reference for item in selected]:
            raise WindowsHelperServiceError("idempotency_conflict", "The acquisition idempotency key is already bound differently.", http_status=409)
        return acquisition_response(db, existing)
    base = _receiving_base()
    expected_bytes = sum(int(item.size_bytes or 0) for item in selected)
    free_bytes = shutil.disk_usage(base).free
    reserve = settings.acquisition_disk_reserve_bytes
    if free_bytes < expected_bytes + reserve:
        raise WindowsHelperServiceError("receiving_capacity_insufficient", "Receiving storage lacks the required safety reserve.", http_status=409)
    run_uuid = uuid4()
    receiving_root = str(base / str(run_uuid))
    item_uuids = [uuid4() for _ in selected]
    proposal_digest = _digest(
        {
            "domain": "photo-organizer-source-acquisition-proposal-v1",
            "run_id": str(run_uuid),
            "item_ids": [str(value) for value in item_uuids],
            "inventory_chain_digest": chain_digest,
            "receiving_root": receiving_root,
            "total_expected_bytes": expected_bytes,
            "candidate_evidence": [
                {
                    "reference": item.candidate_reference,
                    "relative_path": ntpath.normcase(item.provider_native_path.provider_native_relative_path),
                    "size": item.size_bytes,
                    "mtime_ns": item.modified_time_ns,
                    "file_id": item.stable_file_id_digest,
                    "local_residency": item.local_residency,
                    "windows_file_attributes": item.windows_file_attributes,
                }
                for item in selected
            ],
        }
    )
    run = SourceAcquisitionRun(
        run_uuid=str(run_uuid), idempotency_key=str(request.idempotency_key), provider=PROVIDER,
        access_node_id=node.id, source_endpoint_id=endpoint.id, source_profile_id=source.id,
        inventory_generation=str(generation), inventory_chain_digest=chain_digest,
        proposal_digest=proposal_digest, source_fingerprint=fingerprint,
        provider_native_root=source.source_root_path,
        receiving_root=receiving_root, state="planned",
        selected_item_count=len(selected), expected_byte_count=expected_bytes,
        disk_free_bytes_at_plan=free_bytes, disk_reserve_bytes=reserve,
    )
    db.add(run)
    db.flush()
    for ordinal, (item, item_uuid) in enumerate(zip(selected, item_uuids, strict=True), start=1):
        extension = PureWindowsPath(item.filename).suffix.casefold()
        normalized_relative_path = ntpath.normcase(
            item.provider_native_path.provider_native_relative_path
        )
        db.add(SourceAcquisitionItem(
            item_uuid=str(item_uuid), run_id=run.id, ordinal=ordinal,
            candidate_reference=item.candidate_reference, inventory_generation=str(generation),
            provider_native_root=item.provider_native_path.provider_native_root,
            provider_native_relative_path=item.provider_native_path.provider_native_relative_path,
            provider_native_relative_path_normalized=normalized_relative_path,
            provider_native_relative_path_normalized_digest=_digest(normalized_relative_path),
            provider_native_full_path=item.provider_native_path.provider_native_full_path,
            filename=item.filename, safe_extension=extension,
            expected_size_bytes=item.size_bytes, expected_modified_time_ns=item.modified_time_ns,
            expected_file_id_digest=item.stable_file_id_digest, source_fingerprint=fingerprint,
            windows_file_attributes=item.windows_file_attributes, local_residency=item.local_residency,
            eligibility_reason="current_linux_media_policy", state="pending",
            partial_relative_path=f"partial/{item_uuid}.part",
            ready_relative_path=f"ready/{item_uuid}{extension}",
        ))
    db.commit()
    db.refresh(run)
    return acquisition_response(db, run)


def activate_run(db: Session, run_id: UUID, proposal_digest: str) -> SourceAcquisitionRunResponse:
    run = db.scalar(select(SourceAcquisitionRun).where(SourceAcquisitionRun.run_uuid == str(run_id)).with_for_update())
    if run is None:
        raise WindowsHelperServiceError("acquisition_run_not_found", "The acquisition run was not found.", http_status=404)
    if run.proposal_digest != proposal_digest:
        raise WindowsHelperServiceError("proposal_digest_mismatch", "Approval does not match the planned proposal.", http_status=409)
    if run.state == "active":
        return acquisition_response(db, run)
    if run.state != "planned":
        raise WindowsHelperServiceError("acquisition_run_not_planned", "Only a planned run may be activated.", http_status=409)
    source, endpoint, node = _load_profile(db, run.source_profile_id)
    items = list(
        db.scalars(
            select(SourceAcquisitionItem)
            .where(SourceAcquisitionItem.run_id == run.id)
            .order_by(SourceAcquisitionItem.ordinal)
        )
    )
    current_proposal_digest = _digest(
        {
            "domain": "photo-organizer-source-acquisition-proposal-v1",
            "run_id": run.run_uuid,
            "item_ids": [item.item_uuid for item in items],
            "inventory_chain_digest": run.inventory_chain_digest,
            "receiving_root": run.receiving_root,
            "total_expected_bytes": run.expected_byte_count,
            "candidate_evidence": [
                {
                    "reference": item.candidate_reference,
                    "relative_path": item.provider_native_relative_path_normalized,
                    "size": item.expected_size_bytes,
                    "mtime_ns": item.expected_modified_time_ns,
                    "file_id": item.expected_file_id_digest,
                    "local_residency": item.local_residency,
                    "windows_file_attributes": item.windows_file_attributes,
                }
                for item in items
            ],
        }
    )
    if (
        source.id != run.source_profile_id
        or endpoint.id != run.source_endpoint_id
        or node.id != run.access_node_id
        or endpoint.identity_fingerprint_hash != run.source_fingerprint
        or ntpath.normcase(source.source_root_path or "") != ntpath.normcase(run.provider_native_root)
        or len(items) != run.selected_item_count
        or sum(item.expected_size_bytes for item in items) != run.expected_byte_count
        or current_proposal_digest != run.proposal_digest
        or any(item.state != "pending" or item.committed_offset != 0 for item in items)
    ):
        raise WindowsHelperServiceError(
            "acquisition_proposal_stale",
            "The planned acquisition no longer matches its immutable Source proposal.",
            http_status=409,
        )
    base = _receiving_base()
    free_bytes = shutil.disk_usage(base).free
    remaining = run.expected_byte_count - run.committed_byte_count
    if free_bytes < remaining + run.disk_reserve_bytes:
        raise WindowsHelperServiceError("receiving_capacity_insufficient", "Receiving storage lacks the required safety reserve.", http_status=409)
    run_root = Path(run.receiving_root)
    expected_run_root = base / run.run_uuid
    if run_root != expected_run_root:
        raise WindowsHelperServiceError(
            "receiving_path_escape",
            "The acquisition receiving path escaped its configured root.",
            http_status=409,
        )
    if run_root.exists():
        raise WindowsHelperServiceError("receiving_path_conflict", "The run receiving path already exists unexpectedly.", http_status=409)
    created_directories: list[Path] = []
    try:
        for directory in (run_root, run_root / "partial", run_root / "ready"):
            directory.mkdir(mode=0o700)
            created_directories.append(directory)
            os.chmod(directory, 0o700)
    except OSError:
        for directory in reversed(created_directories):
            try:
                directory.rmdir()
            except OSError:
                pass
        raise
    run.state = "active"
    run.activated_at = _now()
    db.add(run)
    db.commit()
    return acquisition_response(db, run)


def get_run(db: Session, run_id: UUID) -> SourceAcquisitionRunResponse:
    run = db.scalar(select(SourceAcquisitionRun).where(SourceAcquisitionRun.run_uuid == str(run_id)))
    if run is None:
        raise WindowsHelperServiceError("acquisition_run_not_found", "The acquisition run was not found.", http_status=404)
    return acquisition_response(db, run)


def acquisition_response(db: Session, run: SourceAcquisitionRun) -> SourceAcquisitionRunResponse:
    node = db.get(AccessNode, run.access_node_id)
    if node is None:
        raise WindowsHelperServiceError("acquisition_access_node_missing", "The acquisition Access Node is unavailable.", http_status=409)
    items = list(db.scalars(select(SourceAcquisitionItem).where(SourceAcquisitionItem.run_id == run.id).order_by(SourceAcquisitionItem.ordinal)))
    return SourceAcquisitionRunResponse(
        acquisition_run_id=UUID(run.run_uuid), provider=run.provider,
        access_node_id=UUID(node.access_node_uuid), source_endpoint_id=run.source_endpoint_id,
        source_profile_id=run.source_profile_id, inventory_generation=UUID(run.inventory_generation),
        inventory_chain_digest=run.inventory_chain_digest, proposal_digest=run.proposal_digest,
        provider_native_root=run.provider_native_root, receiving_root=run.receiving_root,
        state=run.state, selected_item_count=run.selected_item_count,
        expected_byte_count=run.expected_byte_count, committed_byte_count=run.committed_byte_count,
        ready_item_count=run.ready_item_count, failed_item_count=run.failed_item_count,
        disk_free_bytes_at_plan=run.disk_free_bytes_at_plan, disk_reserve_bytes=run.disk_reserve_bytes,
        disk_reserve_passed=run.disk_free_bytes_at_plan >= run.expected_byte_count + run.disk_reserve_bytes,
        items=[SourceAcquisitionItemSummary(
            acquisition_item_id=UUID(item.item_uuid), ordinal=item.ordinal,
            candidate_reference=item.candidate_reference, filename=item.filename,
            provider_native_relative_path=item.provider_native_relative_path,
            expected_size_bytes=item.expected_size_bytes, state=item.state,
            committed_offset=item.committed_offset, verified_byte_count=item.verified_byte_count,
            local_residency=item.local_residency, helper_source_sha256=item.helper_source_sha256,
            linux_verified_sha256=item.linux_verified_sha256, failure_code=item.failure_code,
        ) for item in items],
        created_at=run.created_at, activated_at=run.activated_at,
        completed_at=run.completed_at, failure_code=run.failure_code,
    )
