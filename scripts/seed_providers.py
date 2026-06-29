"""Seed the logistics_providers table.

Manual is enabled; API providers are recorded but disabled until their credentials
are configured. Idempotent.

Usage: python scripts/seed_providers.py
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.db import _normalize_async_url
from app.models import LogisticsProvider
from app.services.delivery.registry import all_providers


async def run() -> None:
    engine = create_async_engine(_normalize_async_url(get_settings().database_url))
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    added = 0
    async with maker() as session:
        existing = {
            p.key for p in (await session.execute(select(LogisticsProvider))).scalars().all()
        }
        for prov in all_providers():
            if prov.key in existing:
                # Keep enabled flag in sync with current credential availability.
                row = (
                    await session.execute(select(LogisticsProvider).where(LogisticsProvider.key == prov.key))
                ).scalar_one()
                row.is_enabled = prov.enabled
                row.supports_gps = prov.supports_gps
                row.supports_tracking_url = prov.supports_tracking_url
                continue
            session.add(
                LogisticsProvider(
                    key=prov.key,
                    name=prov.name,
                    is_enabled=prov.enabled,
                    supports_gps=prov.supports_gps,
                    supports_tracking_url=prov.supports_tracking_url,
                )
            )
            added += 1
        await session.commit()
    await engine.dispose()
    print(f"providers seeded: {added} new (others synced).")


if __name__ == "__main__":
    asyncio.run(run())
