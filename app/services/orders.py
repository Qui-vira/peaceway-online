"""Order lifecycle: creation, status transitions, and history."""
from __future__ import annotations

import secrets
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Order,
    OrderItem,
    OrderStatus,
    OrderStatusHistory,
    RxStatus,
)
from app.services.pricing import Quote


def generate_code() -> str:
    """Short, human-friendly order code, e.g. PW-7QK3M2."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "PW-" + "".join(secrets.choice(alphabet) for _ in range(6))


async def create_order(
    session: AsyncSession,
    *,
    customer_id: UUID,
    cart: list[dict],
    quote: Quote,
    delivery: dict,
    payment_method,
) -> Order:
    """Persist an order, its items, and the opening status-history row."""
    has_rx = any(i.get("requires_prescription") for i in cart)

    order_items = []
    for item in cart:
        unit = Decimal(item["unit_price"])
        qty = int(item["qty"])
        order_items.append(
            OrderItem(
                product_id=UUID(item["product_id"]),
                product_name=item["name"],
                quantity=qty,
                unit_price=unit,
                line_total=unit * qty,
                requires_prescription=bool(item.get("requires_prescription")),
            )
        )

    order = Order(
        code=generate_code(),
        customer_id=customer_id,
        status=OrderStatus.NEW,
        rx_status=RxStatus.PRESCRIPTION_REQUIRED if has_rx else RxStatus.NOT_REQUIRED,
        payment_method=payment_method,
        subtotal=quote.subtotal,
        delivery_fee=quote.delivery_fee,
        payment_fee=quote.payment_fee,
        offramp_fee=quote.offramp_fee,
        handling_fee=quote.handling_fee,
        total=quote.total,
        delivery_name=delivery.get("full_name"),
        delivery_phone=delivery.get("phone"),
        delivery_address=delivery.get("address"),
        delivery_area=delivery.get("area"),
        delivery_landmark=delivery.get("landmark"),
        delivery_preferred_time=delivery.get("preferred_time"),
        delivery_note=delivery.get("note"),
        items=order_items,
    )
    session.add(order)
    await session.flush()

    # Opening state: Rx orders await pharmacist review; OTC awaits payment.
    if has_rx:
        await _record(session, order.id, "rx_status", None, RxStatus.PRESCRIPTION_REQUIRED.value, "system")
    else:
        order.status = OrderStatus.AWAITING_PAYMENT
        await _record(session, order.id, "status", OrderStatus.NEW.value, OrderStatus.AWAITING_PAYMENT.value, "system")

    await session.flush()
    return order


async def _record(session, order_id, field, from_value, to_value, by, note=None) -> None:
    session.add(
        OrderStatusHistory(
            order_id=order_id,
            field=field,
            from_value=from_value,
            to_value=to_value,
            changed_by=by,
            note=note,
        )
    )


async def transition_status(
    session: AsyncSession, order: Order, new_status: OrderStatus, by: str, note: str | None = None
) -> None:
    old = order.status.value
    order.status = new_status
    await _record(session, order.id, "status", old, new_status.value, by, note)


async def transition_rx(
    session: AsyncSession, order: Order, new_rx: RxStatus, by: str, note: str | None = None
) -> None:
    old = order.rx_status.value
    order.rx_status = new_rx
    await _record(session, order.id, "rx_status", old, new_rx.value, by, note)


async def transition_delivery(
    session: AsyncSession, order: Order, new_delivery, by: str, note: str | None = None
) -> None:
    old = order.delivery_status.value
    order.delivery_status = new_delivery
    await _record(session, order.id, "delivery_status", old, new_delivery.value, by, note)
