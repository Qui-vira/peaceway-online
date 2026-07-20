"""Seed the twelve orientation rotation topics (owner's marketing plan §10.5).

One topic per week, twelve-week cycle. Idempotent by sort_order: re-running never
duplicates or reorders, and leaves any owner-added topics untouched. Topic text is only
inserted when a row for that position does not already exist.

Usage:
  python scripts/seed_orientation.py
  # in prod:
  railway run python scripts/seed_orientation.py
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.db import _normalize_async_url
from app.models import OrientationTopic

# In rotation order. sort_order = list index (0-based).
TOPICS: list[str] = [
    "Who we sell to and why they choose us",
    "What we are not allowed to say. Claims library and the approval chain.",
    "Customer data rules and why the group stays clean",
    "The order journey end to end, and where your handoff sits",
    "Handling complaints and returns",
    "Stock and expiry, why a stockout costs more than the sale",
    "Cold chain and delivery standards",
    "Reading the numbers, what contribution margin means for your job",
    "Escalation drill. Run a live clinical question and time the response.",
    "Competitor review, what the pharmacy down the road does better",
    "Refill follow-up practice, script and objections",
    "Licence refresher, what the licence covers and what breaks it",
]


async def run() -> None:
    engine = create_async_engine(_normalize_async_url(get_settings().database_url))
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    created = 0
    async with maker() as session:
        for order, text in enumerate(TOPICS):
            exists = (
                await session.execute(
                    select(OrientationTopic).where(OrientationTopic.sort_order == order)
                )
            ).scalar_one_or_none()
            if exists:
                continue
            session.add(OrientationTopic(sort_order=order, topic_text=text, active=True))
            created += 1
        await session.commit()
    await engine.dispose()
    print(f"orientation topics seeded: {created} new, {len(TOPICS) - created} already present")


if __name__ == "__main__":
    asyncio.run(run())
