"""Import all models so Base.metadata is fully populated (Alembic, create_all)."""
from app.models.base import Base, TimestampMixin
from app.models.catalog import Product, ProductAlias, ProductPricing
from app.models.logistics import (
    DeliveryOrder,
    DeliveryQuote,
    DeliveryTrackingEvent,
    DeliveryWebhookEvent,
    LogisticsProvider,
    RiderAssignment,
    TrackingLink,
)
from app.models.ops import (
    AuditLog,
    DeliveryZone,
    FeeSetting,
    PharmacistQuestion,
    Prescription,
    Staff,
    StaffRole,
)
from app.models.orders import (
    Customer,
    DeliveryStatus,
    Order,
    OrderItem,
    OrderStatus,
    OrderStatusHistory,
    PaymentMethod,
    RxStatus,
)
from app.models.payments import Payment, PaymentStatus, PaymentWebhookEvent

__all__ = [
    "Base",
    "TimestampMixin",
    "Product",
    "ProductAlias",
    "ProductPricing",
    "Customer",
    "Order",
    "OrderItem",
    "OrderStatusHistory",
    "OrderStatus",
    "RxStatus",
    "DeliveryStatus",
    "PaymentMethod",
    "Payment",
    "PaymentStatus",
    "PaymentWebhookEvent",
    "Staff",
    "StaffRole",
    "FeeSetting",
    "DeliveryZone",
    "PharmacistQuestion",
    "Prescription",
    "AuditLog",
    "LogisticsProvider",
    "DeliveryQuote",
    "DeliveryOrder",
    "RiderAssignment",
    "TrackingLink",
    "DeliveryTrackingEvent",
    "DeliveryWebhookEvent",
]
