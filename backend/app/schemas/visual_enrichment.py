"""Schemas for Visual Enrichment candidate preview and run controls."""

from __future__ import annotations

from pydantic import BaseModel, Field


class VisualEnrichmentCandidatePreviewRequest(BaseModel):
    pool_type: str = Field(default="collection")
    pool_id: int = Field(ge=1)
    canonical_only: bool = True
    exclude_existing_observations: bool = True
    exclude_existing_context_labels: bool = True
    limit: int = Field(default=50, ge=1, le=200)


class VisualEnrichmentCandidateAssetSummary(BaseModel):
    asset_sha256: str
    filename: str
    image_url: str | None = None
    display_url: str | None = None
    is_canonical: bool
    duplicate_group_id: int | None = None
    has_landmark_observation: bool
    has_landmark_context_label: bool


class VisualEnrichmentCandidatePreviewResponse(BaseModel):
    candidate_count: int
    excluded_existing_observations_count: int
    excluded_existing_context_labels_count: int
    run_count: int
    showing_count: int
    assets: list[VisualEnrichmentCandidateAssetSummary]


class VisualEnrichmentRunRequest(BaseModel):
    asset_sha256s: list[str] = Field(min_length=1)
    live: bool = False
    mock_provider: bool = True
    feature_landmark: bool = True
    feature_web: bool = False
    feature_label: bool = False
    feature_object: bool = False


class VisualEnrichmentScoredItem(BaseModel):
    description: str
    score: float | None = None


class VisualEnrichmentObjectItem(BaseModel):
    name: str
    score: float | None = None


class VisualEnrichmentAssetRunSummary(BaseModel):
    asset_sha256: str
    filename: str
    status: str
    error: str | None = None
    landmarks: list[VisualEnrichmentScoredItem] = Field(default_factory=list)
    web_entities: list[VisualEnrichmentScoredItem] = Field(default_factory=list)
    best_guess_labels: list[str] = Field(default_factory=list)
    labels: list[VisualEnrichmentScoredItem] = Field(default_factory=list)
    objects: list[VisualEnrichmentObjectItem] = Field(default_factory=list)
    created_observations: int
    no_landmark: bool


class VisualEnrichmentRunResponse(BaseModel):
    requested_count: int
    processed_count: int
    provider_calls_attempted: int
    observations_created_count: int
    no_landmark_count: int
    failed_count: int
    report_path: str
    mode: str
    features_requested: list[str]
    asset_results: list[VisualEnrichmentAssetRunSummary]
