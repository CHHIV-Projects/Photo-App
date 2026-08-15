"""Strict enrollment and authenticated-channel contracts for protocol v1."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .protocol import (
    HelperAcquireItemRequest,
    HelperCapabilityIdentity,
    HelperInventoryPageRequest,
    HelperProbeRequest,
    PROTOCOL_VERSION,
    require_protocol_version,
)


class _StrictChannelModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PairingCompleteRequest(_StrictChannelModel):
    protocol_version: int = PROTOCOL_VERSION
    pairing_code: str = Field(min_length=32, max_length=256)
    access_node_id: UUID
    capability_identity: HelperCapabilityIdentity

    @model_validator(mode="after")
    def _validate_binding(self) -> "PairingCompleteRequest":
        require_protocol_version(self.protocol_version)
        intended = self.capability_identity.intended_access_node_id
        if intended is None or intended != self.access_node_id:
            raise ValueError("capability identity must target the requested Access Node")
        return self


class PairingCompleteResponse(_StrictChannelModel):
    protocol_version: int = PROTOCOL_VERSION
    access_node_id: UUID
    credential_id: str = Field(min_length=1, max_length=64)
    credential_version: int = Field(ge=1)
    credential_token: str = Field(min_length=32, max_length=256)
    status: Literal["paired"] = "paired"


class HelperHeartbeatRequest(_StrictChannelModel):
    protocol_version: int = PROTOCOL_VERSION
    access_node_id: UUID
    capability_identity: HelperCapabilityIdentity

    @model_validator(mode="after")
    def _validate_binding(self) -> "HelperHeartbeatRequest":
        require_protocol_version(self.protocol_version)
        intended = self.capability_identity.intended_access_node_id
        if intended is None or intended != self.access_node_id:
            raise ValueError("capability identity must target the requested Access Node")
        return self


class HelperSessionResponse(_StrictChannelModel):
    protocol_version: int = PROTOCOL_VERSION
    access_node_id: UUID
    credential_id: str = Field(min_length=1, max_length=64)
    credential_version: int = Field(ge=1)
    credential_status: Literal["active"] = "active"
    helper_version: str | None = Field(default=None, max_length=32)
    last_seen_at: datetime | None = None


class HelperHeartbeatResponse(HelperSessionResponse):
    heartbeat_status: Literal["accepted"] = "accepted"


class ClaimedProbeOperation(_StrictChannelModel):
    operation_type: Literal["probe_source"] = "probe_source"
    operation_id: UUID
    lease_expires_at: datetime
    request: HelperProbeRequest


class ClaimedInventoryOperation(_StrictChannelModel):
    operation_type: Literal["inventory_page"] = "inventory_page"
    operation_id: UUID
    lease_expires_at: datetime
    request: HelperInventoryPageRequest


class ClaimedAcquireOperation(_StrictChannelModel):
    operation_type: Literal["acquire_item"] = "acquire_item"
    operation_id: UUID
    lease_expires_at: datetime
    request: HelperAcquireItemRequest


ClaimedHelperOperation = Annotated[
    ClaimedProbeOperation | ClaimedInventoryOperation | ClaimedAcquireOperation,
    Field(discriminator="operation_type"),
]


class HelperOperationClaimResponse(_StrictChannelModel):
    operation: ClaimedHelperOperation | None = None
    poll_after_seconds: int = Field(default=2, ge=1, le=30)


class HelperOperationCompletionResponse(_StrictChannelModel):
    operation_id: UUID
    operation_type: Literal["probe_source", "inventory_page", "acquire_item"]
    state: Literal["completed"] = "completed"
    result_digest: str = Field(min_length=71, max_length=71, pattern=r"^sha256:[0-9a-f]{64}$")
    idempotent_replay: bool = False


class HelperOperationFailureRequest(_StrictChannelModel):
    error_code: Literal[
        "operation_unsupported",
        "source_unavailable",
        "identity_changed",
        "invalid_cursor",
        "operation_failed",
        "source_changed",
        "placeholder_unavailable",
        "transfer_failed",
    ]


class HelperOperationFailureResponse(_StrictChannelModel):
    operation_id: UUID
    state: Literal["failed"] = "failed"
    error_code: str = Field(min_length=1, max_length=64)


class HelperAcquisitionStatusResponse(_StrictChannelModel):
    acquisition_run_id: UUID
    acquisition_item_id: UUID
    state: Literal["pending", "transferring", "verifying", "ready", "failed"]
    committed_offset: int = Field(ge=0)
    expected_size_bytes: int = Field(ge=1)
    maximum_chunk_bytes: int = Field(ge=1)


class HelperChunkCommitResponse(_StrictChannelModel):
    acquisition_run_id: UUID
    acquisition_item_id: UUID
    accepted_offset: int = Field(ge=0)
    committed_offset: int = Field(ge=0)
    bytes_committed: int = Field(ge=0)
    idempotent_replay: bool = False
