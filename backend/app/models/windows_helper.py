"""Durable Windows Helper pairing and credential records."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.source_endpoint import AccessNode


class WindowsHelperCredential(Base):
    """The single revocable application credential bound to an Access Node."""

    __tablename__ = "windows_helper_credentials"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    access_node_id: Mapped[int] = mapped_column(
        ForeignKey("access_nodes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    credential_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    token_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    access_node: Mapped[AccessNode] = relationship()


class WindowsHelperPairingAuthorization(Base):
    """Short-lived, one-time verification material for one Access Node."""

    __tablename__ = "windows_helper_pairing_authorizations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    access_node_id: Mapped[int] = mapped_column(
        ForeignKey("access_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    secret_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    access_node: Mapped[AccessNode] = relationship()


class WindowsHelperOperation(Base):
    """One bounded typed operation authorized for an exact Helper Access Node."""

    __tablename__ = "windows_helper_operations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    operation_uuid: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True, index=True, default=lambda: str(uuid4())
    )
    access_node_id: Mapped[int] = mapped_column(
        ForeignKey("access_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_endpoint_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_endpoints.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("ingestion_sources.id", ondelete="SET NULL"), nullable=True, index=True
    )
    operation_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    request_json: Mapped[str] = mapped_column(Text, nullable=False)
    request_digest: Mapped[str] = mapped_column(String(71), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_digest: Mapped[str | None] = mapped_column(String(71), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)

    access_node: Mapped[AccessNode] = relationship()
