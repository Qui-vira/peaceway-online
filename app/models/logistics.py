"""Logistics & delivery-tracking models.

Created now so the schema is stable; populated/used by the Phase 2 logistics
provider integration. P1 uses ManualProvider + manual staff status updates.
"""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import JSONB, Base, TimestampMixin


class LogisticsProvider(Base, TimestampMixin):
    __tablename__ = "logistics_providers"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    key: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)  # manual|kwik|fez|gokada|custom
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_gps: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_tracking_url: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class DeliveryQuote(Base, TimestampMixin):
    __tablename__ = "delivery_quotes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"))
    provider_key: Mapped[str] = mapped_column(String(40), nullable=False)
    fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    eta_minutes: Mapped[int | None] = mapped_column()
    raw: Mapped[dict | None] = mapped_column(JSONB)


class DeliveryOrder(Base, TimestampMixin):
    __tablename__ = "delivery_orders"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    provider_key: Mapped[str] = mapped_column(String(40), nullable=False)
    provider_delivery_id: Mapped[str | None] = mapped_column(String(255), index=True)
    pickup_address: Mapped[str | None] = mapped_column(Text)
    dropoff_address: Mapped[str | None] = mapped_column(Text)
    customer_phone: Mapped[str | None] = mapped_column(String(50))
    package_description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String(60))
    raw: Mapped[dict | None] = mapped_column(JSONB)


class RiderAssignment(Base, TimestampMixin):
    __tablename__ = "rider_assignments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    provider_key: Mapped[str | None] = mapped_column(String(40))
    rider_name: Mapped[str | None] = mapped_column(String(255))
    rider_phone: Mapped[str | None] = mapped_column(String(50))
    is_manual: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class TrackingLink(Base, TimestampMixin):
    __tablename__ = "tracking_links"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)


class DeliveryTrackingEvent(Base, TimestampMixin):
    __tablename__ = "delivery_tracking_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    provider_key: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(60), nullable=False)
    latitude: Mapped[float | None] = mapped_column()
    longitude: Mapped[float | None] = mapped_column()
    raw: Mapped[dict | None] = mapped_column(JSONB)


class DeliveryWebhookEvent(Base, TimestampMixin):
    __tablename__ = "delivery_webhook_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider_key: Mapped[str] = mapped_column(String(40), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(255), index=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    raw: Mapped[dict | None] = mapped_column(JSONB)
