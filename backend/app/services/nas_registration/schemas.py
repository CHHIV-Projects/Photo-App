"""Browser-safe schemas for operator-assisted NAS registration."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NasRegistrationMessage(BaseModel):
    code: str
    message: str


class CreateNasPendingRegistrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    network_host: str = Field(min_length=1, max_length=255)
    share_name: str = Field(min_length=1, max_length=255)
    appliance_name: str = Field(min_length=1, max_length=255)
    location_name: str = Field(min_length=1, max_length=255)


class NasPendingRegistrationResponse(BaseModel):
    registration_id: UUID
    state: Literal["pending", "completed", "cancelled", "expired"]
    appliance_name: str
    location_name: str
    share_name: str
    server_guid_masked: str
    reuses_registered_appliance: bool
    operation: Literal["create_share", "update_network_host"]
    expires_at: datetime
    operator_command: str
    messages: list[NasRegistrationMessage] = Field(default_factory=list)


class NasInstallerManifestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    registration_id: UUID
    proposed_appliance_id: UUID
    proposed_share_id: UUID
    operation: Literal["create_share", "update_network_host"]
    requested_host: str
    appliance_name: str
    share_name: str
    location_name: str
    location_id: str
    server_guid_hash: str
    server_guid_masked: str
    identity_fingerprint_hash: str
    identity_fingerprint_version: str
    request_digest: str
    expires_at: datetime


class NasRegistrationSummary(BaseModel):
    appliance_id: UUID
    share_id: UUID
    appliance_name: str
    location_name: str
    share_name: str
    location_id: str
    registration_status: Literal["registered", "retired"]
    availability: Literal["available", "unavailable", "identity_conflict", "blocked"]
    status_message: str
    source_endpoint_id: int | None = None


class NasRegistrationListResponse(BaseModel):
    registrations: list[NasRegistrationSummary] = Field(default_factory=list)


class NasRegistrationCompletionResponse(BaseModel):
    registration_id: UUID
    state: Literal["completed"] = "completed"
    location_id: str
    appliance_id: UUID
    share_id: UUID
    created_appliance: bool
    created_share: bool


class ExistingNasAdoptionResponse(BaseModel):
    location_id: Literal["linux-nas-photo-organizer"] = "linux-nas-photo-organizer"
    appliance_id: UUID
    share_id: UUID
    server_guid_masked: str
    endpoint_id: int
    adopted: bool = True


class NasDiscoveryCandidate(BaseModel):
    candidate_id: str
    suggested_name: str
    network_host: str
    address_hint: str


class NasDiscoveryResponse(BaseModel):
    status: Literal["completed", "unavailable"]
    candidates: list[NasDiscoveryCandidate] = Field(default_factory=list)
    manual_entry_available: bool = True
    messages: list[NasRegistrationMessage] = Field(default_factory=list)
