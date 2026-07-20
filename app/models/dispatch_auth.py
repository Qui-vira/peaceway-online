"""Dispatch-partner (rider) portal auth models.

A SEPARATE external auth domain from staff, customers and suppliers. A rider's
identity is a `dispatch_partners` row (matched by portal_login_email); sessions and
OTPs live in dispatch-only tables so a rider token can never resolve to a staff,
customer or supplier identity. The wall is structural, not role-based.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class DispatchPartner(Base, TimestampMixin):
    """An external delivery rider with their own portal login."""

    __tablename__ = "dispatch_partners"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))
    portal_login_email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class DispatchPartnerOtp(Base, TimestampMixin):
    """Short-lived OTP for rider portal email login."""

    __tablename__ = "dispatch_partner_otps"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    dispatch_partner_id: Mapped[UUID] = mapped_column(
        ForeignKey("dispatch_partners.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    dispatch_partner: Mapped[DispatchPartner] = relationship(lazy="selectin")


class DispatchPartnerSession(Base):
    """Active rider portal session, token sent via X-Dispatch-Session."""

    __tablename__ = "dispatch_partner_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    dispatch_partner_id: Mapped[UUID] = mapped_column(
        ForeignKey("dispatch_partners.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    dispatch_partner: Mapped[DispatchPartner] = relationship(lazy="selectin")
