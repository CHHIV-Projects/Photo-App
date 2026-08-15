"""Trusted admin surface for planned provider-neutral Source acquisitions."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.source_acquisition import (
    ActivateSourceAcquisitionRequest,
    CreateAcquireItemOperationRequest,
    CreateSourceAcquisitionPlanRequest,
    SourceAcquisitionCleanupResponse,
    SourceAcquisitionOperationResponse,
    SourceAcquisitionRunResponse,
)
from app.services.source_acquisition.receiving import cleanup_failed_partials
from app.services.source_acquisition.service import activate_run, create_planned_run, get_run
from app.services.windows_helper.operations import create_acquire_operation
from app.services.windows_helper.service import WindowsHelperServiceError


router = APIRouter(prefix="/api/admin/source-acquisitions", tags=["admin", "source-acquisition"])


def _raise_http(exc: WindowsHelperServiceError) -> None:
    raise HTTPException(status_code=exc.http_status, detail={"code": exc.code, "message": exc.message}) from exc


@router.post("/plans", response_model=SourceAcquisitionRunResponse)
def create_plan(
    body: CreateSourceAcquisitionPlanRequest,
    db: Session = Depends(get_db_session),
) -> SourceAcquisitionRunResponse:
    try:
        return create_planned_run(db, body)
    except WindowsHelperServiceError as exc:
        _raise_http(exc)


@router.get("/{run_id}", response_model=SourceAcquisitionRunResponse)
def acquisition_status(run_id: UUID, db: Session = Depends(get_db_session)) -> SourceAcquisitionRunResponse:
    try:
        return get_run(db, run_id)
    except WindowsHelperServiceError as exc:
        _raise_http(exc)


@router.post("/{run_id}/activate", response_model=SourceAcquisitionRunResponse)
def activate(
    run_id: UUID,
    body: ActivateSourceAcquisitionRequest,
    db: Session = Depends(get_db_session),
) -> SourceAcquisitionRunResponse:
    try:
        return activate_run(db, run_id, body.proposal_digest)
    except WindowsHelperServiceError as exc:
        _raise_http(exc)


@router.post("/{run_id}/operations/acquire", response_model=SourceAcquisitionOperationResponse)
def create_acquire(
    run_id: UUID,
    body: CreateAcquireItemOperationRequest,
    db: Session = Depends(get_db_session),
) -> SourceAcquisitionOperationResponse:
    try:
        status = get_run(db, run_id)
        if body.acquisition_item_id not in {item.acquisition_item_id for item in status.items}:
            raise WindowsHelperServiceError("acquisition_item_mismatch", "The item belongs to another run.", http_status=409)
        return create_acquire_operation(db, body.acquisition_item_id)
    except WindowsHelperServiceError as exc:
        _raise_http(exc)


@router.post("/{run_id}/cleanup-failed", response_model=SourceAcquisitionCleanupResponse)
def cleanup_failed(run_id: UUID, db: Session = Depends(get_db_session)) -> SourceAcquisitionCleanupResponse:
    try:
        removed, ready = cleanup_failed_partials(db, run_id)
        return SourceAcquisitionCleanupResponse(
            acquisition_run_id=run_id, removed_partial_count=removed, ready_objects_preserved=ready
        )
    except WindowsHelperServiceError as exc:
        _raise_http(exc)
