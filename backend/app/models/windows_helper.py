"""Durable Windows Helper pairing and credential records."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
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
