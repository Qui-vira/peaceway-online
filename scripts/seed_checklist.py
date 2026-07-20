"""Seed starter checklist templates for every staff role + the PA's meeting-prep items.

Idempotent by (role_key, item_text): re-running never duplicates a template, and it
leaves any owner-edited/added templates untouched. Run after the schema migration
(b6d3f8a2c1e5) is applied.

Usage:
  python scripts/seed_checklist.py
  # in prod:
  railway run python scripts/seed_checklist.py
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.db import _normalize_async_url
from app.core.rbac import (
    COMMUNITY_MANAGER,
    DISPATCHER,
    FINANCE,
    LEAD_PHARMACIST,
    PA,
    PACKAGING,
    PHARMACIST_ADMIN,
    SALES_SUPPORT,
    SYSTEM_OWNER,
)
from app.models import ChecklistTemplate

# (role_key, item_text, cadence, weekday). weekday only used for cadence="weekly".
TEMPLATES: list[tuple[str, str, str, int | None]] = [
    # Personal Assistant — the three daily meeting-prep items (owner-agreed).
    (PA, "Confirm today's meeting time and attendees", "daily", None),
    (PA, "Prepare the meeting agenda and share it", "daily", None),
    (PA, "Collect yesterday's open decisions for review", "daily", None),
    # System Owner
    (SYSTEM_OWNER, "Review overnight critical alerts and errors", "daily", None),
    (SYSTEM_OWNER, "Check yesterday's order + payment totals", "daily", None),
    # Lead Pharmacist
    (LEAD_PHARMACIST, "Clear the prescription review queue", "daily", None),
    (LEAD_PHARMACIST, "Respond to escalated pharmacist tickets", "daily", None),
    # Pharmacist Admin
    (PHARMACIST_ADMIN, "Review new prescriptions", "daily", None),
    (PHARMACIST_ADMIN, "Reply to pending pharmacist inbox messages", "daily", None),
    # Sales / Support
    (SALES_SUPPORT, "Reply to overnight customer messages", "daily", None),
    (SALES_SUPPORT, "Follow up on unpaid/pending orders", "daily", None),
    # Community Manager. The inbound-queue clear is a TWICE-daily task, seeded as two
    # distinct rows (morning + evening) rather than one row completed twice, so each
    # pass is tracked and audited independently.
    (COMMUNITY_MANAGER, "Morning: Clear inbound comments, DMs, Telegram & WhatsApp queues", "daily", None),
    (COMMUNITY_MANAGER, "Evening: Clear inbound comments, DMs, Telegram & WhatsApp queues", "daily", None),
    (COMMUNITY_MANAGER, "Send scheduled announcements/follow-ups", "daily", None),
    # Packaging
    (PACKAGING, "Package all paid, approved orders", "daily", None),
    (PACKAGING, "Report any out-of-stock items", "daily", None),
    # Dispatcher
    (DISPATCHER, "Assign riders to ready deliveries", "daily", None),
    (DISPATCHER, "Confirm yesterday's deliveries were completed", "daily", None),
    # Finance
    (FINANCE, "Review and approve payment proofs", "daily", None),
    (FINANCE, "Reconcile the weekly settlement records", "weekly", 4),  # Friday
]


async def run() -> None:
    engine = create_async_engine(_normalize_async_url(get_settings().database_url))
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    created = 0
    async with maker() as session:
        for order, (role_key, item_text, cadence, weekday) in enumerate(TEMPLATES):
            exists = (
                await session.execute(
                    select(ChecklistTemplate).where(
                        ChecklistTemplate.role_key == role_key,
                        ChecklistTemplate.item_text == item_text,
                    )
                )
            ).scalar_one_or_none()
            if exists:
                continue
            session.add(
                ChecklistTemplate(
                    role_key=role_key, item_text=item_text, cadence=cadence,
                    weekday=weekday, active=True, sort_order=order,
                )
            )
            created += 1
        await session.commit()
    await engine.dispose()
    print(f"checklist templates seeded: {created} new, {len(TEMPLATES) - created} already present")


if __name__ == "__main__":
    asyncio.run(run())
