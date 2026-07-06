"""Shared sourcing control logic for out-of-stock rescue workflow."""
from __future__ import annotations

import secrets
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    FulfillmentStatus,
    NetworkPartner,
    Order,
    OrderStatusHistory,
    OrderSourcing,
    PartnerChannel,
    PartnerType,
    ProductPricing,
)


def build_customer_status(status: FulfillmentStatus) -> str:
    labels = {
        FulfillmentStatus.IN_STOCK: "Ordered through Peaceway · In stock now",
        FulfillmentStatus.SOURCE_FROM_NETWORK: "Ordered through Peaceway · Sourcing from approved partner",
        FulfillmentStatus.SOURCING_REQUESTED: "Ordered through Peaceway · Approved partner sourcing requested",
        FulfillmentStatus.PARTNER_CONFIRMED: "Fulfilled by approved partner · Verified by Peaceway",
        FulfillmentStatus.PARTNER_REJECTED: "Source request unsuccessful · Peaceway reviewing next step",
        FulfillmentStatus.PACK_READY: "Fulfilled by approved partner · Packed and ready for pickup",
        FulfillmentStatus.DISPATCH_ASSIGNED: "Delivered under Peaceway tracking · Rider assigned",
        FulfillmentStatus.PICKED_UP: "Delivered under Peaceway tracking · Rider picked up package",
        FulfillmentStatus.DELIVERED: "Delivered under Peaceway tracking",
        FulfillmentStatus.FAILED: "Peaceway is reviewing a fulfilment issue",
    }
    return labels[status]


def generate_pickup_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(8))


async def _record(session: AsyncSession, order_id, field, from_value, to_value, by, note=None) -> None:
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


async def evaluate_cart_stock(session: AsyncSession, cart: list[dict]) -> list[dict]:
    product_ids = [UUID(item["product_id"]) for item in cart]
    rows = (
        await session.execute(
            select(ProductPricing).where(ProductPricing.product_id.in_(product_ids))
        )
    ).scalars().all()
    pricing_map = {row.product_id: row for row in rows}

    shortages: list[dict] = []
    for item in cart:
        pid = UUID(item["product_id"])
        qty = int(item["qty"])
        pricing = pricing_map.get(pid)
        available_qty = pricing.stock_qty if pricing else 0
        is_in_stock = bool(pricing and pricing.is_in_stock and available_qty >= qty)
        if not is_in_stock:
            shortages.append(
                {
                    "product_id": item["product_id"],
                    "product_name": item["name"],
                    "requested_qty": qty,
                    "available_qty": available_qty,
                    "requires_prescription": bool(item.get("requires_prescription")),
                }
            )
    return shortages


async def ensure_order_sourcing(
    session: AsyncSession,
    *,
    order: Order,
    cart: list[dict],
    shortages: list[dict],
    by: str = "system",
) -> OrderSourcing:
    sourcing = order.__dict__.get("sourcing")
    if sourcing is None:
        sourcing = OrderSourcing(order_id=order.id)
        order.sourcing = sourcing
    sourcing.requested_items = [
        {
            "product_id": item["product_id"],
            "product_name": item["name"],
            "requested_qty": int(item["qty"]),
        }
        for item in cart
    ]
    if shortages:
        sourcing.sourcing_required = True
        sourcing.fulfillment_status = FulfillmentStatus.SOURCE_FROM_NETWORK
        sourcing.sourcing_request = {"shortages": shortages}
        sourcing.customer_facing_status = build_customer_status(FulfillmentStatus.SOURCE_FROM_NETWORK)
        session.add(sourcing)
        await session.flush()
        await transition_fulfillment(
            session,
            order=order,
            sourcing=sourcing,
            new_status=FulfillmentStatus.SOURCING_REQUESTED,
            by=by,
            note="Order cannot be fulfilled from Peaceway stock alone.",
        )
    else:
        sourcing.sourcing_required = False
        sourcing.fulfillment_status = FulfillmentStatus.IN_STOCK
        sourcing.customer_facing_status = build_customer_status(FulfillmentStatus.IN_STOCK)
        session.add(sourcing)
    return sourcing


async def transition_fulfillment(
    session: AsyncSession,
    *,
    order: Order,
    sourcing: OrderSourcing,
    new_status: FulfillmentStatus,
    by: str,
    note: str | None = None,
) -> None:
    old = sourcing.fulfillment_status.value if sourcing.fulfillment_status else None
    sourcing.fulfillment_status = new_status
    sourcing.customer_facing_status = build_customer_status(new_status)
    await _record(session, order.id, "fulfillment_status", old, new_status.value, by, note)


async def assign_partner(
    session: AsyncSession,
    *,
    order: Order,
    partner: NetworkPartner,
    note: str | None = None,
    by: str = "system",
) -> OrderSourcing:
    sourcing = order.__dict__.get("sourcing")
    if sourcing is None:
        sourcing = OrderSourcing(order_id=order.id)
        order.sourcing = sourcing
    sourcing.partner_id = partner.id
    sourcing.partner_type = partner.partner_type
    sourcing.sourcing_channel = partner.channel_type
    session.add(sourcing)
    await transition_fulfillment(
        session,
        order=order,
        sourcing=sourcing,
        new_status=FulfillmentStatus.SOURCING_REQUESTED,
        by=by,
        note=note or f"Sourcing request routed to {partner.name}.",
    )
    return sourcing


async def confirm_partner(
    session: AsyncSession,
    *,
    order: Order,
    confirmed_quantity: int,
    confirmed_price: Decimal,
    expiry_or_batch_confirmation: str,
    ready_for_pickup_at: datetime | None,
    confirmed_items: list[dict] | None,
    by: str,
    note: str | None = None,
) -> OrderSourcing:
    sourcing = order.__dict__.get("sourcing")
    if sourcing is None:
        sourcing = OrderSourcing(order_id=order.id)
        order.sourcing = sourcing
    sourcing.confirmed_quantity = confirmed_quantity
    sourcing.confirmed_price = confirmed_price
    sourcing.expiry_or_batch_confirmation = expiry_or_batch_confirmation
    sourcing.ready_for_pickup_at = ready_for_pickup_at
    sourcing.confirmed_items = confirmed_items
    session.add(sourcing)
    await transition_fulfillment(
        session,
        order=order,
        sourcing=sourcing,
        new_status=FulfillmentStatus.PARTNER_CONFIRMED,
        by=by,
        note=note or "Partner confirmed availability and pricing.",
    )
    return sourcing


async def reject_partner(
    session: AsyncSession,
    *,
    order: Order,
    reason: str,
    by: str,
) -> OrderSourcing:
    sourcing = order.__dict__.get("sourcing")
    if sourcing is None:
        sourcing = OrderSourcing(order_id=order.id)
        order.sourcing = sourcing
    sourcing.last_error = reason
    session.add(sourcing)
    await transition_fulfillment(
        session,
        order=order,
        sourcing=sourcing,
        new_status=FulfillmentStatus.PARTNER_REJECTED,
        by=by,
        note=reason,
    )
    return sourcing


async def mark_pack_ready(
    session: AsyncSession,
    *,
    order: Order,
    pack_verification_photo: str | None,
    pickup_code: str | None,
    by: str,
) -> OrderSourcing:
    sourcing = order.__dict__.get("sourcing")
    if sourcing is None:
        sourcing = OrderSourcing(order_id=order.id)
        order.sourcing = sourcing
    sourcing.pack_verification_photo = pack_verification_photo
    sourcing.pickup_code = pickup_code or sourcing.pickup_code or generate_pickup_code()
    session.add(sourcing)
    await transition_fulfillment(
        session,
        order=order,
        sourcing=sourcing,
        new_status=FulfillmentStatus.PACK_READY,
        by=by,
        note="Partner package verified and ready for pickup.",
    )
    return sourcing


async def mark_dispatch_assigned(
    session: AsyncSession,
    *,
    order: Order,
    by: str,
) -> OrderSourcing:
    sourcing = order.__dict__.get("sourcing")
    if sourcing is None:
        sourcing = OrderSourcing(order_id=order.id)
        order.sourcing = sourcing
    session.add(sourcing)
    await transition_fulfillment(
        session,
        order=order,
        sourcing=sourcing,
        new_status=FulfillmentStatus.DISPATCH_ASSIGNED,
        by=by,
        note="Dispatch assigned after pack-ready confirmation.",
    )
    return sourcing


async def mark_picked_up(
    session: AsyncSession,
    *,
    order: Order,
    pickup_proof: str | None,
    by: str,
) -> OrderSourcing:
    sourcing = order.__dict__.get("sourcing")
    if sourcing is None:
        sourcing = OrderSourcing(order_id=order.id)
        order.sourcing = sourcing
    sourcing.pickup_proof = pickup_proof
    session.add(sourcing)
    await transition_fulfillment(
        session,
        order=order,
        sourcing=sourcing,
        new_status=FulfillmentStatus.PICKED_UP,
        by=by,
        note="Pickup verified with Peaceway code and proof.",
    )
    return sourcing


async def mark_delivered(
    session: AsyncSession,
    *,
    order: Order,
    delivery_proof: str | None,
    by: str,
) -> OrderSourcing:
    sourcing = order.__dict__.get("sourcing")
    if sourcing is None:
        sourcing = OrderSourcing(order_id=order.id)
        order.sourcing = sourcing
    sourcing.delivery_proof = delivery_proof
    session.add(sourcing)
    await transition_fulfillment(
        session,
        order=order,
        sourcing=sourcing,
        new_status=FulfillmentStatus.DELIVERED,
        by=by,
        note="Delivery confirmed under Peaceway tracking.",
    )
    return sourcing


async def mark_failed(
    session: AsyncSession,
    *,
    order: Order,
    reason: str,
    by: str,
) -> OrderSourcing:
    sourcing = order.__dict__.get("sourcing")
    if sourcing is None:
        sourcing = OrderSourcing(order_id=order.id)
        order.sourcing = sourcing
    sourcing.last_error = reason
    session.add(sourcing)
    await transition_fulfillment(
        session,
        order=order,
        sourcing=sourcing,
        new_status=FulfillmentStatus.FAILED,
        by=by,
        note=reason,
    )
    return sourcing
