"""Schemas for asset context label APIs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AssetContextLabelSummary(BaseModel):
    id: int
    asset_sha256: str
    asset_filename: str
    asset_image_url: str | None = None
    asset_display_url: str | None = None
    duplicate_group_id: int | None = None
    is_canonical: bool | None = None
    label: str
    label_normalized: str
    context_type: str
    source_type: str
    source_observation_id: int | None = None
    status: str
    confidence: float | None = None
    created_at_utc: datetime


class AssetContextLabelListResponse(BaseModel):
    count: int
    items: list[AssetContextLabelSummary]


class AcceptObservationAsContextRequest(BaseModel):
    label: str | None = None


class AcceptObservationAsContextResponse(BaseModel):
    context_label: AssetContextLabelSummary
    observation_status: str
    already_present: bool


class ContextLabelPropagationTargetSummary(BaseModel):
    asset_sha256: str
    asset_filename: str
    image_url: str | None = None
    display_url: str | None = None
    duplicate_group_id: int
    is_canonical: bool
    already_has_label: bool
    selectable: bool
    default_selected: bool


class ContextLabelPropagationPreviewResponse(BaseModel):
    source_label: AssetContextLabelSummary
    duplicate_group_id: int | None = None
    eligible_target_count: int
    targets: list[ContextLabelPropagationTargetSummary]
    message: str | None = None


class ContextLabelPropagationRequest(BaseModel):
    target_asset_sha256s: list[str]


class ContextLabelPropagationResponse(BaseModel):
    source_label_id: int
    requested_count: int
    added_count: int
    already_present_count: int
    skipped_count: int
    failed_count: int
