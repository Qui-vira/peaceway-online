"""Customer order tracking ('Track My Order')."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from app.bot.keyboards.customer import back_to_menu
from app.core.db import get_session
from app.models import (
    Customer,
    DeliveryStatus,
    FulfillmentStatus,
    Order,
    OrderStatus,
    RiderAssignment,
    TrackingLink,
)

router = Router(name="customer-track")

_ACTIVE = [
    OrderStatus.NEW,
    OrderStatus.AWAITING_PAYMENT,
    OrderStatus.PAYMENT_SUBMITTED,
    OrderStatus.PAYMENT_APPROVED,
    OrderStatus.PROCESSING,
    OrderStatus.DISPATCHED,
]

_FULFILLMENT_LABEL = {
    FulfillmentStatus.IN_STOCK: "In stock now",
    FulfillmentStatus.SOURCE_FROM_NETWORK: "Sourcing from approved network",
    FulfillmentStatus.SOURCING_REQUESTED: "Approved partner request sent",
    FulfillmentStatus.PARTNER_CONFIRMED: "Partner confirmed",
    FulfillmentStatus.PARTNER_REJECTED: "Partner unavailable",
    FulfillmentStatus.PACK_READY: "Pack ready for pickup",
    FulfillmentStatus.DISPATCH_ASSIGNED: "Dispatch assigned",
    FulfillmentStatus.PICKED_UP: "Picked up",
    FulfillmentStatus.DELIVERED: "Delivered",
    FulfillmentStatus.FAILED: "Fulfilment issue under review",
}

_DELIVERY_LABEL = {
    DeliveryStatus.NONE: "Awaiting processing",
    DeliveryStatus.PACKAGING: "📦 Being packaged",
    DeliveryStatus.READY_FOR_DISPATCH: "🚚 Ready for dispatch",
    DeliveryStatus.RIDER_ASSIGNED: "🛵 Rider assigned",
    DeliveryStatus.PICKED_UP: "📦 Picked up",
    DeliveryStatus.IN_TRANSIT: "🛵 On the way",
    DeliveryStatus.NEAR_CUSTOMER: "📍 Rider nearby",
    DeliveryStatus.DELIVERED: "🏁 Delivered",
    DeliveryStatus.FAILED_DELIVERY: "⚠️ Delivery failed",
    DeliveryStatus.RETURNED_TO_PHARMACY: "↩️ Returned to pharmacy",
}


async def _active_orders(telegram_id: int):
    async with get_session() as session:
        customer = (
            await session.execute(select(Customer).where(Customer.telegram_id == telegram_id))
        ).scalar_one_or_none()
        if not customer:
            return []
        return (
            await session.execute(
                select(Order)
                .where(Order.customer_id == customer.id, Order.status.in_(_ACTIVE))
                .order_by(Order.created_at.desc())
                .limit(10)
            )
        ).scalars().all()


def _tracking_kb(orders):
    kb = InlineKeyboardBuilder()
    for o in orders:
        fulfillment = o.sourcing.fulfillment_status.value if o.sourcing else o.status.value
        kb.button(text=f"{o.code} · {fulfillment}", callback_data=f"track:{o.code}")
    kb.button(text="⬅️ Main Menu", callback_data="menu:home")
    kb.adjust(1)
    return kb.as_markup()


async def _render_track_menu(call: CallbackQuery) -> None:
    orders = await _active_orders(call.from_user.id)
    if not orders:
        await call.message.edit_text(
            "📦 You have no active orders to track right now.", reply_markup=back_to_menu()
        )
        await call.answer()
        return
    await call.message.edit_text(
        "📦 <b>Track My Order</b>\nSelect an order:", reply_markup=_tracking_kb(orders)
    )
    await call.answer()


@router.callback_query(F.data == "menu:track")
async def track_menu(call: CallbackQuery, state: FSMContext) -> None:
    from app.bot.customer.email_gate import ensure_email

    if not await ensure_email(call, state, source="tracking", resume=lambda: _render_track_menu(call)):
        return
    await _render_track_menu(call)


@router.message(Command("track"))
async def track_command(message: Message, state: FSMContext) -> None:
    from app.bot.customer.email_gate import ensure_email

    async def _resume():
        orders = await _active_orders(message.from_user.id)
        if not orders:
            await message.answer(
                "📦 You have no active orders to track right now.", reply_markup=back_to_menu()
            )
            return
        await message.answer(
            "📦 <b>Track My Order</b>\nSelect an order:", reply_markup=_tracking_kb(orders)
        )

    if not await ensure_email(message, state, source="tracking", resume=_resume):
        return
    await _resume()


@router.callback_query(F.data.startswith("track:"))
async def track_order(call: CallbackQuery) -> None:
    code = call.data.split("track:", 1)[1]
    async with get_session() as session:
        # Ownership check: only reveal an order to the customer who placed it.
        # Order codes are sequential, so looking up by code alone would leak
        # another customer's status, area, rider, and pickup code.
        customer = (
            await session.execute(select(Customer).where(Customer.telegram_id == call.from_user.id))
        ).scalar_one_or_none()
        order = None
        if customer is not None:
            order = (
                await session.execute(
                    select(Order).where(Order.code == code, Order.customer_id == customer.id)
                )
            ).scalar_one_or_none()
        if order is None:
            await call.answer("Order not found.", show_alert=True)
            return
        rider = (
            await session.execute(
                select(RiderAssignment).where(RiderAssignment.order_id == order.id).order_by(RiderAssignment.created_at.desc())
            )
        ).scalars().first()
        link = (
            await session.execute(
                select(TrackingLink).where(TrackingLink.order_id == order.id).order_by(TrackingLink.created_at.desc())
            )
        ).scalars().first()
        order_status = order.status.value
        delivery_label = _DELIVERY_LABEL.get(order.delivery_status, order.delivery_status.value)
        area = order.delivery_area
        tracking_url = link.url if link else None
        rider_name = rider.rider_name if rider else None
        fulfillment_status = order.sourcing.fulfillment_status if order.sourcing else None
        customer_status = order.sourcing.customer_facing_status if order.sourcing else None
        pickup_code = order.sourcing.pickup_code if order.sourcing else None

    lines = [
        f"📦 <b>Order {code}</b>",
        f"Status: <b>{order_status}</b>",
        f"Delivery: {delivery_label}",
    ]
    if fulfillment_status:
        lines.append(f"Fulfilment: {_FULFILLMENT_LABEL.get(fulfillment_status, fulfillment_status.value)}")
    if customer_status:
        lines.append(customer_status)
    if area:
        lines.append(f"Area: {area}")
    if rider_name:
        lines.append(f"Rider: {rider_name}")
    if pickup_code and fulfillment_status in (
        FulfillmentStatus.PACK_READY,
        FulfillmentStatus.DISPATCH_ASSIGNED,
        FulfillmentStatus.PICKED_UP,
    ):
        lines.append(f"Pickup code: <code>{pickup_code}</code>")
    lines.append("\nWe'll message you as your order progresses.")

    kb = InlineKeyboardBuilder()
    if tracking_url:
        kb.button(text="🗺 Track on Map", url=tracking_url)
    kb.button(text="💬 Speak to a Human", callback_data="menu:human")
    kb.button(text="⬅️ Main Menu", callback_data="menu:home")
    kb.adjust(1)
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup())
    await call.answer()
