"""Web admin authentication: Telegram-bridge OTP + DB sessions."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import rbac
from app.core.config import get_settings
from app.models.admin import AdminRoleAssignment
from app.models.admin import AdminStatus, AdminUser, WebAdminEmailOtp, WebAdminOtp, WebAdminSession
from app.services.otp_service import send_otp_email

OTP_TTL_MINUTES = 5
SESSION_TTL_HOURS = 8


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


async def _ensure_bootstrap_owner_admin(
    db: AsyncSession, telegram_id: int
) -> AdminUser | None:
    """Ensure env-configured owners can use web admin auth.

    `OWNER_TELEGRAM_IDS` already grants runtime system-owner powers, but web OTP
    login still needs a persisted ACTIVE admin row and role assignment so it can
    issue sessions. When the owner signs in from the web for the first time, we
    create or repair that bootstrap record automatically.
    """
    settings = get_settings()
    if telegram_id not in settings.owner_ids:
        return None

    admin = (
        await db.execute(
            select(AdminUser).where(AdminUser.telegram_id == telegram_id)
        )
    ).scalar_one_or_none()

    if admin is None:
        admin = AdminUser(
            telegram_id=telegram_id,
            is_active=True,
            status=AdminStatus.ACTIVE,
        )
        db.add(admin)
        await db.flush()
    else:
        admin.is_active = True
        admin.status = AdminStatus.ACTIVE

    assignment = (
        await db.execute(
            select(AdminRoleAssignment).where(
                AdminRoleAssignment.admin_id == admin.id,
                AdminRoleAssignment.role_key == rbac.SYSTEM_OWNER,
            )
        )
    ).scalar_one_or_none()
    if assignment is None:
        db.add(AdminRoleAssignment(admin_id=admin.id, role_key=rbac.SYSTEM_OWNER))
        await db.flush()

    return admin


async def create_web_otp(
    db: AsyncSession, telegram_id: int
) -> tuple[str, int] | None:
    """Generate a login OTP for an ACTIVE admin.

    Returns (plaintext_code, telegram_id) so the caller can send the code via bot.
    Returns None if the telegram_id is not an active admin (caller returns 200 either way).
    """
    admin = (
        await db.execute(
            select(AdminUser).where(AdminUser.telegram_id == telegram_id)
        )
    ).scalar_one_or_none()

    if admin is None or admin.status != AdminStatus.ACTIVE:
        admin = await _ensure_bootstrap_owner_admin(db, telegram_id)
        if admin is None or admin.status != AdminStatus.ACTIVE:
            return None

    # Invalidate any existing unused OTPs for this telegram_id
    await db.execute(
        update(WebAdminOtp)
        .where(WebAdminOtp.telegram_id == telegram_id, WebAdminOtp.used.is_(False))
        .values(used=True)
    )

    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(
        WebAdminOtp(
            telegram_id=telegram_id,
            code_hash=_hash_code(code),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=OTP_TTL_MINUTES),
            used=False,
        )
    )

    return code, telegram_id


async def create_web_email_otp(
    db: AsyncSession, email: str
) -> tuple[str, str] | None:
    """Generate a login OTP for a single ACTIVE operations user matched by email."""
    normalized = _normalize_email(email)
    admins = (
        await db.execute(
            select(AdminUser).where(
                func.lower(AdminUser.email) == normalized,
                AdminUser.status == AdminStatus.ACTIVE,
            )
        )
    ).scalars().all()

    if len(admins) != 1:
        return None

    admin = admins[0]
    await db.execute(
        update(WebAdminEmailOtp)
        .where(WebAdminEmailOtp.admin_id == admin.id, WebAdminEmailOtp.used.is_(False))
        .values(used=True)
    )

    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(
        WebAdminEmailOtp(
            admin_id=admin.id,
            email=normalized,
            code_hash=_hash_code(code),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=OTP_TTL_MINUTES),
            used=False,
        )
    )
    return code, normalized


async def verify_web_otp_and_create_session(
    db: AsyncSession, telegram_id: int, code: str
) -> str | None:
    """Verify OTP, create a session row, return the session token (UUID string).

    Returns None on any failure (invalid code, expired, admin not active).
    Marks the OTP as used before checking the hash — prevents brute-force.
    """
    now = datetime.now(timezone.utc)

    otp = (
        await db.execute(
            select(WebAdminOtp)
            .where(
                WebAdminOtp.telegram_id == telegram_id,
                WebAdminOtp.used.is_(False),
                WebAdminOtp.expires_at > now,
            )
            .order_by(WebAdminOtp.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if otp is None:
        return None

    otp.used = True  # mark before hash check — prevents brute-force

    if _hash_code(code) != otp.code_hash:
        return None

    admin = (
        await db.execute(
            select(AdminUser).where(AdminUser.telegram_id == telegram_id)
        )
    ).scalar_one_or_none()

    if admin is None or admin.status != AdminStatus.ACTIVE:
        admin = await _ensure_bootstrap_owner_admin(db, telegram_id)
        if admin is None or admin.status != AdminStatus.ACTIVE:
            return None

    session = WebAdminSession(
        id=uuid4(),
        admin_id=admin.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS),
    )
    db.add(session)

    return str(session.id)


async def verify_web_email_otp_and_create_session(
    db: AsyncSession, email: str, code: str
) -> str | None:
    """Verify email OTP, create a session row, and return the session token."""
    normalized = _normalize_email(email)
    now = datetime.now(timezone.utc)

    otp = (
        await db.execute(
            select(WebAdminEmailOtp)
            .where(
                WebAdminEmailOtp.email == normalized,
                WebAdminEmailOtp.used.is_(False),
                WebAdminEmailOtp.expires_at > now,
            )
            .order_by(WebAdminEmailOtp.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if otp is None:
        return None

    otp.used = True
    if _hash_code(code) != otp.code_hash:
        return None

    admin = otp.admin
    if admin is None or admin.status != AdminStatus.ACTIVE:
        return None

    session = WebAdminSession(
        id=uuid4(),
        admin_id=admin.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS),
    )
    db.add(session)
    return str(session.id)


async def get_session_admin(
    db: AsyncSession, token: str
) -> tuple[AdminUser, set[str]] | None:
    """Validate a web session token.

    Returns (AdminUser, role_keys) if valid, None otherwise.
    Updates last_used_at on each successful call.
    """
    try:
        session_id = UUID(token)
    except ValueError:
        return None

    now = datetime.now(timezone.utc)

    web_session = (
        await db.execute(
            select(WebAdminSession).where(
                WebAdminSession.id == session_id,
                WebAdminSession.expires_at > now,
            )
        )
    ).scalar_one_or_none()

    if web_session is None:
        return None

    admin = web_session.admin
    if admin is None or admin.status != AdminStatus.ACTIVE:
        return None

    web_session.last_used_at = now
    role_keys = {a.role_key for a in admin.assignments}
    return admin, role_keys


async def delete_session(db: AsyncSession, token: str) -> None:
    """Delete a web session by token (logout)."""
    try:
        session_id = UUID(token)
    except ValueError:
        return

    web_session = (
        await db.execute(
            select(WebAdminSession).where(WebAdminSession.id == session_id)
        )
    ).scalar_one_or_none()

    if web_session:
        await db.delete(web_session)


async def send_web_email_otp(email: str, code: str) -> None:
    settings = get_settings()
    await send_otp_email(email, code, settings.pharmacy_name)
