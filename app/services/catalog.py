"""Catalog search and lookup used by the customer ordering flow."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product, ProductAlias


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


async def popular_products(session: AsyncSession, limit: int = 10) -> list[Product]:
    """Listed, in-stock products (placeholder for true popularity ranking)."""
    stmt = (
        select(Product)
        .where(Product.is_listed.is_(True))
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
