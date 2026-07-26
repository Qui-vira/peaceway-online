from decimal import Decimal

from app.models import Product, ProductPricing
from app.services.catalog import is_buyable, popular_products


def _product(**overrides):
    defaults = dict(
        name="Test Drug", generic_name="Test", is_listed=True,
        requires_prescription=False, requires_review=False,
    )
    defaults.update(overrides)
    return Product(**defaults)


def test_is_buyable_requires_priced_in_stock_listing():
    p = _product()
    p.pricing = ProductPricing(selling_price=Decimal("500"), stock_qty=10, is_in_stock=True)
    assert is_buyable(p) is True


def test_is_buyable_false_when_unpriced():
    p = _product()
    p.pricing = ProductPricing(selling_price=Decimal("0"), stock_qty=0, is_in_stock=False)
    assert is_buyable(p) is False


def test_is_buyable_false_when_rx():
    p = _product(requires_prescription=True)
    p.pricing = ProductPricing(selling_price=Decimal("500"), stock_qty=10, is_in_stock=True)
    assert is_buyable(p) is False


def test_is_buyable_false_when_review_required():
    p = _product(requires_review=True)
    p.pricing = ProductPricing(selling_price=Decimal("500"), stock_qty=10, is_in_stock=True)
    assert is_buyable(p) is False


async def test_popular_products_excludes_unpriced_and_rx(db_session):
    buyable = _product(name="Buyable Drug")
    buyable.pricing = ProductPricing(selling_price=Decimal("500"), stock_qty=10, is_in_stock=True)

    unpriced = _product(name="Unpriced Drug")
    unpriced.pricing = ProductPricing(selling_price=Decimal("0"), stock_qty=0, is_in_stock=False)

    rx = _product(name="Rx Drug", requires_prescription=True)
    rx.pricing = ProductPricing(selling_price=Decimal("500"), stock_qty=10, is_in_stock=True)

    out_of_stock = _product(name="Out Of Stock Drug")
    out_of_stock.pricing = ProductPricing(selling_price=Decimal("500"), stock_qty=0, is_in_stock=False)

    db_session.add_all([buyable, unpriced, rx, out_of_stock])
    await db_session.flush()

    results = await popular_products(db_session)
    names = {p.name for p in results}
    assert names == {"Buyable Drug"}
