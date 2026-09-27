"""Redacted normal-product API for Windows Local Source ingestion."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.windows_source_ui import (
    WindowsSourceUiCandidateReview,
    WindowsSourceUiComputerList,
    WindowsSourceUiCreateConfirmRequest,
    WindowsSourceUiCreatePlan,
    WindowsSourceUiCreatePlanRequest,
    WindowsSourceUiCreateProbeRequest,
    WindowsSourceUiCreateResult,
    WindowsSourceUiOperation,
    WindowsSourceUiPortableDiscovery,
    WindowsSourceUiPortableDiscoveryRequest,
    WindowsSourceUiPortableDiscoveryResolveRequest,
    WindowsSourceUiPrepareRequest,
    WindowsSourceUiProfileStatus,
    WindowsSourceUiRouteCheck,
    WindowsSourceUiRouteResolveRequest,
    WindowsSourceUiWorkflowStatus,
)
from app.schemas.windows_helper import (
    CreateWindowsHelperPairingRequest,
    WindowsHelperPairingAuthorizationResponse,
)
from app.services.windows_helper.service import WindowsHelperServiceError
from app.services.windows_helper.ui_facade import (
    advance_workflow,
    begin_profile_route_check,
    begin_portable_discovery,
    candidate_review,
    confirm_creation,
    create_computer_pairing,
    create_creation_probe,
    create_profile_probe,
    creation_plan,
    list_computers,
    operation_status,
    prepare_inventory,
    profile_status,
    resolve_profile_route,
    resolve_portable_discovery,
)


router = APIRouter(prefix="/api/admin/windows-source-ui", tags=["admin", "windows-source-ui"])


def _raise_http(exc: WindowsHelperServiceError) -> None:
    raise HTTPException(
        status_code=exc.http_status,
        detail={"code": exc.code, "message": exc.message},
    ) from exc


@router.get("/computers", response_model=WindowsSourceUiComputerList)
def get_computers(db: Session = Depends(get_db_session)) -> WindowsSourceUiComputerList:
    return list_computers(db)


@router.post(
    "/computers/pairing",
    response_model=WindowsHelperPairingAuthorizationResponse,
)
def post_computer_pairing(
    body: CreateWindowsHelperPairingRequest,
    response: Response,
    db: Session = Depends(get_db_session),
) -> WindowsHelperPairingAuthorizationResponse:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    try:
        return create_computer_pairing(db, body)
    except WindowsHelperServiceError as exc:
        _raise_http(exc)


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


@router.post("/profiles/{source_profile_id}/routes", response_model=WindowsSourceUiRouteCheck)
def post_profile_routes(
    source_profile_id: int, db: Session = Depends(get_db_session)
) -> WindowsSourceUiRouteCheck:
    try:
        return begin_profile_route_check(db, source_profile_id)
    except WindowsHelperServiceError as exc:
        _raise_http(exc)


@router.post(
    "/profiles/{source_profile_id}/routes/resolve",
    response_model=WindowsSourceUiRouteCheck,
)
def post_profile_route_resolution(
    source_profile_id: int,
    body: WindowsSourceUiRouteResolveRequest,
    db: Session = Depends(get_db_session),
) -> WindowsSourceUiRouteCheck:
    try:
        return resolve_profile_route(db, source_profile_id, body)
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


@router.post("/creation/devices", response_model=WindowsSourceUiPortableDiscovery)
def post_portable_discovery(
    body: WindowsSourceUiPortableDiscoveryRequest,
    db: Session = Depends(get_db_session),
) -> WindowsSourceUiPortableDiscovery:
    try:
        return begin_portable_discovery(db, body)
    except WindowsHelperServiceError as exc:
        _raise_http(exc)


@router.post("/creation/devices/resolve", response_model=WindowsSourceUiPortableDiscovery)
def post_portable_discovery_resolution(
    body: WindowsSourceUiPortableDiscoveryResolveRequest,
    db: Session = Depends(get_db_session),
) -> WindowsSourceUiPortableDiscovery:
    try:
        return resolve_portable_discovery(db, body)
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
