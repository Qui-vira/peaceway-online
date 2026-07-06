"""Partner portal API — a separate auth domain from staff `/admin/*`.

Wholesalers/suppliers authenticate against `network_partners` via email OTP and
act ONLY on sourcing rows assigned to them. No RBAC roles are involved: the
scope is structural (`OrderSourcing.partner_id == partner.id`), and the allowed
actions are a fixed whitelist (confirm / reject / pack_ready).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DbSession, PartnerSessionDep
from app.core.logging import get_logger
from app.models import Order
from app.models.sourcing import OrderSourcing
from app.services.partner_auth import (
    create_partner_otp,
    delete_partner_session,
    send_partner_otp_email,
    verify_partner_otp_and_create_session,
)
from app.services.sourcing import confirm_partner, mark_pack_ready, reject_partner

router = APIRouter(tags=["partner-portal"])
log = get_logger("partner-api")


class PartnerRequestOtpBody(BaseModel):
    email: str


class PartnerVerifyOtpBody(BaseModel):
    email: str
    code: str


class PartnerActionBody(BaseModel):
    action: Literal["partner_confirmed", "partner_rejected", "pack_ready"]
    confirmed_quantity: int | None = None
    confirmed_price: str | None = None
    expiry_or_batch_confirmation: str | None = None
    ready_for_pickup_at: str | None = None
    confirmed_items: list[dict] | None = None
    pack_verification_photo: str | None = None
    reason: str | None = None


def _sourcing_out(sourcing: OrderSourcing) -> dict:
    """Partner-facing serializer — only fields the portal needs."""
    return {
        "id": str(sourcing.id),
        "order_id": str(sourcing.order_id),
        "fulfillment_status": sourcing.fulfillment_status.value,
        "customer_facing_status": sourcing.customer_facing_status,
        "requested_items": sourcing.requested_items,
        "confirmed_items": sourcing.confirmed_items,
        "confirmed_quantity": sourcing.confirmed_quantity,
        "confirmed_price": str(sourcing.confirmed_price) if sourcing.confirmed_price is not None else None,
        "expiry_or_batch_confirmation": sourcing.expiry_or_batch_confirmation,
        "ready_for_pickup_at": sourcing.ready_for_pickup_at.isoformat() if sourcing.ready_for_pickup_at else None,
        "pickup_code": sourcing.pickup_code,
        "last_error": sourcing.last_error,
        "created_at": sourcing.created_at.isoformat(),
        "updated_at": sourcing.updated_at.isoformat(),
    }


@router.post("/partner/request-otp")
async def partner_request_otp(body: PartnerRequestOtpBody, db: DbSession) -> dict:
    """Send a 6-digit OTP to a partner's portal email.

    Always returns {ok: true} — never reveals whether the email exists.
    """
    result = await create_partner_otp(db, body.email)
    if result is not None:
        code, email = result
        try:
            await send_partner_otp_email(email, code)
        except Exception as exc:  # noqa: BLE001
            log.error("partner_otp_send_failed", error=str(exc))
    return {"ok": True}


@router.post("/partner/verify-otp")
async def partner_verify_otp(body: PartnerVerifyOtpBody, db: DbSession) -> dict:
    """Verify OTP and return a partner session token."""
    token = await verify_partner_otp_and_create_session(db, body.email, body.code)
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired code.")
    return {"token": token}


@router.get("/partner/me")
async def partner_me(partner: PartnerSessionDep) -> dict:
    return {
        "id": str(partner.id),
        "key": partner.key,
        "name": partner.name,
        "partner_type": partner.partner_type.value,
        "channel_type": partner.channel_type.value,
        "portal_login_email": partner.portal_login_email,
        "portal_contact": partner.portal_contact,
    }


@router.delete("/partner/session", status_code=204)
async def partner_logout(
    partner: PartnerSessionDep,
    db: DbSession,
    x_partner_session: str = Header(default=""),
) -> None:
    await delete_partner_session(db, x_partner_session)


@router.get("/partner/sourcing")
async def partner_list_sourcing(partner: PartnerSessionDep, db: DbSession) -> list[dict]:
    """Sourcing requests assigned to THIS partner — hard-scoped, no role logic."""
    rows = (
        await db.execute(
            select(OrderSourcing)
            .where(OrderSourcing.partner_id == partner.id)
            .order_by(OrderSourcing.created_at.desc())
            .limit(200)
        )
    ).scalars().all()
    return [_sourcing_out(row) for row in rows]


@router.post("/partner/sourcing/{sourcing_id}/action")
async def partner_sourcing_action(
    sourcing_id: UUID,
    body: PartnerActionBody,
    partner: PartnerSessionDep,
    db: DbSession,
) -> dict:
    """Partner acts on an assigned sourcing request (confirm / reject / pack ready)."""
    sourcing = (
        await db.execute(
            select(OrderSourcing).where(
                OrderSourcing.id == sourcing_id,
                OrderSourcing.partner_id == partner.id,
            )
        )
    ).scalar_one_or_none()
    if sourcing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sourcing request not found.")

    order = (
        await db.execute(select(Order).where(Order.id == sourcing.order_id))
    ).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    by = f"partner:{partner.key}"

    if body.action == "partner_confirmed":
        if body.confirmed_quantity is None or body.confirmed_price is None or not body.expiry_or_batch_confirmation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity, price, and expiry/batch confirmation are required.",
            )
        try:
            price = Decimal(body.confirmed_price)
        except InvalidOperation:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid price.")
        try:
            ready_at = datetime.fromisoformat(body.ready_for_pickup_at) if body.ready_for_pickup_at else None
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid pickup time.")
        await confirm_partner(
            db,
            order=order,
            confirmed_quantity=body.confirmed_quantity,
            confirmed_price=price,
            expiry_or_batch_confirmation=body.expiry_or_batch_confirmation,
            ready_for_pickup_at=ready_at,
            confirmed_items=body.confirmed_items,
            by=by,
        )
    elif body.action == "partner_rejected":
        await reject_partner(
            db,
            order=order,
            reason=body.reason or "Partner rejected the sourcing request.",
            by=by,
        )
    elif body.action == "pack_ready":
        await mark_pack_ready(
            db,
            order=order,
            pack_verification_photo=body.pack_verification_photo,
            pickup_code=None,  # partners never choose the code; Peaceway generates it
            by=by,
        )

    await db.flush()
    await db.refresh(sourcing)
    return _sourcing_out(sourcing)
