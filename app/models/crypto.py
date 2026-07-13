"""Crypto off-ramp payment record (Phase 3 - optional, manual settlement).

Deliberately conservative: a static wallet address receives funds, the customer
submits a transaction hash, and an admin manually confirms both the on-chain
receipt AND the Naira settlement. No automated crypto->bank settlement.
"""
from __future__ import annotations

import enum
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Enum as SAEnum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class CryptoStatus(str, enum.Enum):
    PENDING = "PENDING"           # awaiting customer tx hash
    SUBMITTED = "SUBMITTED"       # tx hash provided, awaiting admin review
    CONFIRMED = "CONFIRMED"       # on-chain receipt confirmed by admin
    SETTLED = "SETTLED"           # Naira settlement confirmed by admin
    REJECTED = "REJECTED"


class CryptoPayment(Base, TimestampMixin):
    __tablename__ = "crypto_payments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    network: Mapped[str] = mapped_column(String(40), nullable=False)
    token: Mapped[str] = mapped_column(String(40), nullable=False)
    wallet_address: Mapped[str] = mapped_column(String(255), nullable=False)
    expected_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    tx_hash: Mapped[str | None] = mapped_column(String(255), index=True)
    status: Mapped[CryptoStatus] = mapped_column(
        SAEnum(CryptoStatus, name="crypto_status"), default=CryptoStatus.PENDING, nullable=False
    )
    naira_settled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(120))
    note: Mapped[str | None] = mapped_column(Text)
