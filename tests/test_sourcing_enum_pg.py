"""Postgres-only: sourcing enums must round-trip through real PG enum types.

REGRESSION GUARD. SQLAlchemy's Enum persists the Python member NAME by default
(`IN_STOCK`), but the `fulfillment_status` / `partner_type` / `partner_channel` PG
types were created with lowercase VALUES (`in_stock`). Every other enum in the
codebase happens to have name == value (OrderStatus.NEW = "NEW"), so only
app/models/sourcing.py is affected — and the mismatch is INVISIBLE on the SQLite
unit suite, where enum columns are plain VARCHAR with no label constraint.

The result in production: every "Confirm Order" tap raised
    InvalidTextRepresentationError: invalid input value for enum
    fulfillment_status: "IN_STOCK"
inside create_order(), which rolled the transaction back and left the callback
unanswered — a silently dead button. These tests fail without `values_callable`.
"""
from __future__ import annotations

import asyncio
import uuid

import pytest

try:
    import asyncpg
except ImportError:  # pragma: no cover
    asyncpg = None

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import NetworkPartner, OrderSourcing
from app.models.sourcing import FulfillmentStatus, PartnerChannel, PartnerType
from tests.test_gate_phase1_pg import _alembic_upgrade, _base_url, _dsn, _pg_available, _sa_url

BRANCH_DB = "peaceway_sourcing_enum_test"

pytestmark = pytest.mark.skipif(
    not _pg_available(), reason="Postgres not reachable for sourcing enum test"
)


async def _build_and_seed(url: str) -> dict:
    admin = await asyncpg.connect(_dsn(url, "postgres"))
    try:
        await admin.execute(f"DROP DATABASE IF EXISTS {BRANCH_DB} WITH (FORCE)")
        await admin.execute(f"CREATE DATABASE {BRANCH_DB}")
    finally:
        await admin.close()

    _alembic_upgrade(url, BRANCH_DB, "head")

    ids = {"customer": uuid.uuid4(), "order": uuid.uuid4()}
    con = await asyncpg.connect(_dsn(url, BRANCH_DB))
    try:
        await con.execute(
            "INSERT INTO customers(id, full_name, email_verified, email_opt_in) "
            "VALUES($1,'Test',false,true)", ids["customer"])
        await con.execute(
            "INSERT INTO orders(id, code, customer_id, status, rx_status, delivery_status, "
            "subtotal, delivery_fee, payment_fee, offramp_fee, handling_fee, total) "
            "VALUES($1,'PW-ENUM',$2,'PROCESSING','NOT_REQUIRED','NONE',350,700,5,0,0,1055)",
            ids["order"], ids["customer"])
    finally:
        await con.close()
    return ids


@pytest.fixture(scope="module")
def seeded() -> dict:
    url = _base_url()
    ids = asyncio.run(_build_and_seed(url))
    yield ids

    async def _drop():
        admin = await asyncpg.connect(_dsn(url, "postgres"))
        try:
            await admin.execute(f"DROP DATABASE IF EXISTS {BRANCH_DB} WITH (FORCE)")
        finally:
            await admin.close()
    asyncio.run(_drop())


async def _session():
    engine = create_async_engine(_sa_url(_base_url(), BRANCH_DB))
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, maker


async def test_order_sourcing_insert_round_trips(seeded):
    """The exact write that broke every Confirm Order tap in production."""
    engine, maker = await _session()
    try:
        async with maker() as session:
            session.add(
                OrderSourcing(
                    order_id=seeded["order"],
                    fulfillment_status=FulfillmentStatus.IN_STOCK,
                    sourcing_required=False,
                )
            )
            await session.commit()  # raised InvalidTextRepresentationError before the fix

        async with maker() as session:
            row = (
                await session.execute(
                    select(OrderSourcing).where(OrderSourcing.order_id == seeded["order"])
                )
            ).scalar_one()
            # Reads must map the lowercase DB label back to the enum member.
            assert row.fulfillment_status is FulfillmentStatus.IN_STOCK
    finally:
        await engine.dispose()


async def test_network_partner_enums_round_trip(seeded):
    """partner_type / partner_channel have the same name-vs-value shape."""
    engine, maker = await _session()
    try:
        async with maker() as session:
            session.add(
                NetworkPartner(
                    key=f"p-{uuid.uuid4().hex[:8]}",
                    name="Test Wholesaler",
                    partner_type=PartnerType.WHOLESALER,
                    channel_type=PartnerChannel.PORTAL,
                )
            )
            await session.commit()

        async with maker() as session:
            row = (
                await session.execute(
                    select(NetworkPartner).where(NetworkPartner.name == "Test Wholesaler")
                )
            ).scalar_one()
            assert row.partner_type is PartnerType.WHOLESALER
            assert row.channel_type is PartnerChannel.PORTAL
    finally:
        await engine.dispose()
