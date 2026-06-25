"""Internal iCloud acquisition-batch Source Intake handoff.

This module intentionally has no normal UI/API route. It is the internal bridge
from a durable exact-selection acquisition batch to Source Intake.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.asset import Asset
from app.models.icloud_acquisition_run import (
    IcloudAcquisitionBatch,
    IcloudAcquisitionItem,
    IcloudAcquisitionResource,
    IcloudAcquisitionRun,
)
from app.models.ingestion_source import IngestionSource
from app.models.provenance import Provenance
from app.models.source_intake_run import SourceIntakeRun
from app.services.admin.ingestion_operation_guardrail_service import (
    get_ingestion_operation_guardrail_snapshot,
)
from app.services.admin.source_intake_execution_service import (
    STATUS_COMPLETED as SOURCE_INTAKE_STATUS_COMPLETED,
    STATUS_FAILED as SOURCE_INTAKE_STATUS_FAILED,
    STATUS_RUNNING as SOURCE_INTAKE_STATUS_RUNNING,
)
from app.services.admin.source_intake_schema import ensure_source_intake_schema
from app.services.icloud_acquisition.durable_exact_service import (
    STATUS_RESOURCE_PUBLISHED,
)
from app.services.icloud_acquisition.execution_service import (
    ACQUISITION_MODE_INTERNAL_EXACT_SELECTION,
)
from app.services.icloud_acquisition.schema import ensure_icloud_acquisition_schema
from app.services.ingestion.pipeline_orchestrator import (
    PipelineContext,
    RuntimeArgs,
    _run_pipeline,
    resolve_runtime_path,
)
from app.services.ingestion.scanner import FileScanRecord


INTAKE_MODE_ICLOUD_ACQUISITION_BATCH = "icloud_acquisition_batch"

STATUS_BATCH_INTAKE_RUNNING = "intake_running"
STATUS_BATCH_INTAKE_COMPLETED = "intake_completed"
STATUS_BATCH_INTAKE_COMPLETED_WITH_ERRORS = "intake_completed_with_errors"
STATUS_BATCH_INTAKE_FAILED = "intake_failed"
STATUS_BATCH_INTAKE_BLOCKED = "intake_blocked"
STATUS_BATCH_READY_FOR_CLEANUP_DRY_RUN = "ready_for_cleanup_dry_run"

STATUS_ITEM_INTAKE_COMPLETED = "intake_completed"
STATUS_ITEM_INTAKE_COMPLETED_WITH_ERRORS = "intake_completed_with_errors"
STATUS_ITEM_INTAKE_BLOCKED = "intake_blocked"

STATUS_RESOURCE_INTAKE_PROCESSED = "resource_intake_processed"
STATUS_RESOURCE_INTAKE_DUPLICATE_LINKED = "resource_intake_duplicate_linked"
STATUS_RESOURCE_INTAKE_SKIPPED_KNOWN = "resource_intake_skipped_known"
STATUS_RESOURCE_INTAKE_FAILED = "resource_intake_failed"
STATUS_RESOURCE_INTAKE_DEFERRED = "resource_intake_deferred"
STATUS_RESOURCE_MISSING_BEFORE_INTAKE = "resource_missing_before_intake"
STATUS_RESOURCE_SHA_MISMATCH_BEFORE_INTAKE = "resource_sha_mismatch_before_intake"

RESOURCE_SUCCESS_STATUSES = {
    STATUS_RESOURCE_INTAKE_PROCESSED,
    STATUS_RESOURCE_INTAKE_DUPLICATE_LINKED,
    STATUS_RESOURCE_INTAKE_SKIPPED_KNOWN,
}

NEXT_RUN_SOURCE_INTAKE = "Run batch Source Intake"
NEXT_RUN_CLEANUP_DRY_RUN = "Run guarded iCloud cleanup dry run"
NEXT_RETRY_SOURCE_INTAKE = "Retry batch Source Intake after resolving the reported issue"
NEXT_INSPECT_REPORT = "Inspect batch Source Intake report"
NEXT_CLEAR_DROP_ZONE = "Clear or process the Drop Zone before retrying Source Intake"
NEXT_WAIT_FOR_ACTIVE_OPERATION = "Wait for the active ingestion operation to finish"


@dataclass(frozen=True)
class VerifiedBatchResource:
    resource_id: int
    item_id: int
    relative_path: str
    absolute_path: Path
    local_sha256: str
    expected_size: int | None
    file_record: FileScanRecord


@dataclass(frozen=True)
class BatchSourceIntakeResult:
    status: str
    stop_reason: str | None
    next_safe_action: str | None
    acquisition_run_id: int | None
    acquisition_batch_id: int
    source_profile_id: int | None
    source_intake_run_id: int | None
    ingestion_run_id: int | None
    resources_ready_for_intake: int
    resources_processed: int
    resources_duplicate_linked: int
    resources_skipped_known: int
    resources_failed: int
    resources_deferred: int
    missing_files: int
    sha_mismatches: int
    batch_ready_for_cleanup_dry_run: bool
    report_path: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BatchSourceIntakeError(RuntimeError):
    """Raised for non-recoverable handoff validation errors."""

    def __init__(self, code: str, message: str, *, next_safe_action: str | None = NEXT_INSPECT_REPORT) -> None:
        super().__init__(message)
        self.code = code
        self.next_safe_action = next_safe_action


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _normalized_relative(value: str | None) -> str:
    return (value or "").replace("\\", "/").strip("/")


def _resolve_resource_path(staging_root: Path, relative_path: str) -> Path:
    rel = Path(relative_path)
    if rel.is_absolute() or any(part == ".." for part in rel.parts):
        raise BatchSourceIntakeError("unsafe_resource_path", f"Unsafe acquisition resource path: {relative_path}")
    resolved = (staging_root / rel).resolve()
    if not _is_within(resolved, staging_root):
        raise BatchSourceIntakeError("resource_outside_staging_root", f"Resource is outside staging root: {relative_path}")
    return resolved


def _is_partial_path(path: Path) -> bool:
    lowered_parts = [part.lower() for part in path.parts]
    return any(part.endswith(".partial") or part == ".partial" for part in lowered_parts)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _file_record(path: Path) -> FileScanRecord:
    stat = path.stat()
    modified_utc = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    return FileScanRecord(
        full_path=str(path.resolve()),
        file_name=path.name,
        extension=path.suffix.lower(),
        size_bytes=int(stat.st_size),
        modified_timestamp_utc=modified_utc.isoformat(),
        original_source_path=str(path.resolve()),
        original_filename=path.name,
    )


def _report_directory() -> Path:
    report_root = resolve_runtime_path("../storage/logs/icloud_batch_source_intake_reports")
    report_root.mkdir(parents=True, exist_ok=True)
    return report_root


def _write_batch_report(
    *,
    batch: IcloudAcquisitionBatch,
    run: IcloudAcquisitionRun | None,
    result: BatchSourceIntakeResult,
    resource_samples: list[dict[str, Any]],
    source_intake_report_path: str | None,
) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = _report_directory() / f"icloud_batch_source_intake_{batch.id}_{timestamp}.json"
    payload = {
        "report_type": "icloud_acquisition_batch_source_intake",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "acquisition_run_id": result.acquisition_run_id,
        "acquisition_batch_id": result.acquisition_batch_id,
        "source_profile_id": result.source_profile_id,
        "source_intake_run_id": result.source_intake_run_id,
        "ingestion_run_id": result.ingestion_run_id,
        "status": result.status,
        "stop_reason": result.stop_reason,
        "next_safe_action": result.next_safe_action,
        "counts": {
            "resources_ready_for_intake": result.resources_ready_for_intake,
            "resources_processed": result.resources_processed,
            "resources_duplicate_linked": result.resources_duplicate_linked,
            "resources_skipped_known": result.resources_skipped_known,
            "resources_failed": result.resources_failed,
            "resources_deferred": result.resources_deferred,
            "missing_files": result.missing_files,
            "sha_mismatches": result.sha_mismatches,
        },
        "batch_ready_for_cleanup_dry_run": result.batch_ready_for_cleanup_dry_run,
        "source_intake_report_path": source_intake_report_path,
        "acquisition_batch_status": batch.status,
        "acquisition_run_status": run.status if run is not None else None,
        "resource_samples": resource_samples[:20],
    }
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(report_path)


def _source_staging_root(source: IngestionSource) -> Path:
    root_value = source.managed_staging_path or source.source_root_path or ""
    if not root_value.strip():
        raise BatchSourceIntakeError("source_staging_root_missing", "Source Profile has no managed staging path.")
    root = Path(root_value).expanduser()
    return root.resolve() if root.is_absolute() else (Path.cwd() / root).resolve()


def _load_batch_context(
    db_session: Session,
    *,
    batch_id: int,
    source_id: int | None,
) -> tuple[IcloudAcquisitionBatch, IcloudAcquisitionRun, IngestionSource, Path]:
    batch = db_session.get(IcloudAcquisitionBatch, batch_id)
    if batch is None:
        raise BatchSourceIntakeError("batch_not_found", f"iCloud acquisition batch {batch_id} was not found.")
    run = db_session.get(IcloudAcquisitionRun, batch.run_id)
    if run is None:
        raise BatchSourceIntakeError("run_not_found", f"iCloud acquisition run {batch.run_id} was not found.")
    if run.acquisition_mode != ACQUISITION_MODE_INTERNAL_EXACT_SELECTION:
        raise BatchSourceIntakeError(
            "not_internal_exact_selection",
            "Only internal exact-selection iCloud acquisition batches can use this handoff.",
        )
    if source_id is not None and run.source_profile_id != source_id:
        raise BatchSourceIntakeError(
            "wrong_source_profile",
            f"Batch belongs to Source Profile {run.source_profile_id}, not {source_id}.",
        )
    if run.source_profile_id is None:
        raise BatchSourceIntakeError("source_profile_missing", "Acquisition run is not linked to a Source Profile.")
    source = db_session.get(IngestionSource, run.source_profile_id)
    if source is None:
        raise BatchSourceIntakeError("source_profile_not_found", "Linked Source Profile was not found.")
    if (source.profile_status or "active").strip().lower() != "active":
        raise BatchSourceIntakeError("source_profile_not_active", "Linked Source Profile is not active.")
    if (source.cloud_provider or "").lower() != "icloud" or (source.source_type or "").lower() != "cloud_export":
        raise BatchSourceIntakeError("source_profile_not_icloud", "Linked Source Profile is not an active iCloud export profile.")
    staging_root = _source_staging_root(source)
    if not staging_root.exists() or not staging_root.is_dir():
        raise BatchSourceIntakeError("staging_root_missing", f"Managed staging path is not available: {staging_root}")
    for path_value in (run.staging_path, run.source_root_path):
        if path_value and Path(path_value).expanduser().resolve() != staging_root:
            raise BatchSourceIntakeError(
                "staging_root_mismatch",
                "Acquisition run staging path does not match the selected Source Profile managed staging path.",
            )
    return batch, run, source, staging_root


def _resource_provenance_rows(
    db_session: Session,
    *,
    source_id: int,
    relative_path: str,
) -> list[Provenance]:
    normalized = _normalized_relative(relative_path)
    lookup = {normalized, normalized.replace("/", "\\")}
    return list(
        db_session.scalars(
            select(Provenance).where(
                Provenance.ingestion_source_id == source_id,
                Provenance.source_relative_path.in_(lookup),
            )
        ).all()
    )


def _mark_resource(
    resource: IcloudAcquisitionResource,
    *,
    status: str,
    source_intake_run_id: int | None,
    ingestion_run_id: int | None,
    asset_sha256: str | None,
    error: str | None = None,
) -> None:
    resource.status = status
    resource.source_intake_status = status
    resource.source_intake_run_id = source_intake_run_id
    resource.ingestion_run_id = ingestion_run_id
    resource.asset_sha256 = asset_sha256
    resource.source_intake_error = error
    resource.failure_reason = error if status not in RESOURCE_SUCCESS_STATUSES else resource.failure_reason
    resource.source_intake_completed_at = _utc_now()


def _reconcile_already_processed_resource(
    db_session: Session,
    *,
    source_id: int,
    resource: IcloudAcquisitionResource,
) -> bool:
    if resource.local_sha256 is None:
        return False
    rows = _resource_provenance_rows(db_session, source_id=source_id, relative_path=resource.relative_path)
    if not rows:
        return False
    hashes = {(row.asset_sha256 or "").strip().lower() for row in rows if (row.asset_sha256 or "").strip()}
    if resource.local_sha256.lower() in hashes and db_session.get(Asset, resource.local_sha256.lower()) is not None:
        _mark_resource(
            resource,
            status=STATUS_RESOURCE_INTAKE_SKIPPED_KNOWN,
            source_intake_run_id=resource.source_intake_run_id,
            ingestion_run_id=resource.ingestion_run_id,
            asset_sha256=resource.local_sha256.lower(),
        )
        return True
    if hashes:
        _mark_resource(
            resource,
            status=STATUS_RESOURCE_INTAKE_FAILED,
            source_intake_run_id=resource.source_intake_run_id,
            ingestion_run_id=resource.ingestion_run_id,
            asset_sha256=None,
            error="conflicting_existing_provenance",
        )
        raise BatchSourceIntakeError(
            "conflicting_existing_provenance",
            f"Existing provenance for {resource.relative_path} does not match the acquisition resource digest.",
        )
    return False


def _verified_resources_for_intake(
    db_session: Session,
    *,
    batch: IcloudAcquisitionBatch,
    source: IngestionSource,
    staging_root: Path,
) -> tuple[list[VerifiedBatchResource], int]:
    if not batch.batch_ready_for_source_intake:
        raise BatchSourceIntakeError(
            "batch_not_ready_for_source_intake",
            "Acquisition batch is not marked ready for Source Intake.",
            next_safe_action=NEXT_RUN_SOURCE_INTAKE,
        )

    verified: list[VerifiedBatchResource] = []
    skipped_known = 0
    for item in batch.items:
        for resource in item.resources:
            if not resource.selected_for_download:
                continue
            if resource.status in RESOURCE_SUCCESS_STATUSES:
                if _reconcile_already_processed_resource(db_session, source_id=source.id, resource=resource):
                    skipped_known += 1
                    continue
                raise BatchSourceIntakeError(
                    "processed_resource_missing_provenance",
                    f"Resource {resource.relative_path} is marked processed but matching provenance was not found.",
                )
            if resource.status != STATUS_RESOURCE_PUBLISHED:
                raise BatchSourceIntakeError(
                    "batch_has_non_ready_resources",
                    f"Resource {resource.relative_path} is not ready for Source Intake: {resource.status}",
                )

            absolute_path = _resolve_resource_path(staging_root, resource.relative_path)
            if _is_partial_path(absolute_path):
                _mark_resource(
                    resource,
                    status=STATUS_RESOURCE_INTAKE_DEFERRED,
                    source_intake_run_id=None,
                    ingestion_run_id=None,
                    asset_sha256=None,
                    error="partial_file_selected",
                )
                raise BatchSourceIntakeError(
                    "partial_file_selected",
                    f"Partial file cannot be selected for Source Intake: {resource.relative_path}",
                )
            if not absolute_path.exists() or not absolute_path.is_file():
                _mark_resource(
                    resource,
                    status=STATUS_RESOURCE_MISSING_BEFORE_INTAKE,
                    source_intake_run_id=None,
                    ingestion_run_id=None,
                    asset_sha256=None,
                    error="file_missing_before_intake",
                )
                raise BatchSourceIntakeError(
                    "file_missing_before_intake",
                    f"Ready resource is missing before Source Intake: {resource.relative_path}",
                )
            size = absolute_path.stat().st_size
            expected_size = resource.expected_size if resource.expected_size is not None else resource.byte_count
            if expected_size is not None and int(size) != int(expected_size):
                _mark_resource(
                    resource,
                    status=STATUS_RESOURCE_INTAKE_FAILED,
                    source_intake_run_id=None,
                    ingestion_run_id=None,
                    asset_sha256=None,
                    error="size_mismatch_before_intake",
                )
                raise BatchSourceIntakeError(
                    "size_mismatch_before_intake",
                    f"Ready resource size changed before Source Intake: {resource.relative_path}",
                )
            local_sha256 = _sha256_file(absolute_path)
            if resource.local_sha256 and local_sha256.lower() != resource.local_sha256.lower():
                _mark_resource(
                    resource,
                    status=STATUS_RESOURCE_SHA_MISMATCH_BEFORE_INTAKE,
                    source_intake_run_id=None,
                    ingestion_run_id=None,
                    asset_sha256=None,
                    error="sha_mismatch_before_intake",
                )
                raise BatchSourceIntakeError(
                    "sha_mismatch_before_intake",
                    f"Ready resource SHA-256 changed before Source Intake: {resource.relative_path}",
                )
            resource.local_sha256 = local_sha256.lower()
            resource.byte_count = int(size)

            if _reconcile_already_processed_resource(db_session, source_id=source.id, resource=resource):
                skipped_known += 1
                continue

            verified.append(
                VerifiedBatchResource(
                    resource_id=resource.id,
                    item_id=item.id,
                    relative_path=resource.relative_path,
                    absolute_path=absolute_path,
                    local_sha256=local_sha256.lower(),
                    expected_size=int(size),
                    file_record=_file_record(absolute_path),
                )
            )
    return verified, skipped_known


def _resource_by_path(batch: IcloudAcquisitionBatch) -> dict[str, IcloudAcquisitionResource]:
    return {
        str((resource.relative_path or "")).replace("\\", "/").strip("/").lower(): resource
        for item in batch.items
        for resource in item.resources
    }


def _path_key(path: str | Path, root: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(root.resolve())).replace("\\", "/").strip("/").lower()
    except ValueError:
        return str(path).replace("\\", "/").strip("/").lower()


def _update_resources_from_pipeline(
    *,
    db_session: Session,
    batch: IcloudAcquisitionBatch,
    source: IngestionSource,
    staging_root: Path,
    source_intake_run_id: int,
    ingestion_run_id: int | None,
    ctx: PipelineContext,
) -> None:
    by_path = _resource_by_path(batch)

    for item in ctx.persistence_result.inserted_records if ctx.persistence_result else []:
        hashed = item.copied_file.hashed_file
        resource = by_path.get(_path_key(hashed.record.original_source_path, staging_root))
        if resource is not None:
            _mark_resource(
                resource,
                status=STATUS_RESOURCE_INTAKE_PROCESSED,
                source_intake_run_id=source_intake_run_id,
                ingestion_run_id=ingestion_run_id,
                asset_sha256=hashed.sha256,
            )

    for item in ctx.persistence_result.skipped_existing_records if ctx.persistence_result else []:
        hashed = item.copied_file.hashed_file
        resource = by_path.get(_path_key(hashed.record.original_source_path, staging_root))
        if resource is not None:
            _mark_resource(
                resource,
                status=STATUS_RESOURCE_INTAKE_DUPLICATE_LINKED,
                source_intake_run_id=source_intake_run_id,
                ingestion_run_id=ingestion_run_id,
                asset_sha256=hashed.sha256,
            )

    successful_duplicates = (
        ctx.duplicate_provenance_result.successful_duplicates
        if ctx.duplicate_provenance_result is not None
        else []
    )
    for item in successful_duplicates:
        resource = by_path.get(_path_key(item.duplicate.record.original_source_path, staging_root))
        if resource is not None:
            _mark_resource(
                resource,
                status=STATUS_RESOURCE_INTAKE_DUPLICATE_LINKED,
                source_intake_run_id=source_intake_run_id,
                ingestion_run_id=ingestion_run_id,
                asset_sha256=item.duplicate.sha256,
            )

    failure_by_path: dict[str, str] = {}
    for item in ctx.stage_result.failures if ctx.stage_result else []:
        failure_by_path[_path_key(item.source_record.full_path, staging_root)] = item.reason
    for item in ctx.filter_result.rejected if ctx.filter_result else []:
        failure_by_path[_path_key(item.record.original_source_path, staging_root)] = item.reason
    for item in ctx.hash_result.errors if ctx.hash_result else []:
        failure_by_path[_path_key(item.record.original_source_path, staging_root)] = item.reason
    for item in ctx.storage_result.failed_files if ctx.storage_result else []:
        failure_by_path[_path_key(item.hashed_file.record.original_source_path, staging_root)] = item.reason
    for item in ctx.persistence_result.failed_inserts if ctx.persistence_result else []:
        failure_by_path[_path_key(item.copied_file.hashed_file.record.original_source_path, staging_root)] = item.reason
    if ctx.duplicate_provenance_result is not None:
        for item, reason in ctx.duplicate_provenance_result.failed_duplicates:
            failure_by_path[_path_key(item.duplicate.record.original_source_path, staging_root)] = reason

    for key, reason in failure_by_path.items():
        resource = by_path.get(key)
        if resource is not None:
            _mark_resource(
                resource,
                status=STATUS_RESOURCE_INTAKE_FAILED,
                source_intake_run_id=source_intake_run_id,
                ingestion_run_id=ingestion_run_id,
                asset_sha256=None,
                error=reason[:255],
            )

    for resource in by_path.values():
        if resource.source_intake_status in RESOURCE_SUCCESS_STATUSES or resource.source_intake_status == STATUS_RESOURCE_INTAKE_FAILED:
            continue
        if resource.status in RESOURCE_SUCCESS_STATUSES:
            continue
        if resource.status != STATUS_RESOURCE_PUBLISHED:
            continue
        rows = _resource_provenance_rows(db_session, source_id=source.id, relative_path=resource.relative_path)
        hashes = {(row.asset_sha256 or "").strip().lower() for row in rows if (row.asset_sha256 or "").strip()}
        if resource.local_sha256 and resource.local_sha256.lower() in hashes:
            _mark_resource(
                resource,
                status=STATUS_RESOURCE_INTAKE_PROCESSED,
                source_intake_run_id=source_intake_run_id,
                ingestion_run_id=ingestion_run_id,
                asset_sha256=resource.local_sha256.lower(),
            )
        else:
            _mark_resource(
                resource,
                status=STATUS_RESOURCE_INTAKE_FAILED,
                source_intake_run_id=source_intake_run_id,
                ingestion_run_id=ingestion_run_id,
                asset_sha256=None,
                error="source_intake_evidence_missing",
            )


def _update_item_statuses(batch: IcloudAcquisitionBatch) -> None:
    for item in batch.items:
        resource_statuses = {resource.source_intake_status or resource.status for resource in item.resources}
        if resource_statuses and resource_statuses.issubset(RESOURCE_SUCCESS_STATUSES):
            item.status = STATUS_ITEM_INTAKE_COMPLETED
            item.source_intake_status = STATUS_ITEM_INTAKE_COMPLETED
            item.source_intake_error = None
        elif any(status in resource_statuses for status in {STATUS_RESOURCE_INTAKE_FAILED, STATUS_RESOURCE_MISSING_BEFORE_INTAKE, STATUS_RESOURCE_SHA_MISMATCH_BEFORE_INTAKE}):
            item.status = STATUS_ITEM_INTAKE_COMPLETED_WITH_ERRORS
            item.source_intake_status = STATUS_ITEM_INTAKE_COMPLETED_WITH_ERRORS
            item.source_intake_error = "one_or_more_resources_failed"
        else:
            item.status = STATUS_ITEM_INTAKE_BLOCKED
            item.source_intake_status = STATUS_ITEM_INTAKE_BLOCKED
            item.source_intake_error = "not_all_resources_processed"
        item.source_intake_completed_at = _utc_now()


def _batch_counts(batch: IcloudAcquisitionBatch) -> dict[str, int]:
    resources = [resource for item in batch.items for resource in item.resources]
    return {
        "processed": sum(1 for resource in resources if resource.source_intake_status == STATUS_RESOURCE_INTAKE_PROCESSED),
        "duplicate": sum(1 for resource in resources if resource.source_intake_status == STATUS_RESOURCE_INTAKE_DUPLICATE_LINKED),
        "skipped_known": sum(1 for resource in resources if resource.source_intake_status == STATUS_RESOURCE_INTAKE_SKIPPED_KNOWN),
        "failed": sum(1 for resource in resources if resource.source_intake_status == STATUS_RESOURCE_INTAKE_FAILED),
        "deferred": sum(1 for resource in resources if resource.source_intake_status == STATUS_RESOURCE_INTAKE_DEFERRED),
        "missing": sum(1 for resource in resources if resource.source_intake_status == STATUS_RESOURCE_MISSING_BEFORE_INTAKE),
        "sha_mismatch": sum(1 for resource in resources if resource.source_intake_status == STATUS_RESOURCE_SHA_MISMATCH_BEFORE_INTAKE),
    }


def _resource_samples(batch: IcloudAcquisitionBatch) -> list[dict[str, Any]]:
    return [
        {
            "resource_id": resource.id,
            "item_id": resource.item_id,
            "relative_path": resource.relative_path,
            "status": resource.source_intake_status or resource.status,
            "asset_sha256": resource.asset_sha256,
            "error": resource.source_intake_error,
        }
        for item in batch.items
        for resource in item.resources
    ]


def _result_from_batch(
    *,
    batch: IcloudAcquisitionBatch,
    run: IcloudAcquisitionRun | None,
    source_profile_id: int | None,
    source_intake_run_id: int | None,
    ingestion_run_id: int | None,
    status: str,
    stop_reason: str | None,
    next_safe_action: str | None,
    report_path: str | None,
    resources_ready_for_intake: int,
) -> BatchSourceIntakeResult:
    counts = _batch_counts(batch)
    return BatchSourceIntakeResult(
        status=status,
        stop_reason=stop_reason,
        next_safe_action=next_safe_action,
        acquisition_run_id=run.id if run is not None else None,
        acquisition_batch_id=batch.id,
        source_profile_id=source_profile_id,
        source_intake_run_id=source_intake_run_id,
        ingestion_run_id=ingestion_run_id,
        resources_ready_for_intake=resources_ready_for_intake,
        resources_processed=counts["processed"],
        resources_duplicate_linked=counts["duplicate"],
        resources_skipped_known=counts["skipped_known"],
        resources_failed=counts["failed"],
        resources_deferred=counts["deferred"],
        missing_files=counts["missing"],
        sha_mismatches=counts["sha_mismatch"],
        batch_ready_for_cleanup_dry_run=bool(batch.ready_for_cleanup_dry_run),
        report_path=report_path,
    )


def _apply_batch_final_status(
    batch: IcloudAcquisitionBatch,
    *,
    final_status: str,
    failure_reason: str | None,
    next_safe_action: str | None,
    ready_for_cleanup: bool,
    source_intake_report_path: str | None,
) -> None:
    counts = _batch_counts(batch)
    batch.status = final_status
    batch.failure_reason = failure_reason
    batch.next_safe_action = next_safe_action
    batch.intake_processed_resource_count = counts["processed"]
    batch.intake_duplicate_resource_count = counts["duplicate"]
    batch.intake_skipped_known_resource_count = counts["skipped_known"]
    batch.intake_failed_resource_count = counts["failed"] + counts["missing"] + counts["sha_mismatch"]
    batch.intake_deferred_resource_count = counts["deferred"]
    batch.ready_for_cleanup_dry_run = ready_for_cleanup
    batch.cleanup_readiness_reason = "source_intake_verified" if ready_for_cleanup else failure_reason
    batch.source_intake_report_path = source_intake_report_path
    batch.intake_finished_at = _utc_now()
    _update_item_statuses(batch)


def _blocked_result(
    db_session: Session,
    *,
    batch: IcloudAcquisitionBatch,
    run: IcloudAcquisitionRun | None,
    source_profile_id: int | None,
    reason: str,
    next_safe_action: str | None,
    resources_ready_for_intake: int = 0,
) -> BatchSourceIntakeResult:
    _apply_batch_final_status(
        batch,
        final_status=STATUS_BATCH_INTAKE_BLOCKED,
        failure_reason=reason,
        next_safe_action=next_safe_action,
        ready_for_cleanup=False,
        source_intake_report_path=batch.source_intake_report_path,
    )
    preliminary = _result_from_batch(
        batch=batch,
        run=run,
        source_profile_id=source_profile_id,
        source_intake_run_id=batch.source_intake_run_id,
        ingestion_run_id=None,
        status=STATUS_BATCH_INTAKE_BLOCKED,
        stop_reason=reason,
        next_safe_action=next_safe_action,
        report_path=None,
        resources_ready_for_intake=resources_ready_for_intake,
    )
    report_path = _write_batch_report(
        batch=batch,
        run=run,
        result=preliminary,
        resource_samples=_resource_samples(batch),
        source_intake_report_path=batch.source_intake_report_path,
    )
    batch.source_intake_report_path = report_path
    db_session.commit()
    return _result_from_batch(
        batch=batch,
        run=run,
        source_profile_id=source_profile_id,
        source_intake_run_id=batch.source_intake_run_id,
        ingestion_run_id=None,
        status=STATUS_BATCH_INTAKE_BLOCKED,
        stop_reason=reason,
        next_safe_action=next_safe_action,
        report_path=report_path,
        resources_ready_for_intake=resources_ready_for_intake,
    )


def run_batch_source_intake(
    db_session: Session,
    *,
    batch_id: int,
    source_id: int | None = None,
    created_by: str = "internal_script",
) -> BatchSourceIntakeResult:
    """Run Source Intake for exactly one durable iCloud acquisition batch."""

    ensure_icloud_acquisition_schema(db_session)
    ensure_source_intake_schema(db_session)

    batch, run, source, staging_root = _load_batch_context(db_session, batch_id=batch_id, source_id=source_id)

    guardrail = get_ingestion_operation_guardrail_snapshot(db_session, source_id=source.id)
    if guardrail.blocked:
        return _blocked_result(
            db_session,
            batch=batch,
            run=run,
            source_profile_id=source.id,
            reason=(guardrail.blocking_reasons[0].code.lower() if guardrail.blocking_reasons else "operation_active"),
            next_safe_action=NEXT_WAIT_FOR_ACTIVE_OPERATION,
        )

    drop_zone = resolve_runtime_path(settings.drop_zone_path)
    if drop_zone.exists() and any(drop_zone.iterdir()):
        return _blocked_result(
            db_session,
            batch=batch,
            run=run,
            source_profile_id=source.id,
            reason="drop_zone_not_empty",
            next_safe_action=NEXT_CLEAR_DROP_ZONE,
        )

    try:
        verified_resources, skipped_known = _verified_resources_for_intake(
            db_session,
            batch=batch,
            source=source,
            staging_root=staging_root,
        )
    except BatchSourceIntakeError as exc:
        return _blocked_result(
            db_session,
            batch=batch,
            run=run,
            source_profile_id=source.id,
            reason=exc.code,
            next_safe_action=exc.next_safe_action,
        )

    if not verified_resources:
        _apply_batch_final_status(
            batch,
            final_status=STATUS_BATCH_READY_FOR_CLEANUP_DRY_RUN,
            failure_reason=None,
            next_safe_action=NEXT_RUN_CLEANUP_DRY_RUN,
            ready_for_cleanup=True,
            source_intake_report_path=batch.source_intake_report_path,
        )
        preliminary = _result_from_batch(
            batch=batch,
            run=run,
            source_profile_id=source.id,
            source_intake_run_id=batch.source_intake_run_id,
            ingestion_run_id=None,
            status=STATUS_BATCH_INTAKE_COMPLETED,
            stop_reason="already_processed",
            next_safe_action=NEXT_RUN_CLEANUP_DRY_RUN,
            report_path=None,
            resources_ready_for_intake=skipped_known,
        )
        report_path = _write_batch_report(
            batch=batch,
            run=run,
            result=preliminary,
            resource_samples=_resource_samples(batch),
            source_intake_report_path=batch.source_intake_report_path,
        )
        batch.source_intake_report_path = report_path
        db_session.commit()
        return _result_from_batch(
            batch=batch,
            run=run,
            source_profile_id=source.id,
            source_intake_run_id=batch.source_intake_run_id,
            ingestion_run_id=None,
            status=STATUS_BATCH_INTAKE_COMPLETED,
            stop_reason="already_processed",
            next_safe_action=NEXT_RUN_CLEANUP_DRY_RUN,
            report_path=report_path,
            resources_ready_for_intake=skipped_known,
        )

    source_intake_run = SourceIntakeRun(
        status=SOURCE_INTAKE_STATUS_RUNNING,
        ingestion_source_id=source.id,
        ingestion_run_id=None,
        source_label=source.source_label,
        source_type=source.source_type,
        source_root_path=str(staging_root),
        intake_mode=INTAKE_MODE_ICLOUD_ACQUISITION_BATCH,
        icloud_acquisition_batch_id=batch.id,
        source_intake_limit=None,
        ingest_batch_size=max(1, len(verified_resources)),
        started_at=_utc_now(),
        created_by=created_by,
    )
    db_session.add(source_intake_run)
    db_session.flush()
    batch.status = STATUS_BATCH_INTAKE_RUNNING
    batch.source_intake_run_id = source_intake_run.id
    batch.intake_started_at = _utc_now()
    batch.ready_for_cleanup_dry_run = False
    batch.cleanup_readiness_reason = None
    db_session.commit()

    started_at = time.perf_counter()
    final_status = SOURCE_INTAKE_STATUS_FAILED
    error_message: str | None = None
    ctx = PipelineContext(
        from_path=staging_root,
        drop_zone_path=resolve_runtime_path(settings.drop_zone_path),
        vault_path=resolve_runtime_path(settings.vault_path),
        quarantine_path=resolve_runtime_path(settings.quarantine_path),
        ingest_failures_path=resolve_runtime_path(settings.ingest_failures_path),
        ingest_batch_size=max(1, len(verified_resources)),
        ingest_source_limit=None,
        source_label=source.source_label,
        source_type=source.source_type,
        explicit_source_records=[item.file_record for item in verified_resources],
        source_intake_context={
            "mode": INTAKE_MODE_ICLOUD_ACQUISITION_BATCH,
            "acquisition_run_id": run.id,
            "acquisition_batch_id": batch.id,
            "source_profile_id": source.id,
            "resource_count": len(verified_resources),
        },
    )
    args = RuntimeArgs(
        from_path=ctx.from_path,
        source_label=source.source_label,
        source_type=source.source_type,
        dry_run=False,
        ingest_batch_size=ctx.ingest_batch_size,
        ingest_source_limit=None,
        skip_exif_extraction=False,
        skip_metadata_normalization=False,
        skip_duplicate_lineage=True,
        skip_face_processing=True,
        skip_crop_generation=True,
        skip_event_clustering=False,
        run_face_detection_rebuild=False,
        run_face_clustering_rebuild=False,
    )

    outcomes = _run_pipeline(ctx, args)
    failed = next((item for item in outcomes if item.status == "failed"), None)
    elapsed = time.perf_counter() - started_at
    if failed is not None:
        error_message = f"Stage failed: {failed.key}"
    else:
        final_status = SOURCE_INTAKE_STATUS_COMPLETED

    source_intake_run = db_session.get(SourceIntakeRun, source_intake_run.id)
    if source_intake_run is None:
        raise BatchSourceIntakeError("source_intake_run_missing", "Source Intake run row disappeared.")
    source_intake_run.status = final_status
    source_intake_run.finished_at = _utc_now()
    source_intake_run.elapsed_seconds = elapsed
    source_intake_run.files_scanned = ctx.source_files_scanned_total
    source_intake_run.skipped_known = ctx.source_files_skipped_known + skipped_known
    source_intake_run.selected = ctx.source_files_selected
    source_intake_run.staged = ctx.source_files_selected
    source_intake_run.processed_new_unique = ctx.total_new_unique_ingested
    source_intake_run.failed_or_rejected = len(ctx.moved_to_ingest_failures)
    source_intake_run.remaining_unknown = ctx.source_files_remaining_unknown
    source_intake_run.error_message = error_message
    if ctx.source_intake_report_path is not None:
        source_intake_run.report_path = str(ctx.source_intake_report_path)
    if ctx.resolved_ingestion_context is not None:
        source_intake_run.ingestion_run_id = ctx.resolved_ingestion_context.ingestion_run_id

    _update_resources_from_pipeline(
        db_session=db_session,
        batch=batch,
        source=source,
        staging_root=staging_root,
        source_intake_run_id=source_intake_run.id,
        ingestion_run_id=source_intake_run.ingestion_run_id,
        ctx=ctx,
    )

    counts = _batch_counts(batch)
    failure_count = counts["failed"] + counts["missing"] + counts["sha_mismatch"] + counts["deferred"]
    ready_for_cleanup = final_status == SOURCE_INTAKE_STATUS_COMPLETED and failure_count == 0
    batch_status = (
        STATUS_BATCH_READY_FOR_CLEANUP_DRY_RUN
        if ready_for_cleanup
        else STATUS_BATCH_INTAKE_COMPLETED_WITH_ERRORS
        if final_status == SOURCE_INTAKE_STATUS_COMPLETED
        else STATUS_BATCH_INTAKE_FAILED
    )
    stop_reason = None if ready_for_cleanup else error_message or "resource_intake_errors"
    next_safe_action = NEXT_RUN_CLEANUP_DRY_RUN if ready_for_cleanup else NEXT_RETRY_SOURCE_INTAKE

    _apply_batch_final_status(
        batch,
        final_status=batch_status,
        failure_reason=stop_reason,
        next_safe_action=next_safe_action,
        ready_for_cleanup=ready_for_cleanup,
        source_intake_report_path=source_intake_run.report_path,
    )
    db_session.flush()

    preliminary = _result_from_batch(
        batch=batch,
        run=run,
        source_profile_id=source.id,
        source_intake_run_id=source_intake_run.id,
        ingestion_run_id=source_intake_run.ingestion_run_id,
        status=STATUS_BATCH_INTAKE_COMPLETED if ready_for_cleanup else batch_status,
        stop_reason=stop_reason,
        next_safe_action=next_safe_action,
        report_path=None,
        resources_ready_for_intake=len(verified_resources) + skipped_known,
    )
    batch_report_path = _write_batch_report(
        batch=batch,
        run=run,
        result=preliminary,
        resource_samples=_resource_samples(batch),
        source_intake_report_path=source_intake_run.report_path,
    )
    batch.source_intake_report_path = batch_report_path
    source_intake_run.report_path = batch_report_path
    db_session.commit()

    return _result_from_batch(
        batch=batch,
        run=run,
        source_profile_id=source.id,
        source_intake_run_id=source_intake_run.id,
        ingestion_run_id=source_intake_run.ingestion_run_id,
        status=STATUS_BATCH_INTAKE_COMPLETED if ready_for_cleanup else batch_status,
        stop_reason=stop_reason,
        next_safe_action=next_safe_action,
        report_path=batch_report_path,
        resources_ready_for_intake=len(verified_resources) + skipped_known,
    )
