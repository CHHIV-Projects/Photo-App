"""Dedicated authenticated Windows Helper API surface."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.models.windows_helper import WindowsHelperCredential
from app.services.windows_helper.service import (
    WindowsHelperServiceError,
    authenticate_credential,
    complete_pairing,
    helper_session,
    record_heartbeat,
)
from app.windows_helper_shared.channel import (
    HelperHeartbeatRequest,
    HelperHeartbeatResponse,
    HelperSessionResponse,
    PairingCompleteRequest,
    PairingCompleteResponse,
)


router = APIRouter(prefix="/api/helper/v1", tags=["windows-helper"])


def _raise_http(exc: WindowsHelperServiceError) -> None:
    raise HTTPException(status_code=exc.http_status, detail={"code": exc.code, "message": exc.message}) from exc


def get_authenticated_helper(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    db: Session = Depends(get_db_session),
) -> WindowsHelperCredential:
    try:
        return authenticate_credential(db, authorization)
    except WindowsHelperServiceError as exc:
        _raise_http(exc)


@router.get("/health")
def helper_health() -> dict[str, str]:
    """Narrow unauthenticated liveness probe with no durable evidence."""
    return {"status": "ok", "surface": "windows-helper-v1"}


@router.post("/pair", response_model=PairingCompleteResponse)
def pair_helper(
    body: PairingCompleteRequest,
    response: Response,
    db: Session = Depends(get_db_session),
) -> PairingCompleteResponse:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    try:
        return complete_pairing(db, body)
    except WindowsHelperServiceError as exc:
        _raise_http(exc)


@router.get("/session", response_model=HelperSessionResponse)
def get_helper_session(
    credential: WindowsHelperCredential = Depends(get_authenticated_helper),
    db: Session = Depends(get_db_session),
) -> HelperSessionResponse:
    try:
        return helper_session(db, credential)
    except WindowsHelperServiceError as exc:
        _raise_http(exc)


@router.post("/heartbeat", response_model=HelperHeartbeatResponse)
def heartbeat(
    body: HelperHeartbeatRequest,
    credential: WindowsHelperCredential = Depends(get_authenticated_helper),
    db: Session = Depends(get_db_session),
) -> HelperHeartbeatResponse:
    try:
        return record_heartbeat(db, credential, body)
    except WindowsHelperServiceError as exc:
        _raise_http(exc)
