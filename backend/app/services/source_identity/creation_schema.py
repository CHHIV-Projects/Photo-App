"""Schemas for transactional, drive-agnostic filesystem source creation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.services.source_identity.durable_identity import DurableIdentityStatus


SourceCreationType = Literal["local", "external", "removable", "nas"]
SourceCreationPlanStatus = Literal["ready", "needs_review", "blocked", "source_exists"]
SourceCreationStatus = Literal["completed", "blocked"]
SourceCreationNameAction = Literal["create_new", "use_existing", "rename_existing", "cancel"]
SourceCreationRecognitionStatus = Literal[
    "new_device",
    "existing_device",
    "existing_device_type_mismatch",
    "existing_source_active",
    "existing_source_inactive",
    "existing_legacy_source",
    "multiple_source_matches",
    "identity_needs_review",
    "location_blocked",
]
SourceCreationEndpointAction = Literal[
    "create_new_endpoint",
    "reuse_existing_endpoint",
    "upgrade_legacy_endpoint",
    "rename_existing_endpoint",
    "upgrade_and_rename_endpoint",
    "none",
]
SourceCreationProfileAction = Literal[
    "create_new_source",
    "reuse_existing_source",
    "reactivate_existing_source",
    "adopt_legacy_source",
    "adopt_and_reactivate_source",
    "canonicalize_existing_source",
    "canonicalize_and_reactivate_source",
    "none",
]


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


class SourceCreationSourceMatch(BaseModel):
    """Safe exact-root Source Profile match shown during recognition."""

    source_profile_id: int
    source_label: str
    source_type: str
    profile_status: str
    source_root_path: str | None = None
    source_endpoint_id: int | None = None
    endpoint_alias: str | None = None
    endpoint_relative_root: str | None = None
    match_kind: Literal["modern_exact", "legacy_exact"]
    classification: str
    provenance_count: int = 0
    ingestion_runs_count: int = 0
    source_intake_runs_count: int = 0
    asset_count: int = 0
    has_protected_history: bool = False
    recommended_action: str | None = None
    allowed_actions: list[str] = Field(default_factory=list)
    selected_for_action: bool = False
    conflict_reason: str | None = None


class SourceCreationPlanRequest(BaseModel):
    """Read-only request to derive and validate a filesystem Source."""

    source_type: SourceCreationType
    observed_path: str
    source_name: str | None = None
    device_name: str | None = None
    naming_action: SourceCreationNameAction | None = None
    selected_existing_endpoint_id: int | None = None
    selected_canonical_source_id: int | None = None
    duplicate_source_ids_to_inactivate: list[int] = Field(default_factory=list)
    use_registered_source_type: bool = False
    operator_review_acknowledged: bool = False


class SourceCreationPlanResponse(BaseModel):
    """Stateless creation plan with normal and advanced operator fields."""

    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    plan_status: SourceCreationPlanStatus
    plan_fingerprint: str
    recognition_status: SourceCreationRecognitionStatus
    recognition_title: str
    recognition_message: str
    source_type: SourceCreationType
    recognized_source_type: SourceCreationType
    registered_endpoint_source_type: str | None = None
    source_type_mismatch: bool = False
    persisted_source_type: str
    requested_device_name: str
    device_name: str
    naming_action: SourceCreationNameAction | None = None
    name_decision_required: bool = False
    observed_path: str
    canonical_source_root_path: str
    endpoint_relative_root: str
    entire_endpoint: bool
    entire_endpoint_label: str | None = None
    suggested_source_name: str
    requested_source_name: str | None = None
    source_name_suggested_alternative: str | None = None
    source_display_name: str
    durable_identity_status: DurableIdentityStatus
    durable_identity_reason: str | None = None
    durable_identity_identifier_type: str | None = None
    durable_identity_identifier: str | None = None
    durable_identity_evidence: list[str] = Field(default_factory=list)
    endpoint_action: SourceCreationEndpointAction = "none"
    source_action: SourceCreationProfileAction = "none"
    selected_existing_endpoint_id: int | None = None
    selected_canonical_source_id: int | None = None
    existing_source_profile_id: int | None = None
    existing_source_status: str | None = None
    duplicate_source_ids_to_inactivate: list[int] = Field(default_factory=list)
    possible_matches: list[SourceCreationEndpointMatch] = Field(default_factory=list)
    exact_source_matches: list[SourceCreationSourceMatch] = Field(default_factory=list)
    conflicting_source_profile_ids: list[int] = Field(default_factory=list)
    final_action_label: str
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
    alias_event_id: int | None = None
    source_type: SourceCreationType
    recognized_source_type: SourceCreationType
    persisted_source_type: str
    device_name: str
    observed_path: str
    canonical_source_root_path: str
    endpoint_relative_root: str
    entire_endpoint: bool
    entire_endpoint_label: str | None = None
    suggested_source_name: str
    requested_source_name: str | None = None
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
    renamed_endpoint: bool = False
    created_source: bool = False
    reused_source: bool = False
    reactivated_source: bool = False
    adopted_legacy_source: bool = False
    canonicalized_source: bool = False
    inactivated_duplicate_source_ids: list[int] = Field(default_factory=list)
    created_observed_path: bool = False
    blockers: list[SourceCreationMessage] = Field(default_factory=list)
    warnings: list[SourceCreationMessage] = Field(default_factory=list)
    advanced_details: dict[str, Any] = Field(default_factory=dict)
