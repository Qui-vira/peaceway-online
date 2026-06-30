from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models import PriceHistory, Product
from app.services.products_admin import apply_change, parse_int, parse_money


def test_parse_money():
    assert parse_money("1,500") == Decimal("1500")
    assert parse_money("₦800") == Decimal("800")
    assert parse_money("abc") is None
    assert parse_money("-5") is None


def test_parse_int():
    assert parse_int("50") == 50
    assert parse_int("1,000") == 1000
    assert parse_int("x") is None


async def _product(session):
    p = Product(name="Test Drug", generic_name="Test", requires_review=True, is_listed=False)
    session.add(p)
    await session.flush()
    return p


async def test_set_selling_price_lists_product_and_logs(session):
    p = await _product(session)
    p.pricing = None
    summary = await apply_change(session, p, "selling_price", "1500", admin_id=111)
    await session.flush()
    assert p.pricing.selling_price == Decimal("1500")
    assert p.is_listed is True  # pricing an item lists it
    assert "1,500" in summary
    hist = (await session.execute(select(PriceHistory).where(PriceHistory.product_id == p.id))).scalars().all()
    assert any(h.field == "selling_price" and h.new_value == "1500" for h in hist)


async def test_invalid_price_raises(session):
    p = await _product(session)
    with pytest.raises(ValueError):
        await apply_change(session, p, "selling_price", "notanumber", admin_id=111)


async def test_stock_sets_in_stock(session):
    p = await _product(session)
    await apply_change(session, p, "selling_price", "500", admin_id=1)
    await apply_change(session, p, "stock", "20", admin_id=1)
    await session.flush()
    assert p.pricing.stock_qty == 20
    assert p.pricing.is_in_stock is True


async def test_rx_toggle(session):
    p = await _product(session)
    await apply_change(session, p, "rx", True, admin_id=1)
    assert p.requires_prescription is True
    await apply_change(session, p, "rx", False, admin_id=1)
    assert p.requires_prescription is False
