"""Internal durable exact-selection iCloud acquisition foundation.

This module is intentionally not registered as an API route or normal
acquisition mode. It provides the one-batch durable state foundation for the
exact-selection helper path after Phase0 validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.icloud_acquisition_run import (
    IcloudAcquisitionBatch,
    IcloudAcquisitionItem,
    IcloudAcquisitionResource,
    IcloudAcquisitionRun,
)
from app.models.ingestion_source import IngestionSource
from app.services.icloud_acquisition.exact_selection_adapter import (
    DEFAULT_LIBRARY,
    PREPARATION_BLOCKED,
    PREPARATION_FAILED,
    PREPARATION_READY,
    ExactSelectionHelperClient,
    ExactSelectionListing,
    ExactSelectionPreparation,
    ExactSelectionPrototypeError,
    count_partial_workspace_files,
    execute_prepared_exact_selection,
    find_staged_unknown_resources,
    prepare_exact_selection_prototype,
    validate_exact_selection_profile,
)
from app.services.icloud_acquisition.exact_selection_protocol import (
    AUTHENTICATED,
    OPERATION_DOWNLOAD_SELECTED,
    PROTOCOL_VERSION,
    RESOURCE_LIVE_PHOTO_ORIGINAL,
    RESOURCE_PRIMARY_ORIGINAL,
    decode_verification_checksum,
    validate_helper_request,
)
from app.services.icloud_acquisition.execution_service import (
    ACQUISITION_MODE_INTERNAL_EXACT_SELECTION,
    RUNNING_STATUSES,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_RUNNING,
)
from app.services.icloud_acquisition.new_count_planner import STILL_EXTENSIONS
from app.services.icloud_acquisition.schema import ensure_icloud_acquisition_schema


STATUS_BATCH_PLANNED = "planned"
STATUS_BATCH_DOWNLOADING = "downloading"
STATUS_BATCH_READY_FOR_SOURCE_INTAKE = "batch_ready_for_source_intake"
STATUS_BATCH_NEEDS_RETRY = "needs_retry"
STATUS_BATCH_BLOCKED = "blocked"
STATUS_BATCH_FAILED = "failed"
STATUS_RUN_BLOCKED = "blocked"

STATUS_ITEM_PLANNED = "planned"
STATUS_ITEM_DOWNLOADING = "downloading"
STATUS_ITEM_PUBLISHED = "published"
STATUS_ITEM_FAILED = "failed"
STATUS_ITEM_NEEDS_RETRY = "needs_retry"
STATUS_ITEM_BLOCKED = "blocked"

STATUS_RESOURCE_PLANNED = "planned"
STATUS_RESOURCE_PUBLISHED = "published"
STATUS_RESOURCE_FAILED = "failed"
STATUS_RESOURCE_NEEDS_RETRY = "needs_retry"
STATUS_RESOURCE_BLOCKED = "blocked"

NEXT_RUN_SOURCE_INTAKE = "Run Source Intake"
NEXT_RETRY_BATCH = "Retry batch"
NEXT_REAUTHENTICATE = "Re-authenticate iCloud"
NEXT_RESOLVE_STAGED_UNKNOWN = "Resolve staged unknown files by running Source Intake"
NEXT_INSPECT_PARTIAL = "Clear or inspect partial workspace"
NEXT_INSPECT_REPORT = "Stop and inspect report"
NEXT_RETRY_NETWORK = "Retry after network/cloud issue"

STOP_SELECTED_CANDIDATE_NOT_ORDINARY_STILL = "selected_candidate_not_ordinary_still"

_TRANSIENT_FAILURE_REASONS = {
    "helper_timeout",
    "helper_crash",
    "icloud_timeout",
    "network_error",
    "provider_error",
    "download_failed",
    "partial_item_failed",
    "lost_response_unresolved",
}

_AUTH_FAILURE_REASONS = {
    "authentication_required",
    "auth_required",
    "session_expired",
    "reauthentication_required",
    "authentication_failed",
    "helper_unavailable",
}

_CONFLICT_FAILURE_REASONS = {
    "size_mismatch",
    "checksum_mismatch",
    "partial_publication_detected",
    "conflicting_published_file",
    "selection_manifest_changed",
    "identity_digest_not_found",
    "identity_digest_not_unique",
}

_FORBIDDEN_MANIFEST_TERMS = (
    "password",
    "token",
    "cookie",
    "session",
    "download_url",
    "url",
    "remote_id",
    "item_id",
)


@dataclass(frozen=True)
class DurableExactRunResult:
    run_id: int
    batch_id: int | None
    status: str
    stop_reason: str | None
    next_safe_action: str | None
    batch_ready_for_source_intake: bool


class DurableExactAcquisitionError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _digest_remote_id(salt: str, remote_id: str) -> str:
    return hashlib.sha256(f"{salt}:{remote_id}".encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _provider_checksum_kind(value: str | None) -> str | None:
    if not value:
        return None
    try:
        kind, _ = decode_verification_checksum(value)
    except Exception:  # noqa: BLE001 - metadata classification only
        return "unsupported"
    return kind


def _next_safe_action(reason: str | None, *, ready: bool = False) -> str:
    if ready:
        return NEXT_RUN_SOURCE_INTAKE
    reason = (reason or "").strip().lower()
    if reason == "staged_unknown_pending_intake":
        return NEXT_RESOLVE_STAGED_UNKNOWN
    if reason == "partial_workspace_present":
        return NEXT_INSPECT_PARTIAL
    if reason in _AUTH_FAILURE_REASONS:
        return NEXT_REAUTHENTICATE
    if reason in _TRANSIENT_FAILURE_REASONS:
        return NEXT_RETRY_NETWORK if reason in {"network_error", "icloud_timeout"} else NEXT_RETRY_BATCH
    if reason in _CONFLICT_FAILURE_REASONS:
        return NEXT_INSPECT_REPORT
    return NEXT_INSPECT_REPORT


def _active_lease(db_session: Session) -> IcloudAcquisitionRun | None:
    return db_session.scalar(
        select(IcloudAcquisitionRun)
        .where(IcloudAcquisitionRun.status.in_(RUNNING_STATUSES))
        .order_by(IcloudAcquisitionRun.id.desc())
        .limit(1)
    )


def _create_internal_run(
    db_session: Session,
    *,
    source: IngestionSource,
    target_new_item_count: int,
    candidate_scan_limit: int,
    created_by: str,
) -> IcloudAcquisitionRun:
    salt = secrets.token_hex(16)
    now = _utc_now()
    run = IcloudAcquisitionRun(
        status=STATUS_RUNNING,
        source_label=source.source_label,
        source_type=source.source_type,
        source_root_path=source.source_root_path,
        acquisition_mode=ACQUISITION_MODE_INTERNAL_EXACT_SELECTION,
        source_registration_status="registered",
        username=source.account_username,
        staging_path=source.managed_staging_path or source.source_root_path,
        recent_count=target_new_item_count,
        source_profile_id=int(source.id),
        target_new_item_count=target_new_item_count,
        candidate_scan_limit=candidate_scan_limit,
        started_at=now,
        last_heartbeat_at=now,
        downloaded_count=0,
        skipped_existing_count=0,
        failed_count=0,
        run_identity_salt=salt,
        created_by=created_by,
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    return run


def _heartbeat(db_session: Session, run: IcloudAcquisitionRun) -> None:
    run.last_heartbeat_at = _utc_now()
    db_session.commit()


def _stop_requested(db_session: Session, run_id: int) -> bool:
    db_session.expire_all()
    run = db_session.get(IcloudAcquisitionRun, run_id)
    return bool(run and run.stop_requested)


def _attach_helper_callbacks(
    helper_client: ExactSelectionHelperClient,
    *,
    db_session: Session,
    run: IcloudAcquisitionRun,
) -> tuple[Any, Any]:
    prior_heartbeat = getattr(helper_client, "heartbeat_callback", None)
    prior_stop = getattr(helper_client, "stop_requested_callback", None)
    setattr(helper_client, "heartbeat_callback", lambda: _heartbeat(db_session, run))
    setattr(helper_client, "stop_requested_callback", lambda: _stop_requested(db_session, run.id))
    return prior_heartbeat, prior_stop


def _restore_helper_callbacks(
    helper_client: ExactSelectionHelperClient,
    callbacks: tuple[Any, Any],
) -> None:
    heartbeat, stop_requested = callbacks
    setattr(helper_client, "heartbeat_callback", heartbeat)
    setattr(helper_client, "stop_requested_callback", stop_requested)


def _finalize_run(
    db_session: Session,
    run: IcloudAcquisitionRun,
    *,
    status: str,
    stop_reason: str | None,
    failure_reason: str | None = None,
    next_safe_action: str | None = None,
    downloaded_count: int = 0,
    failed_count: int = 0,
) -> None:
    run.status = status
    run.stop_reason = stop_reason
    run.failure_reason = failure_reason
    run.error_code = failure_reason or stop_reason
    run.next_safe_action = next_safe_action or _next_safe_action(stop_reason)
    run.downloaded_count = downloaded_count
    run.failed_count = failed_count
    run.completed_at = _utc_now()
    run.last_heartbeat_at = run.completed_at
    if run.started_at is not None:
        completed_at = run.completed_at
        started_at = run.started_at
        if completed_at.tzinfo is not None and started_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=None)
        elif completed_at.tzinfo is None and started_at.tzinfo is not None:
            started_at = started_at.replace(tzinfo=None)
        run.elapsed_seconds = max(
            0.0,
            (completed_at - started_at).total_seconds(),
        )
    db_session.commit()


def _secret_free_manifest_text(manifest: dict[str, Any]) -> str:
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    lowered = encoded.casefold()
    if any(term in lowered for term in _FORBIDDEN_MANIFEST_TERMS):
        raise DurableExactAcquisitionError(
            "unsafe_manifest",
            "The durable exact-selection manifest contained a forbidden term.",
        )
    return json.dumps(manifest, indent=2, sort_keys=True)


def _selected_items_from_preparation(
    preparation: ExactSelectionPreparation,
) -> list[dict[str, Any]]:
    request = preparation.download_request or {}
    items = request.get("selected_items", [])
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _listing_items_by_id(listing: ExactSelectionListing | None) -> dict[str, Any]:
    if listing is None:
        return {}
    return {item.item_id: item for item in listing.items}


def _create_batch_from_preparation(
    db_session: Session,
    *,
    run: IcloudAcquisitionRun,
    preparation: ExactSelectionPreparation,
    target_new_item_count: int,
) -> IcloudAcquisitionBatch | None:
    selected_items = _selected_items_from_preparation(preparation)
    listing_by_id = _listing_items_by_id(preparation.listing)
    selected_resource_count = sum(len(item.get("resources", [])) for item in selected_items)
    batch = IcloudAcquisitionBatch(
        run_id=run.id,
        batch_index=1,
        status=STATUS_BATCH_PLANNED,
        target_new_item_count=target_new_item_count,
        selected_new_item_count=len(selected_items),
        selected_new_resource_count=selected_resource_count,
        planner_stop_reason=preparation.stopping_reason,
        started_at=_utc_now(),
        batch_ready_for_source_intake=False,
    )
    db_session.add(batch)
    db_session.flush()

    manifest_items: list[dict[str, Any]] = []
    salt = run.run_identity_salt or ""
    for item_index, selected_item in enumerate(selected_items, start=1):
        raw_item_id = str(selected_item.get("item_id") or "")
        remote_digest = _digest_remote_id(salt, raw_item_id)
        listed_item = listing_by_id.get(raw_item_id)
        resources = selected_item.get("resources", [])
        item_row = IcloudAcquisitionItem(
            batch_id=batch.id,
            item_index=item_index,
            remote_item_digest=remote_digest,
            grouping=getattr(listed_item, "grouping", None),
            status=STATUS_ITEM_PLANNED,
            selected_for_download=True,
            already_known=False,
            expected_resource_count=len(resources) if isinstance(resources, list) else 0,
            selected_resource_count=len(resources) if isinstance(resources, list) else 0,
            published_resource_count=0,
        )
        db_session.add(item_row)
        db_session.flush()

        manifest_resources: list[dict[str, Any]] = []
        for resource_index, resource in enumerate(resources, start=1):
            if not isinstance(resource, dict):
                continue
            checksum = str(resource.get("expected_checksum") or "")
            checksum_kind = _provider_checksum_kind(checksum)
            resource_row = IcloudAcquisitionResource(
                item_id=item_row.id,
                resource_index=resource_index,
                resource_role=str(resource.get("resource_id") or ""),
                relative_path=str(resource.get("relative_path") or ""),
                expected_size=int(resource.get("expected_size") or 0),
                provider_checksum=checksum,
                provider_checksum_kind=checksum_kind,
                status=STATUS_RESOURCE_PLANNED,
                selected_for_download=True,
                already_known=False,
            )
            db_session.add(resource_row)
            manifest_resources.append(
                {
                    "resource_ordinal": resource_index,
                    "role": resource_row.resource_role,
                    "relative_path": resource_row.relative_path,
                    "expected_size": resource_row.expected_size,
                    "provider_checksum_kind": checksum_kind,
                    "selected_for_download": True,
                }
            )
        manifest_items.append(
            {
                "item_ordinal": item_index,
                "remote_item_digest": remote_digest,
                "grouping": item_row.grouping,
                "resources": manifest_resources,
            }
        )

    manifest = {
        "manifest_version": 1,
        "run_id": run.id,
        "batch_index": 1,
        "source_profile_id": run.source_profile_id,
        "target_new_item_count": target_new_item_count,
        "candidate_scan_limit": run.candidate_scan_limit,
        "planner_stop_reason": preparation.stopping_reason,
        "items": manifest_items,
    }
    batch.manifest_json = _secret_free_manifest_text(manifest)
    run.manifest_json = batch.manifest_json
    db_session.commit()
    db_session.refresh(batch)
    return batch


def _preparation_selects_only_ordinary_stills(preparation: ExactSelectionPreparation) -> bool:
    """Return true only when all selected items are still-image primaries.

    This is intentionally stricter than the generic durable path. It is used by
    the 12.62.18 internal validation script to make the real-account execution
    gate durable, not merely a pre-execution advisory. 12.62.19 generalizes the
    same safety gate to small internal multi-batch validation where a batch may
    select more than one ordinary still.
    """

    plan = preparation.plan
    listing = preparation.listing
    if plan is None or listing is None:
        return False
    selected_items = [item for item in plan.items if item.selected_new]
    if not selected_items:
        return False

    listing_by_id = {item.item_id: item for item in listing.items}
    for planned_item in selected_items:
        planned_resources = {
            resource.adapter_resource_id: resource for resource in planned_item.resources
        }
        selected_resources = [
            resource for resource in planned_item.resources if resource.selected_for_download
        ]
        if len(selected_resources) != 1:
            return False
        if RESOURCE_LIVE_PHOTO_ORIGINAL in planned_resources:
            return False

        primary = planned_resources.get(RESOURCE_PRIMARY_ORIGINAL)
        if primary is None or primary.already_known or not primary.selected_for_download:
            return False

        listed_item = listing_by_id.get(planned_item.adapter_logical_item_id or "")
        if listed_item is None or listed_item.identity_ambiguous:
            return False
        blocking_reasons = [
            reason
            for reason in listed_item.unsupported_reasons
            if reason != "unsupported_adjustment_metadata_only"
        ]
        if blocking_reasons:
            return False
        listed_primary = next(
            (
                resource
                for resource in listed_item.resources
                if resource.resource_id == RESOURCE_PRIMARY_ORIGINAL
            ),
            None,
        )
        if listed_primary is None:
            return False

        extension = Path(listed_primary.relative_path).suffix.casefold()
        if not (
            listed_primary.content_type.casefold().startswith("image/")
            or extension in STILL_EXTENSIONS
        ):
            return False
    return True


def _block_batch_before_download(
    db_session: Session,
    *,
    run: IcloudAcquisitionRun,
    batch: IcloudAcquisitionBatch | None,
    reason: str,
) -> DurableExactRunResult:
    if batch is not None:
        batch.status = STATUS_BATCH_BLOCKED
        batch.failure_reason = reason
        batch.next_safe_action = _next_safe_action(reason)
        batch.finished_at = _utc_now()
        for item in batch.items:
            item.status = STATUS_ITEM_BLOCKED
            item.failure_reason = reason
            item.finished_at = batch.finished_at
            for resource in item.resources:
                resource.status = STATUS_RESOURCE_BLOCKED
                resource.failure_reason = reason
        db_session.commit()
    _finalize_run(
        db_session,
        run,
        status=STATUS_RUN_BLOCKED,
        stop_reason=reason,
        failure_reason=None,
        next_safe_action=_next_safe_action(reason),
    )
    return DurableExactRunResult(
        run_id=run.id,
        batch_id=batch.id if batch is not None else None,
        status=run.status,
        stop_reason=run.stop_reason,
        next_safe_action=run.next_safe_action,
        batch_ready_for_source_intake=False,
    )


def _batch_resources(batch: IcloudAcquisitionBatch) -> list[IcloudAcquisitionResource]:
    return [resource for item in batch.items for resource in item.resources]


def reconcile_batch_filesystem(
    db_session: Session,
    *,
    batch_id: int,
) -> IcloudAcquisitionBatch:
    """Reconcile durable resource rows against staging filesystem evidence."""

    batch = db_session.get(IcloudAcquisitionBatch, batch_id)
    if batch is None:
        raise DurableExactAcquisitionError("batch_not_found", "Acquisition batch not found.")
    run = db_session.get(IcloudAcquisitionRun, batch.run_id)
    if run is None or not run.staging_path:
        raise DurableExactAcquisitionError("run_not_found", "Acquisition run not found.")

    staging_root = Path(run.staging_path).resolve()
    partial_files = []
    partial_root = staging_root / ".partial"
    if partial_root.exists():
        partial_files = [path for path in partial_root.rglob("*") if path.is_file()]

    conflict_reason: str | None = None
    for item in batch.items:
        published_for_item = 0
        missing_for_item = 0
        failed_for_item = 0
        for resource in item.resources:
            if resource.status in {STATUS_RESOURCE_FAILED, STATUS_RESOURCE_BLOCKED}:
                failed_for_item += 1
                conflict_reason = conflict_reason or resource.failure_reason or "partial_item_failed"
                continue
            path = (staging_root / resource.relative_path).resolve()
            try:
                path.relative_to(staging_root)
            except ValueError:
                resource.status = STATUS_RESOURCE_BLOCKED
                resource.failure_reason = "local_filesystem_error"
                conflict_reason = conflict_reason or "local_filesystem_error"
                failed_for_item += 1
                continue
            if not path.exists():
                if resource.status == STATUS_RESOURCE_PUBLISHED:
                    resource.status = STATUS_RESOURCE_NEEDS_RETRY
                missing_for_item += 1
                continue
            try:
                actual_size = path.stat().st_size
            except OSError:
                resource.status = STATUS_RESOURCE_BLOCKED
                resource.failure_reason = "local_filesystem_error"
                conflict_reason = conflict_reason or "local_filesystem_error"
                failed_for_item += 1
                continue
            if resource.expected_size is not None and actual_size != resource.expected_size:
                resource.status = STATUS_RESOURCE_BLOCKED
                resource.failure_reason = "size_mismatch"
                conflict_reason = conflict_reason or "size_mismatch"
                failed_for_item += 1
                continue
            resource.byte_count = actual_size
            resource.local_sha256 = _sha256_file(path)
            resource.status = STATUS_RESOURCE_PUBLISHED
            resource.failure_reason = None
            resource.published_at = resource.published_at or _utc_now()
            published_for_item += 1

        item.published_resource_count = published_for_item
        if failed_for_item:
            item.status = STATUS_ITEM_BLOCKED
            item.failure_reason = conflict_reason
        elif missing_for_item and published_for_item:
            item.status = STATUS_ITEM_BLOCKED
            item.failure_reason = "partial_publication_detected"
            conflict_reason = conflict_reason or "partial_publication_detected"
        elif missing_for_item:
            item.status = STATUS_ITEM_NEEDS_RETRY
        else:
            item.status = STATUS_ITEM_PUBLISHED
            item.failure_reason = None
            item.finished_at = item.finished_at or _utc_now()

    resources = _batch_resources(batch)
    published_count = sum(1 for resource in resources if resource.status == STATUS_RESOURCE_PUBLISHED)
    failed_count = sum(
        1
        for resource in resources
        if resource.status in {STATUS_RESOURCE_FAILED, STATUS_RESOURCE_BLOCKED}
    )
    missing_count = sum(
        1
        for resource in resources
        if resource.status in {STATUS_RESOURCE_PLANNED, STATUS_RESOURCE_NEEDS_RETRY}
    )
    batch.downloaded_resource_count = published_count
    batch.downloaded_item_count = sum(
        1 for item in batch.items if item.status == STATUS_ITEM_PUBLISHED
    )
    batch.failed_resource_count = failed_count
    batch.failed_item_count = sum(
        1 for item in batch.items if item.status in {STATUS_ITEM_FAILED, STATUS_ITEM_BLOCKED}
    )
    if partial_files:
        conflict_reason = conflict_reason or "partial_workspace_present"
    if conflict_reason:
        batch.status = STATUS_BATCH_BLOCKED
        batch.failure_reason = conflict_reason
        batch.next_safe_action = _next_safe_action(conflict_reason)
        batch.batch_ready_for_source_intake = False
    elif missing_count:
        batch.status = STATUS_BATCH_NEEDS_RETRY
        batch.failure_reason = "lost_response_unresolved"
        batch.next_safe_action = NEXT_RETRY_BATCH
        batch.batch_ready_for_source_intake = False
    else:
        batch.status = STATUS_BATCH_READY_FOR_SOURCE_INTAKE
        batch.failure_reason = None
        batch.next_safe_action = NEXT_RUN_SOURCE_INTAKE
        batch.batch_ready_for_source_intake = True
        batch.finished_at = batch.finished_at or _utc_now()
    db_session.commit()
    db_session.refresh(batch)
    return batch


def _apply_download_response(
    db_session: Session,
    *,
    batch: IcloudAcquisitionBatch,
    response: dict[str, Any],
) -> None:
    batch.status = STATUS_BATCH_DOWNLOADING
    batch.downloaded_item_count = int(response.get("downloaded_item_count", 0))
    batch.downloaded_resource_count = int(response.get("downloaded_resource_count", 0))
    batch.failed_item_count = int(response.get("failed_item_count", 0))
    batch.failed_resource_count = int(response.get("failed_resource_count", 0))
    result_items = response.get("items", [])
    if isinstance(result_items, list):
        item_by_index = {item.item_index: item for item in batch.items}
        for result in result_items:
            if not isinstance(result, dict):
                continue
            item = item_by_index.get(int(result.get("selection_index") or 0))
            if item is None:
                continue
            if result.get("status") == "completed":
                item.status = STATUS_ITEM_PUBLISHED
                item.finished_at = _utc_now()
            elif result.get("status") == "failed":
                item.failure_reason = str(result.get("error_code") or "partial_item_failed")
                retryable = item.failure_reason in _TRANSIENT_FAILURE_REASONS
                item.status = STATUS_ITEM_NEEDS_RETRY if retryable else STATUS_ITEM_FAILED
                for resource in item.resources:
                    resource.status = STATUS_RESOURCE_NEEDS_RETRY if retryable else STATUS_RESOURCE_FAILED
                    resource.failure_reason = item.failure_reason
    db_session.commit()


def _download_request_from_batch(
    *,
    run: IcloudAcquisitionRun,
    batch: IcloudAcquisitionBatch,
    listing: ExactSelectionListing,
    library: str = DEFAULT_LIBRARY,
) -> dict[str, Any]:
    if not run.run_identity_salt:
        raise DurableExactAcquisitionError("identity_salt_missing", "Run identity salt is missing.")
    digest_matches: dict[str, list[Any]] = {item.remote_item_digest: [] for item in batch.items}
    for listed in listing.items:
        digest = _digest_remote_id(run.run_identity_salt, listed.item_id)
        if digest in digest_matches:
            digest_matches[digest].append(listed)

    selected_items: list[dict[str, Any]] = []
    for item in batch.items:
        matches = digest_matches.get(item.remote_item_digest, [])
        if not matches:
            raise DurableExactAcquisitionError(
                "identity_digest_not_found",
                "A selected logical item was not found during retry/reconcile.",
            )
        if len(matches) != 1:
            raise DurableExactAcquisitionError(
                "identity_digest_not_unique",
                "A selected logical item digest matched more than one candidate.",
            )
        listed = matches[0]
        listed_resources = {resource.resource_id: resource for resource in listed.resources}
        selected_resources: list[dict[str, Any]] = []
        for resource in item.resources:
            if resource.status == STATUS_RESOURCE_PUBLISHED:
                continue
            listed_resource = listed_resources.get(resource.resource_role)
            if listed_resource is None:
                raise DurableExactAcquisitionError(
                    "selection_manifest_changed",
                    "A selected resource was absent during retry/reconcile.",
                )
            if (
                listed_resource.relative_path != resource.relative_path
                or listed_resource.expected_size != resource.expected_size
                or listed_resource.expected_checksum != resource.provider_checksum
            ):
                raise DurableExactAcquisitionError(
                    "selection_manifest_changed",
                    "A selected resource manifest changed during retry/reconcile.",
                )
            selected_resources.append(
                {
                    "resource_id": listed_resource.resource_id,
                    "relative_path": listed_resource.relative_path,
                    "expected_size": listed_resource.expected_size,
                    "expected_checksum": listed_resource.expected_checksum,
                }
            )
        if selected_resources:
            selected_items.append({"item_id": listed.item_id, "resources": selected_resources})
    if not selected_items:
        raise DurableExactAcquisitionError("batch_already_complete", "Batch is already complete.")
    return validate_helper_request(
        {
            "protocol_version": PROTOCOL_VERSION,
            "operation": OPERATION_DOWNLOAD_SELECTED,
            "account_username": str(run.username or ""),
            "library": library,
            "candidate_scan_limit": int(run.candidate_scan_limit or 1),
            "staging_root": str(run.staging_path or ""),
            "run_token": secrets.token_hex(16),
            "selected_items": selected_items,
        }
    )


def _classify_preparation_status(preparation: ExactSelectionPreparation) -> tuple[str, str | None]:
    if preparation.status == PREPARATION_FAILED:
        return STATUS_FAILED, preparation.error_code or preparation.stopping_reason
    if preparation.status == PREPARATION_BLOCKED:
        return STATUS_RUN_BLOCKED, preparation.stopping_reason
    if preparation.status == PREPARATION_READY:
        return STATUS_RUNNING, preparation.stopping_reason
    return STATUS_FAILED, "unknown_error"


def run_durable_exact_selection_batch(
    db_session: Session,
    *,
    source_id: int,
    target_new_item_count: int,
    candidate_scan_limit: int,
    helper_client: ExactSelectionHelperClient,
    created_by: str = "internal_exact_phase1",
    ordinary_still_only: bool = False,
) -> DurableExactRunResult:
    """Plan and execute one durable exact-selection acquisition batch."""

    ensure_icloud_acquisition_schema(db_session)
    active = _active_lease(db_session)
    if active is not None:
        raise DurableExactAcquisitionError(
            "icloud_acquisition_lease_active",
            "Another iCloud acquisition run is active.",
        )
    source = db_session.get(IngestionSource, source_id)
    if source is None:
        raise DurableExactAcquisitionError("source_not_found", "Source Profile not found.")
    run = _create_internal_run(
        db_session,
        source=source,
        target_new_item_count=target_new_item_count,
        candidate_scan_limit=candidate_scan_limit,
        created_by=created_by,
    )
    callbacks = _attach_helper_callbacks(helper_client, db_session=db_session, run=run)

    batch: IcloudAcquisitionBatch | None = None
    try:
        _heartbeat(db_session, run)
        preparation = prepare_exact_selection_prototype(
            db_session,
            source_id=source_id,
            target_new_item_count=target_new_item_count,
            candidate_scan_limit=candidate_scan_limit,
            helper_client=helper_client,
            ordinary_still_only=ordinary_still_only,
        )
        batch = _create_batch_from_preparation(
            db_session,
            run=run,
            preparation=preparation,
            target_new_item_count=target_new_item_count,
        )
        status, reason = _classify_preparation_status(preparation)
        if preparation.status != PREPARATION_READY:
            if batch is not None:
                batch.status = STATUS_BATCH_BLOCKED if status == STATUS_RUN_BLOCKED else STATUS_BATCH_FAILED
                batch.failure_reason = reason
                batch.next_safe_action = _next_safe_action(reason)
                batch.finished_at = _utc_now()
            _finalize_run(
                db_session,
                run,
                status=status,
                stop_reason=reason,
                failure_reason=reason if status == STATUS_FAILED else None,
                next_safe_action=_next_safe_action(reason),
            )
            return DurableExactRunResult(
                run_id=run.id,
                batch_id=batch.id if batch is not None else None,
                status=run.status,
                stop_reason=run.stop_reason,
                next_safe_action=run.next_safe_action,
                batch_ready_for_source_intake=False,
            )

        if ordinary_still_only and not _preparation_selects_only_ordinary_stills(preparation):
            return _block_batch_before_download(
                db_session,
                run=run,
                batch=batch,
                reason=STOP_SELECTED_CANDIDATE_NOT_ORDINARY_STILL,
            )

        _heartbeat(db_session, run)
        if batch is not None:
            batch.status = STATUS_BATCH_DOWNLOADING
            for item in batch.items:
                item.status = STATUS_ITEM_DOWNLOADING
            db_session.commit()
        response = execute_prepared_exact_selection(
            db_session,
            preparation=preparation,
            helper_client=helper_client,
        )
        if batch is not None:
            _apply_download_response(db_session, batch=batch, response=response)
            batch = reconcile_batch_filesystem(db_session, batch_id=batch.id)
        ready = bool(batch and batch.batch_ready_for_source_intake)
        stop_reason = "target_new_count_reached" if ready else str(response.get("stop_reason") or "partial_item_failed")
        _finalize_run(
            db_session,
            run,
            status=STATUS_COMPLETED if ready else STATUS_FAILED,
            stop_reason=stop_reason,
            failure_reason=None if ready else stop_reason,
            next_safe_action=_next_safe_action(stop_reason, ready=ready),
            downloaded_count=batch.downloaded_resource_count if batch else 0,
            failed_count=batch.failed_resource_count if batch else 0,
        )
        return DurableExactRunResult(
            run_id=run.id,
            batch_id=batch.id if batch is not None else None,
            status=run.status,
            stop_reason=run.stop_reason,
            next_safe_action=run.next_safe_action,
            batch_ready_for_source_intake=ready,
        )
    except ExactSelectionPrototypeError as exc:
        reason = exc.code
        if batch is not None:
            batch = reconcile_batch_filesystem(db_session, batch_id=batch.id)
            if not batch.batch_ready_for_source_intake:
                batch.failure_reason = batch.failure_reason or reason
                batch.next_safe_action = _next_safe_action(batch.failure_reason)
                db_session.commit()
        _finalize_run(
            db_session,
            run,
            status=STATUS_COMPLETED if batch and batch.batch_ready_for_source_intake else STATUS_FAILED,
            stop_reason=(
                "lost_response_reconciled"
                if batch and batch.batch_ready_for_source_intake
                else reason
            ),
            failure_reason=None if batch and batch.batch_ready_for_source_intake else reason,
            next_safe_action=(
                NEXT_RUN_SOURCE_INTAKE
                if batch and batch.batch_ready_for_source_intake
                else _next_safe_action(reason)
            ),
            downloaded_count=batch.downloaded_resource_count if batch else 0,
            failed_count=batch.failed_resource_count if batch else 0,
        )
        return DurableExactRunResult(
            run_id=run.id,
            batch_id=batch.id if batch is not None else None,
            status=run.status,
            stop_reason=run.stop_reason,
            next_safe_action=run.next_safe_action,
            batch_ready_for_source_intake=bool(batch and batch.batch_ready_for_source_intake),
        )
    finally:
        _restore_helper_callbacks(helper_client, callbacks)


def retry_durable_exact_selection_batch(
    db_session: Session,
    *,
    batch_id: int,
    helper_client: ExactSelectionHelperClient,
    library: str = DEFAULT_LIBRARY,
) -> DurableExactRunResult:
    """Retry one batch only after reconciling frozen manifest evidence."""

    ensure_icloud_acquisition_schema(db_session)
    batch = reconcile_batch_filesystem(db_session, batch_id=batch_id)
    run = db_session.get(IcloudAcquisitionRun, batch.run_id)
    if run is None:
        raise DurableExactAcquisitionError("run_not_found", "Acquisition run not found.")
    callbacks = _attach_helper_callbacks(helper_client, db_session=db_session, run=run)
    try:
        return _retry_durable_exact_selection_batch_with_callbacks(
            db_session,
            batch=batch,
            run=run,
            helper_client=helper_client,
            library=library,
        )
    finally:
        _restore_helper_callbacks(helper_client, callbacks)


def _retry_durable_exact_selection_batch_with_callbacks(
    db_session: Session,
    *,
    batch: IcloudAcquisitionBatch,
    run: IcloudAcquisitionRun,
    helper_client: ExactSelectionHelperClient,
    library: str,
) -> DurableExactRunResult:
    if batch.batch_ready_for_source_intake:
        run.status = STATUS_COMPLETED
        run.stop_reason = "lost_response_reconciled"
        run.next_safe_action = NEXT_RUN_SOURCE_INTAKE
        db_session.commit()
        return DurableExactRunResult(
            run_id=run.id,
            batch_id=batch.id,
            status=run.status,
            stop_reason=run.stop_reason,
            next_safe_action=run.next_safe_action,
            batch_ready_for_source_intake=True,
        )
    if batch.status == STATUS_BATCH_BLOCKED:
        run.status = STATUS_RUN_BLOCKED
        run.stop_reason = batch.failure_reason
        run.next_safe_action = batch.next_safe_action
        db_session.commit()
        return DurableExactRunResult(
            run_id=run.id,
            batch_id=batch.id,
            status=run.status,
            stop_reason=run.stop_reason,
            next_safe_action=run.next_safe_action,
            batch_ready_for_source_intake=False,
        )

    profile = validate_exact_selection_profile(db_session, source_id=int(run.source_profile_id or 0))
    if find_staged_unknown_resources(db_session, profile=profile):
        run.status = STATUS_RUN_BLOCKED
        run.stop_reason = "staged_unknown_pending_intake"
        run.next_safe_action = NEXT_RESOLVE_STAGED_UNKNOWN
        db_session.commit()
        return DurableExactRunResult(run.id, batch.id, run.status, run.stop_reason, run.next_safe_action, False)
    if count_partial_workspace_files(profile):
        run.status = STATUS_RUN_BLOCKED
        run.stop_reason = "partial_workspace_present"
        run.next_safe_action = NEXT_INSPECT_PARTIAL
        db_session.commit()
        return DurableExactRunResult(run.id, batch.id, run.status, run.stop_reason, run.next_safe_action, False)
    auth_state = helper_client.check_auth(account_username=profile.account_username)
    if auth_state != AUTHENTICATED:
        run.status = STATUS_RUN_BLOCKED
        run.stop_reason = auth_state
        run.next_safe_action = NEXT_REAUTHENTICATE
        db_session.commit()
        return DurableExactRunResult(run.id, batch.id, run.status, run.stop_reason, run.next_safe_action, False)
    listing = helper_client.list_candidates(
        account_username=profile.account_username,
        candidate_scan_limit=int(run.candidate_scan_limit or 1),
        library=library,
    )
    try:
        request = _download_request_from_batch(run=run, batch=batch, listing=listing, library=library)
    except DurableExactAcquisitionError as exc:
        batch.status = STATUS_BATCH_BLOCKED
        batch.failure_reason = exc.code
        batch.next_safe_action = _next_safe_action(exc.code)
        run.status = STATUS_RUN_BLOCKED
        run.stop_reason = exc.code
        run.next_safe_action = batch.next_safe_action
        db_session.commit()
        return DurableExactRunResult(run.id, batch.id, run.status, run.stop_reason, run.next_safe_action, False)
    response = helper_client.download_selected(request)
    _apply_download_response(db_session, batch=batch, response=response)
    batch = reconcile_batch_filesystem(db_session, batch_id=batch.id)
    ready = batch.batch_ready_for_source_intake
    run.status = STATUS_COMPLETED if ready else STATUS_FAILED
    run.stop_reason = "target_new_count_reached" if ready else batch.failure_reason or "partial_item_failed"
    run.next_safe_action = _next_safe_action(run.stop_reason, ready=ready)
    run.downloaded_count = batch.downloaded_resource_count
    run.failed_count = batch.failed_resource_count
    run.completed_at = _utc_now()
    db_session.commit()
    return DurableExactRunResult(
        run.id,
        batch.id,
        run.status,
        run.stop_reason,
        run.next_safe_action,
        ready,
    )


def get_source_intake_handoff_manifest(
    db_session: Session,
    *,
    batch_id: int,
) -> dict[str, Any]:
    """Return the future Source Intake handoff contract for a ready batch."""

    batch = db_session.get(IcloudAcquisitionBatch, batch_id)
    if batch is None:
        raise DurableExactAcquisitionError("batch_not_found", "Acquisition batch not found.")
    run = db_session.get(IcloudAcquisitionRun, batch.run_id)
    if run is None:
        raise DurableExactAcquisitionError("run_not_found", "Acquisition run not found.")
    ready_resources = [
        {
            "resource_id": resource.id,
            "logical_item_id": resource.item_id,
            "relative_path": resource.relative_path,
            "resource_role": resource.resource_role,
            "byte_count": resource.byte_count,
            "local_sha256": resource.local_sha256,
        }
        for item in batch.items
        for resource in item.resources
        if resource.status == STATUS_RESOURCE_PUBLISHED
    ]
    return {
        "batch_id": batch.id,
        "run_id": run.id,
        "source_profile_id": run.source_profile_id,
        "batch_ready_for_source_intake": bool(batch.batch_ready_for_source_intake),
        "ready_resources": ready_resources,
        "failed_or_deferred_count": sum(
            1
            for item in batch.items
            for resource in item.resources
            if resource.status != STATUS_RESOURCE_PUBLISHED
        ),
        "report_path": run.report_path,
    }
