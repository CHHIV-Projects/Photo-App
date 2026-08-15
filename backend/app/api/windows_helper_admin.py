"""Narrow existing-boundary administration for Windows Helper enrollment."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.windows_helper import (
    CreateWindowsHelperPairingRequest,
    WindowsHelperAdminStatusListResponse,
    WindowsHelperPairingAuthorizationResponse,
    WindowsHelperRevokeRequest,
    WindowsHelperRevokeResponse,
)
from app.services.windows_helper.service import (
    WindowsHelperServiceError,
    create_pairing_authorization,
    list_helper_status,
    revoke_credential,
)


router = APIRouter(prefix="/api/admin/windows-helper", tags=["admin", "windows-helper-admin"])


def _raise_http(exc: WindowsHelperServiceError) -> None:
    raise HTTPException(status_code=exc.http_status, detail={"code": exc.code, "message": exc.message}) from exc


@router.post("/pairing-authorizations", response_model=WindowsHelperPairingAuthorizationResponse)
def create_pairing(
    body: CreateWindowsHelperPairingRequest,
    response: Response,
    db: Session = Depends(get_db_session),
) -> WindowsHelperPairingAuthorizationResponse:
    del body
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    try:
        return create_pairing_authorization(db)
    except WindowsHelperServiceError as exc:
        _raise_http(exc)


@router.get("/status", response_model=WindowsHelperAdminStatusListResponse)
def helper_status(db: Session = Depends(get_db_session)) -> WindowsHelperAdminStatusListResponse:
    return WindowsHelperAdminStatusListResponse(helpers=list_helper_status(db))


@router.post("/revoke", response_model=WindowsHelperRevokeResponse)
def revoke_helper(
    body: WindowsHelperRevokeRequest,
    db: Session = Depends(get_db_session),
) -> WindowsHelperRevokeResponse:
    try:
        return revoke_credential(db, body.access_node_id)
    except WindowsHelperServiceError as exc:
        _raise_http(exc)
