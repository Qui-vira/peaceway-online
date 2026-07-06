"""Web orders API — cart checkout and order history."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentCustomer, DbSession
from app.models.catalog import Product
from app.models.orders import Order, PaymentMethod
from app.services.orders import create_order as create_order_record
from app.services.pricing import FeeConfig, QuoteItem, quote_order

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
    fulfillment_status: str | None = None
    customer_facing_status: str | None = None
    delivery_status: str
    subtotal: str
    delivery_fee: str
    total: str
    items: list[OrderItemOut]
    created_at: str

    model_config = {"from_attributes": True}


# ── Helpers ───────────────────────────────────────────────────────────────────

DELIVERY_FEE = Decimal("500")  # flat ₦500 for now


def _order_out(order: Order) -> OrderOut:
    return OrderOut(
        id=str(order.id),
        code=order.code,
        status=order.status.value,
        fulfillment_status=order.sourcing.fulfillment_status.value if order.sourcing else None,
        customer_facing_status=order.sourcing.customer_facing_status if order.sourcing else None,
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
    try:
        payment_method = PaymentMethod(body.payment_method)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported payment method.",
        ) from exc

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

    subtotal = Decimal("0")
    quote_items: list[QuoteItem] = []
    service_cart: list[dict] = []

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
        quote_items.append(
            QuoteItem(name=p.name, quantity=ci.quantity, selling_price=unit_price)
        )
        service_cart.append(
            {
                "product_id": str(pid),
                "name": p.name,
                "unit_price": str(unit_price),
                "qty": ci.quantity,
                "requires_prescription": p.requires_prescription,
            }
        )

    quote = quote_order(
        quote_items,
        DELIVERY_FEE,
        FeeConfig(),
        payment_method,
    )

    order = await create_order_record(
        db,
        customer_id=customer.id,
        cart=service_cart,
        quote=quote,
        delivery={
            "full_name": customer.full_name,
            "phone": customer.phone,
            "address": body.delivery_address,
            "area": body.delivery_area or customer.delivery_area,
            "note": body.delivery_note,
        },
        payment_method=payment_method,
    )

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
