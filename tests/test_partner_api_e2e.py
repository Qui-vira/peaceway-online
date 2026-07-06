"""End-to-end HTTP tests for the partner portal through the real ASGI app.

Unlike test_partner_auth.py (service layer), these drive the actual FastAPI app
over HTTP: URL routing, the X-Partner-Session / X-Admin-Session header
dependencies, and the cross-domain wall as a client would hit it. Runs against a
shared in-memory SQLite via a dependency override, so no Postgres/bot is needed.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.main import app
from app.models import Base
from app.models.admin import AdminStatus, AdminUser, WebAdminSession
from app.models.sourcing import NetworkPartner, OrderSourcing, PartnerChannel, PartnerType


@pytest_asyncio.fixture
async def client_and_maker(monkeypatch):
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db():
        async with maker() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db

    # Deterministic OTP so the HTTP verify step knows the code.
    monkeypatch.setattr("app.services.partner_auth.secrets.randbelow", lambda _n: 42)
    # Don't actually send email during request-otp.
    async def _noop_email(email, code):
        return None

    monkeypatch.setattr("app.api.v1.partner.send_partner_otp_email", _noop_email)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, maker

    app.dependency_overrides.clear()
    await engine.dispose()


async def _seed_partner(maker, *, email="sourcing@partner.test", key="acme") -> str:
    async with maker() as s:
        partner = NetworkPartner(
            key=key,
            name="Acme Wholesale",
            partner_type=PartnerType.WHOLESALER,
            channel_type=PartnerChannel.PORTAL,
            is_active=True,
            portal_login_email=email,
        )
        s.add(partner)
        await s.flush()
        pid = str(partner.id)
        await s.commit()
    return pid


@pytest.mark.asyncio
async def test_partner_login_and_read_sourcing_over_http(client_and_maker):
    client, maker = client_and_maker
    partner_id = await _seed_partner(maker)

    # A sourcing row assigned to this partner + one to nobody (must not leak).
    async with maker() as s:
        s.add(OrderSourcing(order_id=uuid4(), partner_id=UUID(partner_id), sourcing_required=True))
        s.add(OrderSourcing(order_id=uuid4(), partner_id=None, sourcing_required=True))
        await s.commit()

    # 1) Request OTP — always 200, code is deterministic ("000042").
    r = await client.post("/api/v1/partner/request-otp", json={"email": "sourcing@partner.test"})
    assert r.status_code == 200

    # 2) Verify OTP → session token.
    r = await client.post(
        "/api/v1/partner/verify-otp", json={"email": "sourcing@partner.test", "code": "000042"}
    )
    assert r.status_code == 200, r.text
    token = r.json()["token"]

    headers = {"X-Partner-Session": token}

    # 3) /partner/me resolves to the right partner.
    r = await client.get("/api/v1/partner/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["id"] == partner_id

    # 4) /partner/sourcing is scoped to this partner only (the unassigned row is hidden).
    r = await client.get("/api/v1/partner/sourcing", headers=headers)
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["order_id"]


@pytest.mark.asyncio
async def test_partner_endpoint_requires_token(client_and_maker):
    client, _ = client_and_maker
    r = await client.get("/api/v1/partner/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_admin_token_rejected_on_partner_endpoint(client_and_maker):
    """An admin session token must NOT authenticate on /partner/*."""
    client, maker = client_and_maker
    async with maker() as s:
        admin = AdminUser(telegram_id=555, status=AdminStatus.ACTIVE, is_active=True)
        s.add(admin)
        await s.flush()
        admin_session = WebAdminSession(
            admin_id=admin.id, expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        s.add(admin_session)
        await s.flush()
        admin_token = str(admin_session.id)
        await s.commit()

    r = await client.get("/api/v1/partner/me", headers={"X-Partner-Session": admin_token})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_partner_token_rejected_on_admin_endpoint(client_and_maker):
    """A partner session token must NOT authenticate on /admin/*."""
    client, maker = client_and_maker
    await _seed_partner(maker)

    await client.post("/api/v1/partner/request-otp", json={"email": "sourcing@partner.test"})
    r = await client.post(
        "/api/v1/partner/verify-otp", json={"email": "sourcing@partner.test", "code": "000042"}
    )
    partner_token = r.json()["token"]

    r = await client.get("/api/v1/admin/me", headers={"X-Admin-Session": partner_token})
    assert r.status_code == 401


async def _admin_token(maker, *, roles=("system_owner",)) -> str:
    """Create an ACTIVE admin with roles + a valid web session; return the token."""
    from app.models.admin import AdminRoleAssignment

    async with maker() as s:
        admin = AdminUser(telegram_id=1001, status=AdminStatus.ACTIVE, is_active=True)
        s.add(admin)
        await s.flush()
        for rk in roles:
            s.add(AdminRoleAssignment(admin_id=admin.id, role_key=rk))
        web_session = WebAdminSession(
            admin_id=admin.id, expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        s.add(web_session)
        await s.flush()
        token = str(web_session.id)
        await s.commit()
    return token


@pytest.mark.asyncio
async def test_staff_can_create_patch_and_list_partners(client_and_maker):
    """Onboarding flow over HTTP: create → list → patch (disable) as a staff owner."""
    client, maker = client_and_maker
    token = await _admin_token(maker)
    headers = {"X-Admin-Session": token}

    # Create
    r = await client.post(
        "/api/v1/admin/network-partners",
        headers=headers,
        json={
            "key": "acme",
            "name": "Acme Wholesale",
            "partner_type": "wholesaler",
            "channel_type": "portal",
            "portal_login_email": "Sourcing@Acme.com",
        },
    )
    assert r.status_code == 201, r.text
    partner_id = r.json()["id"]
    assert r.json()["portal_login_email"] == "sourcing@acme.com"  # normalized

    # List
    r = await client.get("/api/v1/admin/network-partners", headers=headers)
    assert r.status_code == 200
    assert any(p["id"] == partner_id for p in r.json())

    # Patch → disable
    r = await client.patch(
        f"/api/v1/admin/network-partners/{partner_id}", headers=headers, json={"is_active": False}
    )
    assert r.status_code == 200
    assert r.json()["is_active"] is False


@pytest.mark.asyncio
async def test_partner_management_requires_edit_pricing(client_and_maker):
    """A staff member without edit_pricing cannot create partners."""
    client, maker = client_and_maker
    token = await _admin_token(maker, roles=("dispatcher",))  # no edit_pricing
    r = await client.post(
        "/api/v1/admin/network-partners",
        headers={"X-Admin-Session": token},
        json={"key": "x", "name": "X"},
    )
    assert r.status_code == 403
