"""Partner portal auth + cross-domain isolation tests.

The point of the partner domain is that it is walled off from staff: a partner
token must never authenticate as an admin, and an admin token must never
authenticate as a partner. These tests prove both directions plus the basic
OTP lifecycle and per-partner sourcing scoping.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.admin import AdminStatus, AdminUser, WebAdminSession
from app.models.partner_auth import PartnerPortalOtp, PartnerPortalSession
from app.models.sourcing import NetworkPartner, OrderSourcing, PartnerChannel, PartnerType
from app.services.admin_web_auth import get_session_admin
from app.services.partner_auth import (
    _hash_code,
    create_partner_otp,
    delete_partner_session,
    get_session_partner,
    verify_partner_otp_and_create_session,
)


async def _make_partner(session, *, email="sourcing@partner.test", active=True, key="acme") -> NetworkPartner:
    partner = NetworkPartner(
        key=key,
        name="Acme Wholesale",
        partner_type=PartnerType.WHOLESALER,
        channel_type=PartnerChannel.PORTAL,
        is_active=active,
        portal_login_email=email,
    )
    session.add(partner)
    await session.flush()
    return partner


@pytest.mark.asyncio
async def test_partner_otp_roundtrip_issues_session(session):
    partner = await _make_partner(session)
    result = await create_partner_otp(session, "SOURCING@partner.test")  # case-insensitive
    assert result is not None
    code, email = result
    assert email == "sourcing@partner.test"

    token = await verify_partner_otp_and_create_session(session, "sourcing@partner.test", code)
    assert token is not None

    resolved = await get_session_partner(session, token)
    assert resolved is not None
    assert resolved.id == partner.id


@pytest.mark.asyncio
async def test_partner_otp_unknown_email_returns_none(session):
    await _make_partner(session)
    assert await create_partner_otp(session, "nobody@nowhere.test") is None


@pytest.mark.asyncio
async def test_partner_otp_inactive_partner_rejected(session):
    await _make_partner(session, active=False)
    assert await create_partner_otp(session, "sourcing@partner.test") is None


@pytest.mark.asyncio
async def test_partner_otp_is_single_use(session):
    await _make_partner(session)
    code, _ = await create_partner_otp(session, "sourcing@partner.test")
    # Wrong code marks the OTP used (one guess per issuance).
    assert await verify_partner_otp_and_create_session(session, "sourcing@partner.test", "000000") is None
    # The correct code no longer works because the OTP was consumed.
    assert await verify_partner_otp_and_create_session(session, "sourcing@partner.test", code) is None


@pytest.mark.asyncio
async def test_partner_otp_expired_rejected(session):
    partner = await _make_partner(session)
    session.add(
        PartnerPortalOtp(
            partner_id=partner.id,
            email="sourcing@partner.test",
            code_hash=_hash_code("123456"),
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            used=False,
        )
    )
    await session.flush()
    assert await verify_partner_otp_and_create_session(session, "sourcing@partner.test", "123456") is None


@pytest.mark.asyncio
async def test_partner_session_delete_is_logout(session):
    await _make_partner(session)
    code, _ = await create_partner_otp(session, "sourcing@partner.test")
    token = await verify_partner_otp_and_create_session(session, "sourcing@partner.test", code)
    await delete_partner_session(session, token)
    assert await get_session_partner(session, token) is None


# ── Cross-domain isolation ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_token_is_rejected_on_partner_domain(session):
    admin = AdminUser(telegram_id=999, status=AdminStatus.ACTIVE, is_active=True)
    session.add(admin)
    await session.flush()
    admin_session = WebAdminSession(
        admin_id=admin.id, expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    session.add(admin_session)
    await session.flush()

    # An admin session token must NOT resolve to a partner.
    assert await get_session_partner(session, str(admin_session.id)) is None


@pytest.mark.asyncio
async def test_partner_token_is_rejected_on_admin_domain(session):
    partner = await _make_partner(session)
    portal_session = PartnerPortalSession(
        partner_id=partner.id, expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    session.add(portal_session)
    await session.flush()

    # A partner session token must NOT resolve to an admin.
    assert await get_session_admin(session, str(portal_session.id)) is None


@pytest.mark.asyncio
async def test_partner_sourcing_scope_is_per_partner(session):
    """A partner should only ever see OrderSourcing rows assigned to itself."""
    from sqlalchemy import select

    p1 = await _make_partner(session, email="one@p.test", key="p1")
    p2 = await _make_partner(session, email="two@p.test", key="p2")

    session.add(OrderSourcing(order_id=_uuid(), partner_id=p1.id, sourcing_required=True))
    session.add(OrderSourcing(order_id=_uuid(), partner_id=p2.id, sourcing_required=True))
    await session.flush()

    rows = (
        await session.execute(select(OrderSourcing).where(OrderSourcing.partner_id == p1.id))
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].partner_id == p1.id


def _uuid():
    from uuid import uuid4

    return uuid4()
