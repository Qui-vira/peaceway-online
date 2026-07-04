"""Admin web API — Telegram-bridge OTP auth + role-gated staff endpoints."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal
from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import func, or_, select

from app.api.deps import AdminSessionDep, DbSession
from app.core import rbac
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.admin import AdminUser
from app.models.catalog import Product, ProductPricing
from app.models.ops import ProductRequest
from app.models.orders import Customer, Order
from app.services.products_admin import apply_change, parse_int, parse_money

router = APIRouter(tags=["admin"])
log = get_logger("admin-api")


# ── Auth endpoints ─────────────────────────────────────────────────────────────

class RequestOtpBody(BaseModel):
    telegram_id: int


class VerifyOtpBody(BaseModel):
    telegram_id: int
    code: str


class AdminMeResponse(BaseModel):
    telegram_id: int
    full_name: str | None
    roles: list[str]
    role_labels: list[str]
    permissions: list[str]


@router.post("/admin/request-otp")
async def admin_request_otp(body: RequestOtpBody, request: Request, db: DbSession) -> dict:
    """Send a 6-digit OTP to the admin's Telegram chat.

    Always returns {ok: true} — never reveals whether the telegram_id exists.
    """
    from app.services.admin_web_auth import create_web_otp

    result = await create_web_otp(db, body.telegram_id)
    if result is not None:
        code, telegram_id = result
        bot = request.app.state.bot
        message = (
            f"🔐 <b>Peaceway web login code:</b> <code>{code}</code>\n\n"
            f"Expires in 5 minutes. Do not share this code."
        )
        try:
            await bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode="HTML",
            )
            log.info("admin_otp_sent", telegram_id=telegram_id, transport="aiogram")
        except Exception as exc:  # noqa: BLE001
            log.error("admin_otp_send_failed", telegram_id=telegram_id, error=str(exc))
            token = get_settings().telegram_bot_token
            if token:
                try:
                    async with httpx.AsyncClient(timeout=10) as client:
                        resp = await client.post(
                            f"https://api.telegram.org/bot{token}/sendMessage",
                            data={
                                "chat_id": str(telegram_id),
                                "text": message,
                                "parse_mode": "HTML",
                            },
                        )
                        resp.raise_for_status()
                    log.info("admin_otp_sent", telegram_id=telegram_id, transport="http_fallback")
                except Exception as fallback_exc:  # noqa: BLE001
                    log.error(
                        "admin_otp_send_fallback_failed",
                        telegram_id=telegram_id,
                        error=str(fallback_exc),
                    )
    return {"ok": True}


@router.post("/admin/verify-otp")
async def admin_verify_otp(body: VerifyOtpBody, db: DbSession) -> dict:
    """Verify OTP and return a session token."""
    from app.services.admin_web_auth import verify_web_otp_and_create_session

    token = await verify_web_otp_and_create_session(db, body.telegram_id, body.code)
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired code.")
    return {"token": token}


@router.get("/admin/me")
async def admin_me(auth: AdminSessionDep) -> AdminMeResponse:
    """Return the current admin's profile and permissions."""
    admin, role_keys = auth
    permissions: set[str] = set()
    for rk in role_keys:
        perms = rbac.ROLE_PERMISSIONS.get(rk, set())
        if rbac.WILDCARD in perms:
            permissions.add("*")
        else:
            permissions.update(perms)
    permissions -= rbac.WILDCARD_EXCLUDES
    return AdminMeResponse(
        telegram_id=admin.telegram_id,
        full_name=admin.full_name,
        roles=sorted(role_keys),
        role_labels=[rbac.role_label(rk) for rk in sorted(role_keys)],
        permissions=sorted(permissions),
    )


@router.delete("/admin/session", status_code=204)
async def admin_logout(auth: AdminSessionDep, db: DbSession) -> None:
    """Delete all active sessions for the current admin (logout)."""
    from datetime import datetime, timezone
    from app.models.admin import WebAdminSession

    admin, _ = auth
    now = datetime.now(timezone.utc)
    sessions = (
        await db.execute(
            select(WebAdminSession).where(
                WebAdminSession.admin_id == admin.id,
                WebAdminSession.expires_at > now,
            )
        )
    ).scalars().all()
    for s in sessions:
        await db.delete(s)


# ── Helpers ────────────────────────────────────────────────────────────────────

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


# ── Requests ──────────────────────────────────────────────────────────────────

@router.get("/admin/requests")
async def admin_list_requests(db: DbSession, auth: AdminSessionDep) -> list[dict]:
    _, role_keys = auth
    if not rbac.has_permission(role_keys, "view_product_requests"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
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


# ── Orders ─────────────────────────────────────────────────────────────────────

@router.get("/admin/orders")
async def admin_list_orders(db: DbSession, auth: AdminSessionDep) -> list[dict]:
    _, role_keys = auth
    if not (rbac.has_permission(role_keys, "view_all_orders") or rbac.has_permission(role_keys, "view_customer_orders")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
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


# ── Customers ──────────────────────────────────────────────────────────────────

@router.get("/admin/customers")
async def admin_list_customers(db: DbSession, auth: AdminSessionDep) -> list[dict]:
    _, role_keys = auth
    if not rbac.has_permission(role_keys, "view_customers"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
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


# ── Products / Inventory ───────────────────────────────────────────────────────

@router.get("/admin/products")
async def admin_list_products(
    db: DbSession,
    auth: AdminSessionDep,
    q: str | None = None,
    status_filter: Literal["all", "listed", "unlisted", "in_stock", "out_of_stock", "unpriced"] = "all",
    limit: int = 100,
    offset: int = 0,
) -> dict:
    _, role_keys = auth
    if not (rbac.has_permission(role_keys, "view_all_products") or rbac.has_permission(role_keys, "edit_pricing")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
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


@router.patch("/admin/products/{product_id}")
async def admin_update_product(product_id: UUID, body: AdminProductPatch, db: DbSession, auth: AdminSessionDep) -> dict:
    _, role_keys = auth
    if not rbac.has_permission(role_keys, "edit_pricing"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
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
