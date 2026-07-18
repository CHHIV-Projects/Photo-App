"""Schemas for source endpoint enrollment planning and confirmation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from app.services.source_identity.durable_identity import DurableIdentityStatus
from app.services.source_identity.probe_schema import SourceIdentityProbeRequest


EnrollmentPlanStatus = Literal[
    "ready",
    "needs_review",
    "blocked",
    "alias_conflict",
    "duplicate_match",
    "source_profile_already_linked",
]
EndpointEnrollmentAction = Literal["create_new_endpoint", "link_existing_endpoint", "none"]
SourceProfileEnrollmentAction = Literal["link_existing_profile", "none"]
EnrollmentConfirmStatus = Literal["completed", "blocked", "failed"]
IdentityFingerprintStrength = Literal["strong", "medium", "weak", "unavailable"]


class EnrollmentMessage(BaseModel):
    """Operator-safe enrollment message."""

    code: str
    message: str


class SourceEndpointEnrollmentCandidate(BaseModel):
    """Safe candidate endpoint summary derived from a probe result."""

    source_type: str
    observed_path: str | None = None
    normalized_observed_path: str | None = None
    source_root_candidate_path: str | None = None
    filesystem_boundary_type: str = "unknown"
    is_valid_source_root_candidate: bool = False
    probe_status: str
    confidence_tier: str
    safe_to_run: str
    provider_name: str
    provider_version: str
    access_node_label: str
    access_node_os_family: str
    identity_fingerprint_hash: str | None = None
    identity_fingerprint_version: str | None = None
    identity_fingerprint_strength: IdentityFingerprintStrength = "unavailable"


class SourceEndpointEnrollmentMatch(BaseModel):
    """Existing endpoint that may satisfy the enrollment plan."""

    source_endpoint_id: int
    alias: str
    source_type: str
    match_strength: str
    match_reason: str
    identity_confidence: str


class SourceEndpointEnrollmentPlanRequest(BaseModel):
    """Read-only endpoint enrollment plan request."""

    source_profile_id: int
    probe_request: SourceIdentityProbeRequest
    proposed_alias: str | None = None
    selected_existing_endpoint_id: int | None = None
    operator_review_acknowledged: bool = False


class SourceEndpointEnrollmentPlanResponse(BaseModel):
    """Read-only endpoint enrollment plan response."""

    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    plan_status: EnrollmentPlanStatus
    source_profile_id: int
    source_profile_label: str | None = None
    existing_source_endpoint_id: int | None = None
    endpoint_action: EndpointEnrollmentAction = "none"
    source_profile_action: SourceProfileEnrollmentAction = "none"
    proposed_alias: str | None = None
    alias_normalized: str | None = None
    plan_fingerprint: str
    durable_identity_status: DurableIdentityStatus = "unknown"
    durable_identity_reason: str | None = None
    durable_identity_identifier_type: str | None = None
    durable_identity_identifier: str | None = None
    durable_identity_evidence: list[str] = Field(default_factory=list)
    candidate: SourceEndpointEnrollmentCandidate | None = None
    possible_matches: list[SourceEndpointEnrollmentMatch] = Field(default_factory=list)
    blockers: list[EnrollmentMessage] = Field(default_factory=list)
    warnings: list[EnrollmentMessage] = Field(default_factory=list)
    required_confirmations: list[EnrollmentMessage] = Field(default_factory=list)


class SourceEndpointEnrollmentConfirmRequest(BaseModel):
    """Stateless confirmation request for endpoint enrollment."""

    source_profile_id: int
    probe_request: SourceIdentityProbeRequest
    confirmed_alias: str | None = None
    selected_existing_endpoint_id: int | None = None
    plan_fingerprint: str | None = None
    operator_confirmed: bool = False
    operator_review_acknowledged: bool = False


class SourceEndpointEnrollmentConfirmResponse(BaseModel):
    """Result of a confirmed endpoint enrollment write."""

    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    enrollment_status: EnrollmentConfirmStatus
    source_profile_id: int
    source_endpoint_id: int | None = None
    source_profile_endpoint_id: int | None = None
    endpoint_action: EndpointEnrollmentAction = "none"
    source_profile_action: SourceProfileEnrollmentAction = "none"
    already_linked: bool = False
    created_endpoint: bool = False
    created_access_node: bool = False
    created_observed_path: bool = False
    observed_path_id: int | None = None
    plan_fingerprint: str | None = None
    durable_identity_status: DurableIdentityStatus = "unknown"
    durable_identity_reason: str | None = None
    durable_identity_identifier_type: str | None = None
    durable_identity_identifier: str | None = None
    durable_identity_evidence: list[str] = Field(default_factory=list)
    blockers: list[EnrollmentMessage] = Field(default_factory=list)
    warnings: list[EnrollmentMessage] = Field(default_factory=list)
