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

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.asset import Asset
from app.models.ingestion_run import IngestionRun
from app.models.ingestion_source import IngestionSource
from app.models.source_acquisition import SourceAcquisitionItem, SourceAcquisitionRun
from app.models.source_endpoint import AccessNode, SourceEndpoint, SourceEndpointObservedPath
from app.models.source_intake_run import SourceIntakeRun
from app.models.provenance import Provenance
from app.models.windows_helper import WindowsHelperOperation
from app.schemas.source_acquisition import (
    CreateSourceAcquisitionPlanRequest,
    SourceAcquisitionBridgeCounts,
    SourceAcquisitionBridgeHashClassification,
    SourceAcquisitionBridgeItemResult,
    SourceAcquisitionBridgePlanResponse,
    SourceAcquisitionItemSummary,
    SourceAcquisitionRunResponse,
)
from app.services.admin.source_intake_execution_service import (
    STATUS_COMPLETED,
    SourceIntakeAlreadyRunningError,
    start_explicit_source_intake,
)
from app.services.ingestion.hasher import HashedFile
from app.services.ingestion.pipeline_orchestrator import resolve_runtime_path
from app.services.ingestion.scanner import FileScanRecord
from app.services.ingestion.storage_manager import (
    ExistingAssetVaultState,
    _build_hash_based_vault_path,
    _verify_existing_asset_vault_file,
)
from app.services.source_acquisition.receiving import verified_ready_path
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


def _load_bridge_run(
    db: Session, run_id: UUID, *, lock: bool = False
) -> tuple[SourceAcquisitionRun, list[SourceAcquisitionItem]]:
    statement = select(SourceAcquisitionRun).where(SourceAcquisitionRun.run_uuid == str(run_id))
    if lock:
        statement = statement.with_for_update()
    run = db.scalar(statement)
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
    return run, items


def _bridge_records(
    run: SourceAcquisitionRun, items: list[SourceAcquisitionItem]
) -> tuple[Path, list[FileScanRecord]]:
    if run.state != "completed":
        raise WindowsHelperServiceError(
            "acquisition_not_completed",
            "Only a completed acquisition run can enter Source Intake.",
            http_status=409,
        )
    if (
        len(items) != run.selected_item_count
        or run.ready_item_count != run.selected_item_count
        or run.failed_item_count != 0
        or sum(item.expected_size_bytes for item in items) != run.expected_byte_count
        or sum(item.verified_byte_count for item in items) != run.expected_byte_count
    ):
        raise WindowsHelperServiceError(
            "acquisition_ready_set_inconsistent",
            "The completed acquisition ready set is inconsistent.",
            http_status=409,
        )

    ready_root = (Path(run.receiving_root) / "ready").resolve(strict=True)
    records: list[FileScanRecord] = []
    seen_paths: set[Path] = set()
    for item in items:
        if (
            not item.provider_native_root
            or not item.provider_native_relative_path
            or not item.provider_native_full_path
            or item.provider_native_root != run.provider_native_root
            or not item.linux_verified_sha256
            or item.linux_verified_sha256 != item.helper_source_sha256
        ):
            raise WindowsHelperServiceError(
                "acquisition_lineage_inconsistent",
                "An acquisition item lacks exact verified lineage.",
                http_status=409,
            )
        ready_path = verified_ready_path(run, item)
        try:
            runtime_relative_path = ready_path.relative_to(ready_root)
        except ValueError as exc:
            raise WindowsHelperServiceError(
                "receiving_path_escape",
                "A ready object escaped the exact ready root.",
                http_status=409,
            ) from exc
        if (
            ready_path in seen_paths
            or runtime_relative_path != Path(item.ready_relative_path).relative_to("ready")
        ):
            raise WindowsHelperServiceError(
                "acquisition_ready_set_ambiguous",
                "Ready-object paths must be exact and unique.",
                http_status=409,
            )
        seen_paths.add(ready_path)
        records.append(
            FileScanRecord(
                full_path=str(ready_path),
                file_name=ready_path.name,
                extension=item.safe_extension,
                size_bytes=item.expected_size_bytes,
                modified_timestamp_utc=datetime.fromtimestamp(
                    item.expected_modified_time_ns / 1_000_000_000,
                    tz=timezone.utc,
                ).isoformat(),
                original_source_path=str(ready_path),
                original_filename=item.filename,
                asset_original_source_path=item.provider_native_full_path,
                explicit_order=item.ordinal,
            )
        )
    return ready_root, records


def _sha256_hex(value: str) -> str:
    if not value.startswith("sha256:") or len(value) != 71:
        raise WindowsHelperServiceError(
            "acquisition_hash_invalid", "Verified acquisition hash evidence is invalid.", http_status=409
        )
    return value.removeprefix("sha256:")


def _provider_native_root_key(provider: str, value: str) -> str:
    """Normalize a provider-native root without translating provider namespaces."""
    if provider == PROVIDER:
        return ntpath.normcase(ntpath.normpath(value))
    return value


def _same_provider_lineage(
    current_run: SourceAcquisitionRun,
    current_item: SourceAcquisitionItem,
    prior_run: SourceAcquisitionRun,
    prior_item: SourceAcquisitionItem,
) -> bool:
    return (
        prior_run.provider == current_run.provider
        and prior_run.source_profile_id == current_run.source_profile_id
        and _provider_native_root_key(prior_run.provider, prior_run.provider_native_root)
        == _provider_native_root_key(current_run.provider, current_run.provider_native_root)
        and _provider_native_root_key(prior_run.provider, prior_item.provider_native_root)
        == _provider_native_root_key(current_run.provider, current_item.provider_native_root)
        and prior_item.provider_native_relative_path_normalized
        == current_item.provider_native_relative_path_normalized
        and prior_item.provider_native_relative_path_normalized_digest
        == current_item.provider_native_relative_path_normalized_digest
        and prior_item.linux_verified_sha256 == current_item.linux_verified_sha256
    )


def _provenance_has_valid_acquisition_anchor(
    db: Session,
    current_run: SourceAcquisitionRun,
    current_item: SourceAcquisitionItem,
    provenance: Provenance,
) -> bool:
    anchors = db.execute(
        select(SourceAcquisitionItem, SourceAcquisitionRun)
        .join(SourceAcquisitionRun, SourceAcquisitionRun.id == SourceAcquisitionItem.run_id)
        .where(
            SourceAcquisitionItem.bridged_provenance_id == provenance.id,
            SourceAcquisitionRun.bridge_state == "completed",
            SourceAcquisitionRun.state == "completed",
        )
    ).all()
    for anchor_item, anchor_run in anchors:
        if not _same_provider_lineage(current_run, current_item, anchor_run, anchor_item):
            continue
        if anchor_run.bridge_ingestion_run_id != provenance.ingestion_run_id:
            continue
        ingestion = db.get(IngestionRun, provenance.ingestion_run_id)
        ready_root = (Path(anchor_run.receiving_root) / "ready").resolve()
        expected_path = str((ready_root / Path(anchor_item.ready_relative_path).name).resolve())
        if (
            ingestion is not None
            and ingestion.ingestion_source_id == current_run.source_profile_id
            and Path(ingestion.from_path or "").resolve() == ready_root
            and provenance.ingestion_source_id == current_run.source_profile_id
            and provenance.source_path == expected_path
            and Path(provenance.source_root_path or "").resolve() == ready_root
            and provenance.source_relative_path == Path(anchor_item.ready_relative_path).name
        ):
            return True
    return False


def _find_prior_observation_reuse(
    db: Session,
    run: SourceAcquisitionRun,
    item: SourceAcquisitionItem,
    record: FileScanRecord,
) -> tuple[SourceAcquisitionItem, Asset, Provenance] | None:
    candidates = db.execute(
        select(SourceAcquisitionItem, SourceAcquisitionRun)
        .join(SourceAcquisitionRun, SourceAcquisitionRun.id == SourceAcquisitionItem.run_id)
        .where(
            SourceAcquisitionRun.id < run.id,
            SourceAcquisitionRun.provider == run.provider,
            SourceAcquisitionRun.source_profile_id == run.source_profile_id,
            SourceAcquisitionRun.state == "completed",
            SourceAcquisitionRun.bridge_state == "completed",
            SourceAcquisitionItem.state == "ready",
            SourceAcquisitionItem.provider_native_relative_path_normalized_digest
            == item.provider_native_relative_path_normalized_digest,
            SourceAcquisitionItem.linux_verified_sha256 == item.linux_verified_sha256,
            SourceAcquisitionItem.bridged_asset_sha256.is_not(None),
            SourceAcquisitionItem.bridged_provenance_id.is_not(None),
        )
        .order_by(SourceAcquisitionRun.id, SourceAcquisitionItem.ordinal)
    ).all()
    valid: dict[tuple[str, int], tuple[SourceAcquisitionItem, Asset, Provenance]] = {}
    for prior_item, prior_run in candidates:
        if not _same_provider_lineage(run, item, prior_run, prior_item):
            continue
        asset = db.get(Asset, prior_item.bridged_asset_sha256)
        provenance = db.get(Provenance, prior_item.bridged_provenance_id)
        if (
            asset is None
            or provenance is None
            or provenance.asset_sha256 != asset.sha256
            or asset.sha256 != _sha256_hex(item.linux_verified_sha256 or "")
            or not _provenance_has_valid_acquisition_anchor(db, run, item, provenance)
        ):
            continue
        _, conflict = _verify_existing_asset_vault_file(
            HashedFile(record=record, sha256=asset.sha256),
            ExistingAssetVaultState(
                sha256=asset.sha256,
                vault_path=asset.vault_path,
                size_bytes=asset.size_bytes,
            ),
        )
        if conflict is None:
            valid[(asset.sha256, provenance.id)] = (prior_item, asset, provenance)
    if len(valid) > 1:
        raise WindowsHelperServiceError(
            "bridge_prior_observation_ambiguous",
            "Prior Source-observation linkage is ambiguous.",
            http_status=409,
        )
    return next(iter(valid.values()), None)


def _bridge_observation_reuse(
    db: Session,
    run: SourceAcquisitionRun,
    items: list[SourceAcquisitionItem],
    records: list[FileScanRecord],
) -> list[tuple[SourceAcquisitionItem, Asset, Provenance] | None]:
    return [
        _find_prior_observation_reuse(db, run, item, record)
        for item, record in zip(items, records, strict=True)
    ]


def _bridge_counts(db: Session) -> SourceAcquisitionBridgeCounts:
    vault_root = resolve_runtime_path(settings.vault_path)
    vault_files = sum(1 for path in vault_root.rglob("*") if path.is_file())
    return SourceAcquisitionBridgeCounts(
        source_intake_runs=int(db.scalar(select(func.count(SourceIntakeRun.id))) or 0),
        ingestion_runs=int(db.scalar(select(func.count(IngestionRun.id))) or 0),
        assets=int(db.scalar(select(func.count(Asset.sha256))) or 0),
        provenance=int(db.scalar(select(func.count(Provenance.id))) or 0),
        canonical_vault_files=vault_files,
    )


def _validate_completed_bridge(
    db: Session, run: SourceAcquisitionRun, items: list[SourceAcquisitionItem], ready_root: Path
) -> None:
    if (run.bridge_source_intake_run_id is None) != (run.bridge_ingestion_run_id is None):
        raise WindowsHelperServiceError(
            "bridge_linkage_incomplete", "Completed bridge run linkage is incomplete.", http_status=409
        )
    intake = (
        db.get(SourceIntakeRun, run.bridge_source_intake_run_id)
        if run.bridge_source_intake_run_id is not None
        else None
    )
    ingestion = (
        db.get(IngestionRun, run.bridge_ingestion_run_id)
        if run.bridge_ingestion_run_id is not None
        else None
    )
    if intake is not None or ingestion is not None:
        if (
            intake is None
            or ingestion is None
            or intake.status != STATUS_COMPLETED
            or intake.ingestion_source_id != run.source_profile_id
            or intake.ingestion_run_id != ingestion.id
            or ingestion.ingestion_source_id != run.source_profile_id
            or Path(ingestion.from_path or "").resolve() != ready_root
        ):
            raise WindowsHelperServiceError(
                "bridge_linkage_inconsistent", "Completed bridge run linkage is inconsistent.", http_status=409
            )

    _, records = _bridge_records(run, items)
    reused = _bridge_observation_reuse(db, run, items, records)
    common_intake_links = 0
    for item, reuse in zip(items, reused, strict=True):
        if not item.bridged_asset_sha256 or item.bridged_provenance_id is None:
            raise WindowsHelperServiceError(
                "bridge_item_linkage_incomplete",
                "Completed acquisition item linkage is incomplete.",
                http_status=409,
            )
        asset = db.get(Asset, item.bridged_asset_sha256)
        provenance = db.get(Provenance, item.bridged_provenance_id)
        if reuse is not None:
            _, reused_asset, reused_provenance = reuse
            if (
                item.bridged_asset_sha256 == reused_asset.sha256
                and item.bridged_provenance_id == reused_provenance.id
            ):
                continue
        expected_path = str((ready_root / Path(item.ready_relative_path).name).resolve())
        if (
            ingestion is None
            or asset is None
            or provenance is None
            or provenance.asset_sha256 != asset.sha256
            or provenance.ingestion_source_id != run.source_profile_id
            or provenance.ingestion_run_id != ingestion.id
            or provenance.source_path != expected_path
            or Path(provenance.source_root_path or "").resolve() != ready_root
            or provenance.source_relative_path != Path(item.ready_relative_path).name
        ):
            raise WindowsHelperServiceError(
                "bridge_item_linkage_inconsistent",
                "Completed acquisition item linkage is inconsistent.",
                http_status=409,
            )
        common_intake_links += 1
    if (ingestion is None and common_intake_links != 0) or (
        ingestion is not None and common_intake_links == 0
    ):
        raise WindowsHelperServiceError(
            "bridge_linkage_inconsistent", "Completed bridge run mode is inconsistent.", http_status=409
        )


def plan_acquisition_bridge(db: Session, run_id: UUID) -> SourceAcquisitionBridgePlanResponse:
    run, items = _load_bridge_run(db, run_id)
    ready_root, records = _bridge_records(run, items)
    bridge_state = run.bridge_state or "not_started"
    if bridge_state not in {"not_started", "running", "completed", "failed"}:
        raise WindowsHelperServiceError(
            "bridge_state_invalid", "The bridge state is invalid.", http_status=409
        )
    if bridge_state == "completed":
        _validate_completed_bridge(db, run, items, ready_root)

    classifications: list[SourceAcquisitionBridgeHashClassification] = []
    by_hash: dict[str, FileScanRecord] = {}
    for item, record in zip(items, records, strict=True):
        by_hash.setdefault(item.linux_verified_sha256 or "", record)
    for digest, record in by_hash.items():
        sha256 = _sha256_hex(digest)
        asset = db.get(Asset, sha256)
        if asset is None:
            destination = _build_hash_based_vault_path(
                resolve_runtime_path(settings.vault_path), sha256, record.extension
            )
            if destination.exists() and bridge_state == "not_started":
                raise WindowsHelperServiceError(
                    "untracked_vault_path_conflict",
                    "A predicted new canonical Vault path is already occupied.",
                    http_status=409,
                )
            classifications.append(
                SourceAcquisitionBridgeHashClassification(
                    sha256=digest, classification="new_content", canonical_vault_verified=False
                )
            )
            continue
        hashed = HashedFile(record=record, sha256=sha256)
        _, conflict = _verify_existing_asset_vault_file(
            hashed,
            ExistingAssetVaultState(
                sha256=asset.sha256, vault_path=asset.vault_path, size_bytes=asset.size_bytes
            ),
        )
        if conflict is not None:
            raise WindowsHelperServiceError(
                "existing_asset_vault_conflict",
                "An exact-known canonical Vault object failed verification.",
                http_status=409,
            )
        classifications.append(
            SourceAcquisitionBridgeHashClassification(
                sha256=digest, classification="exact_known", canonical_vault_verified=True
            )
        )

    reuses = _bridge_observation_reuse(db, run, items, records)
    if bridge_state == "not_started":
        for item, record in zip(items, records, strict=True):
            sha256 = _sha256_hex(item.linux_verified_sha256 or "")
            prior = db.scalar(
                select(Provenance.id).where(
                    Provenance.asset_sha256 == sha256,
                    Provenance.ingestion_source_id == run.source_profile_id,
                    Provenance.source_path == record.original_source_path,
                )
            )
            if prior is not None:
                raise WindowsHelperServiceError(
                    "bridge_prior_provenance_conflict",
                    "Equivalent runtime provenance exists without durable acquisition linkage.",
                    http_status=409,
                )

    classification_by_hash = {item.sha256: item.classification for item in classifications}
    unmatched_hashes = {
        item.linux_verified_sha256 or ""
        for item, reuse in zip(items, reuses, strict=True)
        if reuse is None
    }
    new_count = sum(
        classification_by_hash[digest] == "new_content" for digest in unmatched_hashes
    )
    expected_asset_delta = new_count if bridge_state == "not_started" else 0
    expected_provenance_delta = (
        sum(reuse is None for reuse in reuses) if bridge_state == "not_started" else 0
    )
    plan_digest = _digest(
        {
            "domain": "photo-organizer-source-acquisition-bridge-plan-v2",
            "acquisition_run_id": run.run_uuid,
            "source_endpoint_id": run.source_endpoint_id,
            "source_profile_id": run.source_profile_id,
            "ready_root": str(ready_root),
            "items": [
                {
                    "item_id": item.item_uuid,
                    "ordinal": item.ordinal,
                    "runtime_path": record.original_source_path,
                    "provider_native_full_path": item.provider_native_full_path,
                    "size": item.expected_size_bytes,
                    "sha256": item.linux_verified_sha256,
                    "observation_classification": (
                        "reuse_prior_observation" if reuse is not None else "common_intake"
                    ),
                    "reused_from_acquisition_item_id": (
                        reuse[0].item_uuid if reuse is not None else None
                    ),
                    "reused_asset_sha256": reuse[1].sha256 if reuse is not None else None,
                    "reused_provenance_id": reuse[2].id if reuse is not None else None,
                }
                for item, record, reuse in zip(items, records, reuses, strict=True)
            ],
            "classifications": [item.model_dump() for item in classifications],
        }
    )
    return SourceAcquisitionBridgePlanResponse(
        acquisition_run_id=run_id,
        bridge_state=bridge_state,
        source_profile_id=run.source_profile_id,
        source_endpoint_id=run.source_endpoint_id,
        ready_root=str(ready_root),
        item_count=len(items),
        verified_byte_count=sum(item.verified_byte_count for item in items),
        unique_content_count=len(classifications),
        bridge_plan_digest=plan_digest,
        current_counts=_bridge_counts(db),
        classifications=classifications,
        expected_asset_delta=expected_asset_delta,
        expected_vault_delta=expected_asset_delta,
        expected_provenance_delta=expected_provenance_delta,
        source_intake_run_id=run.bridge_source_intake_run_id,
        ingestion_run_id=run.bridge_ingestion_run_id,
        items=[
            SourceAcquisitionBridgeItemResult(
                acquisition_item_id=UUID(item.item_uuid),
                ordinal=item.ordinal,
                provider_native_relative_path=item.provider_native_relative_path,
                runtime_relative_path=Path(item.ready_relative_path).name,
                linux_verified_sha256=item.linux_verified_sha256 or "",
                observation_classification=(
                    "reuse_prior_observation" if reuse is not None else "common_intake"
                ),
                reused_from_acquisition_item_id=(
                    UUID(reuse[0].item_uuid) if reuse is not None else None
                ),
                asset_sha256=(
                    item.bridged_asset_sha256
                    or (reuse[1].sha256 if reuse is not None else None)
                ),
                provenance_id=(
                    item.bridged_provenance_id
                    or (reuse[2].id if reuse is not None else None)
                ),
            )
            for item, reuse in zip(items, reuses, strict=True)
        ],
    )


def _bind_bridge_intake(run_id: UUID, source_intake_run_id: int) -> None:
    with SessionLocal() as db:
        run, _ = _load_bridge_run(db, run_id, lock=True)
        if run.bridge_state != "running" or run.bridge_source_intake_run_id is not None:
            raise RuntimeError("Acquisition bridge launch binding is inconsistent.")
        run.bridge_source_intake_run_id = source_intake_run_id
        db.commit()


def _finalize_bridge(run_id: UUID, source_intake_run_id: int) -> None:
    with SessionLocal() as db:
        run, items = _load_bridge_run(db, run_id, lock=True)
        if run.bridge_state != "running" or run.bridge_source_intake_run_id != source_intake_run_id:
            return
        intake = db.get(SourceIntakeRun, source_intake_run_id)
        unlinked_items = [
            item
            for item in items
            if item.bridged_asset_sha256 is None and item.bridged_provenance_id is None
        ]
        if any(
            (item.bridged_asset_sha256 is None) != (item.bridged_provenance_id is None)
            for item in items
        ):
            run.bridge_state = "failed"
            run.bridge_failure_code = "reused_item_linkage_incomplete"
            db.commit()
            return
        if (
            intake is None
            or intake.status != STATUS_COMPLETED
            or intake.ingestion_run_id is None
            or intake.failed_or_rejected != 0
            or intake.files_scanned != len(unlinked_items)
            or intake.selected != len(unlinked_items)
        ):
            run.bridge_state = "failed"
            run.bridge_failure_code = "source_intake_incomplete"
            db.commit()
            return
        ready_root = (Path(run.receiving_root) / "ready").resolve(strict=True)
        ingestion = db.get(IngestionRun, intake.ingestion_run_id)
        if (
            ingestion is None
            or intake.ingestion_source_id != run.source_profile_id
            or ingestion.ingestion_source_id != run.source_profile_id
            or Path(ingestion.from_path or "").resolve() != ready_root
        ):
            run.bridge_state = "failed"
            run.bridge_failure_code = "ingestion_context_mismatch"
            db.commit()
            return
        links: list[tuple[SourceAcquisitionItem, str, int]] = []
        for item in unlinked_items:
            sha256 = _sha256_hex(item.linux_verified_sha256 or "")
            ready_path = str((ready_root / Path(item.ready_relative_path).name).resolve())
            rows = list(
                db.scalars(
                    select(Provenance).where(
                        Provenance.asset_sha256 == sha256,
                        Provenance.ingestion_source_id == run.source_profile_id,
                        Provenance.ingestion_run_id == ingestion.id,
                        Provenance.source_path == ready_path,
                    )
                )
            )
            if (
                len(rows) != 1
                or db.get(Asset, sha256) is None
                or Path(rows[0].source_root_path or "").resolve() != ready_root
                or rows[0].source_relative_path != Path(item.ready_relative_path).name
            ):
                run.bridge_state = "failed"
                run.bridge_failure_code = "item_result_linkage_mismatch"
                db.commit()
                return
            links.append((item, sha256, rows[0].id))
        for item, sha256, provenance_id in links:
            item.bridged_asset_sha256 = sha256
            item.bridged_provenance_id = provenance_id
        run.bridge_ingestion_run_id = ingestion.id
        run.bridge_state = "completed"
        run.bridge_failure_code = None
        run.bridge_completed_at = _now()
        db.commit()


def _finalize_bridge_safely(run_id: UUID, source_intake_run_id: int) -> None:
    try:
        _finalize_bridge(run_id, source_intake_run_id)
    except Exception:
        with SessionLocal() as db:
            run, _ = _load_bridge_run(db, run_id, lock=True)
            if run.bridge_state == "running":
                run.bridge_state = "failed"
                run.bridge_failure_code = "bridge_finalization_failed"
                db.commit()


def execute_acquisition_bridge(
    db: Session, run_id: UUID, bridge_plan_digest: str
) -> SourceAcquisitionBridgePlanResponse:
    plan = plan_acquisition_bridge(db, run_id)
    if plan.bridge_state in {"completed", "running"}:
        return plan
    if plan.bridge_plan_digest != bridge_plan_digest:
        raise WindowsHelperServiceError(
            "bridge_plan_digest_mismatch",
            "Bridge execution does not match the verified plan.",
            http_status=409,
        )
    if plan.bridge_state == "failed":
        raise WindowsHelperServiceError(
            "bridge_previously_failed",
            "The acquisition bridge previously failed and requires review.",
            http_status=409,
        )

    run, items = _load_bridge_run(db, run_id, lock=True)
    ready_root, records = _bridge_records(run, items)
    if run.bridge_state != "not_started" or any(
        item.bridged_asset_sha256 is not None or item.bridged_provenance_id is not None
        for item in items
    ):
        raise WindowsHelperServiceError(
            "bridge_state_conflict", "The acquisition bridge state changed.", http_status=409
        )
    reuses = _bridge_observation_reuse(db, run, items, records)
    reused_items: list[SourceAcquisitionItem] = []
    unmatched_records: list[FileScanRecord] = []
    for item, record, reuse in zip(items, records, reuses, strict=True):
        if reuse is None:
            unmatched_records.append(record)
            continue
        _, asset, provenance = reuse
        item.bridged_asset_sha256 = asset.sha256
        item.bridged_provenance_id = provenance.id
        reused_items.append(item)

    now = _now()
    run.bridge_started_at = now
    run.bridge_failure_code = None
    if not unmatched_records:
        run.bridge_state = "completed"
        run.bridge_completed_at = now
        db.commit()
        db.expire_all()
        return plan_acquisition_bridge(db, run_id)

    run.bridge_state = "running"
    db.commit()
    try:
        start_explicit_source_intake(
            db,
            ingestion_source_id=run.source_profile_id,
            runtime_source_root_path=str(ready_root),
            explicit_source_records=unmatched_records,
            ingest_batch_size=len(unmatched_records),
            created_by="source_acquisition_bridge",
            on_created=lambda intake_id: _bind_bridge_intake(run_id, intake_id),
            on_finished=lambda intake_id: _finalize_bridge_safely(run_id, intake_id),
        )
    except SourceIntakeAlreadyRunningError as exc:
        db.refresh(run)
        run.bridge_state = "not_started"
        run.bridge_started_at = None
        for item in reused_items:
            item.bridged_asset_sha256 = None
            item.bridged_provenance_id = None
        db.commit()
        raise WindowsHelperServiceError(
            "source_intake_already_running",
            "Another Source Intake run is active.",
            http_status=409,
        ) from exc
    except Exception:
        db.refresh(run)
        run.bridge_state = "failed"
        run.bridge_failure_code = "bridge_launch_failed"
        for item in reused_items:
            item.bridged_asset_sha256 = None
            item.bridged_provenance_id = None
        db.commit()
        raise
    db.expire_all()
    return plan_acquisition_bridge(db, run_id)


def reset_stale_acquisition_bridges(db: Session) -> None:
    """Fail closed any bridge whose in-process Source Intake runner was lost."""
    stale = list(
        db.scalars(
            select(SourceAcquisitionRun).where(SourceAcquisitionRun.bridge_state == "running")
        )
    )
    for run in stale:
        intake = (
            db.get(SourceIntakeRun, run.bridge_source_intake_run_id)
            if run.bridge_source_intake_run_id is not None
            else None
        )
        if intake is None or intake.status not in {"running", "stop_requested"}:
            run.bridge_state = "failed"
            run.bridge_failure_code = "bridge_runner_interrupted"
    if stale:
        db.commit()
