"""Postgres-only: every SQLAlchemy Enum column must match its real PG enum type.

THE BUG CLASS THIS GUARDS
SQLAlchemy's Enum persists the Python member NAME by default, not its value. When a
model declares lowercase values (FulfillmentStatus.IN_STOCK = "in_stock") but the
migration created the PG type with those lowercase labels, SQLAlchemy sends "IN_STOCK"
and Postgres rejects it:

    InvalidTextRepresentationError: invalid input value for enum
    fulfillment_status: "IN_STOCK"

That shipped once and silently broke every order for days (see
tests/test_sourcing_enum_pg.py). The fix is `values_callable=...`, but nothing stopped
the NEXT enum from repeating it - the SQLite unit suite stores enum columns as plain
VARCHAR with no label constraint, so the mismatch is invisible there.

This test is generic on purpose: it walks EVERY Enum column in the metadata, so an
enum added in future is covered automatically with no maintenance.

`Column.type.enums` is exactly the label list SQLAlchemy reads and writes - member
names by default, or whatever `values_callable` returns - which is what makes this a
true representation check rather than a restatement of the model.
"""
from __future__ import annotations

import asyncio

import pytest
import sqlalchemy as sa

try:
    import asyncpg
except ImportError:  # pragma: no cover
    asyncpg = None

from app.models import Base
from tests.test_gate_phase1_pg import _alembic_upgrade, _base_url, _dsn, _pg_available

BRANCH_DB = "peaceway_enum_drift_test"

pytestmark = pytest.mark.skipif(
    not _pg_available(), reason="Postgres not reachable for enum drift test"
)


def _model_enum_columns() -> dict[str, set[str]]:
    """{pg_type_name: labels SQLAlchemy will actually persist} for every Enum column."""
    out: dict[str, set[str]] = {}
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, sa.Enum) and column.type.name:
                out.setdefault(column.type.name, set()).update(column.type.enums)
    return out


async def _db_enum_labels() -> dict[str, set[str]]:
    admin = await asyncpg.connect(_dsn(_base_url(), "postgres"))
    try:
        await admin.execute(f"DROP DATABASE IF EXISTS {BRANCH_DB} WITH (FORCE)")
        await admin.execute(f"CREATE DATABASE {BRANCH_DB}")
    finally:
        await admin.close()

    _alembic_upgrade(_base_url(), BRANCH_DB, "head")

    con = await asyncpg.connect(_dsn(_base_url(), BRANCH_DB))
    try:
        rows = await con.fetch(
            "SELECT t.typname, e.enumlabel FROM pg_type t "
            "JOIN pg_enum e ON e.enumtypid = t.oid"
        )
    finally:
        await con.close()

    out: dict[str, set[str]] = {}
    for row in rows:
        out.setdefault(row["typname"], set()).add(row["enumlabel"])
    return out


@pytest.fixture(scope="module")
def db_labels() -> dict[str, set[str]]:
    labels = asyncio.run(_db_enum_labels())
    yield labels

    async def _drop():
        admin = await asyncpg.connect(_dsn(_base_url(), "postgres"))
        try:
            await admin.execute(f"DROP DATABASE IF EXISTS {BRANCH_DB} WITH (FORCE)")
        finally:
            await admin.close()
    asyncio.run(_drop())


def test_every_enum_column_matches_its_postgres_type(db_labels):
    """Any drift here means writes raise InvalidTextRepresentation or reads raise LookupError."""
    problems: list[str] = []

    for type_name, model_labels in sorted(_model_enum_columns().items()):
        actual = db_labels.get(type_name)
        if actual is None:
            # Type isn't a native PG enum in this schema (e.g. created as VARCHAR) - the
            # name/value trap does not apply, so there is nothing to compare.
            continue
        if model_labels != actual:
            problems.append(
                f"\n  {type_name}:"
                f"\n    model persists : {sorted(model_labels)}"
                f"\n    postgres has   : {sorted(actual)}"
                f"\n    missing in DB  : {sorted(model_labels - actual) or 'none'}"
                f"\n    missing in code: {sorted(actual - model_labels) or 'none'}"
            )

    assert not problems, (
        "Enum drift between the models and the Postgres types."
        + "".join(problems)
        + "\n\nIf the model uses lowercase values (FOO = \"foo\"), add"
        " values_callable=lambda e: [m.value for m in e] to the SAEnum column so"
        " SQLAlchemy persists values instead of member names. If the DB genuinely"
        " needs a new label, add a migration with ALTER TYPE ... ADD VALUE.\n"
    )


def test_guard_covers_the_enums_that_previously_broke(db_labels):
    """Sanity: the sourcing types are actually in scope (not silently skipped)."""
    checked = _model_enum_columns()
    for type_name in ("fulfillment_status", "partner_type", "order_partner_type"):
        assert type_name in checked, f"{type_name} not discovered by the guard"
        assert type_name in db_labels, f"{type_name} missing from the database"
