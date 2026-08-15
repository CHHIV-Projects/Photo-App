"""Enrollment, authentication, and presence rules for the Windows Helper."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import secrets
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.source_endpoint import AccessNode
from app.models.windows_helper import (
    WindowsHelperCredential,
    WindowsHelperPairingAuthorization,
)
from app.schemas.windows_helper import (
    WindowsHelperAdminStatusResponse,
    WindowsHelperPairingAuthorizationResponse,
    WindowsHelperRevokeResponse,
)
from app.windows_helper_shared.channel import (
    HelperHeartbeatRequest,
    HelperHeartbeatResponse,
    HelperSessionResponse,
    PairingCompleteRequest,
    PairingCompleteResponse,
)


ACCESS_NODE_LABEL = "12.66 Windows Helper Development"
HELPER_PROVIDER_NAME = "windows_helper_v1"
HELPER_PROVIDER_VERSION = "1"
PAIRING_TTL = timedelta(minutes=10)
PAIRING_DIGEST_DOMAIN = b"photo-organizer-windows-helper-pairing-v1\x00"
CREDENTIAL_DIGEST_DOMAIN = b"photo-organizer-windows-helper-credential-v1\x00"


class WindowsHelperServiceError(ValueError):
    def __init__(self, code: str, message: str, *, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _digest(domain: bytes, secret: str) -> str:
    return hashlib.sha256(domain + secret.encode("utf-8")).hexdigest()


def pairing_secret_digest(secret: str) -> str:
    return _digest(PAIRING_DIGEST_DOMAIN, secret)


def credential_token_digest(secret: str) -> str:
    return _digest(CREDENTIAL_DIGEST_DOMAIN, secret)


def _new_secret() -> str:
    return secrets.token_urlsafe(32)


def _new_public_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(16)}"


def _split_composite(value: str, expected_prefix: str) -> tuple[str, str]:
    public_id, separator, secret = value.partition(".")
    if (
        not separator
        or not public_id.startswith(expected_prefix + "_")
        or len(public_id) > 64
        or len(secret) < 32
        or len(secret) > 128
    ):
        raise WindowsHelperServiceError("invalid_credential", "Credential is invalid.", http_status=401)
    return public_id, secret


def _capabilities_json(request: HelperHeartbeatRequest | PairingCompleteRequest) -> str:
    payload = request.capability_identity.model_dump(mode="json", exclude_none=True)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def get_or_create_development_access_node(db: Session) -> tuple[AccessNode, bool]:
    candidates = list(
        db.scalars(
            select(AccessNode).where(
                AccessNode.label == ACCESS_NODE_LABEL,
                AccessNode.os_family == "windows",
                AccessNode.provider_name == HELPER_PROVIDER_NAME,
                AccessNode.provider_version == HELPER_PROVIDER_VERSION,
            )
        )
    )
    if len(candidates) > 1:
        raise WindowsHelperServiceError(
            "ambiguous_access_node",
            "More than one exact Windows Helper Access Node exists.",
            http_status=409,
        )
    if candidates:
        return candidates[0], False

    access_node = AccessNode(
        access_node_uuid=str(uuid4()),
        label=ACCESS_NODE_LABEL,
        os_family="windows",
        provider_name=HELPER_PROVIDER_NAME,
        provider_version=HELPER_PROVIDER_VERSION,
        status="active",
    )
    db.add(access_node)
    db.flush()
    return access_node, True


def create_pairing_authorization(db: Session) -> WindowsHelperPairingAuthorizationResponse:
    access_node, _ = get_or_create_development_access_node(db)
    now = _now()
    for pending in db.scalars(
        select(WindowsHelperPairingAuthorization).where(
            WindowsHelperPairingAuthorization.access_node_id == access_node.id,
            WindowsHelperPairingAuthorization.status == "pending",
        )
    ):
        pending.status = "expired"
        db.add(pending)

    public_id = _new_public_id("p")
    secret = _new_secret()
    expires_at = now + PAIRING_TTL
    authorization = WindowsHelperPairingAuthorization(
        public_id=public_id,
        access_node_id=access_node.id,
        secret_digest=pairing_secret_digest(secret),
        status="pending",
        expires_at=expires_at,
    )
    db.add(authorization)
    db.commit()
    return WindowsHelperPairingAuthorizationResponse(
        access_node_id=UUID(access_node.access_node_uuid),
        access_node_label=access_node.label,
        pairing_id=public_id,
        pairing_code=f"{public_id}.{secret}",
        expires_at=expires_at,
    )


def complete_pairing(db: Session, request: PairingCompleteRequest) -> PairingCompleteResponse:
    try:
        public_id, secret = _split_composite(request.pairing_code, "p")
    except WindowsHelperServiceError as exc:
        raise WindowsHelperServiceError("pairing_denied", "Pairing authorization is invalid.", http_status=401) from exc

    authorization = db.scalar(
        select(WindowsHelperPairingAuthorization)
        .where(WindowsHelperPairingAuthorization.public_id == public_id)
        .with_for_update()
    )
    if authorization is None:
        raise WindowsHelperServiceError("pairing_denied", "Pairing authorization is invalid.", http_status=401)

    now = _now()
    if authorization.status != "pending":
        raise WindowsHelperServiceError("pairing_denied", "Pairing authorization is unavailable.", http_status=409)
    if _aware(authorization.expires_at) <= now:
        authorization.status = "expired"
        db.add(authorization)
        db.commit()
        raise WindowsHelperServiceError("pairing_expired", "Pairing authorization has expired.", http_status=410)
    if not hmac.compare_digest(authorization.secret_digest, pairing_secret_digest(secret)):
        raise WindowsHelperServiceError("pairing_denied", "Pairing authorization is invalid.", http_status=401)

    access_node = db.get(AccessNode, authorization.access_node_id)
    if access_node is None or access_node.access_node_uuid != str(request.access_node_id):
        raise WindowsHelperServiceError("access_node_mismatch", "Pairing Access Node does not match.", http_status=403)
    if access_node.status == "retired":
        raise WindowsHelperServiceError("access_node_unavailable", "Access Node is unavailable.", http_status=403)

    raw_token = _new_secret()
    credential_public_id = _new_public_id("c")
    credential = db.scalar(
        select(WindowsHelperCredential)
        .where(WindowsHelperCredential.access_node_id == access_node.id)
        .with_for_update()
    )
    if credential is None:
        credential = WindowsHelperCredential(
            public_id=credential_public_id,
            access_node_id=access_node.id,
            credential_version=1,
            token_digest=credential_token_digest(raw_token),
            status="active",
        )
        db.add(credential)
    else:
        credential.public_id = credential_public_id
        credential.credential_version += 1
        credential.token_digest = credential_token_digest(raw_token)
        credential.status = "active"
        credential.rotated_at = now
        credential.revoked_at = None
        credential.last_used_at = None
        db.add(credential)

    authorization.status = "consumed"
    authorization.consumed_at = now
    access_node.status = "active"
    access_node.provider_name = HELPER_PROVIDER_NAME
    access_node.provider_version = HELPER_PROVIDER_VERSION
    access_node.capabilities_json = _capabilities_json(request)
    db.add_all([authorization, access_node])
    db.commit()

    return PairingCompleteResponse(
        access_node_id=request.access_node_id,
        credential_id=credential.public_id,
        credential_version=credential.credential_version,
        credential_token=raw_token,
    )


def authenticate_credential(db: Session, authorization_header: str | None) -> WindowsHelperCredential:
    if not authorization_header:
        raise WindowsHelperServiceError("authentication_required", "Helper authentication is required.", http_status=401)
    scheme, separator, composite = authorization_header.partition(" ")
    if not separator or scheme != "PhotoOrganizerHelper":
        raise WindowsHelperServiceError("authentication_required", "Helper authentication is required.", http_status=401)
    try:
        public_id, secret = _split_composite(composite, "c")
    except WindowsHelperServiceError as exc:
        raise WindowsHelperServiceError("authentication_denied", "Helper authentication failed.", http_status=401) from exc

    credential = db.scalar(select(WindowsHelperCredential).where(WindowsHelperCredential.public_id == public_id))
    supplied_digest = credential_token_digest(secret)
    expected_digest = credential.token_digest if credential is not None else "0" * 64
    digest_matches = hmac.compare_digest(expected_digest, supplied_digest)
    if credential is None or not digest_matches or credential.status != "active" or credential.revoked_at is not None:
        raise WindowsHelperServiceError("authentication_denied", "Helper authentication failed.", http_status=401)
    return credential


def helper_session(db: Session, credential: WindowsHelperCredential) -> HelperSessionResponse:
    access_node = db.get(AccessNode, credential.access_node_id)
    if access_node is None or access_node.status == "retired":
        raise WindowsHelperServiceError("access_node_unavailable", "Access Node is unavailable.", http_status=403)
    helper_version = None
    if access_node.capabilities_json:
        try:
            helper_version = json.loads(access_node.capabilities_json).get("helper_version")
        except (TypeError, ValueError):
            helper_version = None
    return HelperSessionResponse(
        access_node_id=UUID(access_node.access_node_uuid),
        credential_id=credential.public_id,
        credential_version=credential.credential_version,
        helper_version=helper_version,
        last_seen_at=access_node.last_seen_at,
    )


def record_heartbeat(
    db: Session,
    credential: WindowsHelperCredential,
    request: HelperHeartbeatRequest,
) -> HelperHeartbeatResponse:
    access_node = db.get(AccessNode, credential.access_node_id)
    if access_node is None or access_node.access_node_uuid != str(request.access_node_id):
        raise WindowsHelperServiceError("access_node_mismatch", "Heartbeat Access Node does not match.", http_status=403)
    if access_node.status == "retired":
        raise WindowsHelperServiceError("access_node_unavailable", "Access Node is unavailable.", http_status=403)

    now = _now()
    credential.last_used_at = now
    access_node.last_seen_at = now
    access_node.status = "active"
    access_node.provider_name = HELPER_PROVIDER_NAME
    access_node.provider_version = HELPER_PROVIDER_VERSION
    access_node.capabilities_json = _capabilities_json(request)
    db.add_all([credential, access_node])
    db.commit()
    return HelperHeartbeatResponse(
        access_node_id=request.access_node_id,
        credential_id=credential.public_id,
        credential_version=credential.credential_version,
        helper_version=request.capability_identity.helper_version,
        last_seen_at=now,
    )


def revoke_credential(db: Session, access_node_uuid: UUID) -> WindowsHelperRevokeResponse:
    access_node = db.scalar(select(AccessNode).where(AccessNode.access_node_uuid == str(access_node_uuid)))
    if access_node is None:
        raise WindowsHelperServiceError("access_node_not_found", "Access Node was not found.", http_status=404)
    credential = db.scalar(
        select(WindowsHelperCredential).where(WindowsHelperCredential.access_node_id == access_node.id)
    )
    if credential is None:
        return WindowsHelperRevokeResponse(
            access_node_id=access_node_uuid, credential_id=None, status="absent", changed=False
        )
    changed = credential.status != "revoked" or credential.revoked_at is None
    if changed:
        credential.status = "revoked"
        credential.revoked_at = _now()
        db.add(credential)
        db.commit()
    return WindowsHelperRevokeResponse(
        access_node_id=access_node_uuid,
        credential_id=credential.public_id,
        status="revoked",
        changed=changed,
    )


def list_helper_status(db: Session) -> list[WindowsHelperAdminStatusResponse]:
    nodes = list(
        db.scalars(
            select(AccessNode)
            .where(
                AccessNode.os_family == "windows",
                AccessNode.provider_name == HELPER_PROVIDER_NAME,
            )
            .order_by(AccessNode.id)
        )
    )
    result: list[WindowsHelperAdminStatusResponse] = []
    for node in nodes:
        credential = db.scalar(
            select(WindowsHelperCredential).where(WindowsHelperCredential.access_node_id == node.id)
        )
        result.append(
            WindowsHelperAdminStatusResponse(
                access_node_id=UUID(node.access_node_uuid),
                access_node_label=node.label,
                access_node_status=node.status,
                provider_name=node.provider_name,
                provider_version=node.provider_version,
                credential_id=credential.public_id if credential else None,
                credential_version=credential.credential_version if credential else None,
                credential_status=credential.status if credential else None,
                credential_created_at=credential.created_at if credential else None,
                credential_rotated_at=credential.rotated_at if credential else None,
                credential_revoked_at=credential.revoked_at if credential else None,
                credential_last_used_at=credential.last_used_at if credential else None,
                last_seen_at=node.last_seen_at,
            )
        )
    return result
