"""Apply admin product/price/stock changes with price-history + audit logging.

Used by both the in-bot Products admin menu and the CSV bulk importer so every
change is recorded consistently.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AdminActivityLog, PriceHistory, Product, ProductPricing

VALID_CATEGORIES = ["Medicines", "Medical Devices", "Vaccines", "Supplements", "Veterinary", "Other"]


def parse_money(raw: str) -> Decimal | None:
    try:
        v = Decimal(str(raw).replace(",", "").replace("₦", "").strip())
        return v if v >= 0 else None
    except (InvalidOperation, ValueError):
        return None


def parse_int(raw: str) -> int | None:
    try:
        v = int(str(raw).replace(",", "").strip())
        return v if v >= 0 else None
    except (TypeError, ValueError):
        return None


async def _ensure_pricing(session: AsyncSession, product: Product) -> ProductPricing:
    # Query explicitly rather than touching the lazy relationship, so this works
    # whether or not `product` was loaded with its pricing eagerly.
    pricing = (
        await session.execute(select(ProductPricing).where(ProductPricing.product_id == product.id))
    ).scalar_one_or_none()
    if pricing is None:
        pricing = ProductPricing(product_id=product.id)
        session.add(pricing)
        await session.flush()
    product.pricing = pricing
    return pricing


def _record(session, product_id, field, old, new, admin_id, reason=None) -> None:
    session.add(
        PriceHistory(
            product_id=product_id,
            field=field,
            old_value=None if old is None else str(old),
            new_value=None if new is None else str(new),
            changed_by=admin_id,
            reason=reason,
        )
    )
    session.add(
        AdminActivityLog(
            telegram_id=admin_id,
            action=f"product_{field}",
            entity="product",
            entity_id=str(product_id),
            detail={"old": str(old), "new": str(new), "reason": reason},
        )
    )


async def apply_change(
    session: AsyncSession, product: Product, field: str, new_value, admin_id: int, reason: str | None = None
) -> str:
    """Apply a single field change. Returns a human summary. Raises ValueError if invalid."""
    pricing = await _ensure_pricing(session, product)

    if field == "selling_price":
        val = parse_money(new_value)
        if val is None:
            raise ValueError("Enter a valid amount, e.g. 1500")
        old = pricing.selling_price
        pricing.selling_price = val
        # Pricing an item with stock makes it buyable.
        if val > 0:
            product.is_listed = True
            if pricing.stock_qty > 0:
                pricing.is_in_stock = True
        _record(session, product.id, "selling_price", old, val, admin_id, reason)
        return f"Selling price: ₦{old:,.0f} → ₦{val:,.0f}"

    if field == "cost_price":
        val = parse_money(new_value)
        if val is None:
            raise ValueError("Enter a valid amount, e.g. 800")
        old = pricing.cost_price
        pricing.cost_price = val
        _record(session, product.id, "cost_price", old, val, admin_id, reason)
        return f"Cost price: ₦{old:,.0f} → ₦{val:,.0f}"

    if field == "stock":
        val = parse_int(new_value)
        if val is None:
            raise ValueError("Enter a whole number, e.g. 50")
        old = pricing.stock_qty
        pricing.stock_qty = val
        pricing.is_in_stock = val > 0
        if val > 0 and pricing.selling_price > 0:
            product.is_listed = True
        _record(session, product.id, "stock", old, val, admin_id, reason)
        return f"Stock: {old} → {val}"

    if field == "category":
        if new_value not in VALID_CATEGORIES:
            raise ValueError("Unknown category")
        old = product.category
        product.category = new_value
        _record(session, product.id, "category", old, new_value, admin_id, reason)
        return f"Category: {old} → {new_value}"

    if field == "available":
        old = product.is_listed
        product.is_listed = bool(new_value)
        if not new_value:
            pricing.is_in_stock = False
        _record(session, product.id, "available", old, bool(new_value), admin_id, reason)
        return f"Availability: {'listed' if new_value else 'hidden'}"

    if field == "rx":
        old = product.requires_prescription
        product.requires_prescription = bool(new_value)
        product.requires_review = bool(new_value)
        _record(session, product.id, "rx", old, bool(new_value), admin_id, reason)
        return f"Prescription required: {bool(new_value)}"

    raise ValueError(f"Unknown field: {field}")
