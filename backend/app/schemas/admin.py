"""Schemas for Admin summary endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class AdminDuplicateTypeCount(BaseModel):
    """Count of duplicate groups for a given type."""

    group_type: str
    count: int


class AdminAssetsSummary(BaseModel):
    """Asset counts across all records."""

    total: int
    visible: int
    demoted: int


class AdminDuplicatesSummary(BaseModel):
    """Duplicate group counts."""

    total_groups: int
    by_type: list[AdminDuplicateTypeCount]


class AdminFacesSummary(BaseModel):
    """Face and unassigned-face counts."""

    total: int
    unassigned: int


class AdminPlacesSummary(BaseModel):
    """Place-level counts including optional operational breakdowns."""

    total: int
    with_user_label: int
    without_user_label: int
    linked_to_assets: int
    empty: int


class AdminSummaryResponse(BaseModel):
    """Read-only system summary for the Admin workspace."""

    generated_at: datetime
    assets: AdminAssetsSummary
    duplicates: AdminDuplicatesSummary
    faces: AdminFacesSummary
    places: AdminPlacesSummary


class DuplicateProcessingRunStatus(BaseModel):
    """Current or last duplicate processing run snapshot."""

    run_id: int | None = None
    status: Literal["idle", "running", "stop_requested", "completed", "failed", "stopped"] = "idle"
    started_at: datetime | None = None
    finished_at: datetime | None = None
    elapsed_seconds: float | None = None
    total_items: int = 0
    processed_items: int = 0
    current_stage: str | None = None
    error_message: str | None = None
    stop_requested: bool = False
    workset_cutoff: datetime | None = None
    last_successful_cutoff: datetime | None = None


class DuplicateProcessingStatusResponse(BaseModel):
    """Live duplicate processing status view for Admin controls."""

    generated_at: datetime
    pending_items: int
    current: DuplicateProcessingRunStatus


class DuplicateProcessingActionResponse(BaseModel):
    """Run/stop action response payload."""

    accepted: bool
    message: str
    status: DuplicateProcessingRunStatus
