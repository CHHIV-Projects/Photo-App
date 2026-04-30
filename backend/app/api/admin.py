"""API routes for Admin summary and foundation views."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.admin import (
    AdminSummaryResponse,
    DuplicateProcessingActionResponse,
    DuplicateProcessingRunStatus,
    DuplicateProcessingStatusResponse,
    FaceProcessingActionResponse,
    FaceProcessingRunStatus,
    FaceProcessingStatusResponse,
    PlaceGeocodingActionResponse,
    PlaceGeocodingRunStatus,
    PlaceGeocodingStatusResponse,
)
from app.services.admin import build_admin_summary
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
