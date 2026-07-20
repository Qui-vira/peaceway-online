"""Seed a dispatch partner (rider) with a portal login. Idempotent by email.

The email is the rider's portal login: OTP codes are sent there, so use an address
the rider actually controls. Reactivates a previously deactivated rider.

Usage:
  python scripts/seed_riders.py "Rider Name" rider@example.com [phone]
"""
from __future__ import annotations

import asyncio
import sys

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.db import _normalize_async_url
from app.models import DispatchPartner


async def run(name: str, email: str, phone: str | None = None) -> None:
    email = email.strip().lower()
    engine = create_async_engine(_normalize_async_url(get_settings().database_url))
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        existing = (
            await session.execute(
                select(DispatchPartner).where(func.lower(DispatchPartner.portal_login_email) == email)
            )
        ).scalar_one_or_none()
        if existing:
            existing.name = name
            existing.phone = phone
            existing.is_active = True
            action = "updated"
        else:
            session.add(DispatchPartner(name=name, portal_login_email=email, phone=phone, is_active=True))
            action = "created"
        await session.commit()
    await engine.dispose()
    print(f"rider {action}: {name} <{email}>")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('Usage: python scripts/seed_riders.py "Rider Name" rider@example.com [phone]')
        raise SystemExit(1)
    asyncio.run(run(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None))
