"""Import the product catalog from PharmaOS into Peaceway Online.

READ-ONLY against PharmaOS: only SELECT statements are issued; nothing is written
back. Products are normalized, prescription-classified, and upserted into
Peaceway's own database keyed on ``nafdac_number`` (idempotent — safe to re-run as
a /resync). Existing ProductPricing is never touched, so admin-set prices/stock
survive a re-sync.

Usage:
    python -m scripts.import_pharmaos            # dry run, prints counts
    python -m scripts.import_pharmaos --commit   # persist into Peaceway DB
"""
from __future__ import annotations

import argparse
import asyncio
import re
import sys
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.db import _normalize_async_url
from app.models import Product, ProductAlias
from app.services.rx_classifier import classify

# PharmaOS category -> customer-friendly Peaceway category.
CATEGORY_MAP = {
    "drugs": "Medicines",
    "medical devices": "Medical Devices",
    "vaccines and biologics": "Vaccines",
    "herbals and nutraceuticals": "Supplements",
    "veterinary": "Veterinary",
    "n/a": "Other",
}

_WS = re.compile(r"\s+")


def normalize_name(raw: str | None) -> str:
    return _WS.sub(" ", (raw or "").strip())


def map_category(raw: str | None) -> str:
    return CATEGORY_MAP.get((raw or "").strip().lower(), "Other")


def normalize_alias(raw: str | None) -> str:
    return _WS.sub(" ", (raw or "").strip().lower())


async def fetch_pharmaos_rows():
    """Read products + aliases from PharmaOS (SELECT only)."""
    url = _normalize_async_url(get_settings().pharmaos_database_url)
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            products = (
                await conn.execute(
                    text(
                        "SELECT id, name, generic_name, brand_name, dosage_form, strength, "
                        "manufacturer, nafdac_number, category FROM products"
                    )
                )
            ).mappings().all()
            aliases = (
                await conn.execute(
                    text("SELECT product_id, alias_name, normalized_name FROM product_aliases")
                )
            ).mappings().all()
    finally:
        await engine.dispose()
    return products, aliases


async def run(commit: bool) -> None:
    settings = get_settings()
    src_products, src_aliases = await fetch_pharmaos_rows()
    print(f"PharmaOS: {len(src_products)} products, {len(src_aliases)} aliases")

    dst_engine = create_async_engine(_normalize_async_url(settings.database_url))
    maker = async_sessionmaker(dst_engine, class_=AsyncSession, expire_on_commit=False)

    stats = {"new": 0, "updated": 0, "skipped": 0, "aliases_new": 0}
    # Map PharmaOS product id -> Peaceway Product (for alias import).
    src_to_product: dict = {}

    async with maker() as session:
        # Index existing Peaceway products by nafdac_number and by name (fallback).
        existing = (await session.execute(select(Product))).scalars().all()
        by_nafdac = {p.nafdac_number: p for p in existing if p.nafdac_number}
        by_name = {p.name.lower(): p for p in existing}

        for row in src_products:
            name = normalize_name(row["name"])
            if not name:
                stats["skipped"] += 1
                continue
            nafdac = (row["nafdac_number"] or "").strip() or None
            requires_rx, requires_review = classify(
                name, row["generic_name"], row["dosage_form"], row["category"]
            )

            target = by_nafdac.get(nafdac) if nafdac else by_name.get(name.lower())
            if target is None:
                target = Product(id=uuid4())
                session.add(target)
                stats["new"] += 1
                if nafdac:
                    by_nafdac[nafdac] = target
                by_name[name.lower()] = target
            else:
                stats["updated"] += 1

            # Update catalog fields (never pricing/listing — admin owns those).
            target.name = name
            target.generic_name = normalize_name(row["generic_name"]) or name
            target.brand_name = normalize_name(row["brand_name"]) or None
            target.dosage_form = normalize_name(row["dosage_form"]) or None
            target.strength = normalize_name(row["strength"]) or None
            target.manufacturer = normalize_name(row["manufacturer"]) or None
            target.nafdac_number = nafdac
            target.category = map_category(row["category"])
            target.requires_prescription = requires_rx
            target.requires_review = requires_review
            src_to_product[row["id"]] = target

        await session.flush()

        # Import aliases (skip ones whose alias_name already exists).
        existing_aliases = {
            a.alias_name.lower()
            for a in (await session.execute(select(ProductAlias))).scalars().all()
        }
        for a in src_aliases:
            product = src_to_product.get(a["product_id"])
            if product is None:
                continue
            alias_name = normalize_name(a["alias_name"])
            if not alias_name or alias_name.lower() in existing_aliases:
                continue
            session.add(
                ProductAlias(
                    product_id=product.id,
                    alias_name=alias_name,
                    normalized_name=normalize_alias(a["normalized_name"] or alias_name),
                )
            )
            existing_aliases.add(alias_name.lower())
            stats["aliases_new"] += 1

        if commit:
            await session.commit()
            print("COMMITTED.")
        else:
            await session.rollback()
            print("DRY RUN — no changes written. Re-run with --commit to persist.")

    await dst_engine.dispose()

    print(
        f"products: new={stats['new']} updated={stats['updated']} skipped={stats['skipped']} | "
        f"aliases: new={stats['aliases_new']}"
    )
    # Rx breakdown preview
    rx = sum(1 for r in src_products if classify(r['name'], r['generic_name'], r['dosage_form'], r['category'])[0])
    review = sum(1 for r in src_products if classify(r['name'], r['generic_name'], r['dosage_form'], r['category'])[1])
    print(f"classification: requires_prescription={rx}  requires_review={review}  (of {len(src_products)})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import PharmaOS catalog into Peaceway.")
    parser.add_argument("--commit", action="store_true", help="Persist changes (default: dry run).")
    args = parser.parse_args()
    try:
        asyncio.run(run(commit=args.commit))
    except Exception as exc:  # noqa: BLE001
        print(f"Import failed: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
