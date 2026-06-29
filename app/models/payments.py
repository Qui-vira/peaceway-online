"""Payment records and raw payment-provider webhook events."""
from __future__ import annotations

import enum
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Enum as SAEnum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import JSONB, Base, TimestampMixin
from app.models.orders import PaymentMethod


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(
        SAEnum(PaymentMethod, name="payment_method", create_type=False), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, name="payment_status"), default=PaymentStatus.PENDING, nullable=False
    )
    # Telegram file_id of the uploaded proof image (manual bank transfer)
    proof_file_id: Mapped[str | None] = mapped_column(String(255))
    # Flutterwave transaction reference
    provider_ref: Mapped[str | None] = mapped_column(String(255), index=True)
    verified_by: Mapped[str | None] = mapped_column(String(120))
    note: Mapped[str | None] = mapped_column(Text)


class PaymentWebhookEvent(Base, TimestampMixin):
    __tablename__ = "payment_webhook_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)  # "flutterwave"
    event_type: Mapped[str | None] = mapped_column(String(80))
    reference: Mapped[str | None] = mapped_column(String(255), index=True)
    verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    raw: Mapped[dict | None] = mapped_column(JSONB)
