from decimal import Decimal

from sqlalchemy import select

from app.models import Product, ProductAlias, ProductPricing


async def test_create_product_with_pricing_and_alias(session):
    p = Product(
        name="Paracetamol 500mg Tablet",
        generic_name="Paracetamol",
        strength="500mg",
        dosage_form="Tablet",
        category="OTC",
        requires_prescription=False,
        requires_review=False,
        is_listed=True,
    )
    p.aliases.append(ProductAlias(alias_name="PCM 500", normalized_name="pcm 500"))
    p.pricing = ProductPricing(
        cost_price=Decimal("200.00"),
        selling_price=Decimal("350.00"),
        stock_qty=50,
        is_in_stock=True,
    )
    session.add(p)
    await session.flush()

    fetched = (await session.execute(select(Product).where(Product.id == p.id))).scalar_one()
    assert fetched.generic_name == "Paracetamol"
    assert fetched.is_listed is True
    assert fetched.pricing.selling_price == Decimal("350.00")
    assert fetched.aliases[0].alias_name == "PCM 500"


async def test_product_defaults_to_review_required(session):
    p = Product(name="Mystery Drug", generic_name="Unknown")
    session.add(p)
    await session.flush()
    assert p.requires_review is True
    assert p.is_listed is False
