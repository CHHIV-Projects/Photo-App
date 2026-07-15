"""Durable source endpoint identity foundation models."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


SOURCE_ENDPOINT_TYPES = {"local", "external_device", "removable_media", "nas", "cloud"}
SOURCE_ENDPOINT_STATUSES = {"active", "needs_review", "retired"}
ACCESS_NODE_STATUSES = {"active", "inactive", "retired"}
SOURCE_ENDPOINT_CONFIDENCE_TIERS = {
    "strong_match",
    "medium_needs_review",
    "weak_manual_confirmation_required",
    "unavailable_not_connected",
    "unknown",
}


class AccessNode(Base):
    """Machine/runtime environment that can observe source endpoint paths."""

    __tablename__ = "access_nodes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    access_node_uuid: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        default=lambda: str(uuid4()),
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    os_family: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown", index=True)
    provider_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    host_fingerprint_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    host_fingerprint_masked: Mapped[str | None] = mapped_column(String(128), nullable=True)
    capabilities_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    created_endpoints: Mapped[list["SourceEndpoint"]] = relationship(
        back_populates="created_from_access_node",
    )
    observed_paths: Mapped[list["SourceEndpointObservedPath"]] = relationship(
        back_populates="access_node",
    )


class SourceEndpoint(Base):
    """Durable source identity anchor with an immutable v1 alias."""

    __tablename__ = "source_endpoints"
    __table_args__ = (
        UniqueConstraint("endpoint_uuid", name="uq_source_endpoints_endpoint_uuid"),
        UniqueConstraint("alias_normalized", name="uq_source_endpoints_alias_normalized"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    endpoint_uuid: Mapped[str] = mapped_column(String(64), nullable=False, default=lambda: str(uuid4()))
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    alias: Mapped[str] = mapped_column(String(255), nullable=False)
    alias_normalized: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    identity_fingerprint_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    identity_fingerprint_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    identity_confidence: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown", index=True)
    evidence_summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_from_access_node_id: Mapped[int | None] = mapped_column(
        ForeignKey("access_nodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_from_access_node: Mapped[AccessNode | None] = relationship(
        back_populates="created_endpoints",
    )
    observed_paths: Mapped[list["SourceEndpointObservedPath"]] = relationship(
        back_populates="source_endpoint",
        cascade="all, delete-orphan",
    )


class SourceEndpointObservedPath(Base):
    """Access-node-specific observation of where an endpoint is reachable."""

    __tablename__ = "source_endpoint_observed_paths"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_endpoint_id: Mapped[int] = mapped_column(
        ForeignKey("source_endpoints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    access_node_id: Mapped[int] = mapped_column(
        ForeignKey("access_nodes.id"),
        nullable=False,
        index=True,
    )
    observed_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    normalized_observed_path: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    filesystem_boundary_type: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown", index=True)
    source_root_candidate_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    is_valid_source_root_candidate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    probe_provider_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    probe_provider_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    probe_status: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    confidence_tier: Mapped[str | None] = mapped_column(String(64), nullable=True)
    match_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    safe_to_run: Mapped[str | None] = mapped_column(String(32), nullable=True)
    blockers_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    warnings_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    source_endpoint: Mapped[SourceEndpoint] = relationship(back_populates="observed_paths")
    access_node: Mapped[AccessNode] = relationship(back_populates="observed_paths")
