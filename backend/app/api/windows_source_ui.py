"""Redacted normal-product API for Windows Local Source ingestion."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.windows_source_ui import (
    WindowsSourceUiCandidateReview,
    WindowsSourceUiCreateConfirmRequest,
    WindowsSourceUiCreatePlan,
    WindowsSourceUiCreatePlanRequest,
    WindowsSourceUiCreateProbeRequest,
    WindowsSourceUiCreateResult,
    WindowsSourceUiOperation,
    WindowsSourceUiPrepareRequest,
    WindowsSourceUiProfileStatus,
    WindowsSourceUiWorkflowStatus,
)
from app.services.windows_helper.service import WindowsHelperServiceError
from app.services.windows_helper.ui_facade import (
    advance_workflow,
    candidate_review,
    confirm_creation,
    create_creation_probe,
    create_profile_probe,
    creation_plan,
    operation_status,
    prepare_inventory,
    profile_status,
)


router = APIRouter(prefix="/api/admin/windows-source-ui", tags=["admin", "windows-source-ui"])


def _raise_http(exc: WindowsHelperServiceError) -> None:
    raise HTTPException(
        status_code=exc.http_status,
        detail={"code": exc.code, "message": exc.message},
    ) from exc


@router.get("/profiles/{source_profile_id}", response_model=WindowsSourceUiProfileStatus)
def get_profile_status(
    source_profile_id: int, db: Session = Depends(get_db_session)
) -> WindowsSourceUiProfileStatus:
    try:
        return profile_status(db, source_profile_id)
    except WindowsHelperServiceError as exc:
        _raise_http(exc)


@router.post("/profiles/{source_profile_id}/probe", response_model=WindowsSourceUiOperation)
def post_profile_probe(
    source_profile_id: int, db: Session = Depends(get_db_session)
) -> WindowsSourceUiOperation:
    try:
        return create_profile_probe(db, source_profile_id)
    except WindowsHelperServiceError as exc:
        _raise_http(exc)


@router.get("/operations/{operation_id}", response_model=WindowsSourceUiOperation)
def get_safe_operation(
    operation_id: UUID, db: Session = Depends(get_db_session)
) -> WindowsSourceUiOperation:
    try:
        return operation_status(db, operation_id)
    except WindowsHelperServiceError as exc:
        _raise_http(exc)


@router.post("/profiles/{source_profile_id}/prepare", response_model=WindowsSourceUiOperation)
def post_prepare(
    source_profile_id: int,
    body: WindowsSourceUiPrepareRequest,
    db: Session = Depends(get_db_session),
) -> WindowsSourceUiOperation:
    try:
        return prepare_inventory(db, source_profile_id, body.probe_operation_token)
    except WindowsHelperServiceError as exc:
        _raise_http(exc)


@router.post(
    "/profiles/{source_profile_id}/inventory/{operation_id}/review",
    response_model=WindowsSourceUiCandidateReview,
)
def post_candidate_review(
    source_profile_id: int,
    operation_id: UUID,
    db: Session = Depends(get_db_session),
) -> WindowsSourceUiCandidateReview:
    try:
        return candidate_review(db, source_profile_id, operation_id)
    except WindowsHelperServiceError as exc:
        _raise_http(exc)


@router.post("/runs/{run_id}/confirm", response_model=WindowsSourceUiWorkflowStatus)
def post_confirm(
    run_id: UUID, db: Session = Depends(get_db_session)
) -> WindowsSourceUiWorkflowStatus:
    try:
        return advance_workflow(db, run_id, confirm=True)
    except WindowsHelperServiceError as exc:
        _raise_http(exc)


@router.post("/runs/{run_id}/advance", response_model=WindowsSourceUiWorkflowStatus)
def post_advance(
    run_id: UUID, db: Session = Depends(get_db_session)
) -> WindowsSourceUiWorkflowStatus:
    try:
        return advance_workflow(db, run_id, confirm=False)
    except WindowsHelperServiceError as exc:
        _raise_http(exc)


@router.post("/creation/probe", response_model=WindowsSourceUiOperation)
def post_creation_probe(
    body: WindowsSourceUiCreateProbeRequest,
    db: Session = Depends(get_db_session),
) -> WindowsSourceUiOperation:
    try:
        return create_creation_probe(db, body)
    except WindowsHelperServiceError as exc:
        _raise_http(exc)


@router.post("/creation/plan", response_model=WindowsSourceUiCreatePlan)
def post_creation_plan(
    body: WindowsSourceUiCreatePlanRequest,
    db: Session = Depends(get_db_session),
) -> WindowsSourceUiCreatePlan:
    try:
        return creation_plan(db, body)
    except WindowsHelperServiceError as exc:
        _raise_http(exc)


@router.post("/creation/confirm", response_model=WindowsSourceUiCreateResult)
def post_creation_confirm(
    body: WindowsSourceUiCreateConfirmRequest,
    db: Session = Depends(get_db_session),
) -> WindowsSourceUiCreateResult:
    try:
        return confirm_creation(db, body)
    except WindowsHelperServiceError as exc:
        _raise_http(exc)
