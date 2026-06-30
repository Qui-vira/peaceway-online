"""Catalog search and lookup used by the customer ordering flow."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product, ProductAlias, ProductPricing


def _like(term: str) -> str:
    # Escape LIKE wildcards in user input.
    safe = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{safe}%"


async def search_products(session: AsyncSession, query: str, limit: int = 12) -> list[Product]:
    """Search by product name, generic name, or alias (normalized)."""
    q = query.strip()
    if not q:
        return []
    pattern = _like(q)
    norm = _like(q.lower())

    alias_subq = (
        select(ProductAlias.product_id)
        .where(ProductAlias.normalized_name.ilike(norm, escape="\\"))
        .scalar_subquery()
    )
    stmt = (
        select(Product)
        .where(
            or_(
                Product.name.ilike(pattern, escape="\\"),
                Product.generic_name.ilike(pattern, escape="\\"),
                Product.brand_name.ilike(pattern, escape="\\"),
                Product.id.in_(alias_subq),
            )
        )
        # Listed (buyable) products first, then alphabetical.
        .order_by(Product.is_listed.desc(), Product.name)
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_product(session: AsyncSession, product_id: UUID) -> Product | None:
    return (
        await session.execute(select(Product).where(Product.id == product_id))
    ).scalar_one_or_none()


def is_buyable(p: Product) -> bool:
    """Single source of truth for 'can a customer add this to cart right now'."""
    return bool(
        p.is_listed
        and not p.requires_prescription
        and not p.requires_review
        and p.pricing
        and p.pricing.is_in_stock
        and p.pricing.selling_price
        and p.pricing.selling_price > 0
    )


async def popular_products(session: AsyncSession, limit: int = 10) -> list[Product]:
    """Only products a customer can actually buy right now: listed, not Rx/review,
    priced, and in stock. Mirrors `is_buyable` at the SQL level."""
    stmt = (
        select(Product)
        .join(ProductPricing, ProductPricing.product_id == Product.id)
        .where(
            Product.is_listed.is_(True),
            Product.requires_prescription.is_(False),
            Product.requires_review.is_(False),
            ProductPricing.is_in_stock.is_(True),
            ProductPricing.selling_price > 0,
        )
        .order_by(Product.name)
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())


async def categories(session: AsyncSession) -> list[str]:
    stmt = select(Product.category).where(Product.category.is_not(None)).group_by(Product.category)
    return [c for c in (await session.execute(stmt)).scalars().all() if c]


async def products_in_category(session: AsyncSession, category: str, limit: int = 12) -> list[Product]:
    stmt = (
        select(Product)
        .where(Product.category == category)
        .order_by(Product.is_listed.desc(), Product.name)
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())
