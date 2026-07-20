"""Phase-1 access-control gates — Postgres-backed acceptance tests.

Triggers / REVOKE / views are Postgres features and CANNOT run on the SQLite unit
suite, so this module builds a throwaway `peaceway_gate_test` database, applies the
real migration chain (`alembic upgrade head`), seeds, and asserts each gate. It is
skipped automatically when Postgres is unreachable, so the SQLite suite is unaffected.
"""
from __future__ import annotations

import asyncio
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

try:
    import asyncpg
except ImportError:  # pragma: no cover
    asyncpg = None

REPO_ROOT = Path(__file__).resolve().parents[1]
BRANCH_DB = "peaceway_gate_test"


def _base_url() -> str | None:
    env = os.environ.get("DATABASE_URL")
    if env:
        return env
    envfile = REPO_ROOT / ".env"
    if envfile.exists():
        for ln in envfile.read_text().splitlines():
            if ln.startswith("DATABASE_URL="):
                return ln.split("=", 1)[1].strip()
    return None


def _dsn(url: str, dbname: str) -> str:
    raw = re.sub(r"\+asyncpg", "", url)
    return re.sub(r"/[^/?]+(\?|$)", f"/{dbname}\\1", raw)


def _sa_url(url: str, dbname: str) -> str:
    if "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return re.sub(r"/[^/?]+(\?|$)", f"/{dbname}\\1", url)


def _role_dsn(dbname: str, user: str, pw: str) -> str:
    """asyncpg DSN for the base host, swapping in a different user/password/db."""
    raw = re.sub(r"\+asyncpg", "", _base_url())
    raw = re.sub(r"://[^@/]+@", f"://{user}:{pw}@", raw)
    return re.sub(r"/[^/?]+(\?|$)", f"/{dbname}\\1", raw)


def _alembic_upgrade(url: str, dbname: str, rev: str = "head") -> None:
    env = dict(os.environ, DATABASE_URL=_sa_url(url, dbname))
    proc = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", rev],
        cwd=str(REPO_ROOT), env=env, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"alembic upgrade {rev} failed:\n{proc.stdout}\n{proc.stderr}")


def _pg_available() -> bool:
    if asyncpg is None:
        return False
    url = _base_url()
    if not url or not url.startswith(("postgresql", "postgres")):
        return False

    async def _check() -> bool:
        try:
            con = await asyncpg.connect(_dsn(url, "postgres"))
            await con.close()
            return True
        except Exception:
            return False

    try:
        return asyncio.run(_check())
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _pg_available(), reason="Postgres not reachable for gate tests")


async def _build_and_seed(url: str) -> dict:
    admin = await asyncpg.connect(_dsn(url, "postgres"))
    try:
        await admin.execute(f"DROP DATABASE IF EXISTS {BRANCH_DB} WITH (FORCE)")
        await admin.execute(f"CREATE DATABASE {BRANCH_DB}")
    finally:
        await admin.close()

    # Apply the REAL migration chain against the throwaway DB.
    _alembic_upgrade(url, BRANCH_DB, "head")

    con = await asyncpg.connect(_dsn(url, BRANCH_DB))
    try:
        # Gate 1 is now activated by migration c5e2b8a4f7d1 (part of `upgrade head`),
        # so it no longer needs to be applied here.
        ids = {k: uuid.uuid4() for k in (
            "cust", "ph", "sales", "prod", "prod_otc",
            "t1", "t1c", "t1d", "t1b", "t1f", "t1g", "t1h",
            "append", "amt", "hf_pom", "hf_otc",
        )}
        await con.execute(
            "INSERT INTO customers(id, full_name, email_verified, email_opt_in) VALUES($1,'Test',false,true)",
            ids["cust"])
        for k, name in (("ph", "Pharm"), ("sales", "Sales")):
            await con.execute(
                "INSERT INTO admin_users(id, full_name, is_active, status) VALUES($1,$2,true,'ACTIVE')",
                ids[k], name)
        await con.execute("INSERT INTO admin_role_assignments(id, admin_id, role_key) VALUES($1,$2,'lead_pharmacist')", uuid.uuid4(), ids["ph"])
        await con.execute("INSERT INTO admin_role_assignments(id, admin_id, role_key) VALUES($1,$2,'sales_support')", uuid.uuid4(), ids["sales"])
        await con.execute(
            "INSERT INTO products(id, name, generic_name, requires_prescription, controlled_substance, requires_review, is_listed) "
            "VALUES($1,'Amoxicillin','Amoxicillin',true,false,false,true)", ids["prod"])
        await con.execute(
            "INSERT INTO products(id, name, generic_name, requires_prescription, controlled_substance, requires_review, is_listed) "
            "VALUES($1,'Vitamin C','Ascorbic',false,false,false,true)", ids["prod_otc"])

        async def mk(oid, code):
            await con.execute(
                "INSERT INTO orders(id, code, customer_id, status, rx_status, delivery_status, "
                "subtotal, delivery_fee, payment_fee, offramp_fee, handling_fee, total) "
                "VALUES($1,$2,$3,'PROCESSING','PHARMACIST_REVIEW','NONE',5000,0,0,0,0,5000)",
                oid, code, ids["cust"])

        async def line(oid, rx, pid=None):
            await con.execute(
                "INSERT INTO order_items(id, order_id, product_id, product_name, quantity, unit_price, line_total, requires_prescription) "
                "VALUES($1,$2,$3,'x',1,5000,5000,$4)", uuid.uuid4(), oid, pid or ids["prod"], rx)

        for k in ("t1", "t1c", "t1d", "t1b", "t1f", "t1g", "append", "hf_pom"):
            await mk(ids[k], f"PW-{k.upper()}")
            await line(ids[k], True)
        await mk(ids["amt"], "PW-AMT"); await line(ids["amt"], False, ids["prod_otc"])
        await mk(ids["hf_otc"], "PW-HFOTC"); await line(ids["hf_otc"], False, ids["prod_otc"])
        await mk(ids["t1h"], "PW-T1H")
        await line(ids["t1h"], True)
        await line(ids["t1h"], False, ids["prod_otc"])
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


async def _approve(con, order_id, pharm_id):
    await con.execute(
        "INSERT INTO prescription_verifications(order_id, pharmacist_user_id, decision, verified_at) "
        "VALUES($1,$2,'APPROVED', now())", order_id, pharm_id)


async def test_gate1_pom_dispatch_without_verification_rejected(seeded):
    con = await _conn()
    try:
        with pytest.raises(asyncpg.exceptions.CheckViolationError):
            await con.execute("UPDATE orders SET status='DISPATCHED' WHERE id=$1", seeded["t1"])
    finally:
        await con.close()


async def test_gate1_pom_pickup_without_verification_rejected(seeded):
    con = await _conn()
    try:
        with pytest.raises(asyncpg.exceptions.CheckViolationError):
            await con.execute("UPDATE orders SET delivery_status='PICKED_UP' WHERE id=$1", seeded["t1c"])
    finally:
        await con.close()


async def test_gate1_verification_by_non_pharmacist_rejected(seeded):
    con = await _conn()
    try:
        await _approve(con, seeded["t1d"], seeded["sales"])
        with pytest.raises(asyncpg.exceptions.CheckViolationError):
            await con.execute("UPDATE orders SET status='DISPATCHED' WHERE id=$1", seeded["t1d"])
    finally:
        await con.close()


async def test_gate1_valid_verification_allows_dispatch(seeded):
    con = await _conn()
    try:
        await _approve(con, seeded["t1b"], seeded["ph"])
        await con.execute("UPDATE orders SET status='DISPATCHED' WHERE id=$1", seeded["t1b"])
        assert await con.fetchval("SELECT status FROM orders WHERE id=$1", seeded["t1b"]) == "DISPATCHED"
    finally:
        await con.close()


async def test_linebinding_mutate_after_verify_rejected(seeded):
    con = await _conn()
    try:
        await _approve(con, seeded["t1f"], seeded["ph"])
        await con.execute("UPDATE order_items SET quantity=2 WHERE order_id=$1", seeded["t1f"])
        with pytest.raises(asyncpg.exceptions.CheckViolationError):
            await con.execute("UPDATE orders SET status='DISPATCHED' WHERE id=$1", seeded["t1f"])
    finally:
        await con.close()


async def test_linebinding_reverify_after_mutate_allows_dispatch(seeded):
    con = await _conn()
    try:
        await _approve(con, seeded["t1g"], seeded["ph"])
        await con.execute("UPDATE order_items SET quantity=3 WHERE order_id=$1", seeded["t1g"])
        await _approve(con, seeded["t1g"], seeded["ph"])  # re-verify the new lines
        await con.execute("UPDATE orders SET status='DISPATCHED' WHERE id=$1", seeded["t1g"])
        assert await con.fetchval("SELECT status FROM orders WHERE id=$1", seeded["t1g"]) == "DISPATCHED"
    finally:
        await con.close()


async def test_linebinding_remove_pom_line_allows_otc_dispatch(seeded):
    con = await _conn()
    try:
        await _approve(con, seeded["t1h"], seeded["ph"])
        await con.execute("DELETE FROM order_items WHERE order_id=$1 AND requires_prescription=true", seeded["t1h"])
        # supersede row IS written (trigger fired) but Gate 1 exits early on has_pom=false
        assert await con.fetchval(
            "SELECT count(*) FROM prescription_verifications WHERE order_id=$1 AND decision='SUPERSEDED'",
            seeded["t1h"]) >= 1
        await con.execute("UPDATE orders SET status='DISPATCHED' WHERE id=$1", seeded["t1h"])
        assert await con.fetchval("SELECT status FROM orders WHERE id=$1", seeded["t1h"]) == "DISPATCHED"
    finally:
        await con.close()


async def test_dispensing_records_append_only(seeded):
    con = await _conn()
    try:
        rid = uuid.uuid4()
        await con.execute("INSERT INTO dispensing_records(id, order_id, pharmacist_user_id) VALUES($1,$2,$3)",
                          rid, seeded["append"], seeded["ph"])
        with pytest.raises(asyncpg.exceptions.RestrictViolationError):
            await con.execute("UPDATE dispensing_records SET payload='{}'::jsonb WHERE id=$1", rid)
        with pytest.raises(asyncpg.exceptions.RestrictViolationError):
            await con.execute("DELETE FROM dispensing_records WHERE id=$1", rid)
    finally:
        await con.close()


async def test_audit_log_append_only_including_delete(seeded):
    con = await _conn()
    try:
        aid = uuid.uuid4()
        await con.execute("INSERT INTO audit_logs(id, action) VALUES($1,'t')", aid)
        with pytest.raises(asyncpg.exceptions.RestrictViolationError):
            await con.execute("DELETE FROM audit_logs WHERE id=$1", aid)
    finally:
        await con.close()


async def test_dispatch_view_hides_product_fields(seeded):
    con = await _conn()
    try:
        cols = {r["column_name"] for r in await con.fetch(
            "SELECT column_name FROM information_schema.columns WHERE table_name='dispatch_delivery_masked'")}
        assert not (cols & {"product_name", "product_id", "line_total", "unit_price", "quantity"})
        assert {"recipient_name", "address", "phone", "amount_to_collect", "handling_flag"} <= cols
    finally:
        await con.close()


async def test_amount_to_collect_nets_approved_payments_floored(seeded):
    con = await _conn()
    try:
        await con.execute("INSERT INTO payments(id, order_id, method, amount, status) VALUES($1,$2,'BANK_TRANSFER',2000,'APPROVED')",
                          uuid.uuid4(), seeded["amt"])
        assert await con.fetchval("SELECT amount_to_collect FROM dispatch_delivery_masked WHERE order_id=$1", seeded["amt"]) == 3000
        await con.execute("INSERT INTO payments(id, order_id, method, amount, status) VALUES($1,$2,'BANK_TRANSFER',4000,'APPROVED')",
                          uuid.uuid4(), seeded["amt"])
        assert await con.fetchval("SELECT amount_to_collect FROM dispatch_delivery_masked WHERE order_id=$1", seeded["amt"]) == 0
    finally:
        await con.close()


async def test_handling_flag_stamped_and_frozen_at_dispatch(seeded):
    con = await _conn()
    try:
        assert await con.fetchval("SELECT handling_flag FROM orders WHERE id=$1", seeded["hf_pom"]) == "RX_ID_CHECK"
        assert await con.fetchval("SELECT handling_flag FROM orders WHERE id=$1", seeded["hf_otc"]) == "STANDARD"
        # freeze: dispatch then remove the POM line — flag must not change
        await _approve(con, seeded["hf_pom"], seeded["ph"])
        await con.execute("UPDATE orders SET status='DISPATCHED' WHERE id=$1", seeded["hf_pom"])
        await con.execute("DELETE FROM order_items WHERE order_id=$1 AND requires_prescription=true", seeded["hf_pom"])
        assert await con.fetchval("SELECT handling_flag FROM orders WHERE id=$1", seeded["hf_pom"]) == "RX_ID_CHECK"
    finally:
        await con.close()


async def test_set_session_actor_stamps_transaction_local_guc(seeded):
    """set_session_actor writes app.current_actor/type for the current transaction and
    it clears at transaction end (so RLS in 2b default-denies once the actor is gone)."""
    from sqlalchemy import text as sa_text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.core.db import set_session_actor

    eng = create_async_engine(_sa_url(_base_url(), BRANCH_DB))
    try:
        async with async_sessionmaker(eng)() as s:
            aid = uuid.uuid4()
            await set_session_actor(s, aid, "admin")
            row = (await s.execute(sa_text(
                "SELECT current_setting('app.current_actor', true) AS actor_val, "
                "current_setting('app.current_actor_type', true) AS actor_kind"
            ))).first()
            assert row.actor_val == str(aid) and row.actor_kind == "admin"
            await s.rollback()  # transaction-local -> value does not survive
            after = (await s.execute(sa_text(
                "SELECT current_setting('app.current_actor', true) AS a"
            ))).scalar()
            assert after != str(aid)
    finally:
        await eng.dispose()


async def test_app_role_has_crud_but_not_ddl_or_append_only_mutation(seeded):
    """The restricted peaceway_app role (migration d7a3c1e9f2b4): full CRUD on normal
    tables + sequences + the masked view, but no DDL and no UPDATE/DELETE on append-only
    tables. Proves the runtime role is safe to connect as (RLS will then apply)."""
    su = await _conn()
    try:
        await su.execute("ALTER ROLE peaceway_app PASSWORD 'testpw_ci'")
        cid, alid = uuid.uuid4(), uuid.uuid4()
        await su.execute("INSERT INTO customers(id, full_name, email_verified, email_opt_in) VALUES($1,'RoleTest',false,true)", cid)
        await su.execute("INSERT INTO audit_logs(id, action) VALUES($1,'seed')", alid)
    finally:
        await su.close()

    app = await asyncpg.connect(_role_dsn(BRANCH_DB, "peaceway_app", "testpw_ci"))
    try:
        assert await app.fetchval("SELECT current_setting('is_superuser')") == "off"

        # CRUD on a normal table
        assert await app.fetchval("SELECT count(*) FROM customers") >= 1
        await app.execute("UPDATE customers SET full_name='RoleTest2' WHERE id=$1", cid)
        tmp = uuid.uuid4()
        await app.execute("INSERT INTO customers(id, full_name, email_verified, email_opt_in) VALUES($1,'x',false,true)", tmp)
        await app.execute("DELETE FROM customers WHERE id=$1", tmp)

        # sequence usage + masked view read
        await app.fetchval("SELECT nextval('fee_settings_id_seq')")
        await app.fetch("SELECT * FROM dispatch_delivery_masked LIMIT 1")

        # REVOKE bites: no UPDATE/DELETE on append-only tables
        with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError):
            await app.execute("UPDATE audit_logs SET action='x' WHERE id=$1", alid)
        with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError):
            await app.execute("DELETE FROM audit_logs WHERE id=$1", alid)

        # no DDL rights (CREATE not granted on the schema)
        with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError):
            await app.execute("CREATE TABLE _nope (id int)")
    finally:
        await app.close()


async def test_gate1_backfill_unblocks_inflight_approved_orders():
    """Migration c5e2b8a4f7d1 backfills verification rows for in-flight approved POM
    orders so activating Gate 1 doesn't freeze legitimate dispatch. Seed BEFORE the
    backfill migration (at the prior revision), then upgrade head and assert."""
    url = _base_url()
    db = "peaceway_gate_backfill"
    admin = await asyncpg.connect(_dsn(url, "postgres"))
    try:
        await admin.execute(f"DROP DATABASE IF EXISTS {db} WITH (FORCE)")
        await admin.execute(f"CREATE DATABASE {db}")
    finally:
        await admin.close()
    try:
        _alembic_upgrade(url, db, "b3f1a2c9d7e4")  # pre-Gate1, pre-backfill
        cust, ph, prod = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        approved, unapproved = uuid.uuid4(), uuid.uuid4()
        con = await asyncpg.connect(_dsn(url, db))
        try:
            await con.execute("INSERT INTO customers(id, full_name, email_verified, email_opt_in) VALUES($1,'C',false,true)", cust)
            await con.execute("INSERT INTO admin_users(id, full_name, is_active, status) VALUES($1,'Ph',true,'ACTIVE')", ph)
            await con.execute("INSERT INTO admin_role_assignments(id, admin_id, role_key) VALUES($1,$2,'lead_pharmacist')", uuid.uuid4(), ph)
            await con.execute("INSERT INTO products(id,name,generic_name,requires_prescription,controlled_substance,requires_review,is_listed) VALUES($1,'Amox','Amox',true,false,false,true)", prod)

            async def order(oid, code, rx):
                await con.execute(
                    "INSERT INTO orders(id,code,customer_id,status,rx_status,delivery_status,"
                    "subtotal,delivery_fee,payment_fee,offramp_fee,handling_fee,total) "
                    "VALUES($1,$2,$3,'AWAITING_PAYMENT',$4,'NONE',5000,0,0,0,0,5000)", oid, code, cust, rx)
                await con.execute("INSERT INTO order_items(id,order_id,product_id,product_name,quantity,unit_price,line_total,requires_prescription) VALUES($1,$2,$3,'x',1,5000,5000,true)", uuid.uuid4(), oid, prod)

            await order(approved, "PW-BF-OK", "APPROVED_FOR_PAYMENT")   # eligible for backfill
            await order(unapproved, "PW-BF-NO", "PHARMACIST_REVIEW")     # NOT approved -> not backfilled
        finally:
            await con.close()

        _alembic_upgrade(url, db, "head")  # runs backfill + activates Gate 1

        con = await asyncpg.connect(_dsn(url, db))
        try:
            # approved order: backfill created an APPROVED verification by the pharmacist
            row = await con.fetchrow("SELECT pharmacist_user_id, decision FROM prescription_verifications WHERE order_id=$1", approved)
            assert row is not None and row["decision"] == "APPROVED" and row["pharmacist_user_id"] == ph
            # ...and it can dispatch under the now-active gate
            await con.execute("UPDATE orders SET status='DISPATCHED' WHERE id=$1", approved)
            assert await con.fetchval("SELECT status FROM orders WHERE id=$1", approved) == "DISPATCHED"

            # unapproved order: NOT backfilled, and Gate 1 blocks its dispatch
            assert await con.fetchval("SELECT count(*) FROM prescription_verifications WHERE order_id=$1", unapproved) == 0
            with pytest.raises(asyncpg.exceptions.CheckViolationError):
                await con.execute("UPDATE orders SET status='DISPATCHED' WHERE id=$1", unapproved)
        finally:
            await con.close()
    finally:
        admin = await asyncpg.connect(_dsn(url, "postgres"))
        try:
            await admin.execute(f"DROP DATABASE IF EXISTS {db} WITH (FORCE)")
        finally:
            await admin.close()
