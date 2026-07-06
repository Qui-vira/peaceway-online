"""Partner portal authentication: email OTP + DB sessions.

This is a SEPARATE auth domain from staff (`admin_web_auth.py`). Identity is a
`network_partners` row matched by `portal_login_email`; sessions/OTPs live in
partner-only tables, so a partner token can never resolve to a staff identity.

Hardening mirrors the staff service: OTP codes are SHA-256 hashed, marked used
BEFORE the hash check (one guess per issuance), and each issuance invalidates
prior unused codes.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.partner_auth import PartnerPortalOtp, PartnerPortalSession
from app.models.sourcing import NetworkPartner
from app.services.otp_service import send_otp_email

OTP_TTL_MINUTES = 5
SESSION_TTL_HOURS = 8


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


async def _active_partner_by_email(db: AsyncSession, email: str) -> NetworkPartner | None:
    normalized = _normalize_email(email)
    partners = (
        await db.execute(
            select(NetworkPartner).where(
                func.lower(NetworkPartner.portal_login_email) == normalized,
                NetworkPartner.is_active.is_(True),
            )
        )
    ).scalars().all()
    # Refuse ambiguous identity — exactly one active partner may own an email.
    if len(partners) != 1:
        return None
    return partners[0]


async def create_partner_otp(db: AsyncSession, email: str) -> tuple[str, str] | None:
    """Generate a login OTP for an active partner matched by portal email.

    Returns (plaintext_code, normalized_email), or None if no single active
    partner owns the email (caller returns 200 either way — never reveal
    whether an email exists).
    """
    partner = await _active_partner_by_email(db, email)
    if partner is None:
        return None

    await db.execute(
        update(PartnerPortalOtp)
        .where(PartnerPortalOtp.partner_id == partner.id, PartnerPortalOtp.used.is_(False))
        .values(used=True)
    )

    normalized = _normalize_email(email)
    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(
        PartnerPortalOtp(
            partner_id=partner.id,
            email=normalized,
            code_hash=_hash_code(code),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=OTP_TTL_MINUTES),
            used=False,
        )
    )
    return code, normalized


async def verify_partner_otp_and_create_session(
    db: AsyncSession, email: str, code: str
) -> str | None:
    """Verify OTP, create a session row, return the session token (UUID string).

    Marks the OTP used before checking the hash — one guess per issuance.
    """
    normalized = _normalize_email(email)
    now = datetime.now(timezone.utc)

    otp = (
        await db.execute(
            select(PartnerPortalOtp)
            .where(
                PartnerPortalOtp.email == normalized,
                PartnerPortalOtp.used.is_(False),
                PartnerPortalOtp.expires_at > now,
            )
            .order_by(PartnerPortalOtp.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if otp is None:
        return None

    otp.used = True  # mark before hash check — prevents brute-force

    if _hash_code(code) != otp.code_hash:
        return None

    partner = otp.partner
    if partner is None or not partner.is_active:
        return None

    session = PartnerPortalSession(
        id=uuid4(),
        partner_id=partner.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS),
    )
    db.add(session)
    return str(session.id)


async def get_session_partner(db: AsyncSession, token: str) -> NetworkPartner | None:
    """Validate a partner session token; returns the NetworkPartner or None.

    Updates last_used_at on each successful call.
    """
    try:
        session_id = UUID(token)
    except ValueError:
        return None

    now = datetime.now(timezone.utc)
    portal_session = (
        await db.execute(
            select(PartnerPortalSession).where(
                PartnerPortalSession.id == session_id,
                PartnerPortalSession.expires_at > now,
            )
        )
    ).scalar_one_or_none()

    if portal_session is None:
        return None

    partner = portal_session.partner
    if partner is None or not partner.is_active:
        return None

    portal_session.last_used_at = now
    return partner


async def delete_partner_session(db: AsyncSession, token: str) -> None:
    """Delete a partner session by token (logout)."""
    try:
        session_id = UUID(token)
    except ValueError:
        return

    portal_session = (
        await db.execute(
            select(PartnerPortalSession).where(PartnerPortalSession.id == session_id)
        )
    ).scalar_one_or_none()

    if portal_session:
        await db.delete(portal_session)


async def send_partner_otp_email(email: str, code: str) -> None:
    settings = get_settings()
    await send_otp_email(email, code, settings.pharmacy_name)
