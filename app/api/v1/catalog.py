"""Public catalog API - lists products marked is_listed=True with pricing."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import or_, select

from app.api.deps import DbSession
from app.models.catalog import Product

router = APIRouter(tags=["catalog"])


class ProductOut(BaseModel):
    id: str
    name: str
    generic_name: str
    brand_name: str | None
    dosage_form: str | None
    strength: str | None
    category: str | None
    description: str | None
    requires_prescription: bool
    selling_price: str | None
    is_in_stock: bool

    model_config = {"from_attributes": True}


def _out(p: Product) -> ProductOut:
    pricing = p.pricing
    return ProductOut(
        id=str(p.id),
        name=p.name,
        generic_name=p.generic_name,
        brand_name=p.brand_name,
        dosage_form=p.dosage_form,
        strength=p.strength,
        category=p.category,
        description=p.description,
        requires_prescription=p.requires_prescription,
        selling_price=str(pricing.selling_price) if pricing else None,
        is_in_stock=pricing.is_in_stock if pricing else False,
    )


@router.get("/catalog")
async def list_catalog(
    db: DbSession,
    q: str | None = Query(None, description="Search by name"),
    category: str | None = Query(None),
    in_stock_only: bool = Query(False),
) -> list[ProductOut]:
    """List all listed products, optionally filtered."""
    stmt = select(Product).where(Product.is_listed == True)  # noqa: E712
    if q:
        term = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                Product.name.ilike(term),
                Product.generic_name.ilike(term),
                Product.brand_name.ilike(term),
            )
        )
    if category:
        stmt = stmt.where(Product.category.ilike(category))
    stmt = stmt.order_by(Product.name)
    rows = (await db.execute(stmt)).scalars().all()
    products = [_out(p) for p in rows]
    if in_stock_only:
        products = [p for p in products if p.is_in_stock]
    return products


@router.get("/catalog/categories")
async def list_categories(db: DbSession) -> list[str]:
    """Return distinct non-null category values from listed products, sorted."""
    rows = (
        await db.execute(
            select(Product.category)
            .where(Product.is_listed == True, Product.category.is_not(None))  # noqa: E712
            .distinct()
            .order_by(Product.category)
        )
    ).scalars().all()
    return [r for r in rows if r]


@router.get("/catalog/{product_id}")
async def get_product(product_id: UUID, db: DbSession) -> ProductOut:
    """Return a single listed product."""
    p = (
        await db.execute(
            select(Product).where(Product.id == product_id, Product.is_listed == True)  # noqa: E712
        )
    ).scalar_one_or_none()
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    return _out(p)
