"""Bounded client and safe schemas for Linux stable-mount Source access."""

from __future__ import annotations

import json
import socket
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


LINUX_SOURCE_BROKER_PROTOCOL_VERSION = 1
LINUX_SOURCE_PROVIDER_NAME = "linux_stable_mount_v1"
LINUX_SOURCE_PROVIDER_VERSION = "1"
DEFAULT_LINUX_SOURCE_BROKER_SOCKET = "/run/photo-organizer-source-access/broker.sock"
DEFAULT_LINUX_SOURCE_BROKER_TIMEOUT_SECONDS = 4.0
MAX_BROKER_MESSAGE_BYTES = 256 * 1024


class LinuxSourceAccessError(RuntimeError):
    """Raised when the broker cannot return a safe structured response."""


class LinuxSourceBrokerMessage(BaseModel):
    """One operator-safe broker warning or blocker."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str


class LinuxSourceAccessNodeEvidence(BaseModel):
    """Sanitized stable host identity returned by the broker."""

    model_config = ConfigDict(extra="forbid")

    access_node_id: str
    label: str
    os_family: Literal["linux"] = "linux"
    host_fingerprint_hash: str
    host_fingerprint_masked: str
    capabilities: dict[str, bool] = Field(default_factory=dict)


class LinuxSourceMountEvidence(BaseModel):
    """Sanitized filesystem evidence needed by the application provider."""

    model_config = ConfigDict(extra="forbid")

    filesystem_type: str
    mount_source_masked: str
    major_minor: str
    filesystem_uuid_hash: str | None = None
    filesystem_uuid_masked: str | None = None
    canonical_nas_source: str | None = None
    authoritative_mount_verified: bool = False
    namespace_mapping_verified: bool = False
    readable: bool = False


class LinuxSourceLocationEvidence(BaseModel):
    """One broker-authoritative stable-mount location or probe result."""

    model_config = ConfigDict(extra="forbid")

    location_id: str
    source_type: Literal["local", "nas"]
    display_name: str
    status: Literal["available", "unavailable", "blocked", "error"]
    status_message: str
    host_slot: str
    host_observed_path: str | None = None
    runtime_slot: str
    runtime_root: str | None = None
    relative_root: str = ""
    filesystem_boundary_type: Literal[
        "local_volume_root",
        "local_folder",
        "nas_share_root",
        "nas_share_folder",
    ]
    identity_fingerprint_hash: str | None = None
    identity_fingerprint_version: str | None = None
    identity_identifier_type: str | None = None
    identity_identifier_masked: str | None = None
    access_node: LinuxSourceAccessNodeEvidence
    mount: LinuxSourceMountEvidence | None = None
    blockers: list[LinuxSourceBrokerMessage] = Field(default_factory=list)
    warnings: list[LinuxSourceBrokerMessage] = Field(default_factory=list)


class LinuxSourceBrokerResponse(BaseModel):
    """Versioned broker response envelope."""

    model_config = ConfigDict(extra="forbid")

    protocol_version: Literal[1] = LINUX_SOURCE_BROKER_PROTOCOL_VERSION
    action: Literal["list_locations", "probe"]
    provider_name: Literal["linux_stable_mount_v1"] = LINUX_SOURCE_PROVIDER_NAME
    provider_version: str = LINUX_SOURCE_PROVIDER_VERSION
    locations: list[LinuxSourceLocationEvidence] = Field(default_factory=list)
    blockers: list[LinuxSourceBrokerMessage] = Field(default_factory=list)


class LinuxSourceLocationSummary(BaseModel):
    """Browser-safe server-discovered Linux location."""

    location_id: str
    source_type: Literal["local", "nas"]
    display_name: str
    availability: Literal["available", "unavailable", "blocked"]
    status_message: str
    relative_root_supported: bool = True


class LinuxSourceLocationsResponse(BaseModel):
    """Browser-safe location discovery result."""

    os_family: Literal["linux"] = "linux"
    provider_name: str = LINUX_SOURCE_PROVIDER_NAME
    provider_version: str = LINUX_SOURCE_PROVIDER_VERSION
    locations: list[LinuxSourceLocationSummary] = Field(default_factory=list)
    blockers: list[LinuxSourceBrokerMessage] = Field(default_factory=list)


class LinuxSourceBrokerClientProtocol(Protocol):
    """Injection seam used by the Linux provider and focused tests."""

    def list_locations(self) -> LinuxSourceBrokerResponse:
        """Return bounded configured stable-mount locations."""

    def probe(
        self,
        *,
        location_id: str,
        source_type: str,
        relative_root: str,
    ) -> LinuxSourceBrokerResponse:
        """Probe one configured location and contained relative root."""


class LinuxSourceBrokerClient:
    """Small JSON-lines Unix-socket client with strict size and time bounds."""

    def __init__(
        self,
        *,
        socket_path: str = DEFAULT_LINUX_SOURCE_BROKER_SOCKET,
        timeout_seconds: float = DEFAULT_LINUX_SOURCE_BROKER_TIMEOUT_SECONDS,
    ) -> None:
        self._socket_path = socket_path
        self._timeout_seconds = timeout_seconds

    def list_locations(self) -> LinuxSourceBrokerResponse:
        return self._request({"action": "list_locations"})

    def probe(
        self,
        *,
        location_id: str,
        source_type: str,
        relative_root: str,
    ) -> LinuxSourceBrokerResponse:
        return self._request(
            {
                "action": "probe",
                "location_id": location_id,
                "source_type": source_type,
                "relative_root": relative_root,
            }
        )

    def _request(self, payload: dict[str, Any]) -> LinuxSourceBrokerResponse:
        request = {
            "protocol_version": LINUX_SOURCE_BROKER_PROTOCOL_VERSION,
            **payload,
        }
        encoded = json.dumps(request, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
        if len(encoded) > MAX_BROKER_MESSAGE_BYTES:
            raise LinuxSourceAccessError("Linux Source broker request exceeds the safe size limit.")

        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(self._timeout_seconds)
                connection.connect(self._socket_path)
                connection.sendall(encoded)
                raw = _receive_one_line(connection)
        except (TimeoutError, socket.timeout) as exc:
            raise LinuxSourceAccessError("Linux Source broker request timed out.") from exc
        except (FileNotFoundError, ConnectionRefusedError, PermissionError, OSError) as exc:
            raise LinuxSourceAccessError("Linux Source broker is unavailable.") from exc

        try:
            decoded = json.loads(raw.decode("utf-8"))
            return LinuxSourceBrokerResponse.model_validate(decoded)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise LinuxSourceAccessError("Linux Source broker returned a malformed response.") from exc


def browser_safe_locations(response: LinuxSourceBrokerResponse) -> LinuxSourceLocationsResponse:
    """Remove paths, mount identity, fingerprints, and host identifiers for normal UI use."""
    locations: list[LinuxSourceLocationSummary] = []
    for location in response.locations:
        availability: Literal["available", "unavailable", "blocked"]
        availability = location.status if location.status in {"available", "unavailable", "blocked"} else "blocked"
        locations.append(
            LinuxSourceLocationSummary(
                location_id=location.location_id,
                source_type=location.source_type,
                display_name=location.display_name,
                availability=availability,
                status_message=location.status_message,
            )
        )
    return LinuxSourceLocationsResponse(
        provider_name=response.provider_name,
        provider_version=response.provider_version,
        locations=locations,
        blockers=response.blockers,
    )


def _receive_one_line(connection: socket.socket) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = connection.recv(min(65536, MAX_BROKER_MESSAGE_BYTES + 1 - total))
        if not chunk:
            break
        newline = chunk.find(b"\n")
        if newline >= 0:
            chunks.append(chunk[:newline])
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > MAX_BROKER_MESSAGE_BYTES:
            raise LinuxSourceAccessError("Linux Source broker response exceeds the safe size limit.")
    raw = b"".join(chunks)
    if not raw:
        raise LinuxSourceAccessError("Linux Source broker returned an empty response.")
    if len(raw) > MAX_BROKER_MESSAGE_BYTES:
        raise LinuxSourceAccessError("Linux Source broker response exceeds the safe size limit.")
    return raw
