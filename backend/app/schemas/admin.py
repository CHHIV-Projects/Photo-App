"""Schemas for Admin summary endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


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


class LivePhotoPairingRunStatus(BaseModel):
    """Current or last Live Photo pairing run snapshot."""

    status: Literal["idle", "running", "completed", "failed"] = "idle"
    started_at: datetime | None = None
    finished_at: datetime | None = None
    elapsed_seconds: float | None = None
    scanned_rows: int = 0
    candidate_groups: int = 0
    pairs_created: int = 0
    already_paired: int = 0
    updated: int = 0
    removed_stale: int = 0
    skipped_missing_source: int = 0
    skipped_ambiguous: int = 0
    skipped_suspicious_delta: int = 0
    last_report_path: str | None = None
    last_error: str | None = None


class LivePhotoPairingStatusResponse(BaseModel):
    """Live Photo pairing status view for Admin controls."""

    generated_at: datetime
    current: LivePhotoPairingRunStatus


class LivePhotoPairingActionResponse(BaseModel):
    """Run action response payload for Live Photo pairing."""

    accepted: bool
    message: str
    status: LivePhotoPairingRunStatus


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
    account_username: str | None = None
    first_seen_at: datetime | None = None
    last_run_at: datetime | None = None
    latest_report_filename: str | None = None
    latest_counts: SourceIntakeReportCounts | None = None
    source_complete: bool | None = None


class SourceIntakeSourcesResponse(BaseModel):
    """List of known ingestion sources with latest intake info."""

    generated_at: datetime
    sources: list[SourceIntakeSourceSummary]


class SourceProfileSummary(BaseModel):
    """Read-only source profile view over ingestion sources."""

    source_id: int
    source_label: str
    source_type: str
    source_root_path: str | None = None
    profile_status: str
    cloud_provider: str | None = None
    acquisition_method: str | None = None
    managed_staging_path: str | None = None
    account_username_masked: str | None = None
    account_username: str | None = None
    first_seen_at: datetime | None = None
    last_run_at: datetime | None = None
    provenance_count: int | None = None
    ingestion_runs_count: int | None = None
    source_intake_runs_count: int | None = None
    icloud_acquisition_runs_count: int | None = None


class SourceProfileDetail(SourceProfileSummary):
    """Expanded source profile detail view for operational diagnostics."""

    normalized_label: str
    effective_path: str | None = None
    effective_path_kind: Literal["source_root_path", "managed_staging_path", "none"] = "none"
    expected_acquisition_path: str | None = None
    source_root_path_relative: str | None = None
    managed_staging_path_relative: str | None = None
    effective_path_relative: str | None = None
    is_referenced: bool = False
    has_path_divergence: bool = False
    warnings: list[str] = Field(default_factory=list)


class IcloudReadinessReason(BaseModel):
    """Machine-readable reason code with operator-facing message."""

    code: str
    message: str


class IcloudReadinessOperationConflicts(BaseModel):
    """Active operation conflict visibility for iCloud readiness."""

    icloud_acquisition_active: bool = False
    source_intake_active: bool = False
    icloud_cleanup_active: bool = False
    source_intake_active_for_this_source: bool | None = None
    icloud_cleanup_active_for_this_source: bool | None = None


class IcloudReadinessLastAcquisition(BaseModel):
    """Latest acquisition snapshot matched to the selected source profile."""

    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    downloaded_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    error_code: str | None = None
    report_path: str | None = None


class IcloudSourceReadinessResponse(BaseModel):
    """Authoritative read-only readiness snapshot for one source profile."""

    source_id: int
    is_icloud_profile: bool
    readiness_status: Literal["ready", "warning", "not_ready", "unknown"]

    profile_status: str
    source_label: str
    source_type: str
    cloud_provider: str | None = None
    account_username_masked: str | None = None

    source_root_path: str | None = None
    managed_staging_path: str | None = None
    expected_acquisition_path: str | None = None
    effective_path: str | None = None

    approved_root_status: Literal["ok", "blocked", "unknown"] = "unknown"
    staging_folder_status: Literal["exists", "missing", "unsafe", "unknown"] = "unknown"
    path_alignment_status: Literal["matched", "mismatch", "unknown"] = "unknown"
    source_root_alignment_status: Literal["matched", "mismatch", "unknown"] = "unknown"
    source_registration_status: Literal["matched", "mismatch", "unknown"] = "unknown"

    auth_status: Literal["unknown", "action_required"] = "unknown"
    last_auth_error_code: str | None = None

    operation_conflicts: IcloudReadinessOperationConflicts
    last_acquisition: IcloudReadinessLastAcquisition | None = None

    blocking_reasons: list[IcloudReadinessReason] = Field(default_factory=list)
    warnings: list[IcloudReadinessReason] = Field(default_factory=list)
    recommended_action: str


class SourceProfilePathCheckResponse(BaseModel):
    """Ephemeral path verification response for one source profile."""

    source_id: int
    path: str | None = None
    path_relative: str | None = None
    path_kind: Literal["source_root_path", "managed_staging_path"]
    exists: bool
    is_directory: bool
    checked_at: datetime


class SourceProfileStagingFolderCreateResponse(BaseModel):
    """Result of explicitly creating an approved iCloud staging folder."""

    source_id: int
    path: str
    path_relative: str | None = None
    created: bool
    exists: bool
    checked_at: datetime


class SourceProfilesResponse(BaseModel):
    """List of source profiles for future ingestion UI compatibility."""

    generated_at: datetime
    profiles: list[SourceProfileSummary]


class SourceProfileCreateRequest(BaseModel):
    """Create payload for strict source profile registration in Ingestion tab."""

    source_label: str
    source_type: str
    source_root_path: str | None = None
    profile_status: str = "active"
    cloud_provider: str | None = None
    account_username: str | None = None
    acquisition_method: str | None = None
    managed_staging_path: str | None = None


class SourceProfileCreateResponse(BaseModel):
    """Create-or-get response for source profile registration."""

    already_exists: bool
    profile: SourceProfileSummary


class SourceProfileMetadataUpdateRequest(BaseModel):
    """Safe metadata edits for existing source profiles."""

    source_label: str | None = None
    profile_status: str | None = None
    cloud_provider: str | None = None
    account_username: str | None = None
    acquisition_method: str | None = None
    managed_staging_path: str | None = None


class SourceProfileStatusUpdateRequest(BaseModel):
    """Narrow lifecycle update payload for one source profile."""

    profile_status: str


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
    account_username: str | None = None
    create_new_label: bool = False


class SourceCreateResponse(BaseModel):
    ingestion_source_id: int
    source_label: str
    source_type: str
    source_root_path: str | None
    account_username: str | None = None
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


# ---------------------------------------------------------------------------
# iCloud staging cleanup (12.44.1)
# ---------------------------------------------------------------------------


class IcloudStagingCleanupRunRequest(BaseModel):
    source_id: int
    dry_run: bool = True


class IcloudStagingCleanupExecuteRequest(BaseModel):
    source_id: int
    dry_run_run_id: int
    explicit_confirmation: str


class IcloudStagingCleanupRunStatus(BaseModel):
    run_id: int | None
    status: str
    source_id: int | None
    source_label: str | None
    source_root_path: str | None
    dry_run: bool
    started_at: datetime | None
    finished_at: datetime | None
    elapsed_seconds: float | None
    eligible_count: int
    deleted_count: int
    skipped_count: int
    total_bytes_eligible: int
    total_bytes_deleted: int
    total_files: int = 0
    processed_files: int = 0
    current_stage: str | None = None
    protected_count: int = 0
    verification_failed_count: int = 0
    file_missing_count: int = 0
    delete_failed_count: int = 0
    manifest_fingerprint: str | None = None
    planner_version: str | None = None
    preview_expires_at: datetime | None = None
    authorized_dry_run_id: int | None = None
    authorization_consumed_at: datetime | None = None
    skipped_reasons: dict[str, int]
    skipped_samples: dict[str, list[str]]
    report_path: str | None
    error_message: str | None


class IcloudStagingCleanupStatusResponse(BaseModel):
    generated_at: datetime
    current: IcloudStagingCleanupRunStatus


class IcloudStagingCleanupRunResponse(BaseModel):
    status: str
    message: str
    current: IcloudStagingCleanupRunStatus


class IcloudStagingCleanupReadinessResponse(BaseModel):
    generated_at: datetime
    source_id: int
    readiness_status: Literal["ready", "blocked"]
    canonical_staging_path: str | None = None
    blocking_reasons: list[IcloudReadinessReason] = Field(default_factory=list)
    latest_dry_run: IcloudStagingCleanupRunStatus


# ---------------------------------------------------------------------------
# icloudpd acquisition (12.42)
# ---------------------------------------------------------------------------


class IcloudAcquisitionRunStatus(BaseModel):
    """Current or last icloudpd acquisition run snapshot."""

    run_id: int | None = None
    status: Literal[
        "idle",
        "running",
        "stop_requested",
        "completed",
        "completed_with_warnings",
        "failed",
        "stopped",
    ] = "idle"
    source_label: str | None = None
    source_type: str | None = None
    source_root_path: str | None = None
    acquisition_mode: Literal["standard", "list_first_non_repeat"] = "standard"
    source_registration_status: str | None = None
    username: str | None = None
    staging_path: str | None = None
    recent_count: int | None = None
    resolved_executable: str | None = None
    icloudpd_version: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    elapsed_seconds: float | None = None
    downloaded_count: int = 0
    skipped_existing_count: int = 0
    failed_count: int = 0
    stdout_tail: str | None = None
    stderr_tail: str | None = None
    report_path: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    stop_requested: bool = False
    file_inventory_count: int | None = None
    recommended_source_intake_command: str | None = None


class IcloudAcquisitionStatusResponse(BaseModel):
    """Live icloudpd acquisition status view for Admin controls."""

    generated_at: datetime
    current: IcloudAcquisitionRunStatus


class IcloudAcquisitionRunResponse(BaseModel):
    """Run action response payload for icloudpd acquisition."""

    status: str
    message: str
    current: IcloudAcquisitionRunStatus


class IcloudAcquisitionStopResponse(BaseModel):
    """Stop action response payload for icloudpd acquisition."""

    status: str
    message: str
    current: IcloudAcquisitionRunStatus


class IcloudAcquisitionRunRequest(BaseModel):
    """Input payload for launching an icloudpd acquisition run."""

    source_label: str
    username: str
    recent_count: int = Field(default=25, ge=1, le=500)
    source_type: str = "cloud_export"
    acquisition_mode: Literal["standard", "list_first_non_repeat"] = "standard"
