"""Partner portal authentication models.

Partners (wholesalers/suppliers) are a SEPARATE auth domain from Peaceway staff:
identity is the `network_partners` row itself (matched by `portal_login_email`),
never an `admin_users` row. Sessions and OTPs live in their own tables so a
partner token can never resolve to a staff identity — the wall is structural,
not role-based.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.sourcing import NetworkPartner


class PartnerPortalOtp(Base, TimestampMixin):
    """Short-lived OTP for partner portal email login."""

    __tablename__ = "partner_portal_otps"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    partner_id: Mapped[UUID] = mapped_column(
        ForeignKey("network_partners.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    partner: Mapped[NetworkPartner] = relationship(lazy="selectin")


class PartnerPortalSession(Base):
    """Active partner portal session — UUID token sent via X-Partner-Session."""

    __tablename__ = "partner_portal_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    partner_id: Mapped[UUID] = mapped_column(
        ForeignKey("network_partners.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    partner: Mapped[NetworkPartner] = relationship(lazy="selectin")
