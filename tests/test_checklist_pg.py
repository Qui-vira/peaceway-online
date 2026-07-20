"""Postgres-only: the checklist_instances append-only TRIGGER.

The trg_checklist_append_only trigger (deny_mutation()) is a Postgres feature and
cannot run on the SQLite unit suite, so this builds a throwaway DB, applies the real
migration chain, seeds one instance, and asserts UPDATE and DELETE are rejected.
Auto-skips when Postgres is unreachable. Reuses the harness helpers from the Gate
Phase-1 module so there is one DB-build implementation.
"""
from __future__ import annotations

import asyncio
import uuid

import pytest

try:
    import asyncpg
except ImportError:  # pragma: no cover
    asyncpg = None

from tests.test_gate_phase1_pg import (
    _alembic_upgrade,
    _base_url,
    _dsn,
    _pg_available,
)

BRANCH_DB = "peaceway_checklist_test"

pytestmark = pytest.mark.skipif(
    not _pg_available(), reason="Postgres not reachable for checklist trigger test"
)


async def _build_and_seed(url: str) -> dict:
    admin = await asyncpg.connect(_dsn(url, "postgres"))
    try:
        await admin.execute(f"DROP DATABASE IF EXISTS {BRANCH_DB} WITH (FORCE)")
        await admin.execute(f"CREATE DATABASE {BRANCH_DB}")
    finally:
        await admin.close()

    _alembic_upgrade(url, BRANCH_DB, "head")

    ids = {"admin": uuid.uuid4(), "template": uuid.uuid4(), "instance": uuid.uuid4()}
    con = await asyncpg.connect(_dsn(url, BRANCH_DB))
    try:
        await con.execute(
            "INSERT INTO admin_users(id, full_name, is_active, status) VALUES($1,'Ade',true,'ACTIVE')",
            ids["admin"])
        await con.execute(
            "INSERT INTO checklist_templates(id, role_key, item_text, cadence, active, sort_order) "
            "VALUES($1,'dispatcher','Do it','daily',true,0)", ids["template"])
        await con.execute(
            "INSERT INTO checklist_instances(id, template_id, assigned_user_id, due_date, status) "
            "VALUES($1,$2,$3,CURRENT_DATE,'pending')",
            ids["instance"], ids["template"], ids["admin"])
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


async def _conn():
    return await asyncpg.connect(_dsn(_base_url(), BRANCH_DB))


async def test_update_on_instance_rejected(seeded):
    con = await _conn()
    try:
        with pytest.raises(asyncpg.exceptions.RestrictViolationError):
            await con.execute(
                "UPDATE checklist_instances SET status='done' WHERE id=$1", seeded["instance"])
    finally:
        await con.close()


async def test_delete_on_instance_rejected(seeded):
    con = await _conn()
    try:
        with pytest.raises(asyncpg.exceptions.RestrictViolationError):
            await con.execute(
                "DELETE FROM checklist_instances WHERE id=$1", seeded["instance"])
    finally:
        await con.close()
