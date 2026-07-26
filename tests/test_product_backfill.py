"""Track 1 — descriptive-field backfill.

The rule under test throughout: nothing is inferred. Pack size is never parsed out
of strength, brand is never guessed from the product name. Staff type every value.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PriceHistory, Product, ProductPricing
from app.services.products_admin import (
    DESCRIPTIVE_FIELDS,
    REQUIRED_BACKFILL_FIELDS,
    apply_change,
    backfill_stats,
    missing_backfill_fields,
    next_backfill_product,
)


def _hand_created(**over) -> Product:
    """A product shaped like the 41 real ones: pack size stranded in `strength`."""
    defaults = dict(
        name="Chemiron Blood Tonic",
        generic_name="Chemiron Blood Tonic",
        brand_name=None,
        manufacturer=None,
        dosage_form=None,
        strength="1000ml",
        pack_size=None,
        is_listed=True,
        requires_prescription=False,
        requires_review=False,
    )
    defaults.update(over)
    return Product(**defaults)


def _complete(**over) -> Product:
    fields = dict(
        name="Afrab Loratadine Syrup",
        brand_name="Afrab",
        manufacturer="Afrab-Chem Limited",
        dosage_form="Syrup",
        strength="5 mg/5 mL",
        pack_size="100 mL",
    )
    fields.update(over)
    return _hand_created(**fields)


# ── Which products need attention ─────────────────────────────────────────────
def test_missing_fields_detected_on_hand_created_product():
    assert set(missing_backfill_fields(_hand_created())) == set(REQUIRED_BACKFILL_FIELDS)


def test_complete_product_reports_nothing_missing():
    assert missing_backfill_fields(_complete()) == []


def test_strength_is_not_required():
    """Afrabvite Multivitamin Drops genuinely has no strength — it must not be stuck
    in the queue forever."""
    p = _complete(strength=None)
    assert "strength" not in missing_backfill_fields(p)
    assert missing_backfill_fields(p) == []


def test_blank_string_counts_as_missing():
    assert "brand_name" in missing_backfill_fields(_complete(brand_name="   "))


# ── Nothing is inferred ───────────────────────────────────────────────────────
def test_pack_size_is_not_parsed_out_of_strength():
    """The whole point of Track 1. '1000ml' sitting in strength must stay there until
    a human moves it; the system never rewrites it."""
    p = _hand_created()
    assert p.pack_size is None
    assert p.strength == "1000ml"
    assert "pack_size" in missing_backfill_fields(p)


def test_brand_is_not_inferred_from_name():
    p = _hand_created(name="Chemiron Blood Tonic")
    assert p.brand_name is None
    assert "brand_name" in missing_backfill_fields(p)


# ── Applying staff edits ──────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_apply_change_sets_descriptive_field(db_session: AsyncSession):
    p = _hand_created()
    db_session.add(p)
    await db_session.flush()

    summary = await apply_change(db_session, p, "pack_size", "1000 mL", 42)
    assert p.pack_size == "1000 mL"
    assert "Pack size" in summary


@pytest.mark.asyncio
async def test_moving_pack_size_leaves_strength_for_staff(db_session: AsyncSession):
    """Setting pack_size must not silently clear strength — that is a second,
    explicit staff action."""
    p = _hand_created()
    db_session.add(p)
    await db_session.flush()

    await apply_change(db_session, p, "pack_size", "1000 mL", 42)
    assert p.strength == "1000ml"

    await apply_change(db_session, p, "strength", "-", 42)
    assert p.strength is None
    assert p.pack_size == "1000 mL"


@pytest.mark.asyncio
async def test_dash_clears_a_field(db_session: AsyncSession):
    p = _complete()
    db_session.add(p)
    await db_session.flush()
    await apply_change(db_session, p, "brand_name", "-", 42)
    assert p.brand_name is None


@pytest.mark.asyncio
async def test_whitespace_is_collapsed_not_interpreted(db_session: AsyncSession):
    p = _hand_created()
    db_session.add(p)
    await db_session.flush()
    await apply_change(db_session, p, "brand_name", "  Chemiron   Blood  ", 42)
    assert p.brand_name == "Chemiron Blood"


@pytest.mark.asyncio
async def test_overlong_value_rejected(db_session: AsyncSession):
    p = _hand_created()
    db_session.add(p)
    await db_session.flush()
    with pytest.raises(ValueError):
        await apply_change(db_session, p, "dosage_form", "x" * 101, 42)


@pytest.mark.asyncio
async def test_every_edit_is_audited(db_session: AsyncSession):
    p = _hand_created()
    db_session.add(p)
    await db_session.flush()
    await apply_change(db_session, p, "manufacturer", "Emzor", 42, reason="staff backfill")
    await db_session.flush()

    rows = (
        await db_session.execute(select(PriceHistory).where(PriceHistory.product_id == p.id))
    ).scalars().all()
    assert [r.field for r in rows] == ["manufacturer"]
    assert rows[0].new_value == "Emzor"
    assert rows[0].changed_by == 42


@pytest.mark.asyncio
async def test_unknown_field_still_rejected(db_session: AsyncSession):
    p = _hand_created()
    db_session.add(p)
    await db_session.flush()
    with pytest.raises(ValueError, match="Unknown field"):
        await apply_change(db_session, p, "nafdac_number", "A4-1234", 42)


def test_descriptive_fields_cover_required_set():
    assert set(REQUIRED_BACKFILL_FIELDS) <= set(DESCRIPTIVE_FIELDS)


# ── Queue + progress ──────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_stats_count_pending_and_complete(db_session: AsyncSession):
    db_session.add_all([_hand_created(), _hand_created(name="Astymin", strength="200ml"), _complete()])
    await db_session.flush()

    stats = await backfill_stats(db_session, listed_only=True)
    assert stats == {"total": 3, "pending": 2, "complete": 1}


@pytest.mark.asyncio
async def test_queue_returns_incomplete_products_only(db_session: AsyncSession):
    db_session.add_all([_complete(), _hand_created()])
    await db_session.flush()

    p = await next_backfill_product(db_session, listed_only=True)
    assert p is not None and p.name == "Chemiron Blood Tonic"


@pytest.mark.asyncio
async def test_queue_respects_skips(db_session: AsyncSession):
    a = _hand_created(name="Astymin", strength="200ml")
    db_session.add(a)
    await db_session.flush()

    assert await next_backfill_product(db_session, listed_only=True) is not None
    assert await next_backfill_product(db_session, listed_only=True, skip_ids={a.id}) is None


@pytest.mark.asyncio
async def test_queue_prefers_listed_but_can_widen(db_session: AsyncSession):
    unlisted = _hand_created(name="Zinc Unlisted", is_listed=False)
    db_session.add(unlisted)
    await db_session.flush()

    assert await next_backfill_product(db_session, listed_only=True) is None
    assert await next_backfill_product(db_session, listed_only=False) is not None


@pytest.mark.asyncio
async def test_completing_a_product_removes_it_from_the_queue(db_session: AsyncSession):
    p = _hand_created()
    p.pricing = ProductPricing(selling_price=Decimal("600"), stock_qty=4, is_in_stock=True)
    db_session.add(p)
    await db_session.flush()

    for field, value in [
        ("brand_name", "Chemiron"),
        ("manufacturer", "Emzor Pharmaceutical Industries Limited"),
        ("dosage_form", "Syrup"),
        ("pack_size", "1000 mL"),
    ]:
        await apply_change(db_session, p, field, value, 42)
    await db_session.flush()

    assert missing_backfill_fields(p) == []
    assert (await backfill_stats(db_session, listed_only=True))["pending"] == 0
