"""Admin web API — password-gated staff endpoints."""
from __future__ import annotations

import os
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, or_, select

from app.api.deps import DbSession
from app.models.catalog import Product, ProductPricing
from app.models.ops import ProductRequest
from app.models.orders import Customer, Order
from app.services.products_admin import apply_change, parse_int, parse_money

router = APIRouter(tags=["admin"])

ADMIN_PASSWORD = os.getenv("ADMIN_WEB_PASSWORD", "")


# ── Auth ──────────────────────────────────────────────────────────────────────

class AuthBody(BaseModel):
    password: str


class AdminProductPatch(BaseModel):
    selling_price: str | None = None
    cost_price: str | None = None
    stock_qty: int | None = None
    is_listed: bool | None = None
    requires_prescription: bool | None = None


def _money_out(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _product_out(product: Product) -> dict:
    pricing = product.pricing
    return {
        "id": str(product.id),
        "name": product.name,
        "generic_name": product.generic_name,
        "brand_name": product.brand_name,
        "dosage_form": product.dosage_form,
        "strength": product.strength,
        "category": product.category,
        "requires_prescription": product.requires_prescription,
        "requires_review": product.requires_review,
        "is_listed": product.is_listed,
        "cost_price": _money_out(pricing.cost_price) if pricing else None,
        "selling_price": _money_out(pricing.selling_price) if pricing else None,
        "stock_qty": pricing.stock_qty if pricing else 0,
        "is_in_stock": pricing.is_in_stock if pricing else False,
        "updated_at": product.updated_at.isoformat(),
    }


@router.post("/admin/auth")
async def admin_auth(body: AuthBody) -> dict:
    if not ADMIN_PASSWORD or body.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password.")
    return {"ok": True}


def _check_admin(x_admin_password: str = Header(default="")) -> None:
    if not ADMIN_PASSWORD or x_admin_password != ADMIN_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized.")


AdminGuard = Depends(_check_admin)


# ── Requests ──────────────────────────────────────────────────────────────────

@router.get("/admin/requests", dependencies=[AdminGuard])
async def admin_list_requests(db: DbSession) -> list[dict]:
    rows = (
        await db.execute(
            select(ProductRequest).order_by(ProductRequest.created_at.desc()).limit(200)
        )
    ).scalars().all()
    return [
        {
            "id": str(r.id),
            "product_name": r.product_name,
            "status": r.status,
            "customer_phone": r.customer_phone,
            "urgency": r.urgency,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


# ── Orders ────────────────────────────────────────────────────────────────────

@router.get("/admin/orders", dependencies=[AdminGuard])
async def admin_list_orders(db: DbSession) -> list[dict]:
    rows = (
        await db.execute(
            select(Order).order_by(Order.created_at.desc()).limit(200)
        )
    ).scalars().all()
    return [
        {
            "id": str(o.id),
            "code": o.code,
            "status": o.status.value,
            "total": str(o.total),
            "created_at": o.created_at.isoformat(),
        }
        for o in rows
    ]


# ── Customers ─────────────────────────────────────────────────────────────────

@router.get("/admin/customers", dependencies=[AdminGuard])
async def admin_list_customers(db: DbSession) -> list[dict]:
    rows = (
        await db.execute(
            select(Customer).order_by(Customer.created_at.desc()).limit(200)
        )
    ).scalars().all()
    return [
        {
            "id": str(c.id),
            "full_name": c.full_name,
            "phone": c.phone,
            "email": c.email,
            "created_at": c.created_at.isoformat(),
        }
        for c in rows
    ]


# ── Products / Inventory ─────────────────────────────────────────────────────

@router.get("/admin/products", dependencies=[AdminGuard])
async def admin_list_products(
    db: DbSession,
    q: str | None = None,
    status_filter: Literal["all", "listed", "unlisted", "in_stock", "out_of_stock", "unpriced"] = "all",
    limit: int = 100,
    offset: int = 0,
) -> dict:
    limit = max(1, min(limit, 500))
    offset = max(0, offset)

    conditions = []
    if q:
        term = f"%{q.strip()}%"
        conditions.append(
            or_(
                Product.name.ilike(term),
                Product.generic_name.ilike(term),
                Product.brand_name.ilike(term),
                Product.nafdac_number.ilike(term),
            )
        )

    if status_filter == "listed":
        conditions.append(Product.is_listed.is_(True))
    elif status_filter == "unlisted":
        conditions.append(Product.is_listed.is_(False))
    elif status_filter == "in_stock":
        conditions.append(ProductPricing.is_in_stock.is_(True))
    elif status_filter == "out_of_stock":
        conditions.append(or_(ProductPricing.id.is_(None), ProductPricing.is_in_stock.is_(False)))
    elif status_filter == "unpriced":
        conditions.append(
            or_(
                ProductPricing.id.is_(None),
                ProductPricing.selling_price.is_(None),
                ProductPricing.selling_price <= 0,
            )
        )

    base = select(Product).outerjoin(ProductPricing)
    count_stmt = select(func.count(Product.id)).select_from(Product).outerjoin(ProductPricing)
    if conditions:
        base = base.where(*conditions)
        count_stmt = count_stmt.where(*conditions)

    rows = (
        await db.execute(base.order_by(Product.is_listed.desc(), Product.name).limit(limit).offset(offset))
    ).scalars().all()
    total = (await db.execute(count_stmt)).scalar_one()

    metrics = (
        await db.execute(
            select(
                func.count(Product.id),
                func.count(Product.id).filter(Product.is_listed.is_(True)),
                func.count(Product.id).filter(ProductPricing.is_in_stock.is_(True)),
                func.count(Product.id).filter(
                    or_(
                        ProductPricing.id.is_(None),
                        ProductPricing.selling_price.is_(None),
                        ProductPricing.selling_price <= 0,
                    )
                ),
            )
            .select_from(Product)
            .outerjoin(ProductPricing)
        )
    ).one()

    return {
        "items": [_product_out(p) for p in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
        "metrics": {
            "total": metrics[0],
            "listed": metrics[1],
            "in_stock": metrics[2],
            "unpriced": metrics[3],
        },
    }


@router.patch("/admin/products/{product_id}", dependencies=[AdminGuard])
async def admin_update_product(product_id: UUID, body: AdminProductPatch, db: DbSession) -> dict:
    product = (
        await db.execute(select(Product).where(Product.id == product_id))
    ).scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")

    if body.selling_price is not None and body.selling_price.strip() != "":
        if parse_money(body.selling_price) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid selling price.")
        await apply_change(db, product, "selling_price", body.selling_price, 0, reason="Web admin")

    if body.cost_price is not None and body.cost_price.strip() != "":
        if parse_money(body.cost_price) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cost price.")
        await apply_change(db, product, "cost_price", body.cost_price, 0, reason="Web admin")

    if body.stock_qty is not None:
        if parse_int(str(body.stock_qty)) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid stock quantity.")
        await apply_change(db, product, "stock", str(body.stock_qty), 0, reason="Web admin")

    if body.is_listed is not None:
        await apply_change(db, product, "available", body.is_listed, 0, reason="Web admin")

    if body.requires_prescription is not None:
        await apply_change(db, product, "rx", body.requires_prescription, 0, reason="Web admin")

    await db.flush()
    return _product_out(product)
