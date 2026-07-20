"""Dispatch-partner (rider) portal auth: email OTP + DB sessions.

Separate auth domain from staff/customers/suppliers. Identity is a
`dispatch_partners` row matched by portal_login_email; sessions/OTPs live in
dispatch-only tables, so a rider token can never resolve to any other identity.
Hardening mirrors the partner service: SHA-256 hashed codes, marked used before
the hash check, each issuance invalidates prior unused codes.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.dispatch_auth import DispatchPartner, DispatchPartnerOtp, DispatchPartnerSession
from app.services.otp_service import send_otp_email

OTP_TTL_MINUTES = 5
SESSION_TTL_HOURS = 8


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


async def _active_rider_by_email(db: AsyncSession, email: str) -> DispatchPartner | None:
    rows = (
        await db.execute(
            select(DispatchPartner).where(
                func.lower(DispatchPartner.portal_login_email) == _normalize_email(email),
                DispatchPartner.is_active.is_(True),
            )
        )
    ).scalars().all()
    return rows[0] if len(rows) == 1 else None


async def create_dispatch_otp(db: AsyncSession, email: str) -> tuple[str, str] | None:
    """Generate a login OTP for an active rider. Returns (code, email) or None."""
    rider = await _active_rider_by_email(db, email)
    if rider is None:
        return None
    await db.execute(
        update(DispatchPartnerOtp)
        .where(DispatchPartnerOtp.dispatch_partner_id == rider.id, DispatchPartnerOtp.used.is_(False))
        .values(used=True)
    )
    normalized = _normalize_email(email)
    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(
        DispatchPartnerOtp(
            dispatch_partner_id=rider.id,
            email=normalized,
            code_hash=_hash_code(code),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=OTP_TTL_MINUTES),
            used=False,
        )
    )
    return code, normalized


async def verify_dispatch_otp_and_create_session(db: AsyncSession, email: str, code: str) -> str | None:
    """Verify OTP, create a session, return the token. Marks OTP used before hashing."""
    normalized = _normalize_email(email)
    now = datetime.now(timezone.utc)
    otp = (
        await db.execute(
            select(DispatchPartnerOtp)
            .where(
                DispatchPartnerOtp.email == normalized,
                DispatchPartnerOtp.used.is_(False),
                DispatchPartnerOtp.expires_at > now,
            )
            .order_by(DispatchPartnerOtp.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if otp is None:
        return None
    otp.used = True
    if _hash_code(code) != otp.code_hash:
        return None
    rider = otp.dispatch_partner
    if rider is None or not rider.is_active:
        return None
    session = DispatchPartnerSession(
        id=uuid4(),
        dispatch_partner_id=rider.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS),
    )
    db.add(session)
    return str(session.id)


async def get_session_rider(db: AsyncSession, token: str) -> DispatchPartner | None:
    """Validate a rider session token; returns the DispatchPartner or None."""
    try:
        session_id = UUID(token)
    except ValueError:
        return None
    now = datetime.now(timezone.utc)
    ps = (
        await db.execute(
            select(DispatchPartnerSession).where(
                DispatchPartnerSession.id == session_id,
                DispatchPartnerSession.expires_at > now,
            )
        )
    ).scalar_one_or_none()
    if ps is None:
        return None
    rider = ps.dispatch_partner
    if rider is None or not rider.is_active:
        return None
    ps.last_used_at = now
    return rider


async def delete_dispatch_session(db: AsyncSession, token: str) -> None:
    try:
        session_id = UUID(token)
    except ValueError:
        return
    ps = (
        await db.execute(select(DispatchPartnerSession).where(DispatchPartnerSession.id == session_id))
    ).scalar_one_or_none()
    if ps:
        await db.delete(ps)


async def send_dispatch_otp_email(email: str, code: str) -> None:
    settings = get_settings()
    await send_otp_email(email, code, settings.pharmacy_name)
