"""Profit-protected pricing engine.

Core rule: delivery, payment, off-ramp, and handling fees are ALWAYS added on top
of the product price. They never reduce product profit. Product profit is purely
``sum((selling_price - cost_price) * qty)`` and is independent of every fee.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from app.models.orders import PaymentMethod

_CENTS = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(_CENTS, rounding=ROUND_HALF_UP)


@dataclass
class QuoteItem:
    name: str
    quantity: int
    selling_price: Decimal
    cost_price: Decimal = Decimal("0")


@dataclass
class FeeConfig:
    """Fee configuration (mirrors FeeSetting, but plain values for testability)."""

    payment_fee_pct: Decimal = Decimal("0")
    payment_fee_flat: Decimal = Decimal("0")
    offramp_fee: Decimal = Decimal("0")
    handling_fee: Decimal = Decimal("0")


@dataclass
class Quote:
    items: list[QuoteItem] = field(default_factory=list)
    subtotal: Decimal = Decimal("0.00")
    delivery_fee: Decimal = Decimal("0.00")
    payment_fee: Decimal = Decimal("0.00")
    offramp_fee: Decimal = Decimal("0.00")
    handling_fee: Decimal = Decimal("0.00")
    total: Decimal = Decimal("0.00")
    product_profit: Decimal = Decimal("0.00")


def quote_order(
    items: list[QuoteItem],
    delivery_fee: Decimal,
    fees: FeeConfig,
    payment_method: PaymentMethod,
) -> Quote:
    """Compute an itemized, profit-protected quote for an order."""
    subtotal = sum((i.selling_price * i.quantity for i in items), Decimal("0"))
    profit = sum(
        ((i.selling_price - i.cost_price) * i.quantity for i in items), Decimal("0")
    )

    # Payment fee = flat + percentage of product subtotal (added on top).
    payment_fee = fees.payment_fee_flat + (fees.payment_fee_pct / Decimal("100") * subtotal)

    # Off-ramp fee only applies to crypto payments (Phase 3); added on top.
    offramp_fee = fees.offramp_fee if payment_method == PaymentMethod.CRYPTO else Decimal("0")

    handling_fee = fees.handling_fee
    delivery_fee = Decimal(delivery_fee)

    total = subtotal + delivery_fee + payment_fee + offramp_fee + handling_fee

    return Quote(
        items=items,
        subtotal=_money(subtotal),
        delivery_fee=_money(delivery_fee),
        payment_fee=_money(payment_fee),
        offramp_fee=_money(offramp_fee),
        handling_fee=_money(handling_fee),
        total=_money(total),
        product_profit=_money(profit),
    )
