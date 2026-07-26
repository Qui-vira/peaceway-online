"""Apply admin product/price/stock changes with price-history + audit logging.

Used by both the in-bot Products admin menu and the CSV bulk importer so every
change is recorded consistently.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AdminActivityLog, PriceHistory, Product, ProductPricing

VALID_CATEGORIES = ["Medicines", "Medical Devices", "Vaccines", "Supplements", "Veterinary", "Other"]

# CSV cell vocabularies shared by the bulk importer.
RX_TRUE = {"rx", "prescription", "prescription-required", "true", "yes", "1", "required"}
AVAIL_TRUE = {"yes", "true", "1", "available", "in stock", "in_stock"}

# Descriptive fields staff can edit during backfill: field -> (label, max length).
# These carry no pricing or safety semantics on their own, but they are the keys the
# image matcher compares on, so they are never auto-populated — only typed by staff.
DESCRIPTIVE_FIELDS: dict[str, tuple[str, int]] = {
    "brand_name": ("Brand", 255),
    "manufacturer": ("Manufacturer", 255),
    "dosage_form": ("Dosage form", 100),
    "strength": ("Strength", 100),
    "pack_size": ("Pack size", 100),
}

_WS = re.compile(r"\s+")


def normalize_name(raw: str | None) -> str:
    """Collapse whitespace in a product name.

    Lives here, not in scripts/import_pharmaos.py, because the running app needs it
    (the in-bot CSV importer matches on it) and `scripts/` is dev tooling that is
    excluded from the Railway upload by .railwayignore. The import script now takes
    it from here, so the dependency points app <- scripts, never the reverse.
    """
    return _WS.sub(" ", (raw or "").strip())


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

    if field in DESCRIPTIVE_FIELDS:
        label, maxlen = DESCRIPTIVE_FIELDS[field]
        # "-" clears the field. Staff need a way to say "this product genuinely has
        # no brand", which is different from "not filled in yet".
        raw = normalize_name(str(new_value))
        val = None if raw in ("", "-") else raw
        if val is not None and len(val) > maxlen:
            raise ValueError(f"{label} must be {maxlen} characters or fewer.")
        old = getattr(product, field)
        setattr(product, field, val)
        _record(session, product.id, field, old, val, admin_id, reason)
        return f"{label}: {old or '—'} → {val or '—'}"

    raise ValueError(f"Unknown field: {field}")


# Fields a product must carry before the image matcher can compare it to anything.
# `strength` is deliberately absent: some products legitimately have none (Afrabvite
# Multivitamin Drops), so requiring it would park them in the queue forever.
REQUIRED_BACKFILL_FIELDS = ("brand_name", "manufacturer", "dosage_form", "pack_size")


def missing_backfill_fields(product: Product) -> list[str]:
    """Which required descriptive fields are empty on this product."""
    return [f for f in REQUIRED_BACKFILL_FIELDS if not (getattr(product, f) or "").strip()]


def _needs_backfill_clause():
    """SQL mirror of missing_backfill_fields() — any required field null or blank."""
    # func.trim (not btrim) — standard SQL, so this works on Postgres in production
    # and on the SQLite the unit tests run against.
    return or_(
        *[
            or_(getattr(Product, f).is_(None), func.trim(getattr(Product, f)) == "")
            for f in REQUIRED_BACKFILL_FIELDS
        ]
    )


async def backfill_stats(session: AsyncSession, *, listed_only: bool = True) -> dict:
    """Progress counts for the staff backfill queue. Reports, never mutates."""
    scope = select(func.count()).select_from(Product)
    if listed_only:
        scope = scope.where(Product.is_listed.is_(True))
    total = (await session.execute(scope)).scalar_one()

    pending_q = select(func.count()).select_from(Product).where(_needs_backfill_clause())
    if listed_only:
        pending_q = pending_q.where(Product.is_listed.is_(True))
    pending = (await session.execute(pending_q)).scalar_one()

    return {"total": total, "pending": pending, "complete": total - pending}


async def next_backfill_product(
    session: AsyncSession, *, listed_only: bool = True, skip_ids: set | None = None
) -> Product | None:
    """The next product needing descriptive data. Listed products come first, since
    those are the ones customers can actually see and buy."""
    stmt = select(Product).where(_needs_backfill_clause())
    if listed_only:
        stmt = stmt.where(Product.is_listed.is_(True))
    if skip_ids:
        stmt = stmt.where(Product.id.notin_(list(skip_ids)))
    stmt = stmt.order_by(Product.name).limit(1)
    return (await session.execute(stmt)).scalar_one_or_none()


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
