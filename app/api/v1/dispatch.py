"""Dispatch-partner (rider) portal API - a separate auth domain.

Riders authenticate against `dispatch_partners` via email OTP and see ONLY the
masked view of their own ACTIVE deliveries. Scope is structural: the rider's
session stamps a `dispatch_partner` actor, and Gate 5 RLS on `rider_assignments`
returns only their non-terminal assignments. No product names / order lines are
ever exposed (dispatch_delivery_masked).
"""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text

from app.api.deps import DbSession, RiderSessionDep
from app.core.logging import get_logger

router = APIRouter(tags=["dispatch-portal"])
log = get_logger("dispatch-api")

# Statuses a rider may set (no going back to pre-dispatch states).
_RIDER_STATUSES = {
    "PICKED_UP", "IN_TRANSIT", "NEAR_CUSTOMER", "DELIVERED", "FAILED_DELIVERY",
}


class RequestOtpBody(BaseModel):
    email: str


class VerifyOtpBody(BaseModel):
    email: str
    code: str


class StatusBody(BaseModel):
    status: Literal["PICKED_UP", "IN_TRANSIT", "NEAR_CUSTOMER", "DELIVERED", "FAILED_DELIVERY"]
    latitude: float | None = None
    longitude: float | None = None
    note: str | None = None


@router.post("/dispatch/request-otp")
async def dispatch_request_otp(body: RequestOtpBody, db: DbSession) -> dict:
    """Send a 6-digit OTP to a rider's portal email. Never reveals if the email exists."""
    from app.services.dispatch_auth import create_dispatch_otp, send_dispatch_otp_email

    result = await create_dispatch_otp(db, body.email)
    if result is not None:
        code, email = result
        try:
            await send_dispatch_otp_email(email, code)
        except Exception as exc:  # noqa: BLE001
            log.error("dispatch_otp_send_failed", error=str(exc))
    return {"ok": True}


@router.post("/dispatch/verify-otp")
async def dispatch_verify_otp(body: VerifyOtpBody, db: DbSession) -> dict:
    from app.services.dispatch_auth import verify_dispatch_otp_and_create_session

    token = await verify_dispatch_otp_and_create_session(db, body.email, body.code)
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired code.")
    return {"token": token}


@router.get("/dispatch/me")
async def dispatch_me(rider: RiderSessionDep) -> dict:
    return {"id": str(rider.id), "name": rider.name, "phone": rider.phone, "email": rider.portal_login_email}


@router.delete("/dispatch/session", status_code=204)
async def dispatch_logout(rider: RiderSessionDep, db: DbSession, x_dispatch_session: str = Header(default="")) -> None:
    from app.services.dispatch_auth import delete_dispatch_session

    await delete_dispatch_session(db, x_dispatch_session)


@router.get("/dispatch/deliveries")
async def dispatch_deliveries(rider: RiderSessionDep, db: DbSession) -> list[dict]:
    """The rider's own ACTIVE deliveries, masked (no product data). Terminal
    deliveries disappear automatically via Gate 5 RLS on rider_assignments."""
    rows = (
        await db.execute(
            text(
                "SELECT * FROM dispatch_delivery_masked "
                "WHERE order_id IN (SELECT order_id FROM rider_assignments) "
                "ORDER BY delivery_window NULLS LAST"
            )
        )
    ).mappings().all()
    return [dict(r) for r in rows]


@router.post("/dispatch/deliveries/{order_id}/status")
async def dispatch_update_status(order_id: UUID, body: StatusBody, rider: RiderSessionDep, db: DbSession) -> dict:
    """Advance the delivery status for one of the rider's own active deliveries."""
    if body.status not in _RIDER_STATUSES:
        raise HTTPException(status_code=400, detail="Not a valid rider status.")

    # Confirm the order is one of THIS rider's active assignments (RLS-scoped subquery).
    assigned = (
        await db.execute(
            text("SELECT 1 FROM rider_assignments WHERE order_id = :oid LIMIT 1"),
            {"oid": str(order_id)},
        )
    ).first()
    if assigned is None:
        raise HTTPException(status_code=404, detail="Delivery not found for this rider.")

    await db.execute(
        text("UPDATE orders SET delivery_status = :st WHERE id = :oid"),
        {"st": body.status, "oid": str(order_id)},
    )
    # Geostamp the movement (never product data).
    await db.execute(
        text(
            "INSERT INTO delivery_tracking_events (id, order_id, provider_key, status, latitude, longitude) "
            "VALUES (gen_random_uuid(), :oid, 'dispatch_portal', :st, :lat, :lng)"
        ),
        {"oid": str(order_id), "st": body.status, "lat": body.latitude, "lng": body.longitude},
    )
    if body.status in ("DELIVERED", "FAILED_DELIVERY"):
        # Terminal: the row will drop out of the rider's list on next fetch (Gate 5).
        if body.status == "DELIVERED":
            await db.execute(
                text("UPDATE orders SET status = 'DELIVERED' WHERE id = :oid AND status <> 'DELIVERED'"),
                {"oid": str(order_id)},
            )
    return {"ok": True, "delivery_status": body.status}
