"""Unit tests for the orientation rotation + swap/example flow (SQLite)."""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select

from app.models import AdminUser, AuditLog, Meeting, OrientationTopic
from app.models.admin import AdminStatus
from app.services import orientation

ANCHOR = orientation.ANCHOR_MONDAY  # Mon 2026-07-27


async def _topics(db_session, n=12, inactive: set[int] = frozenset()):
    for i in range(n):
        db_session.add(
            OrientationTopic(sort_order=i, topic_text=f"Topic {i}", active=i not in inactive)
        )
    await db_session.flush()


async def _admin(db_session, tid=1, name="Owner"):
    a = AdminUser(telegram_id=tid, full_name=name, is_active=True, status=AdminStatus.ACTIVE)
    db_session.add(a)
    await db_session.flush()
    return a


# ── rotation ─────────────────────────────────────────────────────────────────

async def test_week_index_anchor_is_zero(db_session):
    assert orientation.week_index(ANCHOR) == 0
    assert orientation.week_index(ANCHOR + timedelta(days=7)) == 1
    assert orientation.week_index(ANCHOR + timedelta(days=6)) == 0  # same week


async def test_computed_topic_follows_rotation_and_wraps(db_session):
    await _topics(db_session)
    t0, skip0 = await orientation.computed_topic(db_session, ANCHOR)
    assert t0.sort_order == 0 and skip0 == []
    t5, _ = await orientation.computed_topic(db_session, ANCHOR + timedelta(weeks=5))
    assert t5.sort_order == 5
    t12, _ = await orientation.computed_topic(db_session, ANCHOR + timedelta(weeks=12))
    assert t12.sort_order == 0  # wraps after 12


async def test_inactive_topic_is_skipped_and_audited(db_session):
    # Week 3's natural position is topic 3; deactivate it -> topic 4, with an audit row.
    await _topics(db_session, inactive={3})
    on = ANCHOR + timedelta(weeks=3)
    chosen, skipped = await orientation.computed_topic(db_session, on)
    assert chosen.sort_order == 4
    assert [t.sort_order for t in skipped] == [3]

    await orientation.log_topic_skips(db_session, on, skipped)
    audit = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.action == "orientation_topic_skipped")
        )
    ).scalars().all()
    assert len(audit) == 1
    assert audit[0].detail["sort_order"] == 3


async def test_all_inactive_returns_none(db_session):
    await _topics(db_session, n=3, inactive={0, 1, 2})
    chosen, skipped = await orientation.computed_topic(db_session, ANCHOR)
    assert chosen is None
    assert len(skipped) == 3


# ── meeting / example / swap ─────────────────────────────────────────────────

async def test_ensure_week_meeting_is_idempotent(db_session):
    await _topics(db_session)
    chosen, _ = await orientation.computed_topic(db_session, ANCHOR)
    m1 = await orientation.ensure_week_meeting(db_session, ANCHOR, chosen.id)
    m2 = await orientation.ensure_week_meeting(db_session, ANCHOR, chosen.id)
    assert m1.id == m2.id
    rows = (await db_session.execute(select(Meeting))).scalars().all()
    assert len(rows) == 1


async def test_set_example_writes_text_and_audit(db_session):
    await _topics(db_session)
    pa = await _admin(db_session, 9, "PA Zainab")
    chosen, _ = await orientation.computed_topic(db_session, ANCHOR)
    meeting = await orientation.ensure_week_meeting(db_session, ANCHOR, chosen.id)

    result = await orientation.set_example(db_session, meeting.id, pa.id, "Last Wednesday's late delivery")
    assert result.example_text == "Last Wednesday's late delivery"
    audit = (
        await db_session.execute(select(AuditLog).where(AuditLog.action == "orientation_example_set"))
    ).scalar_one()
    assert audit.actor_id == pa.id


async def test_swap_topic_records_origin_and_reason(db_session):
    await _topics(db_session)
    owner = await _admin(db_session, 1, "Owner O")
    chosen, _ = await orientation.computed_topic(db_session, ANCHOR)
    other = (
        await db_session.execute(select(OrientationTopic).where(OrientationTopic.sort_order == 7))
    ).scalar_one()
    meeting = await orientation.ensure_week_meeting(db_session, ANCHOR, chosen.id)

    result = await orientation.swap_topic(db_session, meeting.id, other.id, owner.id, "board asked for numbers first")
    assert result.topic_id == other.id
    assert result.swapped_from_topic_id == chosen.id
    assert result.swapped_by == owner.id

    audit = (
        await db_session.execute(select(AuditLog).where(AuditLog.action == "orientation_topic_swapped"))
    ).scalar_one()
    assert audit.reason == "board asked for numbers first"
    assert audit.detail["to"] == str(other.id)
