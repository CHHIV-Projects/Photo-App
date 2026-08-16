"""Strict admin schemas for provider-neutral Source acquisition."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateSourceAcquisitionPlanRequest(_StrictModel):
    idempotency_key: UUID
    source_profile_id: int = Field(ge=1)
    inventory_operation_ids: list[UUID] = Field(min_length=1, max_length=100)
    candidate_references: list[str] = Field(min_length=1, max_length=100)


class ActivateSourceAcquisitionRequest(_StrictModel):
    proposal_digest: str = Field(min_length=71, max_length=71, pattern=r"^sha256:[0-9a-f]{64}$")


class CreateAcquireItemOperationRequest(_StrictModel):
    acquisition_item_id: UUID


class SourceAcquisitionItemSummary(_StrictModel):
    acquisition_item_id: UUID
    ordinal: int
    candidate_reference: str
    filename: str
    provider_native_relative_path: str
    expected_size_bytes: int
    state: Literal["pending", "transferring", "verifying", "ready", "failed"]
    committed_offset: int
    verified_byte_count: int
    local_residency: str
    helper_source_sha256: str | None = None
    linux_verified_sha256: str | None = None
    failure_code: str | None = None


class SourceAcquisitionRunResponse(_StrictModel):
    acquisition_run_id: UUID
    provider: str
    access_node_id: UUID
    source_endpoint_id: int
    source_profile_id: int
    inventory_generation: UUID
    inventory_chain_digest: str
    proposal_digest: str
    provider_native_root: str
    receiving_root: str
    state: Literal["planned", "active", "completed", "failed", "cancelled"]
    selected_item_count: int
    expected_byte_count: int
    can_run_source_intake: Literal[False] = False
    committed_byte_count: int
    ready_item_count: int
    failed_item_count: int
    disk_free_bytes_at_plan: int
    disk_reserve_bytes: int
    disk_reserve_passed: bool
    items: list[SourceAcquisitionItemSummary]
    created_at: datetime
    activated_at: datetime | None = None
    completed_at: datetime | None = None
    failure_code: str | None = None


class SourceAcquisitionOperationResponse(_StrictModel):
    operation_id: UUID
    operation_type: Literal["acquire_item"] = "acquire_item"
    state: Literal["pending"] = "pending"
    request_digest: str
    expires_at: datetime
    acquisition_run_id: UUID
    acquisition_item_id: UUID


class SourceAcquisitionBridgeCounts(_StrictModel):
    source_intake_runs: int
    ingestion_runs: int
    assets: int
    provenance: int
    canonical_vault_files: int


class SourceAcquisitionBridgeHashClassification(_StrictModel):
    sha256: str = Field(min_length=71, max_length=71, pattern=r"^sha256:[0-9a-f]{64}$")
    classification: Literal["new_content", "exact_known"]
    canonical_vault_verified: bool


class SourceAcquisitionBridgeItemResult(_StrictModel):
    acquisition_item_id: UUID
    ordinal: int
    provider_native_relative_path: str
    runtime_relative_path: str
    linux_verified_sha256: str
    asset_sha256: str | None = None
    provenance_id: int | None = None


class SourceAcquisitionBridgePlanResponse(_StrictModel):
    acquisition_run_id: UUID
    bridge_state: Literal["not_started", "running", "completed", "failed"]
    source_profile_id: int
    source_endpoint_id: int
    ready_root: str
    item_count: int
    verified_byte_count: int
    unique_content_count: int
    bridge_plan_digest: str = Field(min_length=71, max_length=71, pattern=r"^sha256:[0-9a-f]{64}$")
    current_counts: SourceAcquisitionBridgeCounts
    classifications: list[SourceAcquisitionBridgeHashClassification]
    expected_asset_delta: int
    expected_vault_delta: int
    expected_provenance_delta: int
    source_intake_run_id: int | None = None
    ingestion_run_id: int | None = None
    items: list[SourceAcquisitionBridgeItemResult]


class ExecuteSourceAcquisitionBridgeRequest(_StrictModel):
    bridge_plan_digest: str = Field(min_length=71, max_length=71, pattern=r"^sha256:[0-9a-f]{64}$")


class SourceAcquisitionCleanupResponse(_StrictModel):
    acquisition_run_id: UUID
    removed_partial_count: int
    ready_objects_preserved: int
