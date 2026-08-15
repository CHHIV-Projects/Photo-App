"""Dedicated authenticated Windows Helper API surface."""

from __future__ import annotations

import re
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.models.windows_helper import WindowsHelperCredential
from app.services.windows_helper.operations import (
    complete_acquire_operation,
    claim_operation,
    complete_inventory_operation,
    complete_probe_operation,
    fail_operation,
)
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
    HelperOperationClaimResponse,
    HelperOperationCompletionResponse,
    HelperOperationFailureRequest,
    HelperOperationFailureResponse,
    HelperSessionResponse,
    PairingCompleteRequest,
    HelperAcquisitionStatusResponse,
    HelperChunkCommitResponse,
    PairingCompleteResponse,
)
from app.windows_helper_shared.protocol import (
    HelperAcquireItemResponse,
    HelperInventoryPageResponse,
    HelperProbeResponse,
    MAX_ACQUISITION_CHUNK_BYTES,
)
from app.services.source_acquisition.receiving import acquisition_status, commit_chunk


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


@router.post("/operations/claim", response_model=HelperOperationClaimResponse)
def claim_next_operation(
    credential: WindowsHelperCredential = Depends(get_authenticated_helper),
    db: Session = Depends(get_db_session),
) -> HelperOperationClaimResponse:
    try:
        return claim_operation(db, credential)
    except WindowsHelperServiceError as exc:
        _raise_http(exc)


@router.post(
    "/operations/{operation_id}/complete-probe",
    response_model=HelperOperationCompletionResponse,
)
def complete_probe(
    operation_id: UUID,
    body: HelperProbeResponse,
    credential: WindowsHelperCredential = Depends(get_authenticated_helper),
    db: Session = Depends(get_db_session),
) -> HelperOperationCompletionResponse:
    try:
        return complete_probe_operation(db, credential, operation_id, body)
    except WindowsHelperServiceError as exc:
        _raise_http(exc)


@router.post(
    "/operations/{operation_id}/complete-inventory",
    response_model=HelperOperationCompletionResponse,
)
def complete_inventory(
    operation_id: UUID,
    body: HelperInventoryPageResponse,
    credential: WindowsHelperCredential = Depends(get_authenticated_helper),
    db: Session = Depends(get_db_session),
) -> HelperOperationCompletionResponse:
    try:
        return complete_inventory_operation(db, credential, operation_id, body)
    except WindowsHelperServiceError as exc:
        _raise_http(exc)


@router.post(
    "/operations/{operation_id}/fail",
    response_model=HelperOperationFailureResponse,
)
def fail_helper_operation(
    operation_id: UUID,
    body: HelperOperationFailureRequest,
    credential: WindowsHelperCredential = Depends(get_authenticated_helper),
    db: Session = Depends(get_db_session),
) -> HelperOperationFailureResponse:
    try:
        return fail_operation(db, credential, operation_id, body)
    except WindowsHelperServiceError as exc:
        _raise_http(exc)


@router.get(
    "/operations/{operation_id}/acquisitions/{run_id}/items/{item_id}/status",
    response_model=HelperAcquisitionStatusResponse,
)
def get_acquisition_status(
    operation_id: UUID,
    run_id: UUID,
    item_id: UUID,
    credential: WindowsHelperCredential = Depends(get_authenticated_helper),
    db: Session = Depends(get_db_session),
) -> HelperAcquisitionStatusResponse:
    try:
        return acquisition_status(db, credential, operation_id, run_id, item_id)
    except WindowsHelperServiceError as exc:
        _raise_http(exc)


@router.put(
    "/operations/{operation_id}/acquisitions/{run_id}/items/{item_id}/chunk",
    response_model=HelperChunkCommitResponse,
)
async def upload_acquisition_chunk(
    operation_id: UUID,
    run_id: UUID,
    item_id: UUID,
    request: Request,
    content_length: Annotated[str | None, Header(alias="Content-Length")] = None,
    chunk_offset: Annotated[str | None, Header(alias="X-Photo-Organizer-Chunk-Offset")] = None,
    chunk_sha256: Annotated[str | None, Header(alias="X-Photo-Organizer-Chunk-SHA256")] = None,
    credential: WindowsHelperCredential = Depends(get_authenticated_helper),
    db: Session = Depends(get_db_session),
) -> HelperChunkCommitResponse:
    try:
        if content_length is None or chunk_offset is None or chunk_sha256 is None:
            raise WindowsHelperServiceError("chunk_headers_required", "Required chunk headers are missing.", http_status=411)
        if request.headers.get("content-type", "").casefold() != "application/octet-stream":
            raise WindowsHelperServiceError("chunk_media_type_invalid", "The chunk media type is invalid.", http_status=415)
        try:
            declared_length = int(content_length)
            offset = int(chunk_offset)
        except ValueError as exc:
            raise WindowsHelperServiceError("chunk_headers_invalid", "Chunk headers are invalid.", http_status=400) from exc
        if declared_length <= 0 or declared_length > MAX_ACQUISITION_CHUNK_BYTES:
            raise WindowsHelperServiceError("chunk_size_invalid", "The acquisition chunk size is invalid.", http_status=413)
        if re.fullmatch(r"sha256:[0-9a-f]{64}", chunk_sha256) is None:
            raise WindowsHelperServiceError("chunk_digest_invalid", "The chunk digest is invalid.", http_status=400)
        received = bytearray()
        async for part in request.stream():
            remaining_bound = min(declared_length, MAX_ACQUISITION_CHUNK_BYTES) - len(received)
            if len(part) > remaining_bound:
                raise WindowsHelperServiceError("chunk_size_invalid", "The request body exceeded its bound.", http_status=413)
            received.extend(part)
        if len(received) != declared_length:
            raise WindowsHelperServiceError("chunk_length_mismatch", "The request body length did not match.", http_status=400)
        return commit_chunk(
            db, credential, operation_id, run_id, item_id,
            offset=offset, supplied_digest=chunk_sha256, body=bytes(received),
        )
    except WindowsHelperServiceError as exc:
        _raise_http(exc)


@router.post(
    "/operations/{operation_id}/complete-acquire",
    response_model=HelperOperationCompletionResponse,
)
def complete_acquire(
    operation_id: UUID,
    body: HelperAcquireItemResponse,
    credential: WindowsHelperCredential = Depends(get_authenticated_helper),
    db: Session = Depends(get_db_session),
) -> HelperOperationCompletionResponse:
    try:
        return complete_acquire_operation(db, credential, operation_id, body)
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
