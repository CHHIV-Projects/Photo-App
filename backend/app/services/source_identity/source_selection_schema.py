"""Schemas for read-only Source Selection."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.services.source_identity.durable_identity import DurableIdentityStatus


SourceSelectionResult = Literal["selected", "not_selected"]
SourceSelectionAvailability = Literal["available", "unavailable", "needs_attention"]
SourceSelectionWorkflowKind = Literal["filesystem_source_intake", "icloud_intake"]


class SourceSelectionRequest(BaseModel):
    """Read-only request to select and verify one Source Profile."""

    model_config = ConfigDict(extra="forbid")

    source_profile_id: int


class SelectedSourceContext(BaseModel):
    """Safe selected Source context for future Step 3 handoff."""

    source_profile_id: int
    source_endpoint_id: int | None = None
    source_type: str | None = None
    friendly_source_type: str
    device_label: str
    source_name: str
    profile_status: str
    endpoint_status: str | None = None
    endpoint_relative_root: str | None = None
    configured_source_root: str | None = None
    resolved_source_root: str | None = None
    resolved_endpoint_path: str | None = None
    root_display: str
    durable_identity_status: DurableIdentityStatus
    identity_match_status: str
    availability: SourceSelectionAvailability
    workflow_kind: SourceSelectionWorkflowKind
    provider_context: dict[str, Any] | None = None
    selected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    selection_version: str = "source_selection_v1"
    selection_fingerprint: str | None = None


class SourceSelectionResponse(BaseModel):
    """Normalized Source Selection result."""

    result: SourceSelectionResult
    availability: SourceSelectionAvailability
    workflow_kind: SourceSelectionWorkflowKind | None = None
    selected_source_context: SelectedSourceContext | None = None
    message: str
    retry_guidance: str | None = None
    advanced_details: dict[str, Any] = Field(default_factory=dict)
