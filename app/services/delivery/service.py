"""High-level delivery orchestration: booking, status application, customer updates."""
from __future__ import annotations

from uuid import UUID

from aiogram import Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import get_session
from app.core.logging import get_logger
from app.models import (
    Customer,
    DeliveryOrder,
    DeliveryStatus,
    DeliveryTrackingEvent,
    Order,
    TrackingLink,
)
from app.services import orders as orders_svc
from app.services.delivery.base import DeliveryRequest, StatusResult
from app.services.delivery.registry import get_provider

log = get_logger("delivery")

# Provider/webhook status strings -> our DeliveryStatus enum.
STATUS_MAP = {
    "packaging": DeliveryStatus.PACKAGING,
    "ready": DeliveryStatus.READY_FOR_DISPATCH,
    "ready_for_dispatch": DeliveryStatus.READY_FOR_DISPATCH,
    "assigned": DeliveryStatus.RIDER_ASSIGNED,
    "rider_assigned": DeliveryStatus.RIDER_ASSIGNED,
    "picked_up": DeliveryStatus.PICKED_UP,
    "pickup": DeliveryStatus.PICKED_UP,
    "in_transit": DeliveryStatus.IN_TRANSIT,
    "on_the_way": DeliveryStatus.IN_TRANSIT,
    "near": DeliveryStatus.NEAR_CUSTOMER,
    "near_customer": DeliveryStatus.NEAR_CUSTOMER,
    "arriving": DeliveryStatus.NEAR_CUSTOMER,
    "delivered": DeliveryStatus.DELIVERED,
    "completed": DeliveryStatus.DELIVERED,
    "failed": DeliveryStatus.FAILED_DELIVERY,
    "failed_delivery": DeliveryStatus.FAILED_DELIVERY,
    "returned": DeliveryStatus.RETURNED_TO_PHARMACY,
}

_CUSTOMER_MSG = {
    DeliveryStatus.PICKED_UP: "📦 Your order {code} has been picked up by the rider.",
    DeliveryStatus.IN_TRANSIT: "🛵 Your order {code} is on the way.",
    DeliveryStatus.NEAR_CUSTOMER: "📍 Your rider is nearby with order {code}.",
    DeliveryStatus.DELIVERED: "🏁 Your order {code} has been delivered.",
    DeliveryStatus.FAILED_DELIVERY: "⚠️ Delivery of {code} failed. Our team will contact you.",
    DeliveryStatus.RETURNED_TO_PHARMACY: "↩️ Order {code} was returned to the pharmacy. We'll reach out.",
}


def map_status(raw_status: str | None) -> DeliveryStatus | None:
    if not raw_status:
        return None
    return STATUS_MAP.get(str(raw_status).strip().lower())


async def book_delivery(order_id: UUID, provider_key: str) -> DeliveryOrder | None:
    provider = get_provider(provider_key)
    if provider is None or not provider.enabled:
        return None
    s = get_settings()
    async with get_session() as session:
        order = (await session.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
        if order is None:
            return None
        req = DeliveryRequest(
            pickup_address=f"{s.pharmacy_name}, Igando, Lagos",
            dropoff_address=order.delivery_address or "",
            customer_phone=order.delivery_phone or "",
            package_description=f"Order {order.code}",
            customer_name=order.delivery_name,
            area=order.delivery_area,
            landmark=order.delivery_landmark,
        )
        booking = await provider.create_delivery(req)
        d = DeliveryOrder(
            order_id=order.id,
            provider_key=provider_key,
            provider_delivery_id=booking.provider_delivery_id,
            pickup_address=req.pickup_address,
            dropoff_address=req.dropoff_address,
            customer_phone=req.customer_phone,
            package_description=req.package_description,
            status=booking.status,
            raw=booking.raw,
        )
        session.add(d)
        if booking.tracking_url:
            session.add(TrackingLink(order_id=order.id, url=booking.tracking_url))
        await session.flush()
        return d


async def apply_status(bot: Bot, order_id: UUID, result: StatusResult) -> None:
    """Record a tracking event, update the order, and notify the customer."""
    mapped = map_status(result.status)
    async with get_session() as session:
        order = (await session.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
        if order is None:
            return
        session.add(
            DeliveryTrackingEvent(
                order_id=order.id,
                provider_key=result.provider_key,
                status=result.status,
                latitude=result.latitude,
                longitude=result.longitude,
                raw=result.raw,
            )
        )
        if result.tracking_url:
            session.add(TrackingLink(order_id=order.id, url=result.tracking_url))
        if mapped is not None:
            await orders_svc.transition_delivery(session, order, mapped, f"provider:{result.provider_key}")
        customer = await session.get(Customer, order.customer_id)
        code = order.code
        chat_id = customer.telegram_id if customer else None

    if chat_id is None:
        return

    # GPS coordinates -> Telegram map location.
    if result.latitude is not None and result.longitude is not None:
        try:
            await bot.send_location(chat_id, latitude=result.latitude, longitude=result.longitude)
        except Exception as exc:  # noqa: BLE001
            log.error("send_location_failed", error=str(exc))

    msg = _CUSTOMER_MSG.get(mapped, "").format(code=code) if mapped else ""
    kb = None
    if result.tracking_url:
        b = InlineKeyboardBuilder()
        b.button(text="🗺 Track on Map", url=result.tracking_url)
        kb = b.as_markup()
        msg = msg or f"📦 Update on your order {code}."
    if msg:
        try:
            await bot.send_message(chat_id, msg, reply_markup=kb)
        except Exception as exc:  # noqa: BLE001
            log.error("status_notify_failed", error=str(exc))
