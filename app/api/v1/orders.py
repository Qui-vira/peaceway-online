"""Web orders API - cart checkout and order history."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentCustomer, DbSession
from app.models.catalog import Product
from app.models.ops import DeliveryZone
from app.models.orders import Order, PaymentMethod
from app.services.orders import create_order as create_order_record
from app.services.pricing import FeeConfig, QuoteItem, quote_order
from app.services.web_customers import get_delivery_area

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
    delivery_code: str | None = None
    subtotal: str
    delivery_fee: str
    total: str
    items: list[OrderItemOut]
    created_at: str

    model_config = {"from_attributes": True}


# ── Helpers ───────────────────────────────────────────────────────────────────

# The fallback when an order names no area, or names one we do not deliver to.
# It is deliberately the most expensive real zone rather than a cheap round
# number: under-quoting a delivery is a refund and a phone call, and the flat
# ₦500 this replaced was below every zone the pharmacy actually serves.
FALLBACK_DELIVERY_FEE = Decimal("2500")


async def resolve_delivery_fee(db: AsyncSession, area: str | None) -> Decimal:
    """Fee for *area* from the delivery_zones table.

    The web checkout used to hardcode ₦500 on both sides of the wire while
    `/profile` showed the customer the real per-area prices (₦700-₦3,500) from
    this same table. One product quoting two numbers for the same delivery is
    the kind of thing that reads as "not a real pharmacy", so the price now has
    exactly one source and it is the one operations already maintain.

    Matching is case-insensitive on the zone name because the area arrives from
    a customer profile field, not from a foreign key.
    """
    if not area:
        return FALLBACK_DELIVERY_FEE

    zone = (
        await db.execute(
            select(DeliveryZone)
            .where(
                DeliveryZone.is_active.is_(True),
                func.lower(DeliveryZone.name) == area.strip().lower(),
            )
            .limit(1)
        )
    ).scalar_one_or_none()

    return Decimal(zone.fee) if zone else FALLBACK_DELIVERY_FEE


def _order_out(order: Order) -> OrderOut:
    return OrderOut(
        id=str(order.id),
        code=order.code,
        status=order.status.value,
        fulfillment_status=order.sourcing.fulfillment_status.value if order.sourcing else None,
        customer_facing_status=order.sourcing.customer_facing_status if order.sourcing else None,
        delivery_status=order.delivery_status.value,
        # The customer reads this to the rider at hand-off (only while out for delivery).
        delivery_code=order.delivery_code if order.delivery_status.value in ("PICKED_UP", "IN_TRANSIT", "NEAR_CUSTOMER") else None,
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

    # `customer.delivery_area` used to be read straight off the model here. There
    # is no such attribute - the area lives in the `addresses` JSONB list and has
    # an accessor for exactly that reason - so every web order raised
    # AttributeError and 500'd, and the customer was told to check their
    # connection. Go through the accessor, like the rest of the codebase does.
    delivery_area = body.delivery_area or get_delivery_area(customer)
    delivery_fee = await resolve_delivery_fee(db, delivery_area)

    quote = quote_order(
        quote_items,
        delivery_fee,
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
            "area": delivery_area,
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
