"""Schemas for asset context label APIs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AssetContextLabelSummary(BaseModel):
    id: int
    asset_sha256: str
    asset_filename: str
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
