"""Medication reminder service tests: schedule math, lifecycle, dispatch."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from app.models import Customer, ReminderConsent, ReminderEventStatus, ReminderSource, ReminderStatus
from app.services.reminders import (
    collect_due,
    compute_next_run,
    create_reminder,
    grant_consent,
    pause_reminder,
    record_send_result,
    resume_reminder,
    stop_reminder,
    validate_times,
)

LAGOS = "Africa/Lagos"  # fixed UTC+1, no DST


def utc(y, mo, d, h, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


async def make_customer(session, telegram_id=111) -> Customer:
    c = Customer(telegram_id=telegram_id, full_name="Test", phone="+2348000000000")
    session.add(c)
    await session.flush()
    return c


# ── validate_times ──────────────────────────────────────────────────────────

def test_validate_times_sorts_and_dedupes():
    assert validate_times(["20:00", "08:00", "08:00"]) == ["08:00", "20:00"]


def test_validate_times_rejects_bad_format():
    with pytest.raises(ValueError):
        validate_times(["25:00"])
    with pytest.raises(ValueError):
        validate_times(["8am"])
    with pytest.raises(ValueError):
        validate_times([])


# ── compute_next_run ────────────────────────────────────────────────────────

def test_next_run_today_when_time_still_ahead():
    # 06:00 UTC = 07:00 Lagos; 08:00 Lagos is still ahead today
    now = utc(2026, 7, 2, 6)
    nxt = compute_next_run(["08:00"], LAGOS, date(2026, 7, 1), None, now)
    assert nxt == utc(2026, 7, 2, 7)  # 08:00 Lagos == 07:00 UTC


def test_next_run_rolls_to_tomorrow_when_passed():
    # 10:00 UTC = 11:00 Lagos; 08:00 already passed -> tomorrow
    now = utc(2026, 7, 2, 10)
    nxt = compute_next_run(["08:00"], LAGOS, date(2026, 7, 1), None, now)
    assert nxt == utc(2026, 7, 3, 7)


def test_next_run_picks_earliest_upcoming_of_multiple():
    now = utc(2026, 7, 2, 8, 30)  # 09:30 Lagos, between 08:00 and 14:00
    nxt = compute_next_run(["08:00", "14:00", "20:00"], LAGOS, date(2026, 7, 1), None, now)
    assert nxt == utc(2026, 7, 2, 13)  # 14:00 Lagos


def test_next_run_waits_for_future_start_date():
    now = utc(2026, 7, 2, 6)
    nxt = compute_next_run(["08:00"], LAGOS, date(2026, 7, 10), None, now)
    assert nxt == utc(2026, 7, 10, 7)


def test_next_run_none_after_end_date():
    now = utc(2026, 7, 2, 6)
    assert compute_next_run(["08:00"], LAGOS, date(2026, 6, 1), date(2026, 7, 1), now) is None


# ── lifecycle ───────────────────────────────────────────────────────────────

async def test_create_customer_reminder_is_active_and_scheduled(session):
    customer = await make_customer(session)
    r = await create_reminder(
        session,
        customer=customer,
        medicine_name="Amlodipine 5mg",
        times=["08:00"],
        start_date=date(2026, 7, 1),
        now=utc(2026, 7, 2, 6),
    )
    assert r.status == ReminderStatus.ACTIVE.value
    assert r.consent_status == ReminderConsent.GRANTED.value
    assert r.next_run_at == utc(2026, 7, 2, 7)


async def test_pharmacist_reminder_waits_for_consent(session):
    customer = await make_customer(session)
    r = await create_reminder(
        session,
        customer=customer,
        medicine_name="Lisinopril",
        times=["09:00"],
        start_date=date(2026, 7, 1),
        source=ReminderSource.PHARMACIST.value,
        created_by_admin_id=42,
        now=utc(2026, 7, 2, 6),
    )
    assert r.consent_status == ReminderConsent.PENDING.value
    assert r.next_run_at is None  # not schedulable until customer accepts

    await grant_consent(session, r, now=utc(2026, 7, 2, 6))
    assert r.consent_status == ReminderConsent.GRANTED.value
    assert r.next_run_at == utc(2026, 7, 2, 8)  # 09:00 Lagos


async def test_pause_resume_stop(session):
    customer = await make_customer(session)
    r = await create_reminder(
        session,
        customer=customer,
        medicine_name="Metformin",
        times=["08:00", "20:00"],
        start_date=date(2026, 7, 1),
        now=utc(2026, 7, 2, 6),
    )
    await pause_reminder(session, r)
    assert r.status == ReminderStatus.PAUSED.value
    assert r.next_run_at is None

    await resume_reminder(session, r, now=utc(2026, 7, 2, 10))
    assert r.status == ReminderStatus.ACTIVE.value
    assert r.next_run_at == utc(2026, 7, 2, 19)  # 20:00 Lagos

    await stop_reminder(session, r)
    assert r.status == ReminderStatus.STOPPED.value
    assert r.next_run_at is None


async def test_create_rejects_bad_input(session):
    customer = await make_customer(session)
    with pytest.raises(ValueError):
        await create_reminder(
            session, customer=customer, medicine_name="  ",
            times=["08:00"], start_date=date(2026, 7, 1),
        )
    with pytest.raises(ValueError):
        await create_reminder(
            session, customer=customer, medicine_name="X",
            times=["08:00"], start_date=date(2026, 7, 10), end_date=date(2026, 7, 1),
        )


# ── dispatch ────────────────────────────────────────────────────────────────

async def test_collect_due_sends_fresh_and_skips_stale(session):
    customer = await make_customer(session)
    now = utc(2026, 7, 2, 6)

    fresh = await create_reminder(
        session, customer=customer, medicine_name="Fresh",
        times=["08:00"], start_date=date(2026, 7, 1), now=utc(2026, 7, 2, 5),
    )
    fresh.next_run_at = now - timedelta(minutes=2)  # due 2 min ago -> send
    stale = await create_reminder(
        session, customer=customer, medicine_name="Stale",
        times=["08:00"], start_date=date(2026, 7, 1), now=utc(2026, 7, 2, 5),
    )
    stale.next_run_at = now - timedelta(hours=3)  # due 3h ago -> missed
    await session.flush()

    work = await collect_due(session, now=now)
    actions = {r.medicine_name: action for r, _at, action in work}
    assert actions == {"Fresh": "send", "Stale": "missed"}

    # both advanced to the next occurrence, still active
    assert fresh.next_run_at == utc(2026, 7, 2, 7)
    assert stale.next_run_at == utc(2026, 7, 2, 7)
    assert fresh.status == ReminderStatus.ACTIVE.value


async def test_collect_due_completes_past_end_date(session):
    customer = await make_customer(session)
    now = utc(2026, 7, 2, 6)
    r = await create_reminder(
        session, customer=customer, medicine_name="Course done",
        times=["06:30"], start_date=date(2026, 7, 1), end_date=date(2026, 7, 2),
        now=utc(2026, 7, 2, 5),
    )
    r.next_run_at = now - timedelta(minutes=1)  # last occurrence of the course
    await session.flush()

    work = await collect_due(session, now=now)
    assert [a for _r, _at, a in work] == ["send"]
    assert r.next_run_at is None
    assert r.status == ReminderStatus.COMPLETED.value


async def test_collect_due_ignores_paused_and_pending_consent(session):
    customer = await make_customer(session)
    now = utc(2026, 7, 2, 6)
    r = await create_reminder(
        session, customer=customer, medicine_name="Paused one",
        times=["08:00"], start_date=date(2026, 7, 1), now=utc(2026, 7, 2, 5),
    )
    await pause_reminder(session, r)
    await create_reminder(
        session, customer=customer, medicine_name="No consent",
        times=["08:00"], start_date=date(2026, 7, 1),
        source=ReminderSource.PHARMACIST.value, now=utc(2026, 7, 2, 5),
    )
    assert await collect_due(session, now=now) == []


async def test_record_send_result(session):
    customer = await make_customer(session)
    r = await create_reminder(
        session, customer=customer, medicine_name="X",
        times=["08:00"], start_date=date(2026, 7, 1), now=utc(2026, 7, 2, 5),
    )
    at = utc(2026, 7, 2, 7)
    ok = record_send_result(session, r, at)
    assert ok.status == ReminderEventStatus.SENT.value and ok.sent_at is not None
    failed = record_send_result(session, r, at + timedelta(days=1), error="boom")
    assert failed.status == ReminderEventStatus.FAILED.value and failed.error == "boom"
