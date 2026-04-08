"""Pydantic schemas for Milestone 10 UI API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FaceSummary(BaseModel):
    """UI-facing face summary inside a cluster detail response."""

    face_id: int
    asset_sha256: str
    thumbnail_url: str | None = None


class ClusterSummary(BaseModel):
    """UI-facing summary of one face cluster."""

    cluster_id: int
    face_count: int
    person_id: int | None = None
    person_name: str | None = None
    is_ignored: bool
    preview_thumbnail_urls: list[str] = Field(default_factory=list)


class ClusterDetail(BaseModel):
    """UI-facing detail for one cluster including all faces."""

    cluster_id: int
    person_id: int | None = None
    person_name: str | None = None
    is_ignored: bool
    faces: list[FaceSummary] = Field(default_factory=list)


class PersonSummary(BaseModel):
    """UI-facing summary of one person."""

    person_id: int
    display_name: str


class ClusterAssignmentSummary(BaseModel):
    """Cluster assignment summary used in people-with-clusters output."""

    cluster_id: int
    face_count: int


class PersonWithClusters(BaseModel):
    """Person plus currently assigned clusters."""

    person_id: int
    display_name: str
    clusters: list[ClusterAssignmentSummary] = Field(default_factory=list)


class AssignPersonRequest(BaseModel):
    """Request body for assigning one cluster to one person."""

    person_id: int = Field(gt=0)


class MoveFaceRequest(BaseModel):
    """Request body for moving one face into another cluster."""

    target_cluster_id: int = Field(gt=0)


class SuccessResponse(BaseModel):
    """Simple success envelope for mutation endpoints."""

    success: bool


class ClusterListResponse(BaseModel):
    """Response wrapper for cluster listing endpoints."""

    count: int
    items: list[ClusterSummary]


class PeopleListResponse(BaseModel):
    """Response wrapper for people listing endpoint."""

    count: int
    items: list[PersonSummary]


class PeopleWithClustersResponse(BaseModel):
    """Response wrapper for people-with-clusters endpoint."""

    count: int
    items: list[PersonWithClusters]
