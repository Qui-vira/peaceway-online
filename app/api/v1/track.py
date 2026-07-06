"""Public order-tracking endpoint — no auth required."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DbSession
from app.models.orders import Customer, Order, OrderStatusHistory

router = APIRouter(tags=["tracking"])


class TrackingHistoryItem(BaseModel):
    field: str
    to_value: str
    note: str | None
    created_at: str


class TrackingOut(BaseModel):
    code: str
    status: str
    fulfillment_status: str | None = None
    customer_facing_status: str | None = None
    pickup_code: str | None = None
    delivery_status: str
    items: list[dict]
    history: list[TrackingHistoryItem]
    created_at: str


@router.get("/track")
async def track_order(
    db: DbSession,
    code: str = Query(..., description="Order code e.g. PW-2024-0042"),
    phone: str = Query(..., description="Phone number used when ordering"),
) -> TrackingOut:
    """Look up an order by code + phone. No authentication required."""
    # Normalize
    code = code.strip().upper()
    phone = phone.strip().replace(" ", "").replace("-", "")

    order = (
        await db.execute(select(Order).where(Order.code == code))
    ).scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found. Check the code and try again.",
        )

    # Verify phone matches the customer
    customer = (
        await db.execute(select(Customer).where(Customer.id == order.customer_id))
    ).scalar_one_or_none()

    if customer is None or (customer.phone or "").replace(" ", "").replace("-", "") != phone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found. Check the code and try again.",
        )

    history_rows = (
        await db.execute(
            select(OrderStatusHistory)
            .where(OrderStatusHistory.order_id == order.id)
            .order_by(OrderStatusHistory.created_at)
        )
    ).scalars().all()

    history = [
        TrackingHistoryItem(
            field=h.field,
            to_value=h.to_value,
            note=h.note,
            created_at=h.created_at.isoformat(),
        )
        for h in history_rows
    ]

    items = [
        {
            "product_name": item.product_name,
            "quantity": item.quantity,
            "unit_price": str(item.unit_price),
            "line_total": str(item.line_total),
        }
        for item in order.items
    ]

    return TrackingOut(
        code=order.code,
        status=order.status.value,
        fulfillment_status=order.sourcing.fulfillment_status.value if order.sourcing else None,
        customer_facing_status=order.sourcing.customer_facing_status if order.sourcing else None,
        pickup_code=order.sourcing.pickup_code if order.sourcing else None,
        delivery_status=order.delivery_status.value,
        items=items,
        history=history,
        created_at=order.created_at.isoformat(),
    )
