"""Schemas for transactional, drive-agnostic filesystem source creation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.services.source_identity.durable_identity import DurableIdentityStatus


SourceCreationType = Literal["local", "external", "nas"]
SourceCreationPlanStatus = Literal["ready", "needs_review", "blocked", "source_exists"]
SourceCreationStatus = Literal["completed", "blocked"]
SourceCreationEndpointAction = Literal[
    "create_new_endpoint",
    "reuse_existing_endpoint",
    "upgrade_legacy_endpoint",
    "none",
]
SourceCreationProfileAction = Literal["create_new_source", "reuse_existing_source", "none"]


class SourceCreationMessage(BaseModel):
    """Operator-safe source-creation message."""

    code: str
    message: str


class SourceCreationEndpointMatch(BaseModel):
    """Safe summary of an endpoint that may represent the selected device."""

    source_endpoint_id: int
    alias: str
    source_type: str
    match_strength: Literal["strong", "legacy_review"]
    match_reason: str
    identity_confidence: str


class SourceCreationPlanRequest(BaseModel):
    """Read-only request to derive and validate a filesystem Source."""

    source_type: SourceCreationType
    device_name: str
    observed_path: str
    selected_existing_endpoint_id: int | None = None
    operator_review_acknowledged: bool = False


class SourceCreationPlanResponse(BaseModel):
    """Stateless creation plan with normal and advanced operator fields."""

    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    plan_status: SourceCreationPlanStatus
    plan_fingerprint: str
    source_type: SourceCreationType
    persisted_source_type: str
    requested_device_name: str
    device_name: str
    observed_path: str
    canonical_source_root_path: str
    endpoint_relative_root: str
    entire_endpoint: bool
    entire_endpoint_label: str | None = None
    source_display_name: str
    durable_identity_status: DurableIdentityStatus
    durable_identity_reason: str | None = None
    durable_identity_identifier_type: str | None = None
    durable_identity_identifier: str | None = None
    durable_identity_evidence: list[str] = Field(default_factory=list)
    endpoint_action: SourceCreationEndpointAction = "none"
    source_action: SourceCreationProfileAction = "none"
    selected_existing_endpoint_id: int | None = None
    existing_source_profile_id: int | None = None
    possible_matches: list[SourceCreationEndpointMatch] = Field(default_factory=list)
    blockers: list[SourceCreationMessage] = Field(default_factory=list)
    warnings: list[SourceCreationMessage] = Field(default_factory=list)
    required_confirmations: list[SourceCreationMessage] = Field(default_factory=list)
    advanced_details: dict[str, Any] = Field(default_factory=dict)


class SourceCreationConfirmRequest(SourceCreationPlanRequest):
    """Stateless confirmation request that recomputes the creation plan."""

    plan_fingerprint: str
    operator_confirmed: bool = False


class SourceCreationConfirmResponse(BaseModel):
    """Transactional source-creation result."""

    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    creation_status: SourceCreationStatus
    plan_fingerprint: str | None = None
    source_profile_id: int | None = None
    source_endpoint_id: int | None = None
    observed_path_id: int | None = None
    source_type: SourceCreationType
    persisted_source_type: str
    device_name: str
    observed_path: str
    canonical_source_root_path: str
    endpoint_relative_root: str
    entire_endpoint: bool
    entire_endpoint_label: str | None = None
    source_display_name: str
    durable_identity_status: DurableIdentityStatus
    durable_identity_reason: str | None = None
    durable_identity_identifier_type: str | None = None
    durable_identity_identifier: str | None = None
    durable_identity_evidence: list[str] = Field(default_factory=list)
    endpoint_action: SourceCreationEndpointAction = "none"
    source_action: SourceCreationProfileAction = "none"
    created_endpoint: bool = False
    reused_endpoint: bool = False
    upgraded_legacy_endpoint: bool = False
    created_source: bool = False
    reused_source: bool = False
    created_observed_path: bool = False
    blockers: list[SourceCreationMessage] = Field(default_factory=list)
    warnings: list[SourceCreationMessage] = Field(default_factory=list)
    advanced_details: dict[str, Any] = Field(default_factory=dict)
