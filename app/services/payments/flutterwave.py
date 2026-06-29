"""Flutterwave payment integration (official API).

Disabled automatically until FLUTTERWAVE_* keys are configured. Uses the official
Flutterwave Standard payments API and verifies webhooks via the configured
`verif-hash` (FLUTTERWAVE_WEBHOOK_HASH).
"""
from __future__ import annotations

import hmac

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("flutterwave")

_BASE = "https://api.flutterwave.com/v3"


async def create_payment_link(*, order_code: str, amount, email: str, name: str) -> str | None:
    """Create a Flutterwave Standard payment link. Returns the link or None."""
    s = get_settings()
    if not s.flutterwave_enabled:
        return None
    redirect = (s.webhook_base_url.rstrip("/") + "/payment/return") if s.webhook_base_url else "https://example.com/return"
    payload = {
        "tx_ref": order_code,
        "amount": str(amount),
        "currency": "NGN",
        "redirect_url": redirect,
        "customer": {"email": email or "customer@peaceway.ng", "name": name or "Customer"},
        "customizations": {"title": s.pharmacy_name, "description": f"Order {order_code}"},
    }
    headers = {"Authorization": f"Bearer {s.flutterwave_secret_key}"}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(f"{_BASE}/payments", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return (data.get("data") or {}).get("link")
    except Exception as exc:  # noqa: BLE001
        log.error("flutterwave_link_failed", order=order_code, error=str(exc))
        return None


def verify_webhook_signature(received_hash: str | None) -> bool:
    """Validate the Flutterwave `verif-hash` header against the configured secret."""
    s = get_settings()
    if not s.flutterwave_webhook_hash:
        return False
    if not received_hash:
        return False
    return hmac.compare_digest(received_hash, s.flutterwave_webhook_hash)
