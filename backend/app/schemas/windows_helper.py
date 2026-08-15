"""Redacted API schemas for Windows Helper administration."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateWindowsHelperPairingRequest(_StrictModel):
    """Intentionally empty: the one approved Development identity is fixed."""


class WindowsHelperPairingAuthorizationResponse(_StrictModel):
    access_node_id: UUID
    access_node_label: str
    pairing_id: str
    pairing_code: str
    expires_at: datetime
    status: Literal["pending"] = "pending"


class WindowsHelperRevokeRequest(_StrictModel):
    access_node_id: UUID


class WindowsHelperAdminStatusResponse(_StrictModel):
    access_node_id: UUID
    access_node_label: str
    access_node_status: str
    provider_name: str | None = None
    provider_version: str | None = None
    credential_id: str | None = None
    credential_version: int | None = None
    credential_status: str | None = None
    credential_created_at: datetime | None = None
    credential_rotated_at: datetime | None = None
    credential_revoked_at: datetime | None = None
    credential_last_used_at: datetime | None = None
    last_seen_at: datetime | None = None


class WindowsHelperRevokeResponse(_StrictModel):
    access_node_id: UUID
    credential_id: str | None = None
    status: Literal["revoked", "absent"]
    changed: bool


class WindowsHelperAdminStatusListResponse(_StrictModel):
    helpers: list[WindowsHelperAdminStatusResponse] = Field(default_factory=list)
