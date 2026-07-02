"""Web session security: expiry issuance, server-side validation, logout."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.api.deps import get_optional_customer
from app.services.web_customers import (
    SESSION_TTL_DAYS,
    clear_web_session,
    get_or_create_web_customer,
    is_session_expired,
)


async def register(session, phone="+2348011122233"):
    customer, _ = await get_or_create_web_customer(
        session, phone=phone, full_name="Session Test"
    )
    await session.flush()
    return customer


async def test_login_issues_token_with_expiry(session):
    customer = await register(session)
    assert customer.web_session_token and len(customer.web_session_token) >= 43
    assert customer.web_session_expires_at is not None
    ttl = customer.web_session_expires_at - datetime.now(timezone.utc).replace(tzinfo=customer.web_session_expires_at.tzinfo)
    assert timedelta(days=SESSION_TTL_DAYS - 1) < ttl <= timedelta(days=SESSION_TTL_DAYS)


async def test_relogin_rotates_token(session):
    customer = await register(session)
    first = customer.web_session_token
    await get_or_create_web_customer(session, phone=customer.phone, full_name="Session Test")
    assert customer.web_session_token != first


async def test_valid_session_resolves_customer(session):
    customer = await register(session)
    found = await get_optional_customer(db=session, pw_session=customer.web_session_token)
    assert found is not None and found.id == customer.id


async def test_expired_session_rejected(session):
    customer = await register(session)
    customer.web_session_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    await session.flush()
    assert await get_optional_customer(db=session, pw_session=customer.web_session_token) is None


async def test_legacy_session_without_expiry_rejected(session):
    customer = await register(session)
    customer.web_session_expires_at = None  # token minted before the expiry column
    await session.flush()
    assert is_session_expired(customer)
    assert await get_optional_customer(db=session, pw_session=customer.web_session_token) is None


async def test_logout_clears_session(session):
    customer = await register(session)
    token = customer.web_session_token
    clear_web_session(customer)
    await session.flush()
    assert customer.web_session_token is None
    assert customer.web_session_expires_at is None
    assert await get_optional_customer(db=session, pw_session=token) is None


async def test_missing_cookie_is_anonymous(session):
    assert await get_optional_customer(db=session, pw_session=None) is None
