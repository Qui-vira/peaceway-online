"""Phase-1 access-control / compliance models.

Append-only tables (prescription_verifications, dispensing_records) and the audit
log are protected by BEFORE UPDATE/DELETE triggers (see app/core/gate_ddl.py);
corrections are made by inserting a new row that points at the superseded one via
amends_record_id. These models describe the tables; the triggers/view enforce them.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import JSONB, Base


class PrescriptionVerification(Base):
    """Append-only. The pharmacist's decision on an order's prescription lines.

    decision: APPROVED | REJECTED | SUPERSEDED. A SUPERSEDED row is written
    automatically by the order_items trigger when a line changes after approval,
    forcing re-verification (latest row wins in the Gate-1 check).
    """

    __tablename__ = "prescription_verifications"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    pharmacist_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("admin_users.id"))
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    amends_record_id: Mapped[UUID | None] = mapped_column(ForeignKey("prescription_verifications.id"))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DispensingRecord(Base):
    """Append-only record of what was dispensed against an order."""

    __tablename__ = "dispensing_records"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    pharmacist_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("admin_users.id"))
    amends_record_id: Mapped[UUID | None] = mapped_column(ForeignKey("dispensing_records.id"))
    dispensed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    payload: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class BreakGlassAccess(Base):
    """Time-boxed emergency read grant (e.g. system_owner reading clinical data).

    Enforced by clinical-field RLS which lands with the superuser-removal ticket;
    the table + 15-minute expiry are in place now so the control ships ready.
    """

    __tablename__ = "break_glass_access"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("admin_users.id"), nullable=False, index=True)
    resource: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(80))
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Approval(Base):
    """Generic approval row (e.g. discount-above-cap, refund-above-limit, exports)."""

    __tablename__ = "approvals"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    request_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    resource_id: Mapped[str | None] = mapped_column(String(80))
    requested_by: Mapped[UUID | None] = mapped_column(ForeignKey("admin_users.id"))
    approved_by: Mapped[UUID | None] = mapped_column(ForeignKey("admin_users.id"))
    decision: Mapped[str | None] = mapped_column(String(20))
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CommunityMember(Base):
    """Telegram community membership, linked to a customer, with join source."""

    __tablename__ = "community_members"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    customer_id: Mapped[UUID | None] = mapped_column(ForeignKey("customers.id"))
    source: Mapped[str | None] = mapped_column(String(40))
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
