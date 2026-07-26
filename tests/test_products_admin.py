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


async def _product(db_session):
    p = Product(name="Test Drug", generic_name="Test", requires_review=True, is_listed=False)
    db_session.add(p)
    await db_session.flush()
    return p


async def test_set_selling_price_lists_product_and_logs(db_session):
    p = await _product(db_session)
    p.pricing = None
    summary = await apply_change(db_session, p, "selling_price", "1500", admin_id=111)
    await db_session.flush()
    assert p.pricing.selling_price == Decimal("1500")
    assert p.is_listed is True  # pricing an item lists it
    assert "1,500" in summary
    hist = (await db_session.execute(select(PriceHistory).where(PriceHistory.product_id == p.id))).scalars().all()
    assert any(h.field == "selling_price" and h.new_value == "1500" for h in hist)


async def test_invalid_price_raises(db_session):
    p = await _product(db_session)
    with pytest.raises(ValueError):
        await apply_change(db_session, p, "selling_price", "notanumber", admin_id=111)


async def test_stock_sets_in_stock(db_session):
    p = await _product(db_session)
    await apply_change(db_session, p, "selling_price", "500", admin_id=1)
    await apply_change(db_session, p, "stock", "20", admin_id=1)
    await db_session.flush()
    assert p.pricing.stock_qty == 20
    assert p.pricing.is_in_stock is True


async def test_rx_toggle(db_session):
    p = await _product(db_session)
    await apply_change(db_session, p, "rx", True, admin_id=1)
    assert p.requires_prescription is True
    await apply_change(db_session, p, "rx", False, admin_id=1)
    assert p.requires_prescription is False
