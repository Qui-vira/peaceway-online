"""List & price a handful of auto-OTC products so the ordering flow is testable.

Picks products the Rx classifier already cleared (requires_review = False,
requires_prescription = False) and gives them a demo cost/selling price + stock.
Admin can later adjust everything from Telegram. Idempotent.

Usage: python scripts/seed_demo_listing.py
"""
from __future__ import annotations

import asyncio
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.db import _normalize_async_url
from app.models import Product, ProductPricing

# Demo price points (cost, selling) keyed by a generic-name fragment to look for.
WANTED = [
    ("paracetamol", Decimal("150"), Decimal("350")),
    ("ibuprofen", Decimal("200"), Decimal("500")),
    ("ascorbic", Decimal("300"), Decimal("700")),      # Vitamin C
    ("multivitamin", Decimal("800"), Decimal("1500")),
    ("loratadine", Decimal("250"), Decimal("600")),
    ("cetirizine", Decimal("250"), Decimal("600")),
    ("oral rehydration", Decimal("150"), Decimal("400")),
    ("zinc", Decimal("300"), Decimal("750")),
]


async def run() -> None:
    engine = create_async_engine(_normalize_async_url(get_settings().database_url))
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    listed = 0

    async with maker() as session:
        for frag, cost, sell in WANTED:
            product = (
                await session.execute(
                    select(Product)
                    .where(
                        Product.generic_name.ilike(f"%{frag}%"),
                        Product.requires_review.is_(False),
                        Product.requires_prescription.is_(False),
                    )
                    .limit(1)
                )
            ).scalar_one_or_none()
            if product is None:
                # Fall back to name match if generic didn't hit.
                product = (
                    await session.execute(
                        select(Product).where(Product.name.ilike(f"%{frag}%")).limit(1)
                    )
                ).scalar_one_or_none()
            if product is None:
                print(f"  (no product found for '{frag}')")
                continue

            product.is_listed = True
            product.requires_review = False
            product.requires_prescription = False
            pricing = product.pricing
            if pricing is None:
                pricing = ProductPricing(product_id=product.id)
                session.add(pricing)
            pricing.cost_price = cost
            pricing.selling_price = sell
            pricing.stock_qty = 100
            pricing.is_in_stock = True
            listed += 1
            print(f"  listed: {product.name}  NGN {sell:,.0f}")

        await session.commit()

    await engine.dispose()
    print(f"Done. {listed} products listed & priced.")


if __name__ == "__main__":
    asyncio.run(run())
