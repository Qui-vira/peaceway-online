"""Operational models: staff, fee settings, delivery zones, pharmacist Q&A,
prescriptions, and audit logs."""
from __future__ import annotations

import enum
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import JSONB, Base, TimestampMixin


class StaffRole(str, enum.Enum):
    OWNER = "OWNER"
    PHARMACIST = "PHARMACIST"
    PACKAGING = "PACKAGING"
    DISPATCHER = "DISPATCHER"
    SUPPORT = "SUPPORT"


class Staff(Base, TimestampMixin):
    __tablename__ = "staff"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[StaffRole] = mapped_column(SAEnum(StaffRole, name="staff_role"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class FeeSetting(Base, TimestampMixin):
    """Singleton-style row (id=1) holding global, admin-editable fee config."""

    __tablename__ = "fee_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    payment_fee_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0"))
    payment_fee_flat: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    offramp_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    handling_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    enable_bank: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_flutterwave: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_crypto: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class DeliveryZone(Base, TimestampMixin):
    __tablename__ = "delivery_zones"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    eta_minutes: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class PharmacistQuestion(Base, TimestampMixin):
    __tablename__ = "pharmacist_questions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text)
    answered_by: Mapped[str | None] = mapped_column(String(120))
    is_answered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Prescription(Base, TimestampMixin):
    __tablename__ = "prescriptions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    order_id: Mapped[UUID | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"))
    file_id: Mapped[str] = mapped_column(String(255), nullable=False)  # Telegram file_id
    review_status: Mapped[str] = mapped_column(String(40), default="PENDING", nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(120))
    note: Mapped[str | None] = mapped_column(Text)


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    actor_telegram_id: Mapped[int | None] = mapped_column(BigInteger)
    actor_role: Mapped[str | None] = mapped_column(String(40))
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity: Mapped[str | None] = mapped_column(String(80))
    entity_id: Mapped[str | None] = mapped_column(String(80))
    detail: Mapped[dict | None] = mapped_column(JSONB)
