"""CSV importer service logic: creating new products + applying rows.

Covers the behaviour the bot handler relies on (create for unmatched rows,
update for matched), including the pharmacy-safety rule that a new product is
only sellable when the row marks it OTC with price + stock.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models import Product, ProductPricing
from app.services.catalog import is_buyable
from app.services.products_admin import apply_csv_row, create_product_from_name

ADMIN = 42


async def _pricing(session, product) -> ProductPricing:
    return (
        await session.execute(select(ProductPricing).where(ProductPricing.product_id == product.id))
    ).scalar_one()


@pytest.mark.asyncio
async def test_create_new_otc_product_becomes_buyable(session):
    row = {
        "product_name": "Vitamin C 1000mg",
        "dosage": "1000mg",
        "cost_price": "800",
        "selling_price": "1500",
        "stock": "40",
        "prescription": "OTC",
        "availability": "yes",
        "category": "Supplements",
        "description": "Immune support",
    }
    p = await create_product_from_name(session, row["product_name"], ADMIN, strength=row["dosage"])
    await apply_csv_row(session, p, row, ADMIN)
    await session.flush()

    assert p.generic_name == "Vitamin C 1000mg"  # seeded from name
    assert p.strength == "1000mg"
    assert p.category == "Supplements"
    assert p.requires_prescription is False
    assert p.requires_review is False  # OTC → cleared for sale
    assert p.is_listed is True
    pricing = await _pricing(session, p)
    assert pricing.selling_price == Decimal("1500")
    assert pricing.cost_price == Decimal("800")
    assert pricing.stock_qty == 40
    assert pricing.is_in_stock is True

    p.pricing = pricing
    assert is_buyable(p) is True


@pytest.mark.asyncio
async def test_new_product_without_prescription_flag_waits_for_review(session):
    """Safety: a new product with no OTC/Rx marker stays review-required (not sellable)."""
    row = {
        "product_name": "Mystery Syrup",
        "selling_price": "1200",
        "stock": "10",
        "availability": "yes",
    }
    p = await create_product_from_name(session, row["product_name"], ADMIN)
    await apply_csv_row(session, p, row, ADMIN)
    await session.flush()

    assert p.requires_review is True  # model default preserved — needs pharmacist clearance
    pricing = await _pricing(session, p)
    p.pricing = pricing
    assert is_buyable(p) is False


@pytest.mark.asyncio
async def test_new_rx_product_requires_review(session):
    row = {"product_name": "Amoxil 250", "selling_price": "900", "stock": "5", "prescription": "Rx"}
    p = await create_product_from_name(session, row["product_name"], ADMIN)
    await apply_csv_row(session, p, row, ADMIN)
    await session.flush()

    assert p.requires_prescription is True
    assert p.requires_review is True
    pricing = await _pricing(session, p)
    p.pricing = pricing
    assert is_buyable(p) is False  # Rx never buyable via catalog


@pytest.mark.asyncio
async def test_apply_row_updates_existing_product(session):
    p = Product(name="Paracetamol 500", generic_name="Paracetamol", requires_review=False)
    p.pricing = ProductPricing(selling_price=Decimal("100"), cost_price=Decimal("50"), stock_qty=5, is_in_stock=True)
    session.add(p)
    await session.flush()

    await apply_csv_row(session, p, {"product_name": "Paracetamol 500", "selling_price": "250", "stock": "80"}, ADMIN)
    await session.flush()

    pricing = await _pricing(session, p)
    assert pricing.selling_price == Decimal("250")
    assert pricing.stock_qty == 80
    assert pricing.is_in_stock is True


@pytest.mark.asyncio
async def test_unknown_category_is_skipped_not_fatal(session):
    p = await create_product_from_name(session, "Odd Item", ADMIN)
    # 'Groceries' is not a valid category — must not raise.
    await apply_csv_row(session, p, {"product_name": "Odd Item", "category": "Groceries", "selling_price": "300"}, ADMIN)
    await session.flush()
    assert p.category is None
