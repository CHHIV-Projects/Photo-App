"""Durable generalized NAS appliance, share, and pending-registration records."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class NasApplianceRegistration(Base):
    """Application identity for one explicitly registered NAS appliance."""

    __tablename__ = "nas_appliance_registrations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    registration_uuid: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    friendly_name: Mapped[str] = mapped_column(String(255), nullable=False)
    server_guid_hash: Mapped[str] = mapped_column(String(71), nullable=False, unique=True, index=True)
    server_guid_masked: Mapped[str] = mapped_column(String(32), nullable=False)
    network_host: Mapped[str] = mapped_column(String(255), nullable=False)
    network_host_normalized: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    shares: Mapped[list["NasShareRegistration"]] = relationship(back_populates="appliance")


class NasShareRegistration(Base):
    """One explicitly authorized SMB share/location beneath a NAS appliance."""

    __tablename__ = "nas_share_registrations"
    __table_args__ = (
        UniqueConstraint("nas_appliance_id", "share_name_normalized", name="uq_nas_share_appliance_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    registration_uuid: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    nas_appliance_id: Mapped[int] = mapped_column(
        ForeignKey("nas_appliance_registrations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    location_id: Mapped[str] = mapped_column(String(96), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    share_name: Mapped[str] = mapped_column(String(255), nullable=False)
    share_name_normalized: Mapped[str] = mapped_column(String(255), nullable=False)
    identity_fingerprint_hash: Mapped[str] = mapped_column(String(71), nullable=False, unique=True, index=True)
    identity_fingerprint_version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_endpoint_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_endpoints.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="registered", index=True)
    installed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    appliance: Mapped[NasApplianceRegistration] = relationship(back_populates="shares")


class NasPendingRegistration(Base):
    """Immutable, secret-free request consumed by the root-owned installer."""

    __tablename__ = "nas_pending_registrations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    proposed_appliance_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    proposed_share_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    operation: Mapped[str] = mapped_column(String(32), nullable=False, default="create_share")
    existing_appliance_id: Mapped[int | None] = mapped_column(
        ForeignKey("nas_appliance_registrations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    existing_share_id: Mapped[int | None] = mapped_column(
        ForeignKey("nas_share_registrations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    requested_host: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_host_normalized: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    appliance_name: Mapped[str] = mapped_column(String(255), nullable=False)
    share_name: Mapped[str] = mapped_column(String(255), nullable=False)
    share_name_normalized: Mapped[str] = mapped_column(String(255), nullable=False)
    location_name: Mapped[str] = mapped_column(String(255), nullable=False)
    location_id: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    server_guid_hash: Mapped[str] = mapped_column(String(71), nullable=False, index=True)
    server_guid_masked: Mapped[str] = mapped_column(String(32), nullable=False)
    identity_fingerprint_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    identity_fingerprint_version: Mapped[str] = mapped_column(String(64), nullable=False)
    request_digest: Mapped[str] = mapped_column(String(71), nullable=False, unique=True, index=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
