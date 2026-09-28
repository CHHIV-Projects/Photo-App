"""Secret-free application side of operator-assisted NAS registration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import ipaddress
import json
import re
import secrets
import socket
import struct
from typing import Callable
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.nas_registration import (
    NasApplianceRegistration,
    NasPendingRegistration,
    NasShareRegistration,
)
from app.models.source_endpoint import SourceEndpoint
from app.services.nas_registration.schemas import (
    CreateNasPendingRegistrationRequest,
    NasInstallerManifestResponse,
    ExistingNasAdoptionResponse,
    NasDiscoveryCandidate,
    NasDiscoveryResponse,
    NasPendingRegistrationResponse,
    NasRegistrationCompletionResponse,
    NasRegistrationListResponse,
    NasRegistrationMessage,
    NasRegistrationSummary,
)
from app.services.source_identity.linux_source_access import LinuxSourceBrokerClient
from app.services.source_identity.identity_fingerprint import REGISTERED_NAS_SHARE_FINGERPRINT_VERSION


PENDING_TTL = timedelta(hours=2)
REGISTER_PROGRAM = "/usr/local/lib/photo-organizer/register-nas-location.py"
LEGACY_NAS_FINGERPRINT_VERSION = "source_endpoint_identity_v1"
LEGACY_LOCATION_ID = "linux-nas-photo-organizer"
LEGACY_APPLIANCE_UUID = uuid5(NAMESPACE_URL, "photo-organizer:nas-appliance:linux-nas-photo-organizer")
LEGACY_SHARE_UUID = uuid5(NAMESPACE_URL, "photo-organizer:nas-share:linux-nas-photo-organizer")
_HOST_LABEL = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?")
_SHARE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9._-])?")
_DISPLAY = re.compile(r"[^\x00-\x1f\x7f]{1,255}")


class NasRegistrationError(RuntimeError):
    def __init__(self, code: str, message: str, *, http_status: int = 409) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def normalize_host(value: str) -> str:
    host = value.strip().rstrip(".").casefold()
    if not host or any(character in host for character in "/\\:@[]\x00"):
        raise NasRegistrationError("nas_host_invalid", "Enter one NAS hostname or IP address.", http_status=422)
    try:
        return ipaddress.ip_address(host).compressed
    except ValueError:
        labels = host.split(".")
        if len(host) > 253 or any(not _HOST_LABEL.fullmatch(label) for label in labels):
            raise NasRegistrationError("nas_host_invalid", "Enter one NAS hostname or IP address.", http_status=422)
        return host


def normalize_share(value: str) -> tuple[str, str]:
    share = value.strip()
    if not _SHARE.fullmatch(share) or share.endswith("$"):
        raise NasRegistrationError(
            "nas_share_invalid",
            "Enter one non-administrative SMB share name without a path.",
            http_status=422,
        )
    return share, share.casefold()


def normalize_display(value: str, field: str) -> str:
    display = " ".join(value.strip().split())
    if not _DISPLAY.fullmatch(display) or any(character in display for character in "`$\\/"):
        raise NasRegistrationError(f"{field}_invalid", f"Enter a valid {field.replace('_', ' ')}.", http_status=422)
    return display


def _versioned_hash(version: str, parts: list[str]) -> str:
    payload = json.dumps({"parts": parts, "version": version}, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _request_digest(payload: dict[str, str]) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _recv_exact(connection: socket.socket, size: int) -> bytes:
    value = b""
    while len(value) < size:
        chunk = connection.recv(size - len(value))
        if not chunk:
            raise OSError("SMB peer closed the negotiate response.")
        value += chunk
    return value


def probe_smb_server_guid(host: str) -> bytes:
    """Return one unauthenticated SMB2 ServerGuid using a bounded negotiate."""

    dialects = (0x0202, 0x0210, 0x0300, 0x0302)
    client_guid = secrets.token_bytes(16)
    header = struct.pack(
        "<4sHHIHHIIQIIQ16s",
        b"\xfeSMB", 64, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, b"\x00" * 16,
    )
    body = struct.pack("<HHHHI16sQ", 36, len(dialects), 1, 0, 0, client_guid, 0)
    body += b"".join(struct.pack("<H", value) for value in dialects)
    request = header + body
    frame = bytes((0,)) + len(request).to_bytes(3, "big") + request
    try:
        with socket.create_connection((host, 445), timeout=3.0) as connection:
            connection.settimeout(3.0)
            connection.sendall(frame)
            prefix = _recv_exact(connection, 4)
            if prefix[0] != 0:
                raise OSError("Unexpected NetBIOS response.")
            size = int.from_bytes(prefix[1:], "big")
            if size < 128 or size > 1024 * 1024:
                raise OSError("Unexpected SMB response size.")
            response = _recv_exact(connection, size)
    except (OSError, TimeoutError) as exc:
        raise NasRegistrationError(
            "nas_identity_unavailable",
            "The NAS did not provide bounded SMB identity evidence.",
        ) from exc
    if response[:4] != b"\xfeSMB" or len(response) < 128:
        raise NasRegistrationError("nas_identity_invalid", "The NAS SMB identity response was invalid.")
    status = struct.unpack_from("<I", response, 8)[0]
    command = struct.unpack_from("<H", response, 12)[0]
    flags = struct.unpack_from("<I", response, 16)[0]
    structure_size = struct.unpack_from("<H", response, 64)[0]
    server_guid = response[72:88]
    if (
        status != 0
        or command != 0
        or not flags & 1
        or structure_size != 65
        or len(server_guid) != 16
        or server_guid == b"\x00" * 16
    ):
        raise NasRegistrationError("nas_identity_invalid", "The NAS SMB identity response was invalid.")
    return server_guid


def _guid_evidence(host: str, probe: Callable[[str], bytes]) -> tuple[str, str]:
    observations = [probe(host) for _ in range(2)]
    if observations[0] != observations[1]:
        raise NasRegistrationError("nas_identity_ambiguous", "The NAS returned inconsistent appliance identity.")
    digest = hashlib.sha256(observations[0]).hexdigest()
    return "sha256:" + digest, "sha256:…" + digest[-12:]


def ensure_existing_nas_adoption(db: Session) -> None:
    """Adopt the accepted existing NAS without rewriting Endpoint/Profile identity."""

    existing_share = db.scalar(
        select(NasShareRegistration).where(NasShareRegistration.location_id == LEGACY_LOCATION_ID)
    )
    if existing_share is not None:
        return
    endpoint = db.scalar(select(SourceEndpoint).where(SourceEndpoint.source_type == "nas").order_by(SourceEndpoint.id))
    if endpoint is None or not endpoint.identity_fingerprint_hash:
        return
    appliance = NasApplianceRegistration(
        registration_uuid=str(LEGACY_APPLIANCE_UUID),
        friendly_name="Photo Organizer NAS",
        server_guid_hash="sha256:" + "0" * 64,
        server_guid_masked="unverified",
        network_host="192.168.1.171",
        network_host_normalized="192.168.1.171",
        status="active",
    )
    db.add(appliance)
    db.flush()
    db.add(
        NasShareRegistration(
            registration_uuid=str(LEGACY_SHARE_UUID),
            nas_appliance_id=appliance.id,
            location_id=LEGACY_LOCATION_ID,
            display_name="Photo Organizer NAS",
            share_name="PhotoOrganizer",
            share_name_normalized="photoorganizer",
            identity_fingerprint_hash=endpoint.identity_fingerprint_hash,
            identity_fingerprint_version=endpoint.identity_fingerprint_version or LEGACY_NAS_FINGERPRINT_VERSION,
            source_endpoint_id=endpoint.id,
            status="registered",
            installed_at=_now(),
        )
    )
    db.commit()


def bind_existing_nas_server_guid(db: Session, *, server_guid_hash: str, server_guid_masked: str) -> None:
    """Bind proven ServerGuid evidence to the compatibility appliance exactly once."""

    appliance = db.scalar(
        select(NasApplianceRegistration).where(
            NasApplianceRegistration.registration_uuid == str(LEGACY_APPLIANCE_UUID)
        )
    )
    if appliance is None:
        raise NasRegistrationError("existing_nas_adoption_missing", "Existing NAS adoption is unavailable.")
    if appliance.server_guid_hash not in {"sha256:" + "0" * 64, server_guid_hash}:
        raise NasRegistrationError("nas_identity_conflict", "Existing NAS appliance identity conflicts.")
    appliance.server_guid_hash = server_guid_hash
    appliance.server_guid_masked = server_guid_masked
    db.commit()


def adopt_existing_nas_identity(
    db: Session,
    *,
    probe: Callable[[str], bytes] = probe_smb_server_guid,
    broker_client: LinuxSourceBrokerClient | None = None,
) -> ExistingNasAdoptionResponse:
    """Bind stable SMB evidence after the generalized host registry is active."""

    ensure_existing_nas_adoption(db)
    server_guid_hash, server_guid_masked = _guid_evidence("192.168.1.171", probe)
    client = broker_client or LinuxSourceBrokerClient()
    try:
        response = client.probe(location_id=LEGACY_LOCATION_ID, source_type="nas", relative_root="")
    except Exception as exc:
        raise NasRegistrationError(
            "existing_nas_not_available",
            "Existing Photo Organizer NAS is not available through the generalized broker.",
        ) from exc
    matches = [item for item in response.locations if item.location_id == LEGACY_LOCATION_ID]
    share = db.scalar(
        select(NasShareRegistration).where(NasShareRegistration.location_id == LEGACY_LOCATION_ID)
    )
    if (
        len(matches) != 1
        or matches[0].status != "available"
        or share is None
        or matches[0].identity_fingerprint_hash != share.identity_fingerprint_hash
        or matches[0].identity_fingerprint_version != share.identity_fingerprint_version
        or share.source_endpoint_id is None
    ):
        raise NasRegistrationError(
            "existing_nas_identity_mismatch",
            "Existing Photo Organizer NAS identity is not exact after generalized adoption.",
        )
    bind_existing_nas_server_guid(
        db,
        server_guid_hash=server_guid_hash,
        server_guid_masked=server_guid_masked,
    )
    return ExistingNasAdoptionResponse(
        appliance_id=LEGACY_APPLIANCE_UUID,
        share_id=LEGACY_SHARE_UUID,
        server_guid_masked=server_guid_masked,
        endpoint_id=share.source_endpoint_id,
    )


def create_pending_registration(
    db: Session,
    body: CreateNasPendingRegistrationRequest,
    *,
    probe: Callable[[str], bytes] = probe_smb_server_guid,
) -> NasPendingRegistrationResponse:
    host = normalize_host(body.network_host)
    share, share_normalized = normalize_share(body.share_name)
    appliance_name = normalize_display(body.appliance_name, "appliance_name")
    location_name = normalize_display(body.location_name, "location_name")
    server_guid_hash, server_guid_masked = _guid_evidence(host, probe)
    existing_appliance = db.scalar(
        select(NasApplianceRegistration).where(
            NasApplianceRegistration.server_guid_hash == server_guid_hash,
            NasApplianceRegistration.status == "active",
        )
    )
    conflicting_host = db.scalar(
        select(NasApplianceRegistration).where(
            NasApplianceRegistration.network_host_normalized == host,
            NasApplianceRegistration.status == "active",
            NasApplianceRegistration.server_guid_hash != server_guid_hash,
        )
    )
    if conflicting_host is not None:
        raise NasRegistrationError(
            "nas_identity_conflict",
            "A different NAS appliance is already registered at this network address.",
        )
    duplicate: NasShareRegistration | None = None
    if existing_appliance is not None:
        duplicate = db.scalar(
            select(NasShareRegistration).where(
                NasShareRegistration.nas_appliance_id == existing_appliance.id,
                NasShareRegistration.share_name_normalized == share_normalized,
                NasShareRegistration.status == "registered",
            )
        )
        if duplicate is not None and existing_appliance.network_host_normalized == host:
            raise NasRegistrationError(
                "nas_share_already_registered",
                "This NAS share is already registered.",
            )
    operation = "update_network_host" if duplicate is not None else "create_share"
    request_identity = {
        "appliance_name": appliance_name,
        "host": host,
        "location_name": location_name,
        "server_guid_hash": server_guid_hash,
        "share": share,
        "registered_appliance": existing_appliance.registration_uuid if existing_appliance is not None else "new",
        "operation": operation,
    }
    digest = _request_digest(request_identity)
    now = _now()
    reusable = db.scalar(
        select(NasPendingRegistration).where(
            NasPendingRegistration.request_digest == digest,
            NasPendingRegistration.state == "pending",
            NasPendingRegistration.expires_at > now,
        )
    )
    if reusable is not None:
        return _pending_response(reusable)
    proposed_appliance_uuid = (
        UUID(existing_appliance.registration_uuid) if existing_appliance is not None else uuid4()
    )
    proposed_share_uuid = UUID(duplicate.registration_uuid) if duplicate is not None else uuid4()
    location_id = duplicate.location_id if duplicate is not None else "linux-nas-" + proposed_share_uuid.hex[:16]
    identity_hash = duplicate.identity_fingerprint_hash if duplicate is not None else _versioned_hash(
        REGISTERED_NAS_SHARE_FINGERPRINT_VERSION,
        [str(proposed_appliance_uuid), server_guid_hash, share_normalized],
    )
    reusable = NasPendingRegistration(
            public_id=str(uuid4()),
            proposed_appliance_uuid=str(proposed_appliance_uuid),
            proposed_share_uuid=str(proposed_share_uuid),
            operation=operation,
            existing_appliance_id=existing_appliance.id if existing_appliance is not None else None,
            existing_share_id=duplicate.id if duplicate is not None else None,
            requested_host=host,
            requested_host_normalized=host,
            appliance_name=appliance_name,
            share_name=share,
            share_name_normalized=share_normalized,
            location_name=location_name,
            location_id=location_id,
            server_guid_hash=server_guid_hash,
            server_guid_masked=server_guid_masked,
            identity_fingerprint_hash=identity_hash,
            identity_fingerprint_version=REGISTERED_NAS_SHARE_FINGERPRINT_VERSION,
            request_digest=digest,
            state="pending",
            expires_at=now + PENDING_TTL,
    )
    db.add(reusable)
    db.commit()
    db.refresh(reusable)
    return _pending_response(reusable)


def _pending_response(pending: NasPendingRegistration) -> NasPendingRegistrationResponse:
    return NasPendingRegistrationResponse(
        registration_id=UUID(pending.public_id),
        state=pending.state,  # type: ignore[arg-type]
        appliance_name=pending.appliance_name,
        location_name=pending.location_name,
        share_name=pending.share_name,
        server_guid_masked=pending.server_guid_masked,
        reuses_registered_appliance=pending.existing_appliance_id is not None,
        operation=pending.operation,  # type: ignore[arg-type]
        expires_at=pending.expires_at,
        operator_command=f"sudo {REGISTER_PROGRAM} install --registration-id {pending.public_id}",
        messages=[
            NasRegistrationMessage(
                code="operator_install_required",
                message="Run the exact operator command on the Photo Organizer server to enter credentials and activate this NAS location.",
            )
        ],
    )


def get_installer_manifest(db: Session, registration_id: UUID) -> NasInstallerManifestResponse:
    pending = db.scalar(
        select(NasPendingRegistration).where(NasPendingRegistration.public_id == str(registration_id))
    )
    if pending is None:
        raise NasRegistrationError("nas_registration_not_found", "Pending NAS registration was not found.", http_status=404)
    if pending.state != "pending":
        raise NasRegistrationError("nas_registration_not_pending", "Pending NAS registration is no longer installable.")
    if _aware(pending.expires_at) <= _now():
        pending.state = "expired"
        db.commit()
        raise NasRegistrationError("nas_registration_expired", "Pending NAS registration expired.")
    return NasInstallerManifestResponse(
        registration_id=UUID(pending.public_id),
        proposed_appliance_id=UUID(pending.proposed_appliance_uuid),
        proposed_share_id=UUID(pending.proposed_share_uuid),
        operation=pending.operation,  # type: ignore[arg-type]
        requested_host=pending.requested_host,
        appliance_name=pending.appliance_name,
        share_name=pending.share_name,
        location_name=pending.location_name,
        location_id=pending.location_id,
        server_guid_hash=pending.server_guid_hash,
        server_guid_masked=pending.server_guid_masked,
        identity_fingerprint_hash=pending.identity_fingerprint_hash,
        identity_fingerprint_version=pending.identity_fingerprint_version,
        request_digest=pending.request_digest,
        expires_at=pending.expires_at,
    )


def complete_registration(
    db: Session,
    registration_id: UUID,
    *,
    broker_client: LinuxSourceBrokerClient | None = None,
) -> NasRegistrationCompletionResponse:
    pending = db.scalar(
        select(NasPendingRegistration).where(NasPendingRegistration.public_id == str(registration_id))
    )
    if pending is None:
        raise NasRegistrationError("nas_registration_not_found", "Pending NAS registration was not found.", http_status=404)
    if pending.state == "completed":
        share = db.scalar(
            select(NasShareRegistration).where(
                NasShareRegistration.registration_uuid == pending.proposed_share_uuid
            )
        )
        if share is None:
            raise NasRegistrationError("nas_registration_inconsistent", "Completed NAS registration is inconsistent.")
        appliance = db.get(NasApplianceRegistration, share.nas_appliance_id)
        assert appliance is not None
        return NasRegistrationCompletionResponse(
            registration_id=registration_id,
            location_id=share.location_id,
            appliance_id=UUID(appliance.registration_uuid),
            share_id=UUID(share.registration_uuid),
            created_appliance=False,
            created_share=False,
        )
    if pending.state != "pending" or _aware(pending.expires_at) <= _now():
        raise NasRegistrationError("nas_registration_not_pending", "Pending NAS registration is not completable.")
    client = broker_client or LinuxSourceBrokerClient()
    try:
        response = client.probe(location_id=pending.location_id, source_type="nas", relative_root="")
    except Exception as exc:
        raise NasRegistrationError(
            "nas_installation_not_verified",
            "The installed NAS location is not available through the Source identity broker.",
        ) from exc
    matches = [item for item in response.locations if item.location_id == pending.location_id]
    if (
        len(matches) != 1
        or matches[0].status != "available"
        or matches[0].identity_fingerprint_hash != pending.identity_fingerprint_hash
        or matches[0].identity_fingerprint_version != pending.identity_fingerprint_version
    ):
        raise NasRegistrationError(
            "nas_installation_identity_mismatch",
            "The installed NAS location does not match the immutable pending registration.",
        )
    appliance = (
        db.get(NasApplianceRegistration, pending.existing_appliance_id)
        if pending.existing_appliance_id is not None
        else None
    )
    created_appliance = appliance is None
    if appliance is None:
        appliance = NasApplianceRegistration(
            registration_uuid=pending.proposed_appliance_uuid,
            friendly_name=pending.appliance_name,
            server_guid_hash=pending.server_guid_hash,
            server_guid_masked=pending.server_guid_masked,
            network_host=pending.requested_host,
            network_host_normalized=pending.requested_host_normalized,
            status="active",
        )
        db.add(appliance)
        db.flush()
    elif appliance.server_guid_hash != pending.server_guid_hash:
        raise NasRegistrationError("nas_identity_conflict", "Registered NAS appliance identity changed.")
    if pending.operation == "update_network_host":
        share = db.get(NasShareRegistration, pending.existing_share_id)
        if (
            share is None
            or share.nas_appliance_id != appliance.id
            or share.registration_uuid != pending.proposed_share_uuid
            or share.location_id != pending.location_id
            or share.identity_fingerprint_hash != pending.identity_fingerprint_hash
        ):
            raise NasRegistrationError("nas_registration_inconsistent", "Existing NAS share registration changed.")
        appliance.network_host = pending.requested_host
        appliance.network_host_normalized = pending.requested_host_normalized
        db.add(appliance)
        created_share = False
    else:
        share = NasShareRegistration(
            registration_uuid=pending.proposed_share_uuid,
            nas_appliance_id=appliance.id,
            location_id=pending.location_id,
            display_name=pending.location_name,
            share_name=pending.share_name,
            share_name_normalized=pending.share_name_normalized,
            identity_fingerprint_hash=pending.identity_fingerprint_hash,
            identity_fingerprint_version=pending.identity_fingerprint_version,
            status="registered",
            installed_at=_now(),
        )
        db.add(share)
        created_share = True
    pending.state = "completed"
    pending.completed_at = _now()
    db.commit()
    return NasRegistrationCompletionResponse(
        registration_id=registration_id,
        location_id=share.location_id,
        appliance_id=UUID(appliance.registration_uuid),
        share_id=UUID(share.registration_uuid),
        created_appliance=created_appliance,
        created_share=created_share,
    )


def list_registrations(
    db: Session,
    *,
    broker_client: LinuxSourceBrokerClient | None = None,
) -> NasRegistrationListResponse:
    client = broker_client or LinuxSourceBrokerClient()
    try:
        locations = {item.location_id: item for item in client.list_locations().locations}
    except Exception:
        locations = {}
    shares = list(db.scalars(select(NasShareRegistration).order_by(NasShareRegistration.id)))
    items: list[NasRegistrationSummary] = []
    for share in shares:
        appliance = db.get(NasApplianceRegistration, share.nas_appliance_id)
        if appliance is None:
            continue
        location = locations.get(share.location_id)
        if location is None:
            availability = "blocked"
            message = "Registered NAS host configuration is unavailable."
        elif location.status == "available":
            availability = "available"
            message = "Registered NAS location is available."
        elif any(item.code.endswith("mismatch") for item in location.blockers):
            availability = "identity_conflict"
            message = "Registered NAS identity conflicts with current host evidence."
        else:
            availability = "unavailable"
            message = "Registered NAS location is not currently available."
        items.append(
            NasRegistrationSummary(
                appliance_id=UUID(appliance.registration_uuid),
                share_id=UUID(share.registration_uuid),
                appliance_name=appliance.friendly_name,
                location_name=share.display_name,
                share_name=share.share_name,
                location_id=share.location_id,
                registration_status=share.status,  # type: ignore[arg-type]
                availability=availability,  # type: ignore[arg-type]
                status_message=message,
                source_endpoint_id=share.source_endpoint_id,
            )
        )
    return NasRegistrationListResponse(registrations=items)


def discover_nas(
    *,
    broker_client: LinuxSourceBrokerClient | None = None,
) -> NasDiscoveryResponse:
    """Return advisory mDNS results; never create durable or host state."""

    client = broker_client or LinuxSourceBrokerClient()
    try:
        result = client.discover_nas()
    except Exception:
        return NasDiscoveryResponse(
            status="unavailable",
            messages=[NasRegistrationMessage(
                code="nas_discovery_unavailable",
                message="NAS discovery is unavailable; enter the NAS manually.",
            )],
        )
    return NasDiscoveryResponse(
        status="completed",
        candidates=[
            NasDiscoveryCandidate(
                candidate_id=item.candidate_id,
                suggested_name=item.suggested_name,
                network_host=item.network_host,
                address_hint=item.address_hint,
            )
            for item in result.candidates
        ],
        messages=[NasRegistrationMessage(code=item.code, message=item.message) for item in result.blockers],
    )
