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


# ---------------------------------------------------------------------------
# Source Intake visibility schemas (12.24)
# ---------------------------------------------------------------------------


class SourceIntakeReportCounts(BaseModel):
    """Counts from a single source intake session report."""

    total_files_scanned: int | None = None
    skipped_already_known: int | None = None
    eligible_unknown_files: int | None = None
    selected_for_session: int | None = None
    staged_to_dropzone: int | None = None
    processed_new_unique: int | None = None
    failed_or_rejected: int | None = None
    deferred_unready_count: int | None = None
    remaining_unknown_eligible: int | None = None


class SourceIntakeSourceSummary(BaseModel):
    """Known ingestion source with latest intake information."""

    source_id: int
    source_label: str
    source_type: str
    source_root_path: str | None = None
    first_seen_at: datetime | None = None
    last_run_at: datetime | None = None
    latest_report_filename: str | None = None
    latest_counts: SourceIntakeReportCounts | None = None
    source_complete: bool | None = None


class SourceIntakeSourcesResponse(BaseModel):
    """List of known ingestion sources with latest intake info."""

    generated_at: datetime
    sources: list[SourceIntakeSourceSummary]


class SourceIntakeReportSummary(BaseModel):
    """Summary of one source intake session report."""

    report_filename: str
    generated_at_utc: str | None = None
    source_label: str | None = None
    source_path: str | None = None
    ingestion_source_id: int | None = None
    ingestion_run_id: int | None = None
    ingest_source_limit: int | None = None
    ingest_batch_size: int | None = None
    source_complete: bool | None = None
    counts: SourceIntakeReportCounts | None = None


class SourceIntakeReportsResponse(BaseModel):
    """List of recent source intake session reports."""

    generated_at: datetime
    reports: list[SourceIntakeReportSummary]


class SourceIntakeReportDetail(BaseModel):
    """Full parsed content of a source intake session report."""

    report_filename: str
    raw: dict


# ---------------------------------------------------------------------------
# Source Registry
# ---------------------------------------------------------------------------


class SourceCreateRequest(BaseModel):
    source_label: str
    source_type: str
    source_root_path: str
    create_new_label: bool = False


class SourceCreateResponse(BaseModel):
    ingestion_source_id: int
    source_label: str
    source_type: str
    source_root_path: str | None
    created_at: datetime
    was_existing: bool


# ---------------------------------------------------------------------------
# Admin-launched Source Intake
# ---------------------------------------------------------------------------


class SourceIntakeRunRequest(BaseModel):
    ingestion_source_id: int
    source_intake_limit: int | None = None
    ingest_batch_size: int = 500


class SourceIntakeStatusSchema(BaseModel):
    run_id: int | None
    status: str
    ingestion_run_id: int | None
    source_label: str | None
    source_type: str | None
    source_root_path: str | None
    source_intake_limit: int | None
    ingest_batch_size: int | None
    started_at: datetime | None
    finished_at: datetime | None
    elapsed_seconds: float | None
    files_scanned: int
    skipped_known: int
    selected: int
    staged: int
    processed_new_unique: int
    failed_or_rejected: int
    remaining_unknown: int
    report_path: str | None
    error_message: str | None
    stop_requested: bool


class SourceIntakeRunResponse(BaseModel):
    status: str
    message: str
    current: SourceIntakeStatusSchema


class SourceIntakeStopResponse(BaseModel):
    status: str
    message: str
    current: SourceIntakeStatusSchema
