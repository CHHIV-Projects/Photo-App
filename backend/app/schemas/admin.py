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


class PlaceGeocodingRunStatus(BaseModel):
    """Current or last place geocoding run snapshot."""

    run_id: int | None = None
    status: Literal["idle", "running", "stop_requested", "completed", "failed", "stopped"] = "idle"
    started_at: datetime | None = None
    finished_at: datetime | None = None
    elapsed_seconds: float | None = None
    total_places: int = 0
    processed_places: int = 0
    succeeded_places: int = 0
    failed_places: int = 0
    current_place_id: int | None = None
    last_error: str | None = None
    last_run_summary: str | None = None
    stop_requested: bool = False


class PlaceGeocodingStatusResponse(BaseModel):
    """Live place geocoding status view for Admin controls."""

    generated_at: datetime
    pending_places: int
    current: PlaceGeocodingRunStatus


class PlaceGeocodingActionResponse(BaseModel):
    """Run/stop action response payload for place geocoding."""

    accepted: bool
    message: str
    status: PlaceGeocodingRunStatus


class FaceProcessingRunStatus(BaseModel):
    """Current or last face processing run snapshot."""

    run_id: int | None = None
    status: Literal["idle", "running", "stop_requested", "completed", "failed", "stopped"] = "idle"
    started_at: datetime | None = None
    finished_at: datetime | None = None
    elapsed_seconds: float | None = None
    assets_pending_detection: int = 0
    assets_processed_detection: int = 0
    faces_pending_embedding: int = 0
    faces_processed_embedding: int = 0
    faces_pending_clustering: int = 0
    faces_processed_clustering: int = 0
    crops_pending: int = 0
    crops_generated: int = 0
    current_stage: str | None = None
    last_error: str | None = None
    last_run_summary: str | None = None
    stop_requested: bool = False


class FaceProcessingStatusResponse(BaseModel):
    """Live face processing status view for Admin controls."""

    generated_at: datetime
    pending_detection: int
    pending_embedding: int
    pending_clustering: int
    pending_crops: int
    current: FaceProcessingRunStatus


class FaceProcessingActionResponse(BaseModel):
    """Run/stop action response payload for face processing."""

    accepted: bool
    message: str
    status: FaceProcessingRunStatus


class HeicPreviewRunStatus(BaseModel):
    """Current or last HEIC preview generation run snapshot."""

    run_id: int | None = None
    status: Literal["idle", "running", "stop_requested", "completed", "failed", "stopped"] = "idle"
    started_at: datetime | None = None
    finished_at: datetime | None = None
    elapsed_seconds: float | None = None
    assets_pending: int = 0
    assets_processed: int = 0
    assets_succeeded: int = 0
    assets_failed: int = 0
    last_error: str | None = None
    last_run_summary: str | None = None
    stop_requested: bool = False


class HeicPreviewStatusResponse(BaseModel):
    """Live HEIC preview generation status view for Admin controls."""

    generated_at: datetime
    pending_previews: int
    current: HeicPreviewRunStatus


class HeicPreviewActionResponse(BaseModel):
    """Run/stop action response payload for HEIC preview generation."""

    accepted: bool
    message: str
    status: HeicPreviewRunStatus
