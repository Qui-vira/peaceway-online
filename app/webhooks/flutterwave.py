"""Flutterwave webhook - verifies signature, records event, approves paid orders."""
from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy import select

from app.core.db import get_session
from app.core.logging import get_logger
from app.models import Order, OrderStatus, PaymentWebhookEvent, RxStatus
from app.services import orders as orders_svc
from app.services.payments.flutterwave import verify_webhook_signature

router = APIRouter()
log = get_logger("flutterwave-webhook")


@router.post("/webhook/flutterwave")
async def flutterwave_webhook(request: Request) -> dict:
    received = request.headers.get("verif-hash")
    verified = verify_webhook_signature(received)
    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001
        payload = {}

    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    tx_ref = data.get("tx_ref")
    status = (data.get("status") or "").lower()

    async with get_session() as session:
        session.add(
            PaymentWebhookEvent(
                provider="flutterwave",
                event_type=payload.get("event") if isinstance(payload, dict) else None,
                reference=tx_ref,
                verified=verified,
                raw=payload,
            )
        )
        if verified and tx_ref and status == "successful":
            # Lock the order row so concurrent duplicate deliveries (Flutterwave
            # retries) can't both read AWAITING_PAYMENT and double-transition.
            order = (
                await session.execute(
                    select(Order).where(Order.code == tx_ref).with_for_update()
                )
            ).scalar_one_or_none()
            if order and order.status in (OrderStatus.AWAITING_PAYMENT, OrderStatus.PAYMENT_SUBMITTED):
                await orders_svc.transition_status(session, order, OrderStatus.PAYMENT_APPROVED, "flutterwave")
                if order.rx_status == RxStatus.NOT_REQUIRED:
                    await orders_svc.transition_status(session, order, OrderStatus.PROCESSING, "system", "Auto: paid via Flutterwave")
                order_id = order.id
            else:
                order_id = None
        else:
            order_id = None

    if order_id:
        try:
            from app.services.alerts import alert_payment_approved

            await alert_payment_approved(request.app.state.bot, order_id)
        except Exception as exc:  # noqa: BLE001
            log.error("fw_alert_failed", error=str(exc))

    if not verified:
        log.warning("flutterwave_unverified_webhook", ref=tx_ref)
    return {"ok": True}
