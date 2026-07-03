"""Web admin OTP + session service tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.admin import AdminRoleAssignment, AdminStatus, AdminUser, WebAdminOtp, WebAdminSession
from app.services.admin_web_auth import (
    create_web_otp,
    delete_session,
    get_session_admin,
    verify_web_otp_and_create_session,
)


@pytest.mark.asyncio
async def test_web_admin_otp_model_exists(session):
    """WebAdminOtp can be created and queried."""
    otp = WebAdminOtp(
        telegram_id=123456789,
        code_hash="abc123",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        used=False,
    )
    session.add(otp)
    await session.flush()
    assert otp.id is not None


@pytest.mark.asyncio
async def test_web_admin_session_model_exists(session):
    """WebAdminSession can be linked to an AdminUser."""
    admin = AdminUser(telegram_id=111222333, status=AdminStatus.ACTIVE, is_active=True)
    session.add(admin)
    await session.flush()

    web_session = WebAdminSession(
        admin_id=admin.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=8),
    )
    session.add(web_session)
    await session.flush()
    assert web_session.id is not None


async def _make_active_admin(session, telegram_id: int = 999888777) -> AdminUser:
    admin = AdminUser(telegram_id=telegram_id, status=AdminStatus.ACTIVE, is_active=True)
    session.add(admin)
    await session.flush()
    return admin


@pytest.mark.asyncio
async def test_create_web_otp_returns_code_for_active_admin(session):
    admin = await _make_active_admin(session)
    result = await create_web_otp(session, admin.telegram_id)
    assert result is not None
    code, tid = result
    assert len(code) == 6 and code.isdigit()
    assert tid == admin.telegram_id


@pytest.mark.asyncio
async def test_create_web_otp_returns_none_for_unknown_id(session):
    result = await create_web_otp(session, 0)
    assert result is None


@pytest.mark.asyncio
async def test_create_web_otp_returns_none_for_pending_admin(session):
    admin = AdminUser(telegram_id=555444333, status=AdminStatus.PENDING, is_active=False)
    session.add(admin)
    await session.flush()
    result = await create_web_otp(session, admin.telegram_id)
    assert result is None


@pytest.mark.asyncio
async def test_verify_otp_creates_session(session):
    admin = await _make_active_admin(session)
    result = await create_web_otp(session, admin.telegram_id)
    assert result is not None
    code, _ = result
    await session.flush()

    token = await verify_web_otp_and_create_session(session, admin.telegram_id, code)
    assert token is not None
    assert len(token) == 36  # UUID string


@pytest.mark.asyncio
async def test_verify_otp_wrong_code_returns_none(session):
    admin = await _make_active_admin(session, telegram_id=111000111)
    await create_web_otp(session, admin.telegram_id)
    await session.flush()

    token = await verify_web_otp_and_create_session(session, admin.telegram_id, "000000")
    assert token is None


@pytest.mark.asyncio
async def test_get_session_admin_returns_admin_and_roles(session):
    from app.models.admin import AdminRoleAssignment
    admin = await _make_active_admin(session, telegram_id=222333444)
    session.add(AdminRoleAssignment(admin_id=admin.id, role_key="packaging"))
    result = await create_web_otp(session, admin.telegram_id)
    assert result is not None
    code, _ = result
    await session.flush()

    token = await verify_web_otp_and_create_session(session, admin.telegram_id, code)
    assert token is not None
    await session.flush()

    auth = await get_session_admin(session, token)
    assert auth is not None
    fetched_admin, role_keys = auth
    assert fetched_admin.telegram_id == admin.telegram_id
    assert "packaging" in role_keys


@pytest.mark.asyncio
async def test_get_session_admin_invalid_token_returns_none(session):
    result = await get_session_admin(session, "not-a-uuid")
    assert result is None


@pytest.mark.asyncio
async def test_delete_session_invalidates_token(session):
    admin = await _make_active_admin(session, telegram_id=777666555)
    result = await create_web_otp(session, admin.telegram_id)
    assert result is not None
    code, _ = result
    await session.flush()

    token = await verify_web_otp_and_create_session(session, admin.telegram_id, code)
    assert token is not None
    await session.flush()

    await delete_session(session, token)
    await session.flush()

    auth = await get_session_admin(session, token)
    assert auth is None


@pytest.mark.asyncio
async def test_create_web_otp_invalidates_previous_otp(session):
    """Second OTP request renders the first code unusable."""
    admin = await _make_active_admin(session, telegram_id=444333222)
    first = await create_web_otp(session, admin.telegram_id)
    assert first is not None
    first_code, _ = first
    await session.flush()

    await create_web_otp(session, admin.telegram_id)
    await session.flush()

    token = await verify_web_otp_and_create_session(session, admin.telegram_id, first_code)
    assert token is None


@pytest.mark.asyncio
async def test_verify_otp_expired_returns_none(session):
    """OTP past its TTL cannot be used."""
    admin = await _make_active_admin(session, telegram_id=333222111)
    result = await create_web_otp(session, admin.telegram_id)
    assert result is not None
    code, _ = result
    await session.flush()

    # Back-date the OTP's expiry so it appears expired
    from app.models.admin import WebAdminOtp as _Otp
    from sqlalchemy import select as _select
    otp_row = (
        await session.execute(_select(_Otp).where(_Otp.telegram_id == admin.telegram_id, _Otp.used.is_(False)))
    ).scalar_one()
    otp_row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    await session.flush()

    token = await verify_web_otp_and_create_session(session, admin.telegram_id, code)
    assert token is None


@pytest.mark.asyncio
async def test_get_session_admin_disabled_admin_returns_none(session):
    """A disabled admin's session is rejected."""
    from app.models.admin import AdminStatus as _Status
    admin = await _make_active_admin(session, telegram_id=888777666)
    result = await create_web_otp(session, admin.telegram_id)
    assert result is not None
    code, _ = result
    await session.flush()

    token = await verify_web_otp_and_create_session(session, admin.telegram_id, code)
    assert token is not None
    await session.flush()

    # Disable the admin after the session was created
    admin.status = _Status.DISABLED
    admin.is_active = False
    await session.flush()

    auth = await get_session_admin(session, token)
    assert auth is None
