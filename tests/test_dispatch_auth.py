"""Unit tests for the dispatch-partner (rider) auth service (SQLite)."""
from __future__ import annotations

from app.models import DispatchPartner
from app.services import dispatch_auth


async def test_dispatch_otp_login_flow(session):
    rider = DispatchPartner(name="Rider One", portal_login_email="rider@peaceway.co", is_active=True)
    session.add(rider)
    await session.flush()

    made = await dispatch_auth.create_dispatch_otp(session, "Rider@Peaceway.co")  # case-insensitive
    assert made is not None
    code, email = made
    assert email == "rider@peaceway.co"

    # wrong code -> no session
    assert await dispatch_auth.verify_dispatch_otp_and_create_session(session, email, "000000") is None

    # a fresh code works, and resolves back to the rider
    code2, _ = await dispatch_auth.create_dispatch_otp(session, email)
    token = await dispatch_auth.verify_dispatch_otp_and_create_session(session, email, code2)
    assert token is not None
    got = await dispatch_auth.get_session_rider(session, token)
    assert got is not None and got.id == rider.id


async def test_dispatch_unknown_email_returns_none(session):
    assert await dispatch_auth.create_dispatch_otp(session, "nobody@nowhere.co") is None


async def test_rider_admin_add_reactivate_toggle(session):
    from app.services import rider_admin

    rider, created = await rider_admin.add_rider(session, name="Ada", email="Ada@x.co", phone="080")
    assert created and rider.is_active and rider.portal_login_email == "ada@x.co"

    # same email -> update, not a duplicate
    again, created2 = await rider_admin.add_rider(session, name="Ada B", email="ada@x.co")
    assert not created2 and again.id == rider.id and again.name == "Ada B"
    assert len(await rider_admin.list_riders(session)) == 1

    assert await rider_admin.set_rider_active(session, rider.id, False) is True
    assert (await rider_admin.get_rider(session, rider.id)).is_active is False
