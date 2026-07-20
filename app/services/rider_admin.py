"""Dispatch-partner (rider) management: list, add, activate/deactivate.

External riders are their own auth domain (dispatch_partners), so this never
touches admin_users. Email is the portal login (OTP is sent there), unique per rider.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DispatchPartner


async def list_riders(session: AsyncSession) -> list[DispatchPartner]:
    return list(
        (await session.execute(select(DispatchPartner).order_by(DispatchPartner.name))).scalars().all()
    )


async def get_rider(session: AsyncSession, rider_id: UUID) -> DispatchPartner | None:
    return await session.get(DispatchPartner, rider_id)


async def add_rider(
    session: AsyncSession, *, name: str, email: str, phone: str | None = None
) -> tuple[DispatchPartner, bool]:
    """Create (or reactivate) a rider by email. Returns (rider, created)."""
    email = email.strip().lower()
    existing = (
        await session.execute(
            select(DispatchPartner).where(func.lower(DispatchPartner.portal_login_email) == email)
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.name = name
        existing.phone = phone
        existing.is_active = True
        return existing, False
    rider = DispatchPartner(name=name, portal_login_email=email, phone=phone, is_active=True)
    session.add(rider)
    await session.flush()
    return rider, True


async def set_rider_active(session: AsyncSession, rider_id: UUID, active: bool) -> bool:
    rider = await session.get(DispatchPartner, rider_id)
    if rider is None:
        return False
    rider.is_active = active
    return True
