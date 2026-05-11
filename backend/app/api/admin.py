"""API routes for Admin summary and foundation views."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
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
    IcloudAcquisitionRunRequest,
    IcloudAcquisitionRunResponse,
    IcloudAcquisitionRunStatus,
    IcloudAcquisitionStatusResponse,
    IcloudAcquisitionStopResponse,
)
from app.services.admin import (
    build_admin_summary,
    create_or_get_ingestion_source,
    get_report_detail,
    get_source_intake_status,
    list_recent_reports,
    list_sources_with_latest_info,
    request_source_intake_stop,
    start_source_intake,
)
from app.services.ingestion.ingestion_context_service import normalize_source_label
from app.services.admin.source_intake_execution_service import (
    SourceIntakeAlreadyRunningError,
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
from app.services.previews.heic_preview_processing_service import (
    HeicPreviewAlreadyRunningError,
    HeicPreviewStatusSnapshot,
    get_heic_preview_status,
    request_heic_preview_stop,
    start_heic_preview_background,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


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
    try:
        result = start_icloud_acquisition_background(
            db,
            source_label=body.source_label,
            username=body.username,
            recent_count=body.recent_count,
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


# ---------------------------------------------------------------------------
# Source Intake visibility routes (12.24 — read-only)
# ---------------------------------------------------------------------------


@router.get("/source-intake/sources", response_model=SourceIntakeSourcesResponse)
def get_source_intake_sources(db: Session = Depends(get_db_session)) -> SourceIntakeSourcesResponse:
    """Return known ingestion sources with latest run and report information."""
    from datetime import datetime, timezone
    sources = list_sources_with_latest_info(db)
    return SourceIntakeSourcesResponse(
        generated_at=datetime.now(timezone.utc),
        sources=sources,
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
    )
    return SourceCreateResponse(
        ingestion_source_id=source.id,
        source_label=source.source_label,
        source_type=source.source_type,
        source_root_path=source.source_root_path,
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
    try:
        snapshot = start_source_intake(
            db,
            ingestion_source_id=body.ingestion_source_id,
            source_intake_limit=body.source_intake_limit,
            ingest_batch_size=body.ingest_batch_size,
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
