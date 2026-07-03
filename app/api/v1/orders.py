"""Web orders API — cart checkout and order history."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func

from app.api.deps import CurrentCustomer, DbSession
from app.models.catalog import Product, ProductPricing
from app.models.orders import (
    Customer,
    Order,
    OrderItem,
    OrderStatus,
    DeliveryStatus,
    RxStatus,
)

router = APIRouter(tags=["orders"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class CartItemIn(BaseModel):
    product_id: str
    quantity: int


class CheckoutBody(BaseModel):
    items: list[CartItemIn]
    delivery_address: str | None = None
    delivery_area: str | None = None
    delivery_note: str | None = None
    payment_method: str = "BANK_TRANSFER"  # BANK_TRANSFER | FLUTTERWAVE


class OrderItemOut(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    unit_price: str
    line_total: str


class OrderOut(BaseModel):
    id: str
    code: str
    status: str
    delivery_status: str
    subtotal: str
    delivery_fee: str
    total: str
    items: list[OrderItemOut]
    created_at: str

    model_config = {"from_attributes": True}


# ── Helpers ───────────────────────────────────────────────────────────────────

DELIVERY_FEE = Decimal("500")  # flat ₦500 for now


def _generate_code(seq: int) -> str:
    from datetime import date
    y = date.today().year
    return f"PW-{y}-{seq:04d}"


def _order_out(order: Order) -> OrderOut:
    return OrderOut(
        id=str(order.id),
        code=order.code,
        status=order.status.value,
        delivery_status=order.delivery_status.value,
        subtotal=str(order.subtotal),
        delivery_fee=str(order.delivery_fee),
        total=str(order.total),
        items=[
            OrderItemOut(
                product_id=str(i.product_id),
                product_name=i.product_name,
                quantity=i.quantity,
                unit_price=str(i.unit_price),
                line_total=str(i.line_total),
            )
            for i in order.items
        ],
        created_at=order.created_at.isoformat(),
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/orders", status_code=status.HTTP_201_CREATED)
async def create_order(
    body: CheckoutBody,
    customer: CurrentCustomer,
    db: DbSession,
) -> OrderOut:
    """Place an order from the web cart."""
    if not body.items:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cart is empty.",
        )

    # Resolve products + prices
    product_ids = [UUID(item.product_id) for item in body.items]
    products = (
        await db.execute(
            select(Product).where(Product.id.in_(product_ids), Product.is_listed == True)  # noqa: E712
        )
    ).scalars().all()

    if len(products) != len(body.items):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="One or more products are unavailable.",
        )

    product_map = {p.id: p for p in products}

    # Build order code — use current order count as sequence
    count = (await db.execute(select(func.count()).select_from(Order))).scalar_one()
    code = _generate_code(count + 1)

    subtotal = Decimal("0")
    order_items: list[OrderItem] = []

    for ci in body.items:
        pid = UUID(ci.product_id)
        p = product_map[pid]
        if p.pricing is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{p.name} has no price set.",
            )
        unit_price = p.pricing.selling_price
        line_total = unit_price * ci.quantity
        subtotal += line_total
        order_items.append(
            OrderItem(
                product_id=pid,
                product_name=p.name,
                quantity=ci.quantity,
                unit_price=unit_price,
                line_total=line_total,
                requires_prescription=p.requires_prescription,
            )
        )

    total = subtotal + DELIVERY_FEE

    order = Order(
        code=code,
        customer_id=customer.id,
        status=OrderStatus.NEW,
        rx_status=RxStatus.NOT_REQUIRED,
        delivery_status=DeliveryStatus.NONE,
        subtotal=subtotal,
        delivery_fee=DELIVERY_FEE,
        total=total,
        delivery_address=body.delivery_address,
        delivery_area=body.delivery_area or customer.delivery_area,
        delivery_note=body.delivery_note,
        delivery_name=customer.full_name,
        delivery_phone=customer.phone,
        items=order_items,
    )
    db.add(order)
    await db.flush()

    return _order_out(order)


@router.get("/orders")
async def list_orders(
    customer: CurrentCustomer,
    db: DbSession,
) -> list[OrderOut]:
    """List all orders for the authenticated customer, newest first."""
    rows = (
        await db.execute(
            select(Order)
            .where(Order.customer_id == customer.id)
            .order_by(Order.created_at.desc())
        )
    ).scalars().all()
    return [_order_out(r) for r in rows]


@router.get("/orders/{order_id}")
async def get_order(
    order_id: UUID,
    customer: CurrentCustomer,
    db: DbSession,
) -> OrderOut:
    order = (
        await db.execute(
            select(Order).where(
                Order.id == order_id,
                Order.customer_id == customer.id,
            )
        )
    ).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    return _order_out(order)
