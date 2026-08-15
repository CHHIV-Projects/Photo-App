"""Strict enrollment and authenticated-channel contracts for protocol v1."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .protocol import HelperCapabilityIdentity, PROTOCOL_VERSION, require_protocol_version


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
