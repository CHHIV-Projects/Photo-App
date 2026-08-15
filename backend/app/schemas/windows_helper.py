"""Redacted API schemas for Windows Helper administration."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.windows_helper_shared.protocol import (
    DEFAULT_INVENTORY_PAGE_SIZE,
    HelperAcquireItemResponse,
    HelperInventoryPageResponse,
    HelperProbeResponse,
    ProbeMode,
    SourceType,
)


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


class CreateWindowsHelperProbeOperationRequest(_StrictModel):
    access_node_id: UUID
    source_type: SourceType
    provider_native_root: str = Field(min_length=3, max_length=4096)
    probe_mode: ProbeMode = ProbeMode.SETUP
    source_profile_id: int | None = Field(default=None, ge=1)


class CreateWindowsHelperInventoryOperationRequest(_StrictModel):
    source_profile_id: int = Field(ge=1)
    probe_operation_id: UUID
    page_size: int = Field(default=DEFAULT_INVENTORY_PAGE_SIZE, ge=1, le=100)
    inventory_generation: UUID | None = None
    cursor: str | None = Field(default=None, min_length=1, max_length=256)


class WindowsHelperOperationCreatedResponse(_StrictModel):
    operation_id: UUID
    operation_type: Literal["probe_source", "inventory_page", "acquire_item"]
    state: Literal["pending"]
    request_digest: str
    expires_at: datetime
    source_endpoint_id: int | None = None
    source_profile_id: int | None = None


class WindowsInventoryCandidate(_StrictModel):
    candidate_reference: str
    provider_native_relative_path: str
    provider_native_full_path: str
    filename: str
    size_bytes: int | None = None
    modified_time_ns: int | None = None
    entry_kind: str
    eligibility: Literal["eligible", "rejected"]
    eligibility_reason: str


class WindowsHelperOperationStatusResponse(_StrictModel):
    operation_id: UUID
    operation_type: Literal["probe_source", "inventory_page", "acquire_item"]
    state: Literal["pending", "claimed", "completed", "failed", "expired"]
    request_digest: str
    result_digest: str | None = None
    created_at: datetime
    claimed_at: datetime | None = None
    completed_at: datetime | None = None
    expires_at: datetime
    lease_expires_at: datetime | None = None
    error_code: str | None = None
    source_endpoint_id: int | None = None
    source_profile_id: int | None = None
    probe_result: HelperProbeResponse | None = None
    inventory_result: HelperInventoryPageResponse | None = None
    inventory_candidates: list[WindowsInventoryCandidate] = Field(default_factory=list)
    acquire_result: HelperAcquireItemResponse | None = None


class WindowsHelperAdminStatusListResponse(_StrictModel):
    helpers: list[WindowsHelperAdminStatusResponse] = Field(default_factory=list)
