"""Unit tests for the staff checklist + meeting tracker (SQLite).

Covers the service logic and the group-safe message builders. The Postgres-only
append-only TRIGGER is exercised in test_checklist_pg.py; SQLite still enforces the
own-completion CHECK, so that guard is asserted here directly.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import (
    AdminRoleAssignment,
    AdminUser,
    AuditLog,
    ChecklistInstance,
    ChecklistTemplate,
    MeetingDecision,
)
from app.models.admin import AdminStatus
from app.services import checklist
from app.services.checklist_messages import (
    build_group_status,
    build_monday_prep,
    build_owner_summary,
)
from app.services.decision_scan import scan_for_contact

TODAY = date(2026, 7, 20)  # a Monday


async def _admin(session, tid, name, role_key, active=True):
    a = AdminUser(
        telegram_id=tid, full_name=name, is_active=active,
        status=AdminStatus.ACTIVE if active else AdminStatus.DISABLED,
    )
    session.add(a)
    await session.flush()
    session.add(AdminRoleAssignment(admin_id=a.id, role_key=role_key))
    await session.flush()
    return a


async def _template(session, role_key, text="Do the thing", cadence="daily", weekday=None):
    t = ChecklistTemplate(role_key=role_key, item_text=text, cadence=cadence, weekday=weekday)
    session.add(t)
    await session.flush()
    return t


# ── generation ───────────────────────────────────────────────────────────────

async def test_generate_is_idempotent(session):
    await _template(session, "dispatcher")
    await _admin(session, 1, "Rider Ade", "dispatcher")

    first = await checklist.generate_instances(session, TODAY)
    assert len(first) == 1

    second = await checklist.generate_instances(session, TODAY)
    assert second == []  # nothing new on re-run

    rows = (await session.execute(select(ChecklistInstance))).scalars().all()
    assert len(rows) == 1  # exactly one pending row per (template, assignee)


async def test_generate_skips_inactive_admins_and_weekly_off_day(session):
    await _template(session, "finance", cadence="weekly", weekday=2)  # Wednesday only
    await _admin(session, 2, "Fin Bola", "finance")
    await _admin(session, 3, "Old Staff", "finance", active=False)

    # TODAY is Monday -> the Wednesday weekly template is not due.
    assert await checklist.generate_instances(session, TODAY) == []
    # Wednesday -> due, but only for the active admin.
    created = await checklist.generate_instances(session, TODAY + timedelta(days=2))
    assert len(created) == 1


# ── completion (append-only + audit + ownership) ──────────────────────────────

async def test_complete_appends_row_and_audit(session):
    await _template(session, "dispatcher")
    admin = await _admin(session, 1, "Rider Ade", "dispatcher")
    [inst] = await checklist.generate_instances(session, TODAY)

    new = await checklist.complete_item(session, inst.id, admin.id, "done")

    assert new is not None
    assert new.id != inst.id           # a NEW row, original untouched
    assert new.supersedes_id == inst.id
    assert new.status == "done"
    assert new.completed_by == admin.id

    audit = (
        await session.execute(select(AuditLog).where(AuditLog.action == "checklist_done"))
    ).scalar_one()
    assert audit.actor_id == admin.id
    assert audit.entity == "checklist_instance"


async def test_skip_records_reason(session):
    await _template(session, "dispatcher")
    admin = await _admin(session, 1, "Rider Ade", "dispatcher")
    [inst] = await checklist.generate_instances(session, TODAY)

    new = await checklist.complete_item(session, inst.id, admin.id, "skipped", skip_reason="bike broke")
    assert new.status == "skipped"
    assert new.skip_reason == "bike broke"


async def test_cannot_complete_another_persons_item(session):
    await _template(session, "dispatcher")
    owner = await _admin(session, 1, "Rider Ade", "dispatcher")
    other = await _admin(session, 2, "Rider Kunle", "dispatcher")
    instances = await checklist.generate_instances(session, TODAY)
    ade_item = next(i for i in instances if i.assigned_user_id == owner.id)

    # Kunle tries to tick Ade's item -> guarded, no write.
    assert await checklist.complete_item(session, ade_item.id, other.id, "done") is None
    rows = (
        await session.execute(
            select(ChecklistInstance).where(ChecklistInstance.template_id == ade_item.template_id)
        )
    ).scalars().all()
    assert all(r.status == "pending" for r in rows)  # nothing completed


async def test_pa_cannot_complete_others_item(session):
    """A PA has view rights but may only complete her OWN items."""
    await _template(session, "dispatcher")
    rider = await _admin(session, 1, "Rider Ade", "dispatcher")
    pa = await _admin(session, 9, "PA Zainab", "pa")
    [rider_item] = await checklist.generate_instances(session, TODAY)

    assert await checklist.complete_item(session, rider_item.id, pa.id, "done") is None


async def test_db_check_blocks_foreign_completion_on_raw_insert(session):
    """The own-completion CHECK is the backstop if the app guard is ever bypassed."""
    await _template(session, "dispatcher")
    owner = await _admin(session, 1, "Rider Ade", "dispatcher")
    other = await _admin(session, 2, "Rider Kunle", "dispatcher")

    session.add(
        ChecklistInstance(
            template_id=(await session.execute(select(ChecklistTemplate.id))).scalar_one(),
            assigned_user_id=owner.id,
            due_date=TODAY,
            status="done",
            completed_by=other.id,  # violates ck_checklist_own_completion
        )
    )
    with pytest.raises(IntegrityError):
        await session.flush()


# ── status reporting ─────────────────────────────────────────────────────────

async def test_aggregate_counts_only(session):
    await _template(session, "dispatcher", text="Item A")
    await _template(session, "dispatcher", text="Item B")
    a = await _admin(session, 1, "Ade", "dispatcher")
    b = await _admin(session, 2, "Bola", "dispatcher")
    instances = await checklist.generate_instances(session, TODAY)  # 4 rows
    # Ade completes one item.
    ade_item = next(i for i in instances if i.assigned_user_id == a.id)
    await checklist.complete_item(session, ade_item.id, a.id, "done")

    agg = await checklist.aggregate_status(session, TODAY)
    assert agg == {
        "done": 1, "total": 4, "outstanding_items": 3, "people_with_outstanding": 2,
    }


async def test_per_person_status(session):
    await _template(session, "dispatcher", text="Item A")
    a = await _admin(session, 1, "Ade", "dispatcher")
    [item] = await checklist.generate_instances(session, TODAY)
    await checklist.complete_item(session, item.id, a.id, "done")

    people = await checklist.per_person_status(session, TODAY)
    assert people == [{"name": "Ade", "done": 1, "total": 1, "skipped": []}]


# ── decisions / Monday prep ──────────────────────────────────────────────────

async def test_open_decisions_flags_overdue(session):
    owner = await _admin(session, 5, "Owner O", "system_owner")
    session.add(MeetingDecision(decision_text="Order new bags", owner_user_id=owner.id,
                                due_date=TODAY - timedelta(days=8), status="open"))
    session.add(MeetingDecision(decision_text="Fresh task", owner_user_id=owner.id,
                                due_date=TODAY - timedelta(days=1), status="open"))
    await session.flush()

    decisions = await checklist.open_decisions(session, TODAY)
    assert decisions[0]["text"] == "Order new bags"     # oldest first
    assert decisions[0]["days_outstanding"] == 8
    assert decisions[0]["owner"] == "Owner O"

    prep = build_monday_prep(decisions)
    assert "Order new bags" in prep
    assert "⏰" in prep  # the 8-day-overdue flag


# ── message-builder safety ───────────────────────────────────────────────────

def test_group_status_is_counts_only():
    text = build_group_status(
        {"done": 2, "total": 5, "outstanding_items": 3, "people_with_outstanding": 2}
    )
    assert "Completed 2 of 5" in text
    assert "3 outstanding across 2 people" in text


def test_group_status_empty_day():
    assert "Nothing scheduled" in build_group_status(
        {"done": 0, "total": 0, "outstanding_items": 0, "people_with_outstanding": 0}
    )


# ── decision contact scan ────────────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "Call the supplier on 08031234567 tomorrow",
    "Reach them at +2347012345678",
    "acct 1234567890 for the transfer",
    "number is 080 3123 4567",
])
def test_scan_catches_numbers(text):
    assert scan_for_contact(text) is True


@pytest.mark.parametrize("text", [
    "Order 3 boxes of gloves by Friday",
    "Follow up with the landlord about rent",
    "",
])
def test_scan_passes_clean_text(text):
    assert scan_for_contact(text) is False


# ── owner summary + scheduler group guard ────────────────────────────────────

def test_owner_summary_lists_people_and_overdue():
    text = build_owner_summary(
        per_person=[{"name": "Ade", "done": 1, "total": 2, "skipped": [("Item B", "bike broke")]}],
        decisions_closed=["Signed the lease"],
        decisions_overdue=[{"text": "Order bags", "owner": "Bola", "days_outstanding": 9}],
    )
    assert "Ade: 1/2" in text
    assert "bike broke" in text
    assert "Signed the lease" in text
    assert "Order bags" in text


def test_group_job_skips_when_no_group_configured():
    """With STAFF_GROUP_CHAT_ID unset, the Monday group post must not fire."""
    from app.scheduler.jobs import _group_chat_id

    assert _group_chat_id() is None


# ── daily nudge ──────────────────────────────────────────────────────────────

async def test_admins_with_pending_excludes_completed(session):
    await _template(session, "dispatcher", text="Item A")
    a = await _admin(session, 1, "Ade", "dispatcher")
    b = await _admin(session, 2, "Bola", "dispatcher")
    instances = await checklist.generate_instances(session, TODAY)
    # Ade completes his item -> only Bola should be nudged.
    ade_item = next(i for i in instances if i.assigned_user_id == a.id)
    await checklist.complete_item(session, ade_item.id, a.id, "done")

    pending = await checklist.admins_with_pending(session, TODAY)
    assert pending == [(b.id, 1)]


async def test_nudge_idempotency_via_audit(session):
    """A recorded checklist_nudge_sent row removes that admin from the next run's targets."""
    from app.models import AuditLog

    await _template(session, "dispatcher")
    a = await _admin(session, 1, "Ade", "dispatcher")
    await checklist.generate_instances(session, TODAY)

    assert await checklist.nudged_admin_ids(session, TODAY) == set()
    # Simulate the job claiming the nudge.
    session.add(AuditLog(action="checklist_nudge_sent", entity="admin_user",
                         entity_id=str(a.id), detail={"due_date": TODAY.isoformat(), "outstanding": 1}))
    await session.flush()

    assert await checklist.nudged_admin_ids(session, TODAY) == {a.id}
    # A different day is unaffected.
    assert await checklist.nudged_admin_ids(session, TODAY + timedelta(days=1)) == set()
