"""Operational models: staff, fee settings, delivery zones, pharmacist Q&A,
prescriptions, and audit logs."""
from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
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
    """A pharmacist-inbox ticket. The original question + reply are kept for
    backward-compat display; the full thread lives in PharmacistMessage."""

    __tablename__ = "pharmacist_questions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    product_id: Mapped[UUID | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text)
    answered_by: Mapped[str | None] = mapped_column(String(120))
    is_answered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class PharmacistMessage(Base, TimestampMixin):
    """One message in a pharmacist-inbox ticket thread (customer or pharmacist)."""

    __tablename__ = "pharmacist_messages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    question_id: Mapped[UUID] = mapped_column(
        ForeignKey("pharmacist_questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender: Mapped[str] = mapped_column(String(20), nullable=False)  # "customer" | "pharmacist"
    telegram_id: Mapped[int | None] = mapped_column(BigInteger)
    body: Mapped[str] = mapped_column(Text, nullable=False)


class Prescription(Base, TimestampMixin):
    __tablename__ = "prescriptions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    order_id: Mapped[UUID | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"))
    product_id: Mapped[UUID | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    question_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("pharmacist_questions.id", ondelete="SET NULL")
    )
    file_id: Mapped[str] = mapped_column(String(255), nullable=False)  # Telegram file_id
    file_type: Mapped[str] = mapped_column(String(20), default="image", nullable=False)  # image|document
    review_status: Mapped[str] = mapped_column(String(40), default="PENDING", nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(120))
    note: Mapped[str | None] = mapped_column(Text)


class ProductRequestStatus(str, enum.Enum):
    """Lifecycle of a product request, treated as a customer lead, not a
    closed ticket. Stored as a plain string column (see Prescription.review_status
    for the same lightweight pattern) — application-validated, not DB-enforced,
    so adding a status never needs a risky column-type migration."""

    NEW = "NEW"
    CHECKING_AVAILABILITY = "CHECKING_AVAILABILITY"
    NEEDS_MORE_INFO = "NEEDS_MORE_INFO"
    AVAILABLE = "AVAILABLE"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    ORDERED_FROM_SUPPLIER = "ORDERED_FROM_SUPPLIER"
    READY_TO_ORDER = "READY_TO_ORDER"
    CUSTOMER_NOTIFIED = "CUSTOMER_NOTIFIED"
    CONVERTED_TO_ORDER = "CONVERTED_TO_ORDER"
    FULFILLED = "FULFILLED"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"


class RequestUrgency(str, enum.Enum):
    TODAY = "TODAY"
    WITHIN_24H = "WITHIN_24H"
    THIS_WEEK = "THIS_WEEK"
    JUST_CHECKING = "JUST_CHECKING"


class ProductRequest(Base, TimestampMixin):
    """Customer request for a medicine/supplement we don't currently stock.

    Treated as a lead with a full lifecycle and message thread, not a closed
    admin task — see ProductRequestMessage / ProductRequestStatusEvent.
    """

    __tablename__ = "product_requests"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    strength: Mapped[str | None] = mapped_column(String(100))
    form: Mapped[str | None] = mapped_column(String(100))
    quantity: Mapped[str | None] = mapped_column(String(100))
    note: Mapped[str | None] = mapped_column(Text)
    delivery_area: Mapped[str | None] = mapped_column(String(120))
    is_medicine: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default=ProductRequestStatus.NEW.value, nullable=False)

    customer_phone: Mapped[str | None] = mapped_column(String(50))
    customer_email: Mapped[str | None] = mapped_column(String(255))
    urgency: Mapped[str | None] = mapped_column(String(20))
    admin_notes: Mapped[str | None] = mapped_column(Text)
    customer_visible_message: Mapped[str | None] = mapped_column(Text)
    last_customer_update_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_admin_update_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    converted_order_id: Mapped[UUID | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProductRequestMessage(Base, TimestampMixin):
    """One message in a product-request thread (customer, admin, or system)."""

    __tablename__ = "product_request_messages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    product_request_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False)  # customer|admin|system
    sender_admin_id: Mapped[int | None] = mapped_column(BigInteger)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_file_id: Mapped[str | None] = mapped_column(String(255))


class ProductRequestStatusEvent(Base, TimestampMixin):
    """Full status timeline for a product request."""

    __tablename__ = "product_request_status_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    product_request_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    old_status: Mapped[str | None] = mapped_column(String(30))
    new_status: Mapped[str] = mapped_column(String(30), nullable=False)
    changed_by_admin_id: Mapped[int | None] = mapped_column(BigInteger)
    customer_visible_message: Mapped[str | None] = mapped_column(Text)


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    actor_telegram_id: Mapped[int | None] = mapped_column(BigInteger)
    actor_role: Mapped[str | None] = mapped_column(String(40))
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity: Mapped[str | None] = mapped_column(String(80))
    entity_id: Mapped[str | None] = mapped_column(String(80))
    detail: Mapped[dict | None] = mapped_column(JSONB)
