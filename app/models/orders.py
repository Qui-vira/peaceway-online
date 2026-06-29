"""Customer, order, order-item, and status-history models + status enums."""
from __future__ import annotations

import enum
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import JSONB, Base, TimestampMixin


class OrderStatus(str, enum.Enum):
    NEW = "NEW"
    AWAITING_PAYMENT = "AWAITING_PAYMENT"
    PAYMENT_SUBMITTED = "PAYMENT_SUBMITTED"
    PAYMENT_APPROVED = "PAYMENT_APPROVED"
    PROCESSING = "PROCESSING"
    DISPATCHED = "DISPATCHED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class RxStatus(str, enum.Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    PRESCRIPTION_REQUIRED = "PRESCRIPTION_REQUIRED"
    PRESCRIPTION_UPLOADED = "PRESCRIPTION_UPLOADED"
    PHARMACIST_REVIEW = "PHARMACIST_REVIEW"
    APPROVED_FOR_PAYMENT = "APPROVED_FOR_PAYMENT"
    REJECTED_BY_PHARMACIST = "REJECTED_BY_PHARMACIST"


class DeliveryStatus(str, enum.Enum):
    NONE = "NONE"
    PACKAGING = "PACKAGING"
    READY_FOR_DISPATCH = "READY_FOR_DISPATCH"
    RIDER_ASSIGNED = "RIDER_ASSIGNED"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    NEAR_CUSTOMER = "NEAR_CUSTOMER"
    DELIVERED = "DELIVERED"
    FAILED_DELIVERY = "FAILED_DELIVERY"
    RETURNED_TO_PHARMACY = "RETURNED_TO_PHARMACY"


class PaymentMethod(str, enum.Enum):
    BANK_TRANSFER = "BANK_TRANSFER"
    FLUTTERWAVE = "FLUTTERWAVE"
    CRYPTO = "CRYPTO"


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    # Saved delivery addresses [{address, area, landmark, preferred_time, note}]
    addresses: Mapped[list | None] = mapped_column(JSONB)

    orders: Mapped[list["Order"]] = relationship(back_populates="customer")


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)

    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus, name="order_status"), default=OrderStatus.NEW, nullable=False, index=True
    )
    rx_status: Mapped[RxStatus] = mapped_column(
        SAEnum(RxStatus, name="rx_status"), default=RxStatus.NOT_REQUIRED, nullable=False
    )
    delivery_status: Mapped[DeliveryStatus] = mapped_column(
        SAEnum(DeliveryStatus, name="delivery_status"), default=DeliveryStatus.NONE, nullable=False
    )
    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        SAEnum(PaymentMethod, name="payment_method")
    )

    # Money (all additive; fees never reduce product profit)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    delivery_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    payment_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    offramp_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    handling_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))

    # Delivery details
    delivery_name: Mapped[str | None] = mapped_column(String(255))
    delivery_phone: Mapped[str | None] = mapped_column(String(50))
    delivery_address: Mapped[str | None] = mapped_column(Text)
    delivery_area: Mapped[str | None] = mapped_column(String(120))
    delivery_landmark: Mapped[str | None] = mapped_column(String(255))
    delivery_preferred_time: Mapped[str | None] = mapped_column(String(120))
    delivery_note: Mapped[str | None] = mapped_column(Text)

    assigned_staff_id: Mapped[UUID | None] = mapped_column(ForeignKey("staff.id"))

    customer: Mapped[Customer] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )
    history: Mapped[list["OrderStatusHistory"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )


class OrderItem(Base, TimestampMixin):
    __tablename__ = "order_items"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    requires_prescription: Mapped[bool] = mapped_column(default=False, nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")


class OrderStatusHistory(Base, TimestampMixin):
    __tablename__ = "order_status_history"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    field: Mapped[str] = mapped_column(String(40), nullable=False)  # status|rx_status|delivery_status
    from_value: Mapped[str | None] = mapped_column(String(60))
    to_value: Mapped[str] = mapped_column(String(60), nullable=False)
    changed_by: Mapped[str | None] = mapped_column(String(120))  # staff id/name or "system"
    note: Mapped[str | None] = mapped_column(Text)

    order: Mapped[Order] = relationship(back_populates="history")
