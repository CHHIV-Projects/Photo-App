"""Crash-safe bounded Linux receiving for authorized acquisition items."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.source_acquisition import SourceAcquisitionItem, SourceAcquisitionRun
from app.models.windows_helper import WindowsHelperCredential, WindowsHelperOperation
from app.services.windows_helper.service import WindowsHelperServiceError
from app.windows_helper_shared.channel import HelperAcquisitionStatusResponse, HelperChunkCommitResponse
from app.windows_helper_shared.protocol import (
    HelperAcquireItemRequest,
    HelperAcquireItemResponse,
    MAX_ACQUISITION_CHUNK_BYTES,
    SourceFileEvidence,
)

_REPARSE_ATTRIBUTE = 0x400

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load_bound(
    db: Session,
    credential: WindowsHelperCredential,
    operation_id: UUID,
    run_id: UUID,
    item_id: UUID,
    *,
    lock_item: bool,
) -> tuple[WindowsHelperOperation, HelperAcquireItemRequest, SourceAcquisitionRun, SourceAcquisitionItem]:
    operation = db.scalar(
        select(WindowsHelperOperation).where(
            WindowsHelperOperation.operation_uuid == str(operation_id),
            WindowsHelperOperation.access_node_id == credential.access_node_id,
        )
    )
    if operation is None or operation.operation_type != "acquire_item":
        raise WindowsHelperServiceError("operation_unavailable", "The acquisition operation is unavailable.", http_status=404)
    request = HelperAcquireItemRequest.model_validate_json(operation.request_json)
    if request.acquisition_run_id != run_id or request.acquisition_item_id != item_id:
        raise WindowsHelperServiceError("acquisition_binding_mismatch", "The acquisition binding is invalid.", http_status=409)
    if operation.state not in {"claimed", "completed"}:
        raise WindowsHelperServiceError("operation_not_claimed", "The acquisition operation is not active.", http_status=409)
    if operation.state == "claimed" and (
        operation.lease_expires_at is None
        or (operation.lease_expires_at if operation.lease_expires_at.tzinfo else operation.lease_expires_at.replace(tzinfo=timezone.utc)) <= _now()
    ):
        raise WindowsHelperServiceError("operation_lease_expired", "The acquisition operation lease expired.", http_status=409)

    statement = select(SourceAcquisitionItem).where(SourceAcquisitionItem.item_uuid == str(item_id))
    if lock_item:
        statement = statement.with_for_update()
    item = db.scalar(statement)
    if item is None:
        raise WindowsHelperServiceError("acquisition_item_not_found", "The acquisition item was not found.", http_status=404)
    run_statement = select(SourceAcquisitionRun).where(SourceAcquisitionRun.id == item.run_id)
    if lock_item:
        run_statement = run_statement.with_for_update()
    run = db.scalar(run_statement)
    if (
        run is None
        or run.run_uuid != str(run_id)
        or run.access_node_id != credential.access_node_id
        or run.source_endpoint_id != request.source_endpoint_id
        or run.source_profile_id != request.source_profile_id
        or item.source_fingerprint != request.expected_identity_fingerprint
    ):
        raise WindowsHelperServiceError("acquisition_binding_mismatch", "The acquisition binding is invalid.", http_status=409)
    return operation, request, run, item


def _run_directories(run: SourceAcquisitionRun) -> tuple[Path, Path, Path]:
    base = Path(settings.acquisition_receiving_path).resolve(strict=True)
    configured_root = Path(run.receiving_root)
    if configured_root.is_symlink():
        raise WindowsHelperServiceError("receiving_path_unsafe", "Receiving run directory is unsafe.", http_status=409)
    try:
        root = configured_root.resolve(strict=True)
    except OSError as exc:
        raise WindowsHelperServiceError(
            "receiving_path_unsafe",
            "Receiving run directory is unavailable.",
            http_status=409,
        ) from exc
    expected_root = base / run.run_uuid
    if root != expected_root:
        raise WindowsHelperServiceError(
            "receiving_path_escape",
            "Receiving path escaped its exact opaque run root.",
            http_status=409,
        )
    if not root.is_dir():
        raise WindowsHelperServiceError("receiving_path_unsafe", "Receiving run directory is unavailable.", http_status=409)

    partial = root / "partial"
    ready = root / "ready"
    for directory in (partial, ready):
        if directory.is_symlink() or not directory.is_dir():
            raise WindowsHelperServiceError("receiving_path_unsafe", "Receiving directory is unsafe.", http_status=409)
    return root, partial, ready


def _paths(run: SourceAcquisitionRun, item: SourceAcquisitionItem) -> tuple[Path, Path]:
    _, partial_dir, ready_dir = _run_directories(run)
    expected_partial = f"{item.item_uuid}.part"
    expected_ready = f"{item.item_uuid}{item.safe_extension}"
    if Path(item.partial_relative_path).name != expected_partial or Path(item.ready_relative_path).name != expected_ready:
        raise WindowsHelperServiceError("receiving_path_unsafe", "Receiving item path is invalid.", http_status=409)
    return partial_dir / expected_partial, ready_dir / expected_ready


def _safe_open(path: Path, flags: int, mode: int = 0o600) -> int:
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    return os.open(path, flags | nofollow, mode)


def _regular_fd(fd: int) -> os.stat_result:
    metadata = os.fstat(fd)
    if not stat.S_ISREG(metadata.st_mode):
        raise WindowsHelperServiceError("receiving_file_unsafe", "Receiving object is not a regular file.", http_status=409)
    return metadata


def _verified_file_digest(path: Path, expected_size: int) -> str:
    try:
        fd = _safe_open(path, os.O_RDONLY)
    except OSError as exc:
        raise WindowsHelperServiceError(
            "ready_object_inconsistent",
            "The durable ready object is missing or unavailable.",
            http_status=409,
        ) from exc
    try:
        metadata = _regular_fd(fd)
        if metadata.st_size != expected_size:
            raise WindowsHelperServiceError(
                "ready_object_inconsistent",
                "The durable ready object size is inconsistent.",
                http_status=409,
            )
        digest = hashlib.sha256()
        while True:
            block = os.read(fd, 1024 * 1024)
            if not block:
                break
            digest.update(block)
        return "sha256:" + digest.hexdigest()
    finally:
        os.close(fd)


def acquisition_status(
    db: Session,
    credential: WindowsHelperCredential,
    operation_id: UUID,
    run_id: UUID,
    item_id: UUID,
) -> HelperAcquisitionStatusResponse:
    _, _, run, item = _load_bound(db, credential, operation_id, run_id, item_id, lock_item=False)
    if item.state == "ready":
        _, ready_path = _paths(run, item)
        ready_digest = _verified_file_digest(ready_path, item.expected_size_bytes)
        if item.linux_verified_sha256 != ready_digest:
            raise WindowsHelperServiceError("ready_object_inconsistent", "The durable ready object digest is inconsistent.", http_status=409)

    if item.state != "ready" and (run.state != "active" or item.state not in {"transferring", "verifying"}):
        raise WindowsHelperServiceError("acquisition_state_invalid", "The acquisition item is not active.", http_status=409)


    return HelperAcquisitionStatusResponse(
        acquisition_run_id=run_id, acquisition_item_id=item_id, state=item.state,
        committed_offset=item.committed_offset, expected_size_bytes=item.expected_size_bytes,
        maximum_chunk_bytes=MAX_ACQUISITION_CHUNK_BYTES,
    )


def commit_chunk(
    db: Session,
    credential: WindowsHelperCredential,
    operation_id: UUID,
    run_id: UUID,
    item_id: UUID,
    *,
    offset: int,
    supplied_digest: str,
    body: bytes,
) -> HelperChunkCommitResponse:
    if not body or len(body) > MAX_ACQUISITION_CHUNK_BYTES:
        raise WindowsHelperServiceError("chunk_size_invalid", "The acquisition chunk size is invalid.", http_status=413)
    actual_digest = "sha256:" + hashlib.sha256(body).hexdigest()
    if supplied_digest != actual_digest:
        raise WindowsHelperServiceError("chunk_digest_mismatch", "The acquisition chunk digest did not match.", http_status=409)
    _, _, run, item = _load_bound(db, credential, operation_id, run_id, item_id, lock_item=True)
    active_transfer = run.state == "active" and item.state in {"transferring", "verifying"}
    verified_replay = item.state == "ready"
    if not (active_transfer or verified_replay):
        raise WindowsHelperServiceError("acquisition_state_invalid", "The acquisition item cannot receive bytes in its current state.", http_status=409)
    if offset < 0 or offset + len(body) > item.expected_size_bytes:
        raise WindowsHelperServiceError("chunk_range_invalid", "The acquisition chunk exceeds the authorized range.", http_status=409)
    partial_path, ready_path = _paths(run, item)
    if item.state == "ready":
        ready_digest = _verified_file_digest(ready_path, item.expected_size_bytes)
        if item.linux_verified_sha256 != ready_digest:
            raise WindowsHelperServiceError("ready_object_inconsistent", "The durable ready object digest is inconsistent.", http_status=409)

    target_path = ready_path if item.state == "ready" else partial_path
    if offset < item.committed_offset:
        if offset + len(body) > item.committed_offset:
            raise WindowsHelperServiceError("chunk_partial_overlap", "Partial-overlap retries are not accepted.", http_status=409)
        fd = _safe_open(target_path, os.O_RDONLY)
        try:
            _regular_fd(fd)
            stored = os.pread(fd, len(body), offset)
        finally:
            os.close(fd)
        if len(stored) != len(body) or "sha256:" + hashlib.sha256(stored).hexdigest() != supplied_digest:
            raise WindowsHelperServiceError("chunk_replay_conflict", "Previously committed bytes conflict with the retry.", http_status=409)
        return HelperChunkCommitResponse(
            acquisition_run_id=run_id, acquisition_item_id=item_id, accepted_offset=offset,
            committed_offset=item.committed_offset, bytes_committed=0, idempotent_replay=True,
        )
    if offset != item.committed_offset:
        raise WindowsHelperServiceError("chunk_offset_mismatch", "The chunk offset does not match Linux committed state.", http_status=409)
    if item.state == "ready":
        raise WindowsHelperServiceError("acquisition_already_ready", "The ready object accepts only exact committed-range replays.", http_status=409)
    remaining = run.expected_byte_count - run.committed_byte_count
    free_bytes = shutil.disk_usage(Path(run.receiving_root)).free
    if free_bytes < remaining + run.disk_reserve_bytes:
        raise WindowsHelperServiceError("receiving_capacity_insufficient", "Receiving storage lacks the safety reserve.", http_status=409)
    if partial_path.exists():
        fd = _safe_open(partial_path, os.O_RDWR)
    else:
        if item.committed_offset != 0:
            raise WindowsHelperServiceError("partial_file_missing", "Committed receiving state has no partial file.", http_status=409)
        fd = _safe_open(partial_path, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        metadata = _regular_fd(fd)
        physical_size = metadata.st_size
        if physical_size == item.committed_offset + len(body):
            stored = os.pread(fd, len(body), item.committed_offset)
            if len(stored) != len(body) or "sha256:" + hashlib.sha256(stored).hexdigest() != supplied_digest:
                raise WindowsHelperServiceError("filesystem_ahead_conflict", "Uncommitted receiving evidence conflicts.", http_status=409)
        elif physical_size == item.committed_offset:
            written = 0
            while written < len(body):
                count = os.pwrite(fd, body[written:], item.committed_offset + written)
                if count <= 0:
                    raise OSError("short receiving write")
                written += count
            os.fsync(fd)
        else:
            raise WindowsHelperServiceError("receiving_state_inconsistent", "Partial size conflicts with durable offset.", http_status=409)
    finally:
        os.close(fd)
    item.committed_offset += len(body)
    item.state = "verifying" if item.committed_offset == item.expected_size_bytes else "transferring"
    run.committed_byte_count += len(body)
    db.add(item)
    db.add(run)
    db.commit()
    return HelperChunkCommitResponse(
        acquisition_run_id=run_id, acquisition_item_id=item_id, accepted_offset=offset,
        committed_offset=item.committed_offset, bytes_committed=len(body), idempotent_replay=False,
    )


def _evidence_matches(item: SourceAcquisitionItem, evidence: SourceFileEvidence) -> bool:
    return (
        evidence.size_bytes == item.expected_size_bytes
        and evidence.modified_time_ns == item.expected_modified_time_ns
        and (
            item.expected_file_id_digest is None
            or evidence.stable_file_id_digest == item.expected_file_id_digest
        )
        and (
            item.windows_file_attributes is None
            or evidence.windows_file_attributes == item.windows_file_attributes
        )
        and evidence.local_residency == item.local_residency == "resident"
        and not ((evidence.windows_file_attributes or 0) & _REPARSE_ATTRIBUTE)
    )


def finalize_item(
    db: Session,
    credential: WindowsHelperCredential,
    operation_id: UUID,
    result: HelperAcquireItemResponse,
) -> tuple[SourceAcquisitionRun, SourceAcquisitionItem, bool]:
    _, request, run, item = _load_bound(
        db, credential, operation_id, result.acquisition_run_id, result.acquisition_item_id, lock_item=True
    )
    if result.result_status.value != "success":
        fail_item(db, item, run, result.error_code or "acquisition_failed")
        return run, item, False
    if (
        result.request_id != operation_id
        or result.source_endpoint_id != run.source_endpoint_id
        or result.source_profile_id != run.source_profile_id
        or result.provider_native_path != request.provider_native_path
        or result.bytes_read != item.expected_size_bytes
        or result.pre_read_evidence is None
        or result.post_read_evidence is None
        or not _evidence_matches(item, result.pre_read_evidence)
        or not _evidence_matches(item, result.post_read_evidence)
        or result.pre_read_evidence != result.post_read_evidence
    ):
        fail_item(db, item, run, "source_evidence_changed")
        raise WindowsHelperServiceError("source_evidence_changed", "Source evidence changed during acquisition.", http_status=409)
    if item.state == "ready":
        _, ready_path = _paths(run, item)
        ready_digest = _verified_file_digest(ready_path, item.expected_size_bytes)
        if item.helper_source_sha256 != result.helper_source_sha256 or item.linux_verified_sha256 != ready_digest:
            raise WindowsHelperServiceError("finalize_conflict", "Ready acquisition evidence conflicts.", http_status=409)
        return run, item, True
    if item.committed_offset != item.expected_size_bytes or item.state != "verifying":
        raise WindowsHelperServiceError("acquisition_incomplete", "The acquisition item is not complete.", http_status=409)
    partial_path, ready_path = _paths(run, item)
    if partial_path.is_symlink() or ready_path.is_symlink():
        raise WindowsHelperServiceError("ready_path_conflict", "Final publication encountered unsafe path evidence.", http_status=409)

    if ready_path.exists():
        if partial_path.exists() and os.stat(partial_path, follow_symlinks=False).st_ino == os.stat(ready_path, follow_symlinks=False).st_ino:
            partial_path.unlink()
        elif partial_path.exists():
            raise WindowsHelperServiceError("ready_path_conflict", "Ready receiving path conflicts with the partial file.", http_status=409)
    if not ready_path.exists():
        fd = _safe_open(partial_path, os.O_RDONLY)
        try:
            metadata = _regular_fd(fd)
            if metadata.st_size != item.expected_size_bytes:
                raise WindowsHelperServiceError("final_size_mismatch", "The received size does not match.", http_status=409)
            digest = hashlib.sha256()
            while True:
                block = os.read(fd, 1024 * 1024)
                if not block:
                    break
                digest.update(block)
            os.fsync(fd)
        finally:
            os.close(fd)
        linux_digest = "sha256:" + digest.hexdigest()
        if linux_digest != result.helper_source_sha256:
            fail_item(db, item, run, "final_digest_mismatch")
            raise WindowsHelperServiceError("final_digest_mismatch", "Independent final verification failed.", http_status=409)
        os.link(partial_path, ready_path, follow_symlinks=False)
        ready_fd = _safe_open(ready_path, os.O_RDONLY)
        try:
            ready_metadata = _regular_fd(ready_fd)
            if ready_metadata.st_size != item.expected_size_bytes:
                raise WindowsHelperServiceError("ready_publication_invalid", "Published ready object is invalid.", http_status=409)
            os.fsync(ready_fd)
        finally:
            os.close(ready_fd)
        directory_fd = os.open(ready_path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        partial_path.unlink()
    fd = _safe_open(ready_path, os.O_RDONLY)
    try:
        metadata = _regular_fd(fd)
        digest = hashlib.sha256()
        while True:
            block = os.read(fd, 1024 * 1024)
            if not block:
                break
            digest.update(block)
    finally:
        os.close(fd)
    linux_digest = "sha256:" + digest.hexdigest()
    if metadata.st_size != item.expected_size_bytes or linux_digest != result.helper_source_sha256:
        raise WindowsHelperServiceError("ready_verification_failed", "Published ready object failed verification.", http_status=409)
    item.state = "ready"
    item.verified_byte_count = item.expected_size_bytes
    item.helper_source_sha256 = result.helper_source_sha256
    item.linux_verified_sha256 = linux_digest
    item.source_pre_evidence_json = json.dumps(result.pre_read_evidence.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    item.source_post_evidence_json = json.dumps(result.post_read_evidence.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    item.completed_at = _now()
    db.add(item)
    db.flush()
    run.ready_item_count = db.scalar(
        select(func.count()).select_from(SourceAcquisitionItem).where(
            SourceAcquisitionItem.run_id == run.id, SourceAcquisitionItem.state == "ready"
        )
    ) or 0
    if run.ready_item_count == run.selected_item_count and run.failed_item_count == 0:
        run.state = "completed"
        run.completed_at = _now()
    db.add(run)
    db.commit()
    return run, item, False


def fail_item(db: Session, item: SourceAcquisitionItem, run: SourceAcquisitionRun, code: str) -> None:
    if item.state == "ready":
        raise WindowsHelperServiceError("ready_item_immutable", "A ready item cannot be failed.", http_status=409)
    if item.state != "failed":
        item.state = "failed"
        item.failure_code = code[:64]
        item.failed_at = _now()
        run.failed_item_count += 1
    run.state = "failed"
    run.failure_code = code[:64]
    run.failed_at = _now()
    db.add(item)
    db.add(run)
    db.commit()


def cleanup_failed_partials(db: Session, run_id: UUID) -> tuple[int, int]:
    run = db.scalar(select(SourceAcquisitionRun).where(SourceAcquisitionRun.run_uuid == str(run_id)).with_for_update())
    if run is None:
        raise WindowsHelperServiceError("acquisition_run_not_found", "The acquisition run was not found.", http_status=404)
    if run.state not in {"failed", "cancelled"}:
        raise WindowsHelperServiceError("cleanup_not_allowed", "Only a terminal unsuccessful run may be cleaned.", http_status=409)
    removed = 0
    now = _now()
    active_operations = list(
        db.scalars(
            select(WindowsHelperOperation).where(
                WindowsHelperOperation.operation_type == "acquire_item",
                WindowsHelperOperation.state.in_(("pending", "claimed")),
            )
        )
    )
    for operation in active_operations:
        request = HelperAcquireItemRequest.model_validate_json(operation.request_json)
        pending_live = operation.state == "pending" and (
            operation.expires_at if operation.expires_at.tzinfo else operation.expires_at.replace(tzinfo=timezone.utc)
        ) > now
        claimed_live = operation.state == "claimed" and operation.lease_expires_at is not None and (
            operation.lease_expires_at
            if operation.lease_expires_at.tzinfo
            else operation.lease_expires_at.replace(tzinfo=timezone.utc)
        ) > now
        if request.acquisition_run_id == run_id and (pending_live or claimed_live):
            raise WindowsHelperServiceError(
                "cleanup_operation_active",
                "An acquisition operation remains active for this run.",
                http_status=409,
            )
    ready_count = 0
    items = list(
        db.scalars(
            select(SourceAcquisitionItem)
            .where(SourceAcquisitionItem.run_id == run.id)
            .order_by(SourceAcquisitionItem.ordinal)
        )
    )
    for item in items:
        partial_path, ready_path = _paths(run, item)
        if ready_path.is_symlink() or partial_path.is_symlink():
            raise WindowsHelperServiceError("cleanup_path_unsafe", "Cleanup encountered an unsafe object.", http_status=409)
        if item.state == "ready":
            ready_digest = _verified_file_digest(ready_path, item.expected_size_bytes)
            if item.linux_verified_sha256 != ready_digest:
                raise WindowsHelperServiceError("ready_object_inconsistent", "The durable ready object digest is inconsistent.", http_status=409)
            ready_count += 1
            continue
        if ready_path.exists():
            raise WindowsHelperServiceError("ready_path_conflict", "Cleanup found unexpected ready evidence.", http_status=409)
        if partial_path.exists():
            if not partial_path.is_file():
                raise WindowsHelperServiceError("cleanup_path_unsafe", "Cleanup encountered an unsafe object.", http_status=409)
            partial_path.unlink()
            removed += 1
            item.state = "failed"
            item.failure_code = item.failure_code or "partial_cleaned"
            item.failed_at = item.failed_at or _now()
            db.add(item)
    db.commit()
    return removed, ready_count
