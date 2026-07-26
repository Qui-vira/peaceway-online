from decimal import Decimal
from uuid import uuid4

from app.models import Customer, FulfillmentStatus, OrderStatus, Product, ProductPricing, RxStatus
from app.services.orders import create_order, generate_code
from app.services.pricing import Quote


def _quote():
    return Quote(
        subtotal=Decimal("2000.00"),
        delivery_fee=Decimal("700.00"),
        payment_fee=Decimal("30.00"),
        total=Decimal("2730.00"),
        product_profit=Decimal("800.00"),
    )


def _delivery():
    return {
        "full_name": "Ada Obi",
        "phone": "08030000000",
        "address": "12 Church St",
        "area": "Igando",
        "landmark": "Near market",
    }


async def _make_customer(db_session):
    c = Customer(telegram_id=12345, full_name="Ada Obi")
    db_session.add(c)
    await db_session.flush()
    return c


async def _make_product(db_session, *, stock_qty: int, is_in_stock: bool, requires_prescription: bool = False):
    pid = uuid4()
    product = Product(
        id=pid,
        name=f"Drug-{pid.hex[:6]}",
        generic_name="Generic",
        requires_prescription=requires_prescription,
        requires_review=requires_prescription,
        is_listed=True,
    )
    pricing = ProductPricing(
        product_id=pid,
        cost_price=Decimal("500"),
        selling_price=Decimal("1000"),
        stock_qty=stock_qty,
        is_in_stock=is_in_stock,
    )
    db_session.add(product)
    db_session.add(pricing)
    await db_session.flush()
    return product


def test_generate_code_format():
    code = generate_code()
    assert code.startswith("PW-") and len(code) == 9


async def test_otc_order_awaits_payment(db_session):
    c = await _make_customer(db_session)
    product = await _make_product(db_session, stock_qty=5, is_in_stock=True)
    cart = [{"product_id": str(product.id), "name": "Paracetamol", "unit_price": "1000", "qty": 2, "requires_prescription": False}]
    order = await create_order(
        db_session, customer_id=c.id, cart=cart, quote=_quote(), delivery=_delivery(), payment_method=None
    )
    assert order.status == OrderStatus.AWAITING_PAYMENT
    assert order.rx_status == RxStatus.NOT_REQUIRED
    assert order.sourcing is not None
    assert order.sourcing.fulfillment_status == FulfillmentStatus.IN_STOCK
    assert order.total == Decimal("2730.00")
    assert len(order.items) == 1


async def test_rx_order_requires_prescription(db_session):
    c = await _make_customer(db_session)
    product = await _make_product(db_session, stock_qty=4, is_in_stock=True, requires_prescription=True)
    cart = [{"product_id": str(product.id), "name": "Amoxicillin", "unit_price": "1500", "qty": 1, "requires_prescription": True}]
    order = await create_order(
        db_session, customer_id=c.id, cart=cart, quote=_quote(), delivery=_delivery(), payment_method=None
    )
    assert order.status == OrderStatus.NEW
    assert order.rx_status == RxStatus.PRESCRIPTION_REQUIRED
    assert order.sourcing is not None
    assert order.sourcing.fulfillment_status == FulfillmentStatus.IN_STOCK


async def test_out_of_stock_order_enters_sourcing_flow(db_session):
    c = await _make_customer(db_session)
    product = await _make_product(db_session, stock_qty=0, is_in_stock=False)
    cart = [{"product_id": str(product.id), "name": "Paracetamol", "unit_price": "1000", "qty": 2, "requires_prescription": False}]
    order = await create_order(
        db_session, customer_id=c.id, cart=cart, quote=_quote(), delivery=_delivery(), payment_method=None
    )
    assert order.status == OrderStatus.NEW
    assert order.sourcing is not None
    assert order.sourcing.sourcing_required is True
    assert order.sourcing.fulfillment_status == FulfillmentStatus.SOURCING_REQUESTED
    assert order.sourcing.customer_facing_status is not None
