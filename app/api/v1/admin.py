"""Admin web API - Telegram-bridge OTP auth + role-gated staff endpoints."""
from __future__ import annotations

from datetime import datetime
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
from app.models.sourcing import FulfillmentStatus, NetworkPartner, OrderSourcing, PartnerChannel, PartnerType
from app.services.products_admin import apply_change, parse_int, parse_money
from app.services.sourcing import (
    assign_partner,
    confirm_partner,
    mark_dispatch_assigned,
    mark_failed,
    mark_pack_ready,
    mark_picked_up,
    reject_partner,
)
from app.services.sourcing_providers.base import ProviderNotConfigured, SourcingDispatchRequest
from app.services.sourcing_providers.registry import get_provider

router = APIRouter(tags=["admin"])
log = get_logger("admin-api")


# ── Auth endpoints ─────────────────────────────────────────────────────────────

class RequestOtpBody(BaseModel):
    telegram_id: int


class VerifyOtpBody(BaseModel):
    telegram_id: int
    code: str


class RequestEmailOtpBody(BaseModel):
    email: str


class VerifyEmailOtpBody(BaseModel):
    email: str
    code: str


class AdminMeResponse(BaseModel):
    telegram_id: int | None
    full_name: str | None
    roles: list[str]
    role_labels: list[str]
    permissions: list[str]


@router.post("/admin/request-otp")
async def admin_request_otp(body: RequestOtpBody, request: Request, db: DbSession) -> dict:
    """Send a 6-digit OTP to the admin's Telegram chat.

    Always returns {ok: true} - never reveals whether the telegram_id exists.
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


@router.post("/admin/request-email-otp")
async def admin_request_email_otp(body: RequestEmailOtpBody, db: DbSession) -> dict:
    """Send a 6-digit OTP to an operations user's email address.

    Always returns {ok: true} - never reveals whether the email exists.
    """
    from app.services.admin_web_auth import create_web_email_otp, send_web_email_otp

    result = await create_web_email_otp(db, body.email)
    if result is not None:
        code, email = result
        await send_web_email_otp(email, code)
    return {"ok": True}


@router.post("/admin/verify-email-otp")
async def admin_verify_email_otp(body: VerifyEmailOtpBody, db: DbSession) -> dict:
    """Verify email OTP and return a session token."""
    from app.services.admin_web_auth import verify_web_email_otp_and_create_session

    token = await verify_web_email_otp_and_create_session(db, body.email, body.code)
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


def _admin_actor_id(admin: AdminUser) -> str:
    if admin.telegram_id is not None:
        return f"admin:telegram:{admin.telegram_id}"
    if admin.email:
        return f"admin:email:{admin.email.lower()}"
    return f"admin:id:{admin.id}"


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


def _sourcing_out(sourcing: OrderSourcing) -> dict:
    return {
        "id": str(sourcing.id),
        "order_id": str(sourcing.order_id),
        "fulfillment_status": sourcing.fulfillment_status.value,
        "sourcing_required": sourcing.sourcing_required,
        "partner_id": str(sourcing.partner_id) if sourcing.partner_id else None,
        "partner_type": sourcing.partner_type.value if sourcing.partner_type else None,
        "sourcing_channel": sourcing.sourcing_channel.value if sourcing.sourcing_channel else None,
        "confirmed_quantity": sourcing.confirmed_quantity,
        "confirmed_price": str(sourcing.confirmed_price) if sourcing.confirmed_price is not None else None,
        "expiry_or_batch_confirmation": sourcing.expiry_or_batch_confirmation,
        "ready_for_pickup_at": sourcing.ready_for_pickup_at.isoformat() if sourcing.ready_for_pickup_at else None,
        "pickup_code": sourcing.pickup_code,
        "pack_verification_photo": sourcing.pack_verification_photo,
        "pickup_proof": sourcing.pickup_proof,
        "delivery_proof": sourcing.delivery_proof,
        "customer_facing_status": sourcing.customer_facing_status,
        "requested_items": sourcing.requested_items,
        "confirmed_items": sourcing.confirmed_items,
        "last_error": sourcing.last_error,
        "created_at": sourcing.created_at.isoformat(),
        "updated_at": sourcing.updated_at.isoformat(),
    }


class SourcingActionBody(BaseModel):
    action: Literal[
        "assign_partner",
        "partner_confirmed",
        "partner_rejected",
        "pack_ready",
        "dispatch_assigned",
        "picked_up",
        "failed",
    ]
    partner_id: str | None = None
    confirmed_quantity: int | None = None
    confirmed_price: str | None = None
    expiry_or_batch_confirmation: str | None = None
    ready_for_pickup_at: str | None = None
    confirmed_items: list[dict] | None = None
    pack_verification_photo: str | None = None
    pickup_code: str | None = None
    pickup_proof: str | None = None
    reason: str | None = None


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
            "fulfillment_status": o.sourcing.fulfillment_status.value if o.sourcing else None,
            "customer_facing_status": o.sourcing.customer_facing_status if o.sourcing else None,
            "total": str(o.total),
            "created_at": o.created_at.isoformat(),
        }
        for o in rows
    ]


@router.get("/admin/sourcing")
async def admin_list_sourcing(
    db: DbSession,
    auth: AdminSessionDep,
    status_filter: str | None = None,
) -> list[dict]:
    _, role_keys = auth
    if not (
        rbac.has_permission(role_keys, "view_all_orders")
        or rbac.has_permission(role_keys, "edit_pricing")
        or rbac.has_permission(role_keys, "view_sourcing_requests")
        or rbac.has_permission(role_keys, "view_dispatch_queue")
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
    stmt = select(OrderSourcing).order_by(OrderSourcing.created_at.desc()).limit(200)
    if status_filter:
        stmt = stmt.where(OrderSourcing.fulfillment_status == FulfillmentStatus(status_filter))
    rows = (await db.execute(stmt)).scalars().all()
    return [_sourcing_out(row) for row in rows]


@router.get("/admin/network-partners")
async def admin_list_network_partners(db: DbSession, auth: AdminSessionDep) -> list[dict]:
    _, role_keys = auth
    if not (
        rbac.has_permission(role_keys, "view_all_orders")
        or rbac.has_permission(role_keys, "edit_pricing")
        or rbac.has_permission(role_keys, "view_partner_directory")
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
    stmt = select(NetworkPartner).order_by(NetworkPartner.name)
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": str(row.id),
            "key": row.key,
            "name": row.name,
            "partner_type": row.partner_type.value,
            "channel_type": row.channel_type.value,
            "api_base_url": row.api_base_url,
            "portal_login_email": row.portal_login_email,
            "portal_contact": row.portal_contact,
            "is_active": row.is_active,
        }
        for row in rows
    ]


@router.post("/admin/network-partners", status_code=status.HTTP_201_CREATED)
async def admin_create_network_partner(
    body: dict,
    db: DbSession,
    auth: AdminSessionDep,
) -> dict:
    _, role_keys = auth
    if not rbac.has_permission(role_keys, "edit_pricing"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
    login_email = str(body.get("portal_login_email") or "").strip().lower() or None
    partner = NetworkPartner(
        key=str(body.get("key", "")).strip(),
        name=str(body.get("name", "")).strip(),
        partner_type=PartnerType(str(body.get("partner_type", "wholesaler"))),
        channel_type=PartnerChannel(str(body.get("channel_type", "portal"))),
        api_base_url=body.get("api_base_url"),
        portal_login_email=login_email,
        portal_contact=body.get("portal_contact"),
        notes=body.get("notes"),
    )
    db.add(partner)
    await db.flush()
    # Partners authenticate through the separate partner portal keyed on
    # `portal_login_email` - no `admin_users` row is created for them.
    return {
        "id": str(partner.id),
        "key": partner.key,
        "name": partner.name,
        "partner_type": partner.partner_type.value,
        "channel_type": partner.channel_type.value,
        "portal_login_email": partner.portal_login_email,
    }


@router.patch("/admin/network-partners/{partner_id}")
async def admin_update_network_partner(
    partner_id: UUID,
    body: dict,
    db: DbSession,
    auth: AdminSessionDep,
) -> dict:
    _, role_keys = auth
    if not rbac.has_permission(role_keys, "edit_pricing"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
    partner = (
        await db.execute(select(NetworkPartner).where(NetworkPartner.id == partner_id))
    ).scalar_one_or_none()
    if partner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found.")

    if "name" in body:
        partner.name = str(body["name"]).strip() or partner.name
    if "portal_login_email" in body:
        partner.portal_login_email = str(body["portal_login_email"] or "").strip().lower() or None
    if "portal_contact" in body:
        partner.portal_contact = body["portal_contact"] or None
    if "api_base_url" in body:
        partner.api_base_url = body["api_base_url"] or None
    if "notes" in body:
        partner.notes = body["notes"] or None
    if "is_active" in body:
        partner.is_active = bool(body["is_active"])

    await db.flush()
    return {
        "id": str(partner.id),
        "key": partner.key,
        "name": partner.name,
        "partner_type": partner.partner_type.value,
        "channel_type": partner.channel_type.value,
        "portal_login_email": partner.portal_login_email,
        "portal_contact": partner.portal_contact,
        "is_active": partner.is_active,
    }


@router.patch("/admin/sourcing/{order_id}")
async def admin_update_sourcing(order_id: UUID, body: SourcingActionBody, db: DbSession, auth: AdminSessionDep) -> dict:
    admin, role_keys = auth
    # Staff-only endpoint. Partners act through the separate partner portal
    # (`/api/v1/partner/*`); their confirm/reject/pack-ready flows never reach here.
    can_full_control = rbac.has_permission(role_keys, "view_all_orders") or rbac.has_permission(role_keys, "edit_pricing")
    order = (await db.execute(select(Order).where(Order.id == order_id))).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    if not (
        can_full_control
        or rbac.has_permission(role_keys, "assign_rider")
        or rbac.has_permission(role_keys, "mark_picked_up")
        or rbac.has_permission(role_keys, "mark_failed_delivery")
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
    by = _admin_actor_id(admin)

    if body.action == "assign_partner":
        if not can_full_control:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
        if not body.partner_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="partner_id is required.")
        partner = (await db.execute(select(NetworkPartner).where(NetworkPartner.id == UUID(body.partner_id)))).scalar_one_or_none()
        if partner is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found.")
        sourcing = await assign_partner(db, order=order, partner=partner, by=by)
        provider = get_provider(partner)
        payload = {
            "order_id": str(order.id),
            "order_code": order.code,
            "requested_items": sourcing.requested_items,
            "delivery_area": order.delivery_area,
            "customer_facing_status": sourcing.customer_facing_status,
        }
        try:
            provider_response = await provider.send_sourcing_request(
                SourcingDispatchRequest(
                    order_id=order.id,
                    order_code=order.code,
                    partner_key=partner.key,
                    payload=payload,
                )
            )
            sourcing.partner_response_raw = provider_response
        except ProviderNotConfigured as exc:
            sourcing.last_error = str(exc)
    elif body.action == "partner_confirmed":
        if not can_full_control:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
        if body.confirmed_quantity is None or body.confirmed_price is None or not body.expiry_or_batch_confirmation:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Partner confirmation fields are required.")
        ready_at = datetime.fromisoformat(body.ready_for_pickup_at) if body.ready_for_pickup_at else None
        await confirm_partner(
            db,
            order=order,
            confirmed_quantity=body.confirmed_quantity,
            confirmed_price=Decimal(body.confirmed_price),
            expiry_or_batch_confirmation=body.expiry_or_batch_confirmation,
            ready_for_pickup_at=ready_at,
            confirmed_items=body.confirmed_items,
            by=by,
        )
    elif body.action == "partner_rejected":
        if not can_full_control:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
        await reject_partner(db, order=order, reason=body.reason or "Partner rejected request.", by=by)
    elif body.action == "pack_ready":
        if not can_full_control:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
        await mark_pack_ready(
            db,
            order=order,
            pack_verification_photo=body.pack_verification_photo,
            pickup_code=body.pickup_code,
            by=by,
        )
    elif body.action == "dispatch_assigned":
        if not (can_full_control or rbac.has_permission(role_keys, "assign_rider")):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
        await mark_dispatch_assigned(db, order=order, by=by)
    elif body.action == "picked_up":
        if not (can_full_control or rbac.has_permission(role_keys, "mark_picked_up")):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
        await mark_picked_up(db, order=order, pickup_proof=body.pickup_proof, by=by)
    elif body.action == "failed":
        if not (can_full_control or rbac.has_permission(role_keys, "mark_failed_delivery")):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
        await mark_failed(db, order=order, reason=body.reason or "Fulfilment failed.", by=by)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported action.")

    await db.flush()
    sourcing = (await db.execute(select(OrderSourcing).where(OrderSourcing.order_id == order.id))).scalar_one_or_none()
    if sourcing is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Sourcing state not found.")
    return _sourcing_out(sourcing)


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
