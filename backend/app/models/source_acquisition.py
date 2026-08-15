"""Provider-neutral durable Source acquisition state."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class SourceAcquisitionRun(Base):
    """One immutable selected-candidate proposal and its transfer lifecycle."""

    __tablename__ = "source_acquisition_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_uuid: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True, default=lambda: str(uuid4()))
    idempotency_key: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    access_node_id: Mapped[int] = mapped_column(ForeignKey("access_nodes.id"), nullable=False, index=True)
    source_endpoint_id: Mapped[int] = mapped_column(ForeignKey("source_endpoints.id"), nullable=False, index=True)
    source_profile_id: Mapped[int] = mapped_column(ForeignKey("ingestion_sources.id"), nullable=False, index=True)
    inventory_generation: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    inventory_chain_digest: Mapped[str] = mapped_column(String(71), nullable=False)
    proposal_digest: Mapped[str] = mapped_column(String(71), nullable=False, unique=True, index=True)
    source_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_native_root: Mapped[str] = mapped_column(String(4096), nullable=False)
    receiving_root: Mapped[str] = mapped_column(String(4096), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="planned", index=True)
    selected_item_count: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_byte_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    committed_byte_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    ready_item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    disk_free_bytes_at_plan: Mapped[int] = mapped_column(BigInteger, nullable=False)
    disk_reserve_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    safe_status: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list["SourceAcquisitionItem"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="SourceAcquisitionItem.ordinal"
    )


class SourceAcquisitionItem(Base):
    """One exact inventory candidate selected into a durable acquisition run."""

    __tablename__ = "source_acquisition_items"
    __table_args__ = (
        UniqueConstraint("run_id", "candidate_reference", name="uq_source_acquisition_item_candidate"),
        UniqueConstraint("run_id", "provider_native_relative_path_normalized_digest", name="uq_source_acquisition_item_path"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    item_uuid: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True, default=lambda: str(uuid4()))
    run_id: Mapped[int] = mapped_column(ForeignKey("source_acquisition_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    inventory_generation: Mapped[str] = mapped_column(String(36), nullable=False)
    provider_native_root: Mapped[str] = mapped_column(String(4096), nullable=False)
    provider_native_relative_path: Mapped[str] = mapped_column(String(4096), nullable=False)
    provider_native_relative_path_normalized: Mapped[str] = mapped_column(String(4096), nullable=False)
    provider_native_full_path: Mapped[str] = mapped_column(String(4096), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    safe_extension: Mapped[str] = mapped_column(String(16), nullable=False)
    expected_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    expected_modified_time_ns: Mapped[int] = mapped_column(BigInteger, nullable=False)
    expected_file_id_digest: Mapped[str | None] = mapped_column(String(71), nullable=True)
    source_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_native_relative_path_normalized_digest: Mapped[str] = mapped_column(String(71), nullable=False)
    windows_file_attributes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    local_residency: Mapped[str] = mapped_column(String(32), nullable=False)
    eligibility_reason: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    committed_offset: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    verified_byte_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    helper_source_sha256: Mapped[str | None] = mapped_column(String(71), nullable=True)
    linux_verified_sha256: Mapped[str | None] = mapped_column(String(71), nullable=True)
    partial_relative_path: Mapped[str] = mapped_column(String(255), nullable=False)
    ready_relative_path: Mapped[str] = mapped_column(String(255), nullable=False)
    source_pre_evidence_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_post_evidence_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    safe_status: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    run: Mapped[SourceAcquisitionRun] = relationship(back_populates="items")
