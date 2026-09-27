"""Redacted normal-UI contracts for the accepted Windows Local workflow."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WindowsSourceUiProfileStatus(_StrictModel):
    provider_kind: Literal["windows_helper"] = "windows_helper"
    source_profile_id: int
    profile_name: str
    device_alias: str
    windows_root: str
    windows_access: Literal["ready", "not_available", "setup_required"]
    paired: bool
    online: bool
    helper_version: str | None = None
    source_readiness: Literal["ready", "not_ready"] = "not_ready"


class WindowsSourceUiOperation(_StrictModel):
    operation_token: UUID
    stage: Literal["checking_source", "preparing_files", "ready", "failed"]
    source_ready: bool = False
    safe_message: str


class WindowsSourceUiRoute(_StrictModel):
    access_node_id: UUID
    computer_alias: str


class WindowsSourceUiRouteCheck(_StrictModel):
    stage: Literal["checking_routes", "checking_source", "unavailable", "ambiguous", "failed"]
    safe_message: str
    observation_tokens: list[UUID] = Field(default_factory=list)
    probe_operation_token: UUID | None = None
    routes: list[WindowsSourceUiRoute] = Field(default_factory=list)


class WindowsSourceUiRouteResolveRequest(_StrictModel):
    observation_tokens: list[UUID] = Field(min_length=1, max_length=64)
    selected_access_node_id: UUID | None = None


class WindowsSourceUiPrepareRequest(_StrictModel):
    probe_operation_token: UUID


class WindowsSourceUiCandidateReview(_StrictModel):
    workflow_token: UUID
    stage: Literal["awaiting_confirmation"] = "awaiting_confirmation"
    files_to_process: int
    total_bytes: int
    profile_name: str
    windows_root: str
    safe_message: str


class WindowsSourceUiWorkflowStatus(_StrictModel):
    workflow_token: UUID
    stage: Literal[
        "awaiting_confirmation",
        "transferring_files",
        "processing_library",
        "complete",
        "failed",
    ]
    files_total: int
    files_completed: int
    expected_bytes: int
    transferred_bytes: int
    new_library_items: int
    already_represented: int
    failed_items: int
    safe_message: str


class WindowsSourceUiComputer(_StrictModel):
    access_node_id: UUID
    computer_alias: str
    paired: bool
    online: bool
    helper_version: str | None = None
    source_device_aliases: list[str] = Field(default_factory=list)


class WindowsSourceUiComputerList(_StrictModel):
    computers: list[WindowsSourceUiComputer] = Field(default_factory=list)


class WindowsSourceUiPortableDiscoveryRequest(_StrictModel):
    source_type: Literal["external", "removable"]


class WindowsSourceUiPortableCandidate(_StrictModel):
    candidate_token: str
    device_alias: str | None = None
    known_device: bool
    current_root: str
    drive_type: str
    current_route_count: int


class WindowsSourceUiPortableDiscovery(_StrictModel):
    stage: Literal["checking_devices", "ready", "unavailable", "failed"]
    safe_message: str
    observation_tokens: list[UUID] = Field(default_factory=list)
    candidates: list[WindowsSourceUiPortableCandidate] = Field(default_factory=list)


class WindowsSourceUiPortableDiscoveryResolveRequest(WindowsSourceUiPortableDiscoveryRequest):
    observation_tokens: list[UUID] = Field(min_length=1, max_length=64)


class WindowsSourceUiCreateProbeRequest(_StrictModel):
    access_node_id: UUID | None = None
    discovery_candidate_token: str | None = Field(default=None, max_length=80)
    source_type: Literal["local", "external", "removable"] = "local"
    device_alias: str = Field(min_length=1, max_length=255)
    windows_root: str = Field(min_length=3, max_length=2048)
    profile_name: str = Field(min_length=1, max_length=255)


class WindowsSourceUiCreatePlanRequest(WindowsSourceUiCreateProbeRequest):
    probe_operation_token: UUID


class WindowsSourceUiCreatePlan(_StrictModel):
    plan_status: Literal["ready", "source_exists", "needs_review", "blocked"]
    device_alias: str
    windows_root: str
    profile_name: str
    device_action: str
    profile_action: str
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class WindowsSourceUiCreateConfirmRequest(WindowsSourceUiCreatePlanRequest):
    operator_confirmed: bool


class WindowsSourceUiCreateResult(_StrictModel):
    status: Literal["completed", "blocked"]
    source_profile_id: int | None = None
    source_endpoint_id: int | None = None
    created_profile: bool = False
    reused_profile: bool = False
    safe_message: str
