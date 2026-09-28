"""Browser-safe and operator-facing generalized NAS registration API."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.services.nas_registration.schemas import (
    CreateNasPendingRegistrationRequest,
    ExistingNasAdoptionResponse,
    NasInstallerManifestResponse,
    NasDiscoveryResponse,
    NasPendingRegistrationResponse,
    NasRegistrationCompletionResponse,
    NasRegistrationListResponse,
)
from app.services.nas_registration.service import (
    NasRegistrationError,
    complete_registration,
    adopt_existing_nas_identity,
    create_pending_registration,
    get_installer_manifest,
    list_registrations,
    discover_nas,
)


router = APIRouter(prefix="/api/admin/nas-registrations", tags=["admin", "nas-registration"])


def _raise(exc: NasRegistrationError) -> None:
    raise HTTPException(exc.http_status, detail={"code": exc.code, "message": exc.message}) from exc


@router.get("", response_model=NasRegistrationListResponse)
def registrations(db: Session = Depends(get_db_session)) -> NasRegistrationListResponse:
    return list_registrations(db)


@router.post("/discover", response_model=NasDiscoveryResponse)
def discover() -> NasDiscoveryResponse:
    return discover_nas()


@router.post("/adopt-existing", response_model=ExistingNasAdoptionResponse)
def adopt_existing(db: Session = Depends(get_db_session)) -> ExistingNasAdoptionResponse:
    try:
        return adopt_existing_nas_identity(db)
    except NasRegistrationError as exc:
        _raise(exc)


@router.post("/pending", response_model=NasPendingRegistrationResponse)
def create_pending(
    body: CreateNasPendingRegistrationRequest,
    response: Response,
    db: Session = Depends(get_db_session),
) -> NasPendingRegistrationResponse:
    response.headers["Cache-Control"] = "no-store"
    try:
        return create_pending_registration(db, body)
    except NasRegistrationError as exc:
        _raise(exc)


@router.get(
    "/pending/{registration_id}/installer-manifest",
    response_model=NasInstallerManifestResponse,
)
def installer_manifest(
    registration_id: UUID,
    response: Response,
    db: Session = Depends(get_db_session),
) -> NasInstallerManifestResponse:
    response.headers["Cache-Control"] = "no-store"
    try:
        return get_installer_manifest(db, registration_id)
    except NasRegistrationError as exc:
        _raise(exc)


@router.post(
    "/pending/{registration_id}/complete",
    response_model=NasRegistrationCompletionResponse,
)
def complete(
    registration_id: UUID,
    response: Response,
    db: Session = Depends(get_db_session),
) -> NasRegistrationCompletionResponse:
    response.headers["Cache-Control"] = "no-store"
    try:
        return complete_registration(db, registration_id)
    except NasRegistrationError as exc:
        _raise(exc)
