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

# CSV cell vocabularies shared by the bulk importer.
RX_TRUE = {"rx", "prescription", "prescription-required", "true", "yes", "1", "required"}
AVAIL_TRUE = {"yes", "true", "1", "available", "in stock", "in_stock"}


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


async def create_product_from_name(
    session: AsyncSession, name: str, admin_id: int, *, strength: str | None = None,
    reason: str = "CSV import (new)",
) -> Product:
    """Create a bare product for an import row that matched no existing catalog entry.

    `generic_name` is required by the model; we seed it from the given name (staff
    can refine later). The product starts with `requires_review=True` (model
    default) so it is NOT sellable until a row marks it OTC or a pharmacist clears
    it - consistent with the catalog safety rule.
    """
    name = name.strip()
    product = Product(name=name, generic_name=name)
    if strength:
        product.strength = strength.strip()[:100]
    session.add(product)
    await session.flush()  # assign product.id before pricing/history writes
    _record(session, product.id, "created", None, name, admin_id, reason=reason)
    return product


async def apply_csv_row(session: AsyncSession, product: Product, row: dict, admin_id: int) -> None:
    """Apply one CSV row's columns to a product (used for both updates and creates)."""
    reason = "CSV import"
    if row.get("cost_price") and parse_money(row["cost_price"]) is not None:
        await apply_change(session, product, "cost_price", row["cost_price"], admin_id, reason=reason)
    if row.get("selling_price") and parse_money(row["selling_price"]) is not None:
        await apply_change(session, product, "selling_price", row["selling_price"], admin_id, reason=reason)
    if row.get("stock") and parse_int(row["stock"]) is not None:
        await apply_change(session, product, "stock", row["stock"], admin_id, reason=reason)
    if row.get("category"):
        try:
            await apply_change(session, product, "category", row["category"].strip().title(), admin_id, reason=reason)
        except ValueError:
            pass  # unknown category - skip silently
    if row.get("prescription"):
        await apply_change(session, product, "rx", row["prescription"].lower() in RX_TRUE, admin_id, reason=reason)
    if row.get("availability"):
        await apply_change(session, product, "available", row["availability"].lower() in AVAIL_TRUE, admin_id, reason=reason)
    if row.get("dosage"):
        product.strength = row["dosage"].strip()[:100]
    if row.get("description"):
        product.description = row["description"][:1000]
