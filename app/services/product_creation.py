"""Create catalogue entries for manufacturer products we do not yet stock.

A crawl finds far more products than it matches. Most unmatched items are not
failures — they are real products from a real manufacturer that simply are not in
our catalogue. Discarding them throws away both the product and its photograph.

WHY ATTACHING THE PHOTO IS SAFE HERE, UNLIKE A MATCH
When we CREATE the product from the scraped item, the product and its photograph
come from the same record on the manufacturer's own site. There is no pairing
decision, so there is nothing to get wrong — the same reasoning that lets the
Vitabiotics import attach images directly. A match is the opposite case: two
separately-sourced things joined by a rule, which is why that path needs a human.

WHAT A CREATED PRODUCT LOOKS LIKE
Never listed, never priced, always flagged for pharmacist review. It is a draft of
a product record, not something a customer can buy. Staff price and list it — the
same gate every imported product passes through.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, Product, ProductPricing
from app.services.image_matching import canonical


@dataclass
class SkipReason:
    reason: str
    existing: str | None = None


async def find_duplicate(session: AsyncSession, item) -> SkipReason | None:
    """Would creating this item duplicate something we already hold?

    Three independent checks, because a duplicate medicine record is worse than a
    missing one: staff would price and stock the same product twice, and a customer
    could see two entries for one box.
    """
    # 1. Registration number — the regulator's unique id, and a UNIQUE column here,
    #    so an insert would fail anyway.
    if item.nafdac:
        existing = (
            await session.execute(
                select(Product).where(
                    func.upper(func.trim(Product.nafdac_number)) == item.nafdac.strip().upper()
                )
            )
        ).scalars().first()
        if existing:
            return SkipReason("same NAFDAC number", existing.name)

    # 2. Same manufacturer, same brand + form + strength.
    if item.brand:
        rows = (
            await session.execute(
                select(Product).where(Product.manufacturer == item.manufacturer)
            )
        ).scalars().all()
        for p in rows:
            if (
                canonical(p.brand_name) == canonical(item.brand)
                and canonical(p.dosage_form) == canonical(item.form)
                and canonical(p.strength) == canonical(item.strength)
                and canonical(p.brand_name)
            ):
                return SkipReason("same brand + form + strength", p.name)

    # 3. Same product name for the same manufacturer.
    if item.title:
        existing = (
            await session.execute(
                select(Product).where(
                    Product.manufacturer == item.manufacturer,
                    func.lower(Product.name) == item.title.strip().lower(),
                )
            )
        ).scalars().first()
        if existing:
            return SkipReason("same name", existing.name)

    return None


async def create_from_scraped(
    session: AsyncSession, item, admin_id: int = 0, *, source_url: str | None = None
) -> Product:
    """Create one draft product from a scraped manufacturer item.

    Fields are copied only where the manufacturer actually published them; anything
    unreadable stays null and the pharmacist fills it in. Nothing is inferred.
    """
    name = (item.title or item.brand or "").strip()[:255]
    if not name:
        raise ValueError("scraped item has no usable name")

    product = Product(
        name=name,
        # No separate generic name on a product page; the title is the honest value.
        generic_name=name,
        brand_name=(item.brand or None),
        dosage_form=(item.form or None),
        strength=(item.strength or None),
        pack_size=(item.pack_size or None),
        manufacturer=item.manufacturer,
        # The manufacturer's own published registration number, where they gave one.
        nafdac_number=(item.nafdac or None),
        category=None,
        requires_prescription=False,
        # Always: this record was assembled from a web page, not from a pharmacist.
        requires_review=True,
        # Always: nothing a customer can see until staff price and list it.
        is_listed=False,
    )
    session.add(product)
    await session.flush()

    # Pricing row with NO price — staff set Naira pricing.
    session.add(ProductPricing(product_id=product.id))

    session.add(
        AuditLog(
            actor_telegram_id=admin_id,
            action="product_created_from_manufacturer_site",
            entity="product",
            entity_id=str(product.id),
            detail={
                "manufacturer": item.manufacturer,
                "source_url": source_url or item.source_url,
                "image_url": item.image_url,
                "nafdac": item.nafdac,
                "created_unlisted_and_unpriced": True,
            },
        )
    )
    return product
