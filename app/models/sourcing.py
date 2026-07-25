"""Partner sourcing models for out-of-stock rescue workflow."""
from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import JSONB, Base, TimestampMixin


# SQLAlchemy's Enum persists the Python member NAME by default ("IN_STOCK"), but the
# PG enum types in this module were created with lowercase VALUES ("in_stock"), so a
# write raises InvalidTextRepresentationError and a read raises LookupError. Every other
# enum in the codebase has name == value (OrderStatus.NEW = "NEW") and is unaffected;
# these must persist .value explicitly. See tests/test_sourcing_enum_pg.py.
def _enum_values(enum_cls) -> list[str]:
    return [member.value for member in enum_cls]


class PartnerType(str, enum.Enum):
    SUPPLIER = "supplier"
    WHOLESALER = "wholesaler"


class PartnerChannel(str, enum.Enum):
    API = "api"
    PORTAL = "portal"


class FulfillmentStatus(str, enum.Enum):
    IN_STOCK = "in_stock"
    SOURCE_FROM_NETWORK = "source_from_network"
    SOURCING_REQUESTED = "sourcing_requested"
    PARTNER_CONFIRMED = "partner_confirmed"
    PARTNER_REJECTED = "partner_rejected"
    PACK_READY = "pack_ready"
    DISPATCH_ASSIGNED = "dispatch_assigned"
    PICKED_UP = "picked_up"
    DELIVERED = "delivered"
    FAILED = "failed"


class NetworkPartner(Base, TimestampMixin):
    __tablename__ = "network_partners"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    partner_type: Mapped[PartnerType] = mapped_column(
        SAEnum(PartnerType, name="partner_type", values_callable=_enum_values), nullable=False
    )
    channel_type: Mapped[PartnerChannel] = mapped_column(
        SAEnum(PartnerChannel, name="partner_channel", values_callable=_enum_values), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    api_base_url: Mapped[str | None] = mapped_column(String(500))
    portal_login_email: Mapped[str | None] = mapped_column(String(255), index=True)
    portal_contact: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)


class OrderSourcing(Base, TimestampMixin):
    __tablename__ = "order_sourcing"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    fulfillment_status: Mapped[FulfillmentStatus] = mapped_column(
        SAEnum(FulfillmentStatus, name="fulfillment_status", values_callable=_enum_values),
        default=FulfillmentStatus.IN_STOCK,
        nullable=False,
        index=True,
    )
    sourcing_required: Mapped[bool] = mapped_column(default=False, nullable=False)
    partner_id: Mapped[UUID | None] = mapped_column(ForeignKey("network_partners.id", ondelete="SET NULL"))
    partner_type: Mapped[PartnerType | None] = mapped_column(
        SAEnum(PartnerType, name="order_partner_type", values_callable=_enum_values)
    )
    sourcing_channel: Mapped[PartnerChannel | None] = mapped_column(
        SAEnum(PartnerChannel, name="order_partner_channel", values_callable=_enum_values)
    )
    sourcing_request: Mapped[dict | None] = mapped_column(JSONB)
    requested_items: Mapped[list | None] = mapped_column(JSONB)
    confirmed_items: Mapped[list | None] = mapped_column(JSONB)
    confirmed_quantity: Mapped[int | None] = mapped_column()
    confirmed_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    expiry_or_batch_confirmation: Mapped[str | None] = mapped_column(Text)
    ready_for_pickup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pickup_code: Mapped[str | None] = mapped_column(String(40), index=True)
    pack_verification_photo: Mapped[str | None] = mapped_column(Text)
    pickup_proof: Mapped[str | None] = mapped_column(Text)
    delivery_proof: Mapped[str | None] = mapped_column(Text)
    customer_facing_status: Mapped[str | None] = mapped_column(String(255))
    last_error: Mapped[str | None] = mapped_column(Text)
    partner_response_raw: Mapped[dict | None] = mapped_column(JSONB)

    order: Mapped["Order"] = relationship(back_populates="sourcing")
    partner: Mapped[NetworkPartner | None] = relationship()
