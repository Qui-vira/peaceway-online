from decimal import Decimal
from uuid import uuid4

from app.models import Customer, OrderStatus, RxStatus
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


async def _make_customer(session):
    c = Customer(telegram_id=12345, full_name="Ada Obi")
    session.add(c)
    await session.flush()
    return c


def test_generate_code_format():
    code = generate_code()
    assert code.startswith("PW-") and len(code) == 9


async def test_otc_order_awaits_payment(session):
    c = await _make_customer(session)
    cart = [{"product_id": str(uuid4()), "name": "Paracetamol", "unit_price": "1000", "qty": 2, "requires_prescription": False}]
    order = await create_order(
        session, customer_id=c.id, cart=cart, quote=_quote(), delivery=_delivery(), payment_method=None
    )
    assert order.status == OrderStatus.AWAITING_PAYMENT
    assert order.rx_status == RxStatus.NOT_REQUIRED
    assert order.total == Decimal("2730.00")
    assert len(order.items) == 1


async def test_rx_order_requires_prescription(session):
    c = await _make_customer(session)
    cart = [{"product_id": str(uuid4()), "name": "Amoxicillin", "unit_price": "1500", "qty": 1, "requires_prescription": True}]
    order = await create_order(
        session, customer_id=c.id, cart=cart, quote=_quote(), delivery=_delivery(), payment_method=None
    )
    assert order.status == OrderStatus.NEW
    assert order.rx_status == RxStatus.PRESCRIPTION_REQUIRED
