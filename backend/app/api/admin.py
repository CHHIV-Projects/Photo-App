"""API routes for Admin summary and foundation views."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.models.ingestion_source import IngestionSource
from app.schemas.admin import (
    AdminSummaryResponse,
    DuplicateProcessingActionResponse,
    DuplicateProcessingRunStatus,
    DuplicateProcessingStatusResponse,
    FaceProcessingActionResponse,
    FaceProcessingRunStatus,
    FaceProcessingStatusResponse,
    HeicPreviewActionResponse,
    HeicPreviewRunStatus,
    HeicPreviewStatusResponse,
    LivePhotoPairingActionResponse,
    LivePhotoPairingRunStatus,
    LivePhotoPairingStatusResponse,
    PlaceGeocodingActionResponse,
    PlaceGeocodingRunStatus,
    PlaceGeocodingStatusResponse,
    SourceIntakeReportDetail,
    SourceIntakeReportsResponse,
    SourceIntakeSourcesResponse,
    SourceCreateRequest,
    SourceCreateResponse,
    SourceIntakeRunRequest,
    SourceIntakeRunResponse,
    SourceIntakeStatusSchema,
    SourceIntakeStopResponse,
    SourceProfileCreateRequest,
    SourceProfileCreateResponse,
    SourceProfileDetail,
    SourceProfilePathCheckResponse,
    SourceProfileMetadataUpdateRequest,
    SourceProfileStagingFolderCreateResponse,
    SourceProfileStatusUpdateRequest,
    SourceProfileSummary,
    SourceProfilesResponse,
    IcloudReadinessReason,
    IcloudSourceReadinessResponse,
    IcloudAcquisitionRunRequest,
    IcloudAcquisitionRunResponse,
    IcloudAcquisitionRunStatus,
    IcloudAcquisitionStatusResponse,
    IcloudAcquisitionStopResponse,
    IcloudStagingCleanupRunRequest,
    IcloudStagingCleanupExecuteRequest,
    IcloudStagingCleanupEligibleFile,
    IcloudStagingCleanupRunResponse,
    IcloudStagingCleanupRunStatus,
    IcloudStagingCleanupStatusResponse,
    IcloudStagingCleanupReadinessResponse,
    IcloudBackfillAcquireRequest,
    IcloudBackfillAcquireResponse,
    IcloudBackfillAcquirePreviewRequest,
    IcloudBackfillAcquirePreviewResponse,
    IcloudBackfillInventoryScanRequest,
    IcloudBackfillInventoryScanResponse,
    IcloudBackfillInventoryStatus,
    IcloudBackfillStatusResponse,
    IcloudHistoricalRoutineChunk,
    IcloudHistoricalRoutineRefreshRequest,
    IcloudHistoricalRoutineRefreshResponse,
    IcloudHistoricalRoutineRunRequest,
    IcloudHistoricalRoutineRunResponse,
    IcloudHistoricalRoutineStatus,
    IcloudHistoricalRoutineStatusResponse,
    IcloudIntakeImportAdvanceRequest,
    IcloudIntakeImportChunkStatus,
    IcloudIntakeImportResumeRequest,
    IcloudIntakeImportStartRequest,
    IcloudIntakeImportStatus,
    IcloudIntakeImportStatusResponse,
    SourceProfileDeferredAssetItem,
    SourceProfileDeferredAssetsResponse,
    InternalIcloudRunRequest,
    InternalIcloudRunResponse,
    InternalIcloudRunStatusResponse,
)
from app.services.admin import (
    build_admin_summary,
    create_source_profile,
    create_source_profile_staging_folder,
    create_or_get_ingestion_source,
    get_source_profile_detail,
    get_report_detail,
    list_source_profiles,
    get_source_intake_status,
    list_recent_reports,
    list_sources_with_latest_info,
    request_source_intake_stop,
    start_source_intake,
    update_source_profile_metadata,
    update_source_profile_status,
    verify_source_profile_path,
    get_icloud_source_readiness,
    start_internal_single_flow_run,
    get_internal_single_flow_run_status,
)
from app.services.ingestion.ingestion_context_service import normalize_source_label
from app.services.admin.source_intake_execution_service import (
    SourceIntakeAlreadyRunningError,
    SourceIntakeReadinessBlockedError,
)
from app.services.duplicates.processing_service import (
    DuplicateProcessingAlreadyRunningError,
    DuplicateProcessingStatusSnapshot,
    get_duplicate_processing_status,
    request_duplicate_processing_stop,
    start_duplicate_processing_background,
)
from app.services.location.place_geocoding_service import (
    PlaceGeocodingAlreadyRunningError,
    PlaceGeocodingStatusSnapshot,
    get_place_geocoding_status,
    request_place_geocoding_stop,
    start_place_geocoding_background,
)
from app.services.face.face_processing_service import (
    FaceProcessingAlreadyRunningError,
    FaceProcessingStatusSnapshot,
    get_face_processing_status,
    request_face_processing_stop,
    start_face_processing_background,
)
from app.services.live_photo.pairing_admin_service import (
    LivePhotoPairingStatusSnapshot,
    get_live_photo_pairing_status,
    run_live_photo_pairing_admin,
)
from app.services.icloud_acquisition.execution_service import (
    IcloudAcquisitionAlreadyRunningError,
    IcloudAcquisitionLaunchError,
    IcloudAcquisitionSourceNotRegisteredError,
    IcloudAcquisitionStatusSnapshot,
    IcloudAcquisitionStatusView,
    get_icloud_acquisition_status,
    request_icloud_acquisition_stop,
    start_icloud_acquisition_background,
)
from app.services.icloud_acquisition.exact_selection_adapter import ExactSelectionPrototypeError
from app.services.icloud_acquisition.exact_selection_protocol import ExactSelectionProtocolError
from app.services.admin.icloud_staging_cleanup_execution_service import (
    CleanupBusyError,
    CleanupAuthorizationError,
    CleanupRunSnapshot,
    CleanupValidationError,
    SourceIntakeActiveError,
    get_cleanup_status,
    get_latest_cleanup_dry_run,
    get_cleanup_source_readiness,
    start_cleanup_execution,
    start_cleanup_run,
)
from app.services.icloud_backfill_inventory_service import (
    IcloudBackfillStateNotFound,
    IcloudBackfillStatusSnapshot,
    IcloudBackfillValidationError,
    IcloudInventoryScanResult,
    get_icloud_backfill_status,
    run_icloud_backfill_inventory_scan as run_icloud_backfill_inventory_scan_service,
)
from app.services.icloud_backfill_acquisition_preview_service import (
    IcloudBackfillAcquisitionPreviewResult,
    preview_icloud_backfill_acquisition as preview_icloud_backfill_acquisition_service,
)
from app.services.icloud_backfill_acquisition_execution_service import (
    IcloudBackfillAcquireResult,
    run_icloud_backfill_acquisition as run_icloud_backfill_acquisition_service,
)
from app.services.icloud_historical_routine_service import (
    IcloudHistoricalRoutineError,
    advance_icloud_intake_import as advance_icloud_intake_import_service,
    get_icloud_intake_import_status as get_icloud_intake_import_status_service,
    get_historical_routine_status as get_historical_routine_status_service,
    refresh_historical_inventory as refresh_historical_inventory_service,
    resume_icloud_intake_import as resume_icloud_intake_import_service,
    run_next_historical_batch as run_next_historical_batch_service,
    start_icloud_intake_import as start_icloud_intake_import_service,
)
from app.services.source_profile_deferred_asset_service import (
    DeferredAssetListItem,
    list_deferred_assets,
)
from app.services.source_identity import (
    SourceEndpointEnrollmentConfirmRequest,
    SourceEndpointEnrollmentConfirmResponse,
    SourceEndpointEnrollmentPlanRequest,
    SourceEndpointEnrollmentPlanResponse,
    SourceEndpointEnrollmentService,
    SourceProfileReadinessResponse,
    SourceProfileReadinessService,
    SourceIdentityCapabilitiesResponse,
    SourceIdentityProbeRequest,
    SourceIdentityProbeResponse,
    SourceIdentityProbeService,
)
from app.services.admin.ingestion_operation_guardrail_service import (
    IngestionOperationGuardrailSnapshot,
    get_ingestion_operation_guardrail_snapshot,
    protected_ingestion_operation_start,
)
from app.services.previews.heic_preview_processing_service import (
    HeicPreviewAlreadyRunningError,
    HeicPreviewStatusSnapshot,
    get_heic_preview_status,
    request_heic_preview_stop,
    start_heic_preview_background,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


def get_source_identity_probe_service() -> SourceIdentityProbeService:
    """Return a read-only source identity probe service."""
    return SourceIdentityProbeService()


def get_source_endpoint_enrollment_service(db: Session) -> SourceEndpointEnrollmentService:
    """Return a stateless source endpoint enrollment service."""
    return SourceEndpointEnrollmentService(
        db_session=db,
        probe_service=get_source_identity_probe_service(),
    )


def get_source_profile_readiness_service(db: Session) -> SourceProfileReadinessService:
    """Return a read-only Source Profile readiness service."""
    return SourceProfileReadinessService(
        db_session=db,
        probe_service=get_source_identity_probe_service(),
    )


def _to_run_status(snapshot: DuplicateProcessingStatusSnapshot) -> DuplicateProcessingRunStatus:
    return DuplicateProcessingRunStatus(
        run_id=snapshot.run_id,
        status=snapshot.status,
        started_at=snapshot.started_at,
        finished_at=snapshot.finished_at,
        elapsed_seconds=snapshot.elapsed_seconds,
        total_items=snapshot.total_items,
        processed_items=snapshot.processed_items,
        current_stage=snapshot.current_stage,
        error_message=snapshot.error_message,
        stop_requested=snapshot.stop_requested,
        workset_cutoff=snapshot.workset_cutoff,
        last_successful_cutoff=snapshot.last_successful_cutoff,
    )


def _to_place_geocoding_run_status(snapshot: PlaceGeocodingStatusSnapshot) -> PlaceGeocodingRunStatus:
    return PlaceGeocodingRunStatus(
        run_id=snapshot.run_id,
        status=snapshot.status,
        started_at=snapshot.started_at,
        finished_at=snapshot.finished_at,
        elapsed_seconds=snapshot.elapsed_seconds,
        total_places=snapshot.total_places,
        processed_places=snapshot.processed_places,
        succeeded_places=snapshot.succeeded_places,
        failed_places=snapshot.failed_places,
        current_place_id=snapshot.current_place_id,
        last_error=snapshot.last_error,
        last_run_summary=snapshot.last_run_summary,
        stop_requested=snapshot.stop_requested,
    )


@router.get("/summary", response_model=AdminSummaryResponse)
def get_admin_summary(db: Session = Depends(get_db_session)) -> AdminSummaryResponse:
    """Return read-only system-level counts for Admin workspace cards."""
    return build_admin_summary(db)


@router.get("/duplicate-processing/status", response_model=DuplicateProcessingStatusResponse)
def get_duplicate_processing_run_status(db: Session = Depends(get_db_session)) -> DuplicateProcessingStatusResponse:
    """Return duplicate processing status and pending-work estimate."""
    status_view = get_duplicate_processing_status(db)
    return DuplicateProcessingStatusResponse(
        generated_at=status_view.generated_at,
        pending_items=status_view.pending_items,
        current=_to_run_status(status_view.current),
    )


@router.post("/duplicate-processing/run", response_model=DuplicateProcessingActionResponse)
def run_duplicate_processing() -> DuplicateProcessingActionResponse | JSONResponse:
    """Start duplicate processing in the background when no active run exists."""
    try:
        result = start_duplicate_processing_background(created_by="admin_api")
    except DuplicateProcessingAlreadyRunningError as exc:
        payload = DuplicateProcessingActionResponse(
            accepted=False,
            message="A duplicate-processing run is already active.",
            status=_to_run_status(exc.status),
        )
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=payload.model_dump(mode="json"))

    accepted = result.status.status in {"running", "stop_requested"}
    payload = DuplicateProcessingActionResponse(
        accepted=accepted,
        message=result.message,
        status=_to_run_status(result.status),
    )
    if not accepted:
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=payload.model_dump(mode="json"))
    return payload


@router.post("/duplicate-processing/stop", response_model=DuplicateProcessingActionResponse)
def stop_duplicate_processing(db: Session = Depends(get_db_session)) -> DuplicateProcessingActionResponse:
    """Request graceful stop for the currently active duplicate processing run."""
    result = request_duplicate_processing_stop(db)
    accepted = result.status.status in {"stop_requested", "running"}
    return DuplicateProcessingActionResponse(
        accepted=accepted,
        message=result.message,
        status=_to_run_status(result.status),
    )


@router.get("/place-geocoding/status", response_model=PlaceGeocodingStatusResponse)
def get_place_geocoding_run_status(db: Session = Depends(get_db_session)) -> PlaceGeocodingStatusResponse:
    """Return place geocoding status and pending-work estimate."""
    status_view = get_place_geocoding_status(db)
    return PlaceGeocodingStatusResponse(
        generated_at=status_view.generated_at,
        pending_places=status_view.pending_places,
        current=_to_place_geocoding_run_status(status_view.current),
    )


@router.post("/place-geocoding/run", response_model=PlaceGeocodingActionResponse)
def run_place_geocoding() -> PlaceGeocodingActionResponse | JSONResponse:
    """Start place geocoding in the background when no active run exists."""
    try:
        result = start_place_geocoding_background(created_by="admin_api")
    except PlaceGeocodingAlreadyRunningError as exc:
        payload = PlaceGeocodingActionResponse(
            accepted=False,
            message="A place geocoding run is already active.",
            status=_to_place_geocoding_run_status(exc.status),
        )
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=payload.model_dump(mode="json"))

    accepted = result.status.status in {"running", "stop_requested"}
    payload = PlaceGeocodingActionResponse(
        accepted=accepted,
        message=result.message,
        status=_to_place_geocoding_run_status(result.status),
    )
    if not accepted:
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=payload.model_dump(mode="json"))
    return payload


@router.post("/place-geocoding/stop", response_model=PlaceGeocodingActionResponse)
def stop_place_geocoding(db: Session = Depends(get_db_session)) -> PlaceGeocodingActionResponse:
    """Request graceful stop for the currently active place geocoding run."""
    result = request_place_geocoding_stop(db)
    accepted = result.status.status in {"stop_requested", "running"}
    return PlaceGeocodingActionResponse(
        accepted=accepted,
        message=result.message,
        status=_to_place_geocoding_run_status(result.status),
    )


def _to_face_processing_run_status(snapshot: FaceProcessingStatusSnapshot) -> FaceProcessingRunStatus:
    return FaceProcessingRunStatus(
        run_id=snapshot.run_id,
        status=snapshot.status,
        started_at=snapshot.started_at,
        finished_at=snapshot.finished_at,
        elapsed_seconds=snapshot.elapsed_seconds,
        assets_pending_detection=snapshot.assets_pending_detection,
        assets_processed_detection=snapshot.assets_processed_detection,
        faces_pending_embedding=snapshot.faces_pending_embedding,
        faces_processed_embedding=snapshot.faces_processed_embedding,
        faces_pending_clustering=snapshot.faces_pending_clustering,
        faces_processed_clustering=snapshot.faces_processed_clustering,
        crops_pending=snapshot.crops_pending,
        crops_generated=snapshot.crops_generated,
        current_stage=snapshot.current_stage,
        last_error=snapshot.last_error,
        last_run_summary=snapshot.last_run_summary,
        stop_requested=snapshot.stop_requested,
    )


@router.get("/face-processing/status", response_model=FaceProcessingStatusResponse)
def get_face_processing_run_status(db: Session = Depends(get_db_session)) -> FaceProcessingStatusResponse:
    """Return face processing status and pending-work counts."""
    status_view = get_face_processing_status(db)
    return FaceProcessingStatusResponse(
        generated_at=status_view.generated_at,
        pending_detection=status_view.pending_detection,
        pending_embedding=status_view.pending_embedding,
        pending_clustering=status_view.pending_clustering,
        pending_crops=status_view.pending_crops,
        current=_to_face_processing_run_status(status_view.current),
    )


@router.post("/face-processing/run", response_model=FaceProcessingActionResponse)
def run_face_processing() -> FaceProcessingActionResponse | JSONResponse:
    """Start face processing in the background when no active run exists."""
    try:
        result = start_face_processing_background(created_by="admin_api")
    except FaceProcessingAlreadyRunningError as exc:
        payload = FaceProcessingActionResponse(
            accepted=False,
            message="A face processing run is already active.",
            status=_to_face_processing_run_status(exc.status),
        )
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=payload.model_dump(mode="json"))

    accepted = result.status.status in {"running", "stop_requested"}
    payload = FaceProcessingActionResponse(
        accepted=accepted,
        message=result.message,
        status=_to_face_processing_run_status(result.status),
    )
    if not accepted:
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=payload.model_dump(mode="json"))
    return payload


@router.post("/face-processing/stop", response_model=FaceProcessingActionResponse)
def stop_face_processing(db: Session = Depends(get_db_session)) -> FaceProcessingActionResponse:
    """Request graceful stop for the currently active face processing run."""
    result = request_face_processing_stop(db)
    accepted = result.status.status in {"stop_requested", "running"}
    return FaceProcessingActionResponse(
        accepted=accepted,
        message=result.message,
        status=_to_face_processing_run_status(result.status),
    )


def _to_heic_preview_run_status(snapshot: HeicPreviewStatusSnapshot) -> HeicPreviewRunStatus:
    return HeicPreviewRunStatus(
        run_id=snapshot.run_id,
        status=snapshot.status,
        started_at=snapshot.started_at,
        finished_at=snapshot.finished_at,
        elapsed_seconds=snapshot.elapsed_seconds,
        assets_pending=snapshot.assets_pending,
        assets_processed=snapshot.assets_processed,
        assets_succeeded=snapshot.assets_succeeded,
        assets_failed=snapshot.assets_failed,
        last_error=snapshot.last_error,
        last_run_summary=snapshot.last_run_summary,
        stop_requested=snapshot.stop_requested,
    )


def _to_live_photo_pairing_run_status(snapshot: LivePhotoPairingStatusSnapshot) -> LivePhotoPairingRunStatus:
    return LivePhotoPairingRunStatus(
        status=snapshot.status,
        started_at=snapshot.started_at,
        finished_at=snapshot.finished_at,
        elapsed_seconds=snapshot.elapsed_seconds,
        scanned_rows=snapshot.scanned_rows,
        candidate_groups=snapshot.candidate_groups,
        pairs_created=snapshot.pairs_created,
        already_paired=snapshot.already_paired,
        updated=snapshot.updated,
        removed_stale=snapshot.removed_stale,
        skipped_missing_source=snapshot.skipped_missing_source,
        skipped_ambiguous=snapshot.skipped_ambiguous,
        skipped_suspicious_delta=snapshot.skipped_suspicious_delta,
        last_report_path=snapshot.last_report_path,
        last_error=snapshot.last_error,
    )


def _to_icloud_acquisition_run_status(snapshot: IcloudAcquisitionStatusSnapshot) -> IcloudAcquisitionRunStatus:
    return IcloudAcquisitionRunStatus(
        run_id=snapshot.run_id,
        status=snapshot.status,
        source_label=snapshot.source_label,
        source_type=snapshot.source_type,
        source_root_path=snapshot.source_root_path,
        acquisition_mode=snapshot.acquisition_mode,
        source_registration_status=snapshot.source_registration_status,
        username=snapshot.username,
        staging_path=snapshot.staging_path,
        recent_count=snapshot.recent_count,
        resolved_executable=snapshot.resolved_executable,
        icloudpd_version=snapshot.icloudpd_version,
        started_at=snapshot.started_at,
        completed_at=snapshot.completed_at,
        elapsed_seconds=snapshot.elapsed_seconds,
        downloaded_count=snapshot.downloaded_count,
        skipped_existing_count=snapshot.skipped_existing_count,
        failed_count=snapshot.failed_count,
        stdout_tail=snapshot.stdout_tail,
        stderr_tail=snapshot.stderr_tail,
        report_path=snapshot.report_path,
        error_code=snapshot.error_code,
        error_message=snapshot.error_message,
        stop_requested=snapshot.stop_requested,
        file_inventory_count=snapshot.file_inventory_count,
        recommended_source_intake_command=snapshot.recommended_source_intake_command,
    )


def _safe_cleanup_eligible_files(report_path: str | None) -> list[IcloudStagingCleanupEligibleFile]:
    if not report_path:
        return []
    try:
        report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    rows = report.get("eligible_files")
    if not isinstance(rows, list):
        return []

    safe_rows: list[IcloudStagingCleanupEligibleFile] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        relative_path = row.get("relative_path")
        if not isinstance(relative_path, str) or not relative_path.strip():
            continue
        safe_rows.append(
            IcloudStagingCleanupEligibleFile(
                relative_path=relative_path.replace("\\", "/").lstrip("/"),
                size_bytes=row.get("size_bytes") if isinstance(row.get("size_bytes"), int) else None,
                asset_sha256=row.get("asset_sha256") if isinstance(row.get("asset_sha256"), str) else None,
                staged_sha256=row.get("staged_sha256") if isinstance(row.get("staged_sha256"), str) else None,
                verification_state="verified",
                asset_id=row.get("asset_id") if isinstance(row.get("asset_id"), int) else None,
            )
        )
    return safe_rows


def _to_icloud_cleanup_run_status(snapshot: CleanupRunSnapshot | None) -> IcloudStagingCleanupRunStatus:
    if snapshot is None:
        return IcloudStagingCleanupRunStatus(
            run_id=None,
            status="idle",
            source_id=None,
            source_label=None,
            source_root_path=None,
            dry_run=True,
            started_at=None,
            finished_at=None,
            elapsed_seconds=None,
            eligible_count=0,
            deleted_count=0,
            skipped_count=0,
            total_bytes_eligible=0,
            total_bytes_deleted=0,
            total_files=0,
            processed_files=0,
            current_stage=None,
            protected_count=0,
            verification_failed_count=0,
            file_missing_count=0,
            delete_failed_count=0,
            manifest_fingerprint=None,
            planner_version=None,
            preview_expires_at=None,
            authorized_dry_run_id=None,
            authorization_consumed_at=None,
            skipped_reasons={},
            skipped_samples={},
            eligible_files=[],
            report_path=None,
            error_message=None,
        )
    return IcloudStagingCleanupRunStatus(
        run_id=snapshot.run_id,
        status=snapshot.status,
        source_id=snapshot.source_id,
        source_label=snapshot.source_label,
        source_root_path=snapshot.source_root_path,
        dry_run=snapshot.dry_run,
        started_at=snapshot.started_at,
        finished_at=snapshot.finished_at,
        elapsed_seconds=snapshot.elapsed_seconds,
        eligible_count=snapshot.eligible_count,
        deleted_count=snapshot.deleted_count,
        skipped_count=snapshot.skipped_count,
        total_bytes_eligible=snapshot.total_bytes_eligible,
        total_bytes_deleted=snapshot.total_bytes_deleted,
        total_files=snapshot.total_files,
        processed_files=snapshot.processed_files,
        current_stage=snapshot.current_stage,
        protected_count=snapshot.protected_count,
        verification_failed_count=snapshot.verification_failed_count,
        file_missing_count=snapshot.file_missing_count,
        delete_failed_count=snapshot.delete_failed_count,
        manifest_fingerprint=snapshot.manifest_fingerprint,
        planner_version=snapshot.planner_version,
        preview_expires_at=snapshot.preview_expires_at,
        authorized_dry_run_id=snapshot.authorized_dry_run_id,
        authorization_consumed_at=snapshot.authorization_consumed_at,
        skipped_reasons=snapshot.skipped_reasons,
        skipped_samples=snapshot.skipped_samples,
        eligible_files=_safe_cleanup_eligible_files(snapshot.report_path),
        report_path=snapshot.report_path,
        error_message=snapshot.error_message,
    )


def _to_icloud_backfill_inventory_status(
    snapshot: IcloudInventoryScanResult | IcloudBackfillStatusSnapshot,
) -> IcloudBackfillInventoryStatus:
    if isinstance(snapshot, IcloudInventoryScanResult):
        return IcloudBackfillInventoryStatus(
            source_id=snapshot.source_id,
            status=snapshot.status,
            last_inventory_scan_at=snapshot.scanned_at,
            last_scan_candidate_count=snapshot.scanned_count,
            last_scan_created_count=snapshot.created_count,
            last_scan_updated_count=snapshot.updated_count,
            inventory_total_count=snapshot.inventory_total_count,
            eligible_metadata_count=snapshot.eligible_metadata_count,
            unsupported_or_ambiguous_count=snapshot.unsupported_or_ambiguous_count,
            backfill_completed_count=snapshot.backfill_completed_count,
            unresolved_eligible_count=snapshot.unresolved_eligible_count,
            acquirable_pending_count=snapshot.acquirable_pending_count,
            retryable_failed_count=snapshot.retryable_failed_count,
            ambiguous_or_unsupported_count=snapshot.ambiguous_or_unsupported_count,
            deferred_current_count=snapshot.deferred_current_count,
            deferred_adjusted_resource_count=snapshot.deferred_adjusted_resource_count,
            deferred_ambiguous_count=snapshot.deferred_ambiguous_count,
            deferred_unsupported_count=snapshot.deferred_unsupported_count,
            deferred_new_since_last_scan_count=snapshot.deferred_new_since_last_scan_count,
            deferred_changed_since_last_scan_count=snapshot.deferred_changed_since_last_scan_count,
            source_exhausted=snapshot.source_exhausted,
            scan_limit_reached=snapshot.scan_limit_reached,
            stop_reason=snapshot.stop_reason,
        )
    return IcloudBackfillInventoryStatus(
        source_id=snapshot.source_id,
        status=snapshot.status,
        last_inventory_scan_at=snapshot.last_inventory_scan_at,
        last_scan_candidate_count=snapshot.last_scan_candidate_count,
        last_scan_created_count=snapshot.last_scan_created_count,
        last_scan_updated_count=snapshot.last_scan_updated_count,
        inventory_total_count=snapshot.inventory_total_count,
        eligible_metadata_count=snapshot.eligible_metadata_count,
        unsupported_or_ambiguous_count=snapshot.unsupported_or_ambiguous_count,
        backfill_completed_count=snapshot.backfill_completed_count,
        unresolved_eligible_count=snapshot.unresolved_eligible_count,
        acquirable_pending_count=snapshot.acquirable_pending_count,
        retryable_failed_count=snapshot.retryable_failed_count,
        ambiguous_or_unsupported_count=snapshot.ambiguous_or_unsupported_count,
        deferred_current_count=snapshot.deferred_current_count,
        deferred_adjusted_resource_count=snapshot.deferred_adjusted_resource_count,
        deferred_ambiguous_count=snapshot.deferred_ambiguous_count,
        deferred_unsupported_count=snapshot.deferred_unsupported_count,
        deferred_new_since_last_scan_count=snapshot.deferred_new_since_last_scan_count,
        deferred_changed_since_last_scan_count=snapshot.deferred_changed_since_last_scan_count,
        source_exhausted=snapshot.source_exhausted,
        scan_limit_reached=snapshot.scan_limit_reached,
        stop_reason=snapshot.stop_reason,
    )


def _to_deferred_asset_item(item: DeferredAssetListItem) -> SourceProfileDeferredAssetItem:
    return SourceProfileDeferredAssetItem(
        id=item.id,
        inventory_id=item.inventory_id,
        source_profile_id=item.source_profile_id,
        primary_relative_path=item.primary_relative_path,
        filename=item.filename,
        extension=item.extension,
        content_type=item.content_type,
        resource_count=item.resource_count,
        is_live_photo=item.is_live_photo,
        grouping=item.grouping,
        deferred_category=item.deferred_category,
        deferred_reason_code=item.deferred_reason_code,
        deferred_reason_human=item.deferred_reason_human,
        policy_status=item.policy_status,
        current_state=item.current_state,
        first_seen_at=item.first_seen_at,
        last_seen_at=item.last_seen_at,
        observation_count=item.observation_count,
    )


def _to_historical_routine_status(snapshot) -> IcloudHistoricalRoutineStatus:
    return IcloudHistoricalRoutineStatus(
        source_id=snapshot.source_id,
        source_label=snapshot.source_label,
        total_imported_from_source=snapshot.total_imported_from_source,
        inventory_total_logical=snapshot.inventory_total_logical,
        backfill_completed_logical=snapshot.backfill_completed_logical,
        eligible_pending_logical=snapshot.eligible_pending_logical,
        available_inventory=snapshot.available_inventory,
        logical_candidates_ready=snapshot.logical_candidates_ready,
        latest_prepare_run_id=snapshot.latest_prepare_run_id,
        prepare_status=snapshot.prepare_status,
        prepare_expires_at=snapshot.prepare_expires_at,
        target_logical_candidates=snapshot.target_logical_candidates,
        new_deferred_this_prepare=snapshot.new_deferred_this_prepare,
        source_exhaustion_state=snapshot.source_exhaustion_state,
        provider_records_scanned=snapshot.provider_records_scanned,
        scan_depth_used=snapshot.scan_depth_used,
        deferred_current_logical=snapshot.deferred_current_logical,
        deferred_adjusted_resource_logical=snapshot.deferred_adjusted_resource_logical,
        deferred_ambiguous_logical=snapshot.deferred_ambiguous_logical,
        deferred_unsupported_logical=snapshot.deferred_unsupported_logical,
        retryable_failed_logical=snapshot.retryable_failed_logical,
        last_inventory_scan_at=snapshot.last_inventory_scan_at,
        last_inventory_refresh_at=snapshot.last_inventory_refresh_at,
        last_historical_run_at=snapshot.last_historical_run_at,
        last_historical_run_id=snapshot.last_historical_run_id,
        last_cleanup_run_id=snapshot.last_cleanup_run_id,
        local_staging_file_count=snapshot.local_staging_file_count,
        partial_file_count=snapshot.partial_file_count,
        backfill_execute_file_count=snapshot.backfill_execute_file_count,
        operator_message=snapshot.operator_message,
    )


def _to_intake_import_chunk_status(chunk) -> IcloudIntakeImportChunkStatus:
    return IcloudIntakeImportChunkStatus(
        id=chunk.id,
        chunk_index=chunk.chunk_index,
        status=chunk.status,
        candidate_start_index=chunk.candidate_start_index,
        candidate_end_index=chunk.candidate_end_index,
        logical_candidates=chunk.logical_candidates,
        logical_imported=chunk.logical_imported,
        files_resources_imported=chunk.files_resources_imported,
        local_staging_files_cleaned=chunk.local_staging_files_cleaned,
        new_deferred_this_chunk=chunk.new_deferred_this_chunk,
        execution_failed_retryable_count=chunk.execution_failed_retryable_count,
        execution_failed_terminal_count=chunk.execution_failed_terminal_count,
        source_intake_failed_count=chunk.source_intake_failed_count,
        cleanup_failed_count=chunk.cleanup_failed_count,
        acquisition_run_id=chunk.acquisition_run_id,
        acquisition_batch_id=chunk.acquisition_batch_id,
        source_intake_run_id=chunk.source_intake_run_id,
        cleanup_dry_run_id=chunk.cleanup_dry_run_id,
        cleanup_execution_run_id=chunk.cleanup_execution_run_id,
        cleanup_report_path=chunk.cleanup_report_path,
        cleanup_eligible_count=chunk.cleanup_eligible_count,
        cleanup_skipped_count=chunk.cleanup_skipped_count,
        cleanup_protected_count=chunk.cleanup_protected_count,
        cleanup_verification_failed_count=chunk.cleanup_verification_failed_count,
        cleanup_file_missing_count=chunk.cleanup_file_missing_count,
        cleanup_delete_failed_count=chunk.cleanup_delete_failed_count,
        chunk_total_seconds=chunk.chunk_total_seconds,
        candidate_load_seconds=chunk.candidate_load_seconds,
        fresh_resolution_seconds=chunk.fresh_resolution_seconds,
        download_stage_seconds=chunk.download_stage_seconds,
        source_intake_seconds=chunk.source_intake_seconds,
        cleanup_dry_run_seconds=chunk.cleanup_dry_run_seconds,
        cleanup_execute_seconds=chunk.cleanup_execute_seconds,
        db_state_update_seconds=chunk.db_state_update_seconds,
        inter_chunk_gap_seconds=chunk.inter_chunk_gap_seconds,
        started_at=chunk.started_at,
        completed_at=chunk.completed_at,
        failed_at=chunk.failed_at,
        operator_message=chunk.operator_message,
        stop_reason=chunk.stop_reason,
        timing_note=chunk.timing_note,
    )


def _to_intake_import_status(snapshot) -> IcloudIntakeImportStatus:
    return IcloudIntakeImportStatus(
        source_id=snapshot.source_id,
        source_label=snapshot.source_label,
        total_imported_from_source=snapshot.total_imported_from_source,
        last_inventory_refresh_at=snapshot.last_inventory_refresh_at,
        available_inventory=snapshot.available_inventory,
        logical_candidates_ready=snapshot.logical_candidates_ready,
        latest_prepare_run_id=snapshot.latest_prepare_run_id,
        prepare_status=snapshot.prepare_status,
        prepare_expires_at=snapshot.prepare_expires_at,
        import_run_id=snapshot.import_run_id,
        import_status=snapshot.import_status,
        import_operator_message=snapshot.import_operator_message,
        import_stop_reason=snapshot.import_stop_reason,
        target_logical_candidates=snapshot.target_logical_candidates,
        logical_candidates_total=snapshot.logical_candidates_total,
        logical_imported=snapshot.logical_imported,
        files_resources_imported=snapshot.files_resources_imported,
        local_staging_files_cleaned=snapshot.local_staging_files_cleaned,
        new_deferred_this_run=snapshot.new_deferred_this_run,
        execution_failed_retryable_count=snapshot.execution_failed_retryable_count,
        execution_failed_terminal_count=snapshot.execution_failed_terminal_count,
        source_intake_failed_count=snapshot.source_intake_failed_count,
        cleanup_failed_count=snapshot.cleanup_failed_count,
        current_chunk_index=snapshot.current_chunk_index,
        total_chunks=snapshot.total_chunks,
        internal_batch_size=snapshot.internal_batch_size,
        pending_chunk_count=snapshot.pending_chunk_count,
        completed_chunk_count=snapshot.completed_chunk_count,
        remaining_logical_candidates=snapshot.remaining_logical_candidates,
        resume_available=snapshot.resume_available,
        can_start_import=snapshot.can_start_import,
        can_resume_import=snapshot.can_resume_import,
        can_advance_import=snapshot.can_advance_import,
        current_phase=snapshot.current_phase,
        last_chunk_duration_seconds=snapshot.last_chunk_duration_seconds,
        last_inter_chunk_gap_seconds=snapshot.last_inter_chunk_gap_seconds,
        started_at=snapshot.started_at,
        last_progress_at=snapshot.last_progress_at,
        completed_at=snapshot.completed_at,
        failed_at=snapshot.failed_at,
        interrupted_at=snapshot.interrupted_at,
        resumed_at=snapshot.resumed_at,
        report_path=snapshot.report_path,
        local_staging_file_count=snapshot.local_staging_file_count,
        partial_file_count=snapshot.partial_file_count,
        backfill_execute_file_count=snapshot.backfill_execute_file_count,
        chunks=[_to_intake_import_chunk_status(chunk) for chunk in snapshot.chunks],
    )


def _intake_import_status_response(snapshot) -> IcloudIntakeImportStatusResponse:
    from datetime import datetime, timezone

    return IcloudIntakeImportStatusResponse(
        generated_at=datetime.now(timezone.utc),
        current=_to_intake_import_status(snapshot),
    )


def _to_icloud_backfill_acquire_preview_response(
    snapshot: IcloudBackfillAcquisitionPreviewResult,
) -> IcloudBackfillAcquirePreviewResponse:
    return IcloudBackfillAcquirePreviewResponse(
        source_id=snapshot.source_id,
        status=snapshot.status,
        selected_inventory_count=snapshot.selected_inventory_count,
        matched_listing_count=snapshot.matched_listing_count,
        preview_selected_logical_count=snapshot.preview_selected_logical_count,
        preview_selected_resource_count=snapshot.preview_selected_resource_count,
        skipped_stale_count=snapshot.skipped_stale_count,
        skipped_known_count=snapshot.skipped_known_count,
        skipped_unsupported_count=snapshot.skipped_unsupported_count,
        skipped_ambiguous_count=snapshot.skipped_ambiguous_count,
        skipped_missing_identity_count=snapshot.skipped_missing_identity_count,
        skipped_pending_classification_count=snapshot.skipped_pending_classification_count,
        skipped_completed_count=snapshot.skipped_completed_count,
        unsafe_manifest_count=snapshot.unsafe_manifest_count,
        acquire_limit=snapshot.acquire_limit,
        max_listing_candidates=snapshot.max_listing_candidates,
        stop_reason=snapshot.stop_reason,
        next_safe_action=snapshot.next_safe_action,
        preview_items=[
            {
                "inventory_id": item.inventory_id,
                "logical_resource_count": item.logical_resource_count,
                "is_live_photo": item.is_live_photo,
                "primary_relative_path": item.primary_relative_path,
            }
            for item in snapshot.preview_items
        ],
    )


def _to_icloud_backfill_acquire_response(
    snapshot: IcloudBackfillAcquireResult,
) -> IcloudBackfillAcquireResponse:
    return IcloudBackfillAcquireResponse(
        source_id=snapshot.source_id,
        status=snapshot.status,
        dry_run=snapshot.dry_run,
        auto_run_source_intake=snapshot.auto_run_source_intake,
        selected_inventory_count=snapshot.selected_inventory_count,
        matched_listing_count=snapshot.matched_listing_count,
        selected_logical_count=snapshot.selected_logical_count,
        selected_resource_count=snapshot.selected_resource_count,
        downloaded_logical_count=snapshot.downloaded_logical_count,
        downloaded_resource_count=snapshot.downloaded_resource_count,
        source_intake_attempted=snapshot.source_intake_attempted,
        source_intake_succeeded=snapshot.source_intake_succeeded,
        source_intake_run_id=snapshot.source_intake_run_id,
        acquisition_run_id=snapshot.acquisition_run_id,
        acquisition_batch_id=snapshot.acquisition_batch_id,
        backfill_completed_count=snapshot.backfill_completed_count,
        skipped_stale_count=snapshot.skipped_stale_count,
        skipped_known_count=snapshot.skipped_known_count,
        skipped_unsupported_count=snapshot.skipped_unsupported_count,
        skipped_ambiguous_count=snapshot.skipped_ambiguous_count,
        skipped_missing_identity_count=snapshot.skipped_missing_identity_count,
        skipped_pending_classification_count=snapshot.skipped_pending_classification_count,
        skipped_completed_count=snapshot.skipped_completed_count,
        failed_retryable_count=snapshot.failed_retryable_count,
        failed_terminal_count=snapshot.failed_terminal_count,
        stop_reason=snapshot.stop_reason,
        next_safe_action=snapshot.next_safe_action,
        acquired_resource_paths=list(getattr(snapshot, "acquired_resource_paths", ())),
        items=[
            {
                "inventory_id": item.inventory_id,
                "acquisition_state": item.acquisition_state,
                "backfill_completed": item.backfill_completed,
                "backfill_resolution_state": item.backfill_resolution_state,
                "logical_resource_count": item.logical_resource_count,
                "is_live_photo": item.is_live_photo,
                "primary_relative_path": item.primary_relative_path,
            }
            for item in snapshot.items
        ],
    )



def _guardrail_conflict_content(
    snapshot: IngestionOperationGuardrailSnapshot,
    *,
    detail: str,
    error_code: str = "INGESTION_OPERATION_ACTIVE",
    current: object | None = None,
) -> dict[str, object]:
    content: dict[str, object] = {
        "detail": detail,
        "error_code": error_code,
        "blocking_reasons": [reason.model_dump(mode="json") for reason in snapshot.blocking_reasons],
        "operation_conflicts": snapshot.operation_conflicts.model_dump(mode="json"),
    }
    if current is not None:
        if hasattr(current, "model_dump"):
            content["current"] = current.model_dump(mode="json")
        else:
            content["current"] = current
    return content


def _source_intake_readiness_conflict_content(
    exc: SourceIntakeReadinessBlockedError,
    *,
    current: object | None = None,
) -> dict[str, object]:
    readiness = exc.readiness
    readiness_summary: dict[str, object] = {
        "source_profile_id": readiness.source_profile_id,
        "source_label": readiness.source_label,
        "source_type": readiness.source_type,
        "profile_status": readiness.profile_status,
        "cloud_provider": readiness.cloud_provider,
        "endpoint_id": readiness.endpoint_id,
        "endpoint_alias": readiness.endpoint_alias,
        "endpoint_source_type": readiness.endpoint_source_type,
        "readiness_status": readiness.readiness_status,
        "identity_match_status": readiness.identity_match_status,
        "can_run_source_intake": readiness.can_run_source_intake,
        "requires_operator_acknowledgment": readiness.requires_operator_acknowledgment,
        "hard_block": readiness.hard_block,
        "operator_message": readiness.operator_message,
        "recommended_next_action": readiness.recommended_next_action,
        "warnings": [warning.model_dump(mode="json") for warning in readiness.warnings],
        "blockers": [blocker.model_dump(mode="json") for blocker in readiness.blockers],
        "checked_at": readiness.checked_at.isoformat(),
    }
    content: dict[str, object] = {
        "detail": exc.detail,
        "error_code": exc.error_code,
        **readiness_summary,
        "readiness": readiness_summary,
    }
    if current is not None:
        if hasattr(current, "model_dump"):
            content["current"] = current.model_dump(mode="json")
        else:
            content["current"] = current
    return content


@router.get("/heic-preview/status", response_model=HeicPreviewStatusResponse)
def get_heic_preview_run_status(db: Session = Depends(get_db_session)) -> HeicPreviewStatusResponse:
    """Return display preview generation status and pending-work count."""
    status_view = get_heic_preview_status(db)
    return HeicPreviewStatusResponse(
        generated_at=status_view.generated_at,
        pending_previews=status_view.pending_previews,
        current=_to_heic_preview_run_status(status_view.current),
    )


@router.post("/heic-preview/run", response_model=HeicPreviewActionResponse)
def run_heic_preview_generation() -> HeicPreviewActionResponse | JSONResponse:
    """Start display preview generation in the background when no active run exists."""
    try:
        result = start_heic_preview_background(created_by="admin_api")
    except HeicPreviewAlreadyRunningError as exc:
        payload = HeicPreviewActionResponse(
            accepted=False,
            message="A display preview generation run is already active.",
            status=_to_heic_preview_run_status(exc.status),
        )
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=payload.model_dump(mode="json"))

    accepted = result.status.status in {"running", "stop_requested"}
    payload = HeicPreviewActionResponse(
        accepted=accepted,
        message=result.message,
        status=_to_heic_preview_run_status(result.status),
    )
    if not accepted:
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=payload.model_dump(mode="json"))
    return payload


@router.post("/heic-preview/stop", response_model=HeicPreviewActionResponse)
def stop_heic_preview_generation(db: Session = Depends(get_db_session)) -> HeicPreviewActionResponse:
    """Request graceful stop for the currently active display preview generation run."""
    result = request_heic_preview_stop(db)
    accepted = result.status.status in {"stop_requested", "running"}
    return HeicPreviewActionResponse(
        accepted=accepted,
        message=result.message,
        status=_to_heic_preview_run_status(result.status),
    )


@router.get("/live-photo-pairing/status", response_model=LivePhotoPairingStatusResponse)
def get_live_photo_pairing_run_status() -> LivePhotoPairingStatusResponse:
    """Return Live Photo pairing status and latest summary."""
    status_view = get_live_photo_pairing_status()
    return LivePhotoPairingStatusResponse(
        generated_at=status_view.generated_at,
        current=_to_live_photo_pairing_run_status(status_view.current),
    )


@router.post("/live-photo-pairing/run", response_model=LivePhotoPairingActionResponse)
def run_live_photo_pairing_from_admin(db: Session = Depends(get_db_session)) -> LivePhotoPairingActionResponse:
    """Run Live Photo pairing immediately and return the final summary."""
    result = run_live_photo_pairing_admin(db)
    return LivePhotoPairingActionResponse(
        accepted=result.status.status == "completed",
        message=result.message,
        status=_to_live_photo_pairing_run_status(result.status),
    )


@router.get("/icloud-acquisition/status", response_model=IcloudAcquisitionStatusResponse)
def get_icloud_acquisition_run_status(db: Session = Depends(get_db_session)) -> IcloudAcquisitionStatusResponse:
    """Return current icloudpd acquisition status and pending-run metadata."""
    status_view: IcloudAcquisitionStatusView = get_icloud_acquisition_status(db)
    return IcloudAcquisitionStatusResponse(
        generated_at=status_view.generated_at,
        current=_to_icloud_acquisition_run_status(status_view.current),
    )


@router.post("/icloud-acquisition/run", response_model=IcloudAcquisitionRunResponse)
def run_icloud_acquisition(body: IcloudAcquisitionRunRequest, db: Session = Depends(get_db_session)) -> IcloudAcquisitionRunResponse | JSONResponse:
    """Launch an icloudpd acquisition background run."""
    with protected_ingestion_operation_start(db):
        return _run_icloud_acquisition_locked(body, db)


def _run_icloud_acquisition_locked(body: IcloudAcquisitionRunRequest, db: Session) -> IcloudAcquisitionRunResponse | JSONResponse:
    guardrail_snapshot = get_ingestion_operation_guardrail_snapshot(db)
    if guardrail_snapshot.blocked:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_guardrail_conflict_content(
                guardrail_snapshot,
                detail="Another ingestion-related operation is active.",
                error_code="INGESTION_OPERATION_ACTIVE",
            ),
        )

    try:
        result = start_icloud_acquisition_background(
            db,
            source_label=body.source_label,
            username=body.username,
            recent_count=body.recent_count,
            acquisition_mode=body.acquisition_mode,
            source_type=body.source_type,
            created_by="admin_api",
        )
    except IcloudAcquisitionAlreadyRunningError as exc:
        payload = IcloudAcquisitionRunResponse(
            status=exc.status.status,
            message=exc.message,
            current=_to_icloud_acquisition_run_status(exc.status),
        )
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=payload.model_dump(mode="json"))
    except IcloudAcquisitionLaunchError as exc:
        payload = IcloudAcquisitionRunResponse(
            status=exc.status.status,
            message=exc.message,
            current=_to_icloud_acquisition_run_status(exc.status),
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "detail": exc.message,
                "error_code": exc.error_code,
                "current": payload.current.model_dump(mode="json"),
            },
        )

    payload = IcloudAcquisitionRunResponse(
        status="started",
        message=result.message,
        current=_to_icloud_acquisition_run_status(result.status),
    )
    return payload


@router.post("/icloud-acquisition/stop", response_model=IcloudAcquisitionStopResponse)
def stop_icloud_acquisition(db: Session = Depends(get_db_session)) -> IcloudAcquisitionStopResponse:
    """Request graceful stop for the currently active icloudpd acquisition run."""
    result = request_icloud_acquisition_stop(db)
    return IcloudAcquisitionStopResponse(
        status="stop_requested",
        message=result.message,
        current=_to_icloud_acquisition_run_status(result.status),
    )


@router.get("/icloud-staging-cleanup/status", response_model=IcloudStagingCleanupStatusResponse)
def get_icloud_staging_cleanup_status(
    source_id: int | None = Query(default=None),
    db: Session = Depends(get_db_session),
) -> IcloudStagingCleanupStatusResponse:
    """Return current or latest iCloud staging cleanup run snapshot."""
    from datetime import datetime, timezone

    snapshot = get_cleanup_status(db, source_id=source_id)
    return IcloudStagingCleanupStatusResponse(
        generated_at=datetime.now(timezone.utc),
        current=_to_icloud_cleanup_run_status(snapshot),
    )


@router.get("/icloud-staging-cleanup/readiness", response_model=IcloudStagingCleanupReadinessResponse)
def get_icloud_staging_cleanup_readiness(
    source_id: int = Query(...),
    db: Session = Depends(get_db_session),
) -> IcloudStagingCleanupReadinessResponse:
    """Return local-only cleanup readiness independently of iCloud auth state."""
    from datetime import datetime, timezone

    source_readiness = get_cleanup_source_readiness(db, source_id=source_id)
    guardrail = get_ingestion_operation_guardrail_snapshot(db, source_id=source_id)
    reasons = [IcloudReadinessReason(code=code, message=message) for code, message in source_readiness.blocking_reasons]
    reasons.extend(guardrail.blocking_reasons)
    latest = get_latest_cleanup_dry_run(db, source_id=source_id)
    latest_status = _to_icloud_cleanup_run_status(latest)
    return IcloudStagingCleanupReadinessResponse(
        generated_at=datetime.now(timezone.utc),
        source_id=source_id,
        readiness_status="blocked" if reasons else "ready",
        canonical_staging_path=source_readiness.canonical_staging_path,
        blocking_reasons=reasons,
        latest_dry_run=latest_status,
    )


@router.post("/icloud-staging-cleanup/run", response_model=IcloudStagingCleanupRunResponse)
def run_icloud_staging_cleanup(
    body: IcloudStagingCleanupRunRequest,
    db: Session = Depends(get_db_session),
) -> IcloudStagingCleanupRunResponse | JSONResponse:
    """Launch conservative iCloud staging cleanup in background."""
    with protected_ingestion_operation_start(db):
        return _run_icloud_staging_cleanup_locked(body, db)


def _run_icloud_staging_cleanup_locked(
    body: IcloudStagingCleanupRunRequest,
    db: Session,
) -> IcloudStagingCleanupRunResponse | JSONResponse:
    guardrail_snapshot = get_ingestion_operation_guardrail_snapshot(db, source_id=body.source_id)
    if guardrail_snapshot.blocked:
        conflict_error_code = "INGESTION_OPERATION_ACTIVE"
        conflict_detail = "Another ingestion-related operation is active."
        if guardrail_snapshot.operation_conflicts.icloud_cleanup_active:
            conflict_error_code = "CLEANUP_ALREADY_RUNNING"
            conflict_detail = "A cleanup run is already active."
        elif guardrail_snapshot.operation_conflicts.source_intake_active_for_this_source is True:
            conflict_error_code = "SOURCE_INTAKE_ACTIVE"
            conflict_detail = f"A Source Intake run is active for source {body.source_id}."

        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_guardrail_conflict_content(
                guardrail_snapshot,
                detail=conflict_detail,
                error_code=conflict_error_code,
            ),
        )

    try:
        snapshot = start_cleanup_run(
            db,
            source_id=body.source_id,
            dry_run=body.dry_run,
            created_by="admin_api",
        )
    except CleanupBusyError as exc:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(exc), "error_code": "CLEANUP_ALREADY_RUNNING"},
        )
    except SourceIntakeActiveError as exc:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(exc), "error_code": "SOURCE_INTAKE_ACTIVE"},
        )
    except CleanupValidationError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc), "error_code": exc.code},
        )
    except CleanupAuthorizationError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc), "error_code": exc.code},
        )

    return IcloudStagingCleanupRunResponse(
        status="started",
        message="iCloud staging cleanup started.",
        current=_to_icloud_cleanup_run_status(snapshot),
    )


@router.post("/icloud-staging-cleanup/execute", response_model=IcloudStagingCleanupRunResponse)
def execute_icloud_staging_cleanup(
    body: IcloudStagingCleanupExecuteRequest,
    db: Session = Depends(get_db_session),
) -> IcloudStagingCleanupRunResponse | JSONResponse:
    """Execute cleanup only through a fresh, explicitly confirmed dry-run binding."""
    with protected_ingestion_operation_start(db):
        guardrail_snapshot = get_ingestion_operation_guardrail_snapshot(db, source_id=body.source_id)
        if guardrail_snapshot.blocked:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content=_guardrail_conflict_content(
                    guardrail_snapshot,
                    detail="Another ingestion-related operation is active.",
                    error_code="INGESTION_OPERATION_ACTIVE",
                ),
            )
        try:
            snapshot = start_cleanup_execution(
                db,
                source_id=body.source_id,
                dry_run_run_id=body.dry_run_run_id,
                explicit_confirmation=body.explicit_confirmation,
                created_by="ingestion_ui",
            )
        except (CleanupBusyError, SourceIntakeActiveError) as exc:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={"detail": str(exc), "error_code": "INGESTION_OPERATION_ACTIVE"},
            )
        except CleanupValidationError as exc:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": str(exc), "error_code": exc.code},
            )
        except CleanupAuthorizationError as exc:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": str(exc), "error_code": exc.code},
            )

        return IcloudStagingCleanupRunResponse(
            status="started",
            message="Verified local iCloud staging cleanup started.",
            current=_to_icloud_cleanup_run_status(snapshot),
        )


@router.post("/icloud-backfill/inventory-scan", response_model=IcloudBackfillInventoryScanResponse)
def run_icloud_backfill_inventory_scan(
    body: IcloudBackfillInventoryScanRequest,
    db: Session = Depends(get_db_session),
) -> IcloudBackfillInventoryScanResponse | JSONResponse:
    """Run a metadata-only historical iCloud inventory scan."""

    try:
        result = run_icloud_backfill_inventory_scan_service(
            db,
            source_id=body.source_id,
            max_candidates=body.max_candidates,
        )
    except IcloudBackfillValidationError as exc:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if exc.code == "source_not_found"
            else status.HTTP_400_BAD_REQUEST
        )
        return JSONResponse(
            status_code=status_code,
            content={"detail": str(exc), "error_code": exc.code},
        )
    except (ExactSelectionPrototypeError, ExactSelectionProtocolError) as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "detail": str(exc),
                "error_code": getattr(exc, "code", "icloud_helper_error"),
            },
        )

    return IcloudBackfillInventoryScanResponse(
        status="completed",
        message="iCloud backfill inventory scan completed.",
        current=_to_icloud_backfill_inventory_status(result),
    )


@router.get("/icloud-routine/historical/status", response_model=IcloudHistoricalRoutineStatusResponse)
def get_icloud_historical_routine_status(
    source_id: int,
    db: Session = Depends(get_db_session),
) -> IcloudHistoricalRoutineStatusResponse | JSONResponse:
    """Return operator-level historical iCloud backfill routine status."""
    from datetime import datetime, timezone

    try:
        snapshot = get_historical_routine_status_service(db, source_id=source_id)
    except IcloudHistoricalRoutineError as exc:
        status_code = status.HTTP_404_NOT_FOUND if exc.code == "source_not_found" else status.HTTP_400_BAD_REQUEST
        return JSONResponse(status_code=status_code, content={"detail": str(exc), "error_code": exc.code})
    return IcloudHistoricalRoutineStatusResponse(
        generated_at=datetime.now(timezone.utc),
        current=_to_historical_routine_status(snapshot),
    )


@router.post("/icloud-routine/historical/refresh-inventory", response_model=IcloudHistoricalRoutineRefreshResponse)
def refresh_icloud_historical_inventory(
    body: IcloudHistoricalRoutineRefreshRequest,
    db: Session = Depends(get_db_session),
) -> IcloudHistoricalRoutineRefreshResponse | JSONResponse:
    """Run metadata-only inventory refresh for the historical iCloud routine."""
    try:
        result = refresh_historical_inventory_service(
            db,
            source_id=body.source_id,
            max_candidates=body.max_candidates,
        )
    except (IcloudHistoricalRoutineError, IcloudBackfillValidationError) as exc:
        code = getattr(exc, "code", "invalid_historical_refresh")
        status_code = status.HTTP_404_NOT_FOUND if code == "source_not_found" else status.HTTP_400_BAD_REQUEST
        return JSONResponse(status_code=status_code, content={"detail": str(exc), "error_code": code})
    except (ExactSelectionPrototypeError, ExactSelectionProtocolError) as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "detail": str(exc),
                "error_code": getattr(exc, "code", "icloud_helper_error"),
            },
        )
    return IcloudHistoricalRoutineRefreshResponse(
        status=result.status,
        message=result.operator_message,
        source_id=result.source_id,
        prepare_run_id=result.prepare_run_id,
        inventory_total_logical=result.inventory_total_logical,
        created_logical=result.created_logical,
        updated_logical=result.updated_logical,
        eligible_pending_logical=result.eligible_pending_logical,
        available_inventory=result.available_inventory,
        target_logical_candidates=result.target_logical_candidates,
        logical_candidates_ready=result.logical_candidates_ready,
        new_deferred_this_prepare=result.new_deferred_this_prepare,
        deferred_current_logical=result.deferred_current_logical,
        deferred_adjusted_resource_logical=result.deferred_adjusted_resource_logical,
        source_exhausted=result.source_exhausted,
        scan_limit_reached=result.scan_limit_reached,
        source_exhaustion_state=result.source_exhaustion_state,
        provider_records_scanned=result.provider_records_scanned,
        scan_depth_used=result.scan_depth_used,
        expires_at=result.expires_at,
        scanned_at=result.scanned_at,
        scan_limit_note=result.scan_limit_note,
        operator_message=result.operator_message,
    )


@router.get("/icloud-routine/intake/import/status", response_model=IcloudIntakeImportStatusResponse)
def get_icloud_intake_import_status(
    source_id: int,
    db: Session = Depends(get_db_session),
) -> IcloudIntakeImportStatusResponse | JSONResponse:
    """Return durable iCloud Intake import run/resume status."""
    try:
        snapshot = get_icloud_intake_import_status_service(db, source_id=source_id)
    except IcloudHistoricalRoutineError as exc:
        status_code = status.HTTP_404_NOT_FOUND if exc.code == "source_not_found" else status.HTTP_400_BAD_REQUEST
        return JSONResponse(status_code=status_code, content={"detail": str(exc), "error_code": exc.code})
    return _intake_import_status_response(snapshot)


@router.post("/icloud-routine/intake/import/start", response_model=IcloudIntakeImportStatusResponse)
def start_icloud_intake_import(
    body: IcloudIntakeImportStartRequest,
    db: Session = Depends(get_db_session),
) -> IcloudIntakeImportStatusResponse | JSONResponse:
    """Create a durable iCloud Intake import run for the latest prepared candidate set."""
    try:
        snapshot = start_icloud_intake_import_service(
            db,
            source_id=body.source_id,
            target_logical_assets=body.target_logical_assets,
            internal_batch_size=body.internal_batch_size,
        )
    except (IcloudHistoricalRoutineError, IcloudBackfillValidationError) as exc:
        code = getattr(exc, "code", "intake_import_start_failed")
        status_code = status.HTTP_404_NOT_FOUND if code == "source_not_found" else status.HTTP_400_BAD_REQUEST
        return JSONResponse(status_code=status_code, content={"detail": str(exc), "error_code": code})
    return _intake_import_status_response(snapshot)


@router.post("/icloud-routine/intake/import/resume", response_model=IcloudIntakeImportStatusResponse)
def resume_icloud_intake_import(
    body: IcloudIntakeImportResumeRequest,
    db: Session = Depends(get_db_session),
) -> IcloudIntakeImportStatusResponse | JSONResponse:
    """Explicitly re-arm an interrupted iCloud Intake import run before advancing."""
    try:
        snapshot = resume_icloud_intake_import_service(
            db,
            source_id=body.source_id,
            import_run_id=body.import_run_id,
        )
    except (IcloudHistoricalRoutineError, IcloudBackfillValidationError) as exc:
        code = getattr(exc, "code", "intake_import_resume_failed")
        status_code = status.HTTP_404_NOT_FOUND if code == "source_not_found" else status.HTTP_400_BAD_REQUEST
        return JSONResponse(status_code=status_code, content={"detail": str(exc), "error_code": code})
    return _intake_import_status_response(snapshot)


@router.post("/icloud-routine/intake/import/advance", response_model=IcloudIntakeImportStatusResponse)
def advance_icloud_intake_import(
    body: IcloudIntakeImportAdvanceRequest,
    db: Session = Depends(get_db_session),
) -> IcloudIntakeImportStatusResponse | JSONResponse:
    """Advance exactly one durable iCloud Intake import chunk."""
    guardrail_snapshot = get_ingestion_operation_guardrail_snapshot(db, source_id=body.source_id)
    if guardrail_snapshot.blocked:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_guardrail_conflict_content(
                guardrail_snapshot,
                detail="Another ingestion-related operation is active.",
                error_code="INGESTION_OPERATION_ACTIVE",
            ),
        )
    with protected_ingestion_operation_start(db):
        try:
            snapshot = advance_icloud_intake_import_service(
                db,
                source_id=body.source_id,
                import_run_id=body.import_run_id,
            )
        except (IcloudHistoricalRoutineError, IcloudBackfillValidationError) as exc:
            code = getattr(exc, "code", "intake_import_advance_failed")
            status_code = status.HTTP_404_NOT_FOUND if code == "source_not_found" else status.HTTP_400_BAD_REQUEST
            return JSONResponse(status_code=status_code, content={"detail": str(exc), "error_code": code})
    return _intake_import_status_response(snapshot)


@router.post("/icloud-routine/historical/run-next-batch", response_model=IcloudHistoricalRoutineRunResponse)
def run_icloud_historical_next_batch(
    body: IcloudHistoricalRoutineRunRequest,
    db: Session = Depends(get_db_session),
) -> IcloudHistoricalRoutineRunResponse | JSONResponse:
    """Run the operator-level Backfill Next 1000 historical routine."""
    guardrail_snapshot = get_ingestion_operation_guardrail_snapshot(db, source_id=body.source_id)
    if guardrail_snapshot.blocked:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_guardrail_conflict_content(
                guardrail_snapshot,
                detail="Another ingestion-related operation is active.",
                error_code="INGESTION_OPERATION_ACTIVE",
            ),
        )
    with protected_ingestion_operation_start(db):
        try:
            result = run_next_historical_batch_service(
                db,
                source_id=body.source_id,
                target_logical_assets=body.target_logical_assets,
                internal_batch_size=body.internal_batch_size,
            )
        except (IcloudHistoricalRoutineError, IcloudBackfillValidationError) as exc:
            code = getattr(exc, "code", "historical_routine_failed")
            status_code = status.HTTP_404_NOT_FOUND if code == "source_not_found" else status.HTTP_400_BAD_REQUEST
            return JSONResponse(status_code=status_code, content={"detail": str(exc), "error_code": code})

    return IcloudHistoricalRoutineRunResponse(
        status=result.status,
        source_id=result.source_id,
        prepare_run_id=result.prepare_run_id,
        requested_logical_assets=result.requested_logical_assets,
        logical_candidates=result.logical_candidates,
        internal_batch_size=result.internal_batch_size,
        imported_logical_assets=result.imported_logical_assets,
        logical_imported=result.logical_imported,
        imported_resources=result.imported_resources,
        files_resources_imported=result.files_resources_imported,
        cleaned_local_staging_files=result.cleaned_local_staging_files,
        local_staging_files_cleaned=result.local_staging_files_cleaned,
        new_deferred_this_run=result.new_deferred_this_run,
        execution_failed_this_run=result.execution_failed_this_run,
        eligible_remaining_logical=result.eligible_remaining_logical,
        deferred_current_logical=result.deferred_current_logical,
        deferred_adjusted_resource_logical=result.deferred_adjusted_resource_logical,
        available_inventory=result.available_inventory,
        operator_message=result.operator_message,
        stop_reason=result.stop_reason,
        chunks=[
            IcloudHistoricalRoutineChunk(
                chunk_index=chunk.chunk_index,
                requested_logical_assets=chunk.requested_logical_assets,
                imported_logical_assets=chunk.imported_logical_assets,
                imported_resources=chunk.imported_resources,
                cleaned_local_staging_files=chunk.cleaned_local_staging_files,
                acquisition_run_id=chunk.acquisition_run_id,
                acquisition_batch_id=chunk.acquisition_batch_id,
                source_intake_run_id=chunk.source_intake_run_id,
                cleanup_dry_run_id=chunk.cleanup_dry_run_id,
                cleanup_execution_run_id=chunk.cleanup_execution_run_id,
                cleanup_report_path=chunk.cleanup_report_path,
                status=chunk.status,
                stop_reason=chunk.stop_reason,
                operator_message=chunk.operator_message,
            )
            for chunk in result.chunks
        ],
    )


@router.get(
    "/source-profiles/{source_id}/deferred-assets",
    response_model=SourceProfileDeferredAssetsResponse,
)
def list_source_profile_deferred_assets(
    source_id: int,
    limit: int = 100,
    category: str | None = None,
    reason_code: str | None = None,
    state: str | None = None,
    db: Session = Depends(get_db_session),
) -> SourceProfileDeferredAssetsResponse | JSONResponse:
    """Return bounded, safe deferred asset rows for one Source Profile."""

    if limit < 1 or limit > 500:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "limit must be between 1 and 500.",
                "error_code": "invalid_limit",
            },
        )
    if db.get(IngestionSource, source_id) is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": f"Source Profile {source_id} not found.",
                "error_code": "source_not_found",
            },
        )
    items = list_deferred_assets(
        db,
        source_profile_id=source_id,
        limit=limit,
        category=category,
        reason_code=reason_code,
        state=state,
    )
    return SourceProfileDeferredAssetsResponse(
        source_id=source_id,
        limit=limit,
        category=category,
        reason_code=reason_code,
        state=state,
        items=[_to_deferred_asset_item(item) for item in items],
    )


@router.post("/icloud-backfill/acquire-preview", response_model=IcloudBackfillAcquirePreviewResponse)
def preview_icloud_backfill_acquisition(
    body: IcloudBackfillAcquirePreviewRequest,
    db: Session = Depends(get_db_session),
) -> IcloudBackfillAcquirePreviewResponse | JSONResponse:
    """Preview inventory-driven historical backfill acquisition without downloading."""

    try:
        result = preview_icloud_backfill_acquisition_service(
            db,
            source_id=body.source_id,
            acquire_limit=body.acquire_limit,
            max_listing_candidates=body.max_listing_candidates,
            include_items=body.include_items,
        )
    except IcloudBackfillValidationError as exc:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if exc.code == "source_not_found"
            else status.HTTP_400_BAD_REQUEST
        )
        return JSONResponse(
            status_code=status_code,
            content={"detail": str(exc), "error_code": exc.code},
        )

    return _to_icloud_backfill_acquire_preview_response(result)


@router.post("/icloud-backfill/acquire", response_model=IcloudBackfillAcquireResponse)
def run_icloud_backfill_acquisition(
    body: IcloudBackfillAcquireRequest,
    db: Session = Depends(get_db_session),
) -> IcloudBackfillAcquireResponse | JSONResponse:
    """Run dry-run preview or explicit historical backfill acquisition execution."""

    try:
        result = run_icloud_backfill_acquisition_service(
            db,
            source_id=body.source_id,
            acquire_limit=body.acquire_limit,
            max_listing_candidates=body.max_listing_candidates,
            dry_run=body.dry_run,
            auto_run_source_intake=body.auto_run_source_intake,
            include_items=body.include_items,
        )
    except IcloudBackfillValidationError as exc:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if exc.code == "source_not_found"
            else status.HTTP_400_BAD_REQUEST
        )
        return JSONResponse(
            status_code=status_code,
            content={"detail": str(exc), "error_code": exc.code},
        )

    return _to_icloud_backfill_acquire_response(result)


@router.get("/icloud-backfill/status", response_model=IcloudBackfillStatusResponse)
def get_icloud_backfill_inventory_status(
    source_id: int,
    db: Session = Depends(get_db_session),
) -> IcloudBackfillStatusResponse | JSONResponse:
    """Return metadata-only historical iCloud backfill inventory status."""
    from datetime import datetime, timezone

    try:
        snapshot = get_icloud_backfill_status(db, source_id=source_id)
    except IcloudBackfillStateNotFound:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": f"No iCloud backfill state exists for source {source_id}.",
                "error_code": "ICLOUD_BACKFILL_STATE_NOT_FOUND",
            },
        )

    return IcloudBackfillStatusResponse(
        generated_at=datetime.now(timezone.utc),
        current=_to_icloud_backfill_inventory_status(snapshot),
    )


@router.post("/internal/icloud-runs", response_model=InternalIcloudRunResponse)
def start_internal_icloud_single_flow_run(
    body: InternalIcloudRunRequest,
    db: Session = Depends(get_db_session),
) -> InternalIcloudRunResponse | JSONResponse:
    """Start a bounded internal/admin single-flow iCloud run and return a pollable run reference."""

    try:
        result = start_internal_single_flow_run(
            db,
            source_id=body.source_id,
            batch_size=body.batch_size,
            total_limit=body.total_limit,
            candidate_search_cap=body.candidate_search_cap,
            media_scope=body.media_scope,
            auto_cleanup_if_safe=body.auto_cleanup_if_safe,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc), "error_code": "INVALID_INTERNAL_ICLOUD_RUN_REQUEST"},
        )

    payload = InternalIcloudRunResponse(
        status="started" if result.accepted else "stopped",
        message=result.message,
        current=result.status,
    )
    if result.accepted:
        return payload
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=payload.model_dump(mode="json"),
    )


@router.get("/internal/icloud-runs/{run_id}", response_model=InternalIcloudRunStatusResponse)
def get_internal_icloud_single_flow_run_status(
    run_id: int,
    db: Session = Depends(get_db_session),
) -> InternalIcloudRunStatusResponse | JSONResponse:
    """Return current status for an internal/admin single-flow iCloud run."""
    from datetime import datetime, timezone

    current = get_internal_single_flow_run_status(db, run_id=run_id)
    if current is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": f"Internal iCloud run {run_id} was not found.", "error_code": "INTERNAL_ICLOUD_RUN_NOT_FOUND"},
        )
    return InternalIcloudRunStatusResponse(
        generated_at=datetime.now(timezone.utc),
        current=current,
    )


# ---------------------------------------------------------------------------
# Source Intake visibility routes (12.24 — read-only)
# ---------------------------------------------------------------------------


@router.post("/source-identity/probe", response_model=SourceIdentityProbeResponse)
def post_source_identity_probe(
    body: SourceIdentityProbeRequest,
) -> SourceIdentityProbeResponse:
    """Run a read-only source identity probe."""
    return get_source_identity_probe_service().probe(body)


@router.get("/source-identity/capabilities", response_model=SourceIdentityCapabilitiesResponse)
def get_source_identity_capabilities() -> SourceIdentityCapabilitiesResponse:
    """Return read-only source identity probe provider capabilities."""
    return get_source_identity_probe_service().capabilities()


@router.post("/source-endpoints/enrollment/plan", response_model=SourceEndpointEnrollmentPlanResponse)
def post_source_endpoint_enrollment_plan(
    body: SourceEndpointEnrollmentPlanRequest,
    db: Session = Depends(get_db_session),
) -> SourceEndpointEnrollmentPlanResponse:
    """Build a read-only source endpoint enrollment plan."""
    return get_source_endpoint_enrollment_service(db).plan(body)


@router.post("/source-endpoints/enrollment/confirm", response_model=SourceEndpointEnrollmentConfirmResponse)
def post_source_endpoint_enrollment_confirm(
    body: SourceEndpointEnrollmentConfirmRequest,
    db: Session = Depends(get_db_session),
) -> SourceEndpointEnrollmentConfirmResponse:
    """Confirm a stateless source endpoint enrollment plan."""
    return get_source_endpoint_enrollment_service(db).confirm(body)


@router.get("/source-intake/sources", response_model=SourceIntakeSourcesResponse)
def get_source_intake_sources(db: Session = Depends(get_db_session)) -> SourceIntakeSourcesResponse:
    """Return known ingestion sources with latest run and report information."""
    from datetime import datetime, timezone
    sources = list_sources_with_latest_info(db)
    return SourceIntakeSourcesResponse(
        generated_at=datetime.now(timezone.utc),
        sources=sources,
    )


@router.get("/source-profiles", response_model=SourceProfilesResponse)
def get_source_profiles(
    profile_status: str = Query(default="active", alias="status"),
    include_username: bool = False,
    db: Session = Depends(get_db_session),
) -> SourceProfilesResponse | JSONResponse:
    """Return source profiles for compatibility-first ingestion UI evolution."""
    from datetime import datetime, timezone

    try:
        profiles = list_source_profiles(
            db,
            status=profile_status,
            include_username=include_username,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    return SourceProfilesResponse(
        generated_at=datetime.now(timezone.utc),
        profiles=profiles,
    )


@router.patch("/source-profiles/{source_id}", response_model=SourceProfileSummary)
def patch_source_profile_status(
    source_id: int,
    body: SourceProfileStatusUpdateRequest,
    include_username: bool = False,
    db: Session = Depends(get_db_session),
) -> SourceProfileSummary | JSONResponse:
    """Update only source profile lifecycle status for one source."""
    try:
        return update_source_profile_status(
            db,
            source_id=source_id,
            profile_status=body.profile_status,
            include_username=include_username,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )
    except LookupError:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Source profile not found."},
        )


@router.get("/source-profiles/{source_id}", response_model=SourceProfileDetail)
def get_source_profile(
    source_id: int,
    include_username: bool = False,
    db: Session = Depends(get_db_session),
) -> SourceProfileDetail | JSONResponse:
    """Return one source profile detail view for operational diagnostics."""
    try:
        return get_source_profile_detail(
            db,
            source_id=source_id,
            include_username=include_username,
        )
    except LookupError:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Source profile not found."},
        )


@router.get("/source-profiles/{source_id}/icloud-readiness", response_model=IcloudSourceReadinessResponse)
def get_source_profile_icloud_readiness(
    source_id: int,
    include_username: bool = False,
    db: Session = Depends(get_db_session),
) -> IcloudSourceReadinessResponse | JSONResponse:
    """Return read-only iCloud readiness snapshot for one source profile."""
    try:
        return get_icloud_source_readiness(
            db,
            source_id=source_id,
            include_username=include_username,
        )
    except LookupError:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Source profile not found."},
        )


@router.post("/source-profiles", response_model=SourceProfileCreateResponse)
def post_source_profile(
    body: SourceProfileCreateRequest,
    include_username: bool = False,
    db: Session = Depends(get_db_session),
) -> SourceProfileCreateResponse | JSONResponse:
    """Create or return an existing source profile for Ingestion tab workflows."""
    try:
        return create_source_profile(
            db,
            payload=body,
            include_username=include_username,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )


@router.patch("/source-profiles/{source_id}/metadata", response_model=SourceProfileSummary)
def patch_source_profile_metadata(
    source_id: int,
    body: SourceProfileMetadataUpdateRequest,
    include_username: bool = False,
    db: Session = Depends(get_db_session),
) -> SourceProfileSummary | JSONResponse:
    """Update safe, non-destructive source profile metadata fields."""
    try:
        return update_source_profile_metadata(
            db,
            source_id=source_id,
            payload=body,
            include_username=include_username,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )
    except LookupError:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Source profile not found."},
        )


@router.post("/source-profiles/{source_id}/verify-path", response_model=SourceProfilePathCheckResponse)
def post_source_profile_verify_path(
    source_id: int,
    db: Session = Depends(get_db_session),
) -> SourceProfilePathCheckResponse | JSONResponse:
    """Verify the current effective path for one source profile."""
    try:
        return verify_source_profile_path(
            db,
            source_id=source_id,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )
    except LookupError:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Source profile not found."},
        )


@router.post("/source-profiles/{source_id}/check-readiness", response_model=SourceProfileReadinessResponse)
def post_source_profile_check_readiness(
    source_id: int,
    db: Session = Depends(get_db_session),
) -> SourceProfileReadinessResponse | JSONResponse:
    """Run a read-only Source Profile readiness check."""
    try:
        return get_source_profile_readiness_service(db).check_readiness(source_id)
    except LookupError:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Source profile not found."},
        )


@router.post("/source-profiles/{source_id}/create-staging-folder", response_model=SourceProfileStagingFolderCreateResponse)
def post_source_profile_create_staging_folder(
    source_id: int,
    db: Session = Depends(get_db_session),
) -> SourceProfileStagingFolderCreateResponse | JSONResponse:
    """Create the approved iCloud managed staging folder for one source profile."""
    try:
        return create_source_profile_staging_folder(
            db,
            source_id=source_id,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )
    except LookupError:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Source profile not found."},
        )


@router.get("/source-intake/reports", response_model=SourceIntakeReportsResponse)
def get_source_intake_reports() -> SourceIntakeReportsResponse:
    """Return recent source intake session report summaries."""
    from datetime import datetime, timezone
    reports = list_recent_reports(limit=50)
    return SourceIntakeReportsResponse(
        generated_at=datetime.now(timezone.utc),
        reports=reports,
    )


@router.get("/source-intake/reports/{report_filename}", response_model=SourceIntakeReportDetail)
def get_source_intake_report_detail(
    report_filename: str,
) -> SourceIntakeReportDetail | JSONResponse:
    """Return full parsed content of a single source intake report file."""
    try:
        detail = get_report_detail(report_filename)
    except ValueError:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Invalid report filename."},
        )
    if detail is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Report not found or could not be parsed."},
        )
    return detail


# ---------------------------------------------------------------------------
# Source Registry
# ---------------------------------------------------------------------------


@router.post("/source-intake/sources", response_model=SourceCreateResponse)
def create_intake_source(
    body: SourceCreateRequest,
    db: Session = Depends(get_db_session),
) -> SourceCreateResponse | JSONResponse:
    """Register or retrieve an ingestion source."""
    if body.create_new_label:
        normalized_label = normalize_source_label(body.source_label)
        existing = db.scalar(
            select(IngestionSource.id).where(
                IngestionSource.source_label_normalized == normalized_label,
            ).limit(1)
        )
        if existing is not None:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "detail": "This label already exists. Please select it from the existing label dropdown.",
                },
            )

    source, was_existing = create_or_get_ingestion_source(
        db,
        source_label=body.source_label,
        source_type=body.source_type,
        source_root_path=body.source_root_path,
        account_username=body.account_username,
    )
    return SourceCreateResponse(
        ingestion_source_id=source.id,
        source_label=source.source_label,
        source_type=source.source_type,
        source_root_path=source.source_root_path,
        account_username=source.account_username,
        created_at=source.created_at,
        was_existing=was_existing,
    )


# ---------------------------------------------------------------------------
# Admin-launched Source Intake
# ---------------------------------------------------------------------------


def _snapshot_to_schema(snap) -> SourceIntakeStatusSchema:
    return SourceIntakeStatusSchema(
        run_id=snap.run_id,
        status=snap.status,
        ingestion_run_id=snap.ingestion_run_id,
        source_label=snap.source_label,
        source_type=snap.source_type,
        source_root_path=snap.source_root_path,
        source_intake_limit=snap.source_intake_limit,
        ingest_batch_size=snap.ingest_batch_size,
        started_at=snap.started_at,
        finished_at=snap.finished_at,
        elapsed_seconds=snap.elapsed_seconds,
        files_scanned=snap.files_scanned,
        skipped_known=snap.skipped_known,
        selected=snap.selected,
        staged=snap.staged,
        processed_new_unique=snap.processed_new_unique,
        failed_or_rejected=snap.failed_or_rejected,
        remaining_unknown=snap.remaining_unknown,
        report_path=snap.report_path,
        error_message=snap.error_message,
        stop_requested=snap.stop_requested,
    )


@router.post("/source-intake/run", response_model=SourceIntakeRunResponse)
def launch_source_intake(
    body: SourceIntakeRunRequest,
    db: Session = Depends(get_db_session),
) -> SourceIntakeRunResponse | JSONResponse:
    """Start an admin-launched source intake run."""
    with protected_ingestion_operation_start(db):
        return _launch_source_intake_locked(body, db)


def _launch_source_intake_locked(
    body: SourceIntakeRunRequest,
    db: Session,
) -> SourceIntakeRunResponse | JSONResponse:
    guardrail_snapshot = get_ingestion_operation_guardrail_snapshot(db, source_id=body.ingestion_source_id)
    if guardrail_snapshot.blocked:
        current_snapshot = _snapshot_to_schema(get_source_intake_status(db))
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_guardrail_conflict_content(
                guardrail_snapshot,
                detail="Another ingestion-related operation is active.",
                error_code="INGESTION_OPERATION_ACTIVE",
                current=current_snapshot,
            ),
        )

    try:
        snapshot = start_source_intake(
            db,
            ingestion_source_id=body.ingestion_source_id,
            source_intake_limit=body.source_intake_limit,
            ingest_batch_size=body.ingest_batch_size,
            readiness_acknowledged=body.readiness_acknowledged,
        )
    except SourceIntakeReadinessBlockedError as exc:
        current_snapshot = _snapshot_to_schema(get_source_intake_status(db))
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_source_intake_readiness_conflict_content(exc, current=current_snapshot),
        )
    except SourceIntakeAlreadyRunningError as exc:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "A source intake run is already active.", "current": _snapshot_to_schema(exc.snapshot).model_dump(mode='json')},
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )
    return SourceIntakeRunResponse(
        status="started",
        message="Source intake started.",
        current=_snapshot_to_schema(snapshot),
    )


@router.get("/source-intake/run/status", response_model=SourceIntakeStatusSchema)
def source_intake_run_status(db: Session = Depends(get_db_session)) -> SourceIntakeStatusSchema:
    """Return current source intake run status."""
    snapshot = get_source_intake_status(db)
    return _snapshot_to_schema(snapshot)


@router.post("/source-intake/run/stop", response_model=SourceIntakeStopResponse)
def stop_source_intake(
    db: Session = Depends(get_db_session),
) -> SourceIntakeStopResponse:
    """Request graceful stop of the active source intake run."""
    snapshot = request_source_intake_stop(db)
    return SourceIntakeStopResponse(
        status="stop_requested",
        message="Stop requested. Run will finish current batch and exit.",
        current=_snapshot_to_schema(snapshot),
    )
