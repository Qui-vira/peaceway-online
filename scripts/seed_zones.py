"""Seed Lagos delivery zones and the singleton fee-settings row.

Idempotent: existing zones (matched by name) and the fee row are left untouched,
so admin edits made from Telegram are never overwritten.

Usage:
    python scripts/seed_zones.py
"""
from __future__ import annotations

import asyncio
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.db import _normalize_async_url
from app.models import DeliveryZone, FeeSetting

# (name, fee NGN, eta minutes) — starting defaults, all editable from Telegram.
ZONES = [
    ("Igando", Decimal("700"), 45),
    ("Agodo", Decimal("700"), 45),
    ("Ikotun", Decimal("1000"), 60),
    ("Idimu", Decimal("1000"), 60),
    ("Egbe", Decimal("1200"), 70),
    ("Egbeda", Decimal("1200"), 70),
    ("Ejigbo", Decimal("1300"), 75),
    ("Iyana Ipaja", Decimal("1500"), 80),
    ("Isheri", Decimal("1800"), 90),
    ("Lekki", Decimal("3500"), 150),
    ("Other Lagos areas", Decimal("2500"), 120),
]


async def run() -> None:
    engine = create_async_engine(_normalize_async_url(get_settings().database_url))
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    added_zones = 0
    async with maker() as session:
        existing = {
            z.name for z in (await session.execute(select(DeliveryZone))).scalars().all()
        }
        for name, fee, eta in ZONES:
            if name in existing:
                continue
            session.add(DeliveryZone(name=name, fee=fee, eta_minutes=eta, is_active=True))
            added_zones += 1

        fee_row = await session.get(FeeSetting, 1)
        if fee_row is None:
            session.add(
                FeeSetting(
                    id=1,
                    payment_fee_pct=Decimal("1.50"),
                    payment_fee_flat=Decimal("0"),
                    offramp_fee=Decimal("0"),
                    handling_fee=Decimal("0"),
                    enable_bank=True,
                    enable_flutterwave=True,
                    enable_crypto=False,
                )
            )
            fee_created = True
        else:
            fee_created = False

        await session.commit()

    await engine.dispose()
    print(f"zones added: {added_zones} (existing left untouched)")
    print(f"fee_settings created: {fee_created}")


if __name__ == "__main__":
    asyncio.run(run())
