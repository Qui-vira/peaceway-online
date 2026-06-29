"""Crypto off-ramp helper (Phase 3 — optional, manual settlement).

Provides the configured static wallets and recomputes an order total with the
off-ramp fee added on top (never deducted from product profit). No automated
crypto->Naira settlement: an admin confirms both on-chain receipt and Naira
settlement manually.
"""
from __future__ import annotations

from decimal import Decimal

from app.core.config import get_settings
from app.models import FeeSetting, Order


def crypto_enabled(fee: FeeSetting | None) -> bool:
    """Crypto is offered only when admin enabled it AND a wallet is configured."""
    if fee is None or not fee.enable_crypto:
        return False
    return len(get_settings().crypto_wallet_list) > 0


def available_wallets() -> list[dict]:
    return get_settings().crypto_wallet_list


def find_wallet(network: str, token: str) -> dict | None:
    for w in get_settings().crypto_wallet_list:
        if w["network"] == network and w["token"] == token:
            return w
    return None


def total_with_offramp(order: Order, fee: FeeSetting | None) -> Decimal:
    """Order total including the off-ramp fee (added on top)."""
    offramp = fee.offramp_fee if fee else Decimal("0")
    base = order.subtotal + order.delivery_fee + order.payment_fee + order.handling_fee
    return base + offramp
