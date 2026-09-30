"""Durable whole-source orchestration above bounded Windows acquisition children."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class WindowsSourceWorkflow(Base):
    __tablename__ = "windows_source_workflows"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    workflow_uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid4()))
    source_profile_id: Mapped[int] = mapped_column(ForeignKey("ingestion_sources.id"), nullable=False, index=True)
    source_endpoint_id: Mapped[int] = mapped_column(ForeignKey("source_endpoints.id"), nullable=False, index=True)
    access_node_id: Mapped[int] = mapped_column(ForeignKey("access_nodes.id"), nullable=False, index=True)
    probe_operation_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default="inventorying")
    inventory_generation: Mapped[str | None] = mapped_column(String(36), nullable=True)
    inventory_chain_digest: Mapped[str | None] = mapped_column(String(71), nullable=True)
    proposal_digest: Mapped[str | None] = mapped_column(String(71), nullable=True, unique=True)
    source_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_native_root: Mapped[str] = mapped_column(String(4096), nullable=False)
    max_observed_entries: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    eligible_item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected_item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expected_byte_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    completed_item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    transferred_byte_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    child_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_child_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_library_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    already_represented: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    safe_status: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    pages: Mapped[list["WindowsSourceWorkflowPage"]] = relationship(cascade="all, delete-orphan", order_by="WindowsSourceWorkflowPage.page_index")
    candidates: Mapped[list["WindowsSourceWorkflowCandidate"]] = relationship(cascade="all, delete-orphan", order_by="WindowsSourceWorkflowCandidate.ordinal")
    children: Mapped[list["WindowsSourceWorkflowChild"]] = relationship(cascade="all, delete-orphan", order_by="WindowsSourceWorkflowChild.child_index")


class WindowsSourceWorkflowPage(Base):
    __tablename__ = "windows_source_workflow_pages"
    __table_args__ = (UniqueConstraint("workflow_id", "page_index", name="uq_windows_source_workflow_page_index"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("windows_source_workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    page_index: Mapped[int] = mapped_column(Integer, nullable=False)
    operation_uuid: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    result_digest: Mapped[str | None] = mapped_column(String(71), nullable=True)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_cursor: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WindowsSourceWorkflowCandidate(Base):
    __tablename__ = "windows_source_workflow_candidates"
    __table_args__ = (
        UniqueConstraint("workflow_id", "candidate_reference", name="uq_windows_source_workflow_candidate_ref"),
        UniqueConstraint("workflow_id", "normalized_path_digest", name="uq_windows_source_workflow_candidate_path"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("windows_source_workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    relative_path: Mapped[str] = mapped_column(String(4096), nullable=False)
    normalized_path: Mapped[str] = mapped_column(String(4096), nullable=False)
    normalized_path_digest: Mapped[str] = mapped_column(String(71), nullable=False)
    full_path: Mapped[str] = mapped_column(String(4096), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    safe_extension: Mapped[str] = mapped_column(String(16), nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    modified_time_ns: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    stable_file_id_digest: Mapped[str | None] = mapped_column(String(71), nullable=True)
    windows_file_attributes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    local_residency: Mapped[str] = mapped_column(String(32), nullable=False)
    eligibility: Mapped[str] = mapped_column(String(32), nullable=False)
    eligibility_reason: Mapped[str] = mapped_column(String(64), nullable=False)


class WindowsSourceWorkflowChild(Base):
    __tablename__ = "windows_source_workflow_children"
    __table_args__ = (UniqueConstraint("workflow_id", "child_index", name="uq_windows_source_workflow_child_index"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("windows_source_workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    child_index: Mapped[int] = mapped_column(Integer, nullable=False)
    first_candidate_ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False)
    acquisition_run_id: Mapped[int | None] = mapped_column(ForeignKey("source_acquisition_runs.id"), nullable=True, unique=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
