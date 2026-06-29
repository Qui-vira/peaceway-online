"""Logistics provider webhook receiver.

Stores the raw event for audit, then maps common fields to a tracking update.
Each partner's exact payload shape is mapped when that provider is wired against
its official API; this generic extractor covers the common keys.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request
from sqlalchemy import select

from app.core.db import get_session
from app.core.logging import get_logger
from app.models import DeliveryOrder, DeliveryWebhookEvent
from app.services.delivery.base import StatusResult
from app.services.delivery.service import apply_status

router = APIRouter()
log = get_logger("logistics-webhook")


def _extract(payload: dict) -> dict:
    """Best-effort extraction of common fields from a provider payload."""
    g = payload.get
    return {
        "reference": g("reference") or g("delivery_id") or g("order_id") or g("id"),
        "status": g("status") or g("event") or g("state"),
        "tracking_url": g("tracking_url") or g("trackingUrl") or g("tracking_link"),
        "latitude": g("latitude") or g("lat") or (g("location") or {}).get("lat") if isinstance(g("location"), dict) else g("latitude") or g("lat"),
        "longitude": g("longitude") or g("lng") or g("lon"),
        "rider_name": g("rider_name") or g("driver_name"),
        "rider_phone": g("rider_phone") or g("driver_phone"),
    }


@router.post("/webhook/logistics/{provider_key}")
async def logistics_webhook(provider_key: str, request: Request) -> dict:
    bot = request.app.state.bot
    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001
        payload = {}

    fields = _extract(payload)
    async with get_session() as session:
        session.add(
            DeliveryWebhookEvent(
                provider_key=provider_key,
                reference=str(fields.get("reference")) if fields.get("reference") else None,
                verified=True,
                raw=payload,
            )
        )
        # Resolve which order this belongs to via the stored provider_delivery_id.
        order_id = None
        ref = fields.get("reference")
        if ref:
            d = (
                await session.execute(
                    select(DeliveryOrder).where(
                        DeliveryOrder.provider_key == provider_key,
                        DeliveryOrder.provider_delivery_id == str(ref),
                    )
                )
            ).scalar_one_or_none()
            if d:
                order_id = d.order_id

    if order_id:
        def _f(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        await apply_status(
            bot,
            order_id,
            StatusResult(
                provider_key=provider_key,
                status=fields.get("status") or "",
                rider_name=fields.get("rider_name"),
                rider_phone=fields.get("rider_phone"),
                tracking_url=fields.get("tracking_url"),
                latitude=_f(fields.get("latitude")),
                longitude=_f(fields.get("longitude")),
                raw=payload,
            ),
        )
    else:
        log.warning("logistics_webhook_unmatched", provider=provider_key, ref=fields.get("reference"))

    return {"ok": True}
