"""Admin web API — password-gated staff endpoints."""
from __future__ import annotations

import os
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DbSession
from app.models.ops import ProductRequest
from app.models.orders import Customer, Order

router = APIRouter(tags=["admin"])

ADMIN_PASSWORD = os.getenv("ADMIN_WEB_PASSWORD", "")


# ── Auth ──────────────────────────────────────────────────────────────────────

class AuthBody(BaseModel):
    password: str


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
