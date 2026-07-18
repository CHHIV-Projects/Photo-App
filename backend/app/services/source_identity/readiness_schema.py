"""Schemas for read-only Source Profile readiness checks."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.services.source_identity.durable_identity import DurableIdentityStatus


ReadinessStatus = Literal["ready", "path_only", "needs_review", "blocked", "provider_specific", "unknown"]
IdentityMatchStatus = Literal[
    "not_enrolled",
    "matched",
    "needs_review",
    "mismatch",
    "unavailable",
    "unsupported",
    "provider_specific",
    "ambiguous",
    "unknown",
]


class SourceProfileReadinessMessage(BaseModel):
    """Operator-safe readiness message."""

    code: str
    message: str


class SourceProfileReadinessResponse(BaseModel):
    """Read-only readiness result for a Source Profile."""

    source_profile_id: int
    source_label: str | None = None
    source_type: str | None = None
    profile_status: str | None = None
    cloud_provider: str | None = None

    endpoint_id: int | None = None
    endpoint_alias: str | None = None
    endpoint_source_type: str | None = None

    durable_identity_status: DurableIdentityStatus = "unknown"
    durable_identity_reason: str | None = None
    durable_identity_identifier_type: str | None = None
    durable_identity_identifier: str | None = None
    durable_identity_evidence: list[str] = Field(default_factory=list)

    readiness_status: ReadinessStatus
    identity_match_status: IdentityMatchStatus
    can_run_source_intake: bool
    requires_operator_acknowledgment: bool = False
    hard_block: bool = False

    operator_message: str
    recommended_next_action: str
    warnings: list[SourceProfileReadinessMessage] = Field(default_factory=list)
    blockers: list[SourceProfileReadinessMessage] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    probe_summary: dict[str, Any] = Field(default_factory=dict)
    observed_path_summary: dict[str, Any] = Field(default_factory=dict)
    access_node_summary: dict[str, Any] = Field(default_factory=dict)
    advanced_details: dict[str, Any] = Field(default_factory=dict)
