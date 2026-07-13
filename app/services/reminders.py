"""Medication reminder scheduling logic.

Design notes:
- Reminders carry only user-entered or pharmacist-entered text. Nothing in
  this module generates or completes dosage instructions.
- Scheduling is DB-driven: `next_run_at` (UTC) is the single source of truth
  and the dispatcher simply queries for rows where it is due. This survives
  restarts/redeploys, unlike in-memory APScheduler jobs.
"""
from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Customer,
    MedicationReminder,
    MedicationReminderEvent,
    ReminderConsent,
    ReminderEventStatus,
    ReminderSource,
    ReminderStatus,
)

TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
MAX_TIMES_PER_DAY = 6
# Occurrences older than this when the dispatcher sees them (e.g. the app was
# down) are logged as missed instead of firing late.
MISSED_GRACE = timedelta(minutes=10)

DEFAULT_TZ = "Africa/Lagos"


def validate_times(times: list[str]) -> list[str]:
    """Return sorted unique HH:MM strings or raise ValueError."""
    cleaned = sorted({t.strip() for t in times if t and t.strip()})
    if not cleaned:
        raise ValueError("At least one reminder time is required.")
    if len(cleaned) > MAX_TIMES_PER_DAY:
        raise ValueError(f"At most {MAX_TIMES_PER_DAY} reminder times per day.")
    for t in cleaned:
        if not TIME_RE.match(t):
            raise ValueError(f"Invalid time '{t}' - use 24h HH:MM, e.g. 08:00.")
    return cleaned


def compute_next_run(
    times: list[str],
    tz_name: str,
    start_date: date,
    end_date: date | None,
    now: datetime,
) -> datetime | None:
    """First UTC instant strictly after `now` matching the schedule.

    Returns None when the schedule is exhausted (past end_date).
    """
    tz = ZoneInfo(tz_name)
    local_now = now.astimezone(tz)
    day = max(start_date, local_now.date())

    while end_date is None or day <= end_date:
        for hhmm in times:
            hour, minute = int(hhmm[:2]), int(hhmm[3:])
            candidate = datetime.combine(day, time(hour, minute), tzinfo=tz)
            if candidate > local_now:
                return candidate.astimezone(timezone.utc)
        # Unbounded schedules always resolve within a day, so only bounded
        # ones can loop more than twice here.
        day += timedelta(days=1)

    return None


async def create_reminder(
    session: AsyncSession,
    *,
    customer: Customer,
    medicine_name: str,
    times: list[str],
    start_date: date,
    end_date: date | None = None,
    instructions_text: str | None = None,
    tz_name: str = DEFAULT_TZ,
    source: str = ReminderSource.CUSTOMER.value,
    created_by_admin_id: int | None = None,
    prescription_id: UUID | None = None,
    now: datetime | None = None,
) -> MedicationReminder:
    medicine_name = medicine_name.strip()
    if not medicine_name:
        raise ValueError("Medicine name is required.")
    if end_date and end_date < start_date:
        raise ValueError("End date cannot be before start date.")
    ZoneInfo(tz_name)  # raises for unknown zones

    now = now or datetime.now(timezone.utc)
    cleaned_times = validate_times(times)

    # Pharmacist-created reminders wait for explicit customer consent and are
    # not schedulable until it is granted.
    consent = (
        ReminderConsent.GRANTED.value
        if source == ReminderSource.CUSTOMER.value
        else ReminderConsent.PENDING.value
    )

    reminder = MedicationReminder(
        customer_id=customer.id,
        medicine_name=medicine_name,
        instructions_text=(instructions_text or "").strip() or None,
        source=source,
        created_by_admin_id=created_by_admin_id,
        consent_status=consent,
        times=cleaned_times,
        timezone=tz_name,
        start_date=start_date,
        end_date=end_date,
        prescription_id=prescription_id,
    )
    if consent == ReminderConsent.GRANTED.value:
        reminder.next_run_at = compute_next_run(cleaned_times, tz_name, start_date, end_date, now)
        if reminder.next_run_at is None:
            reminder.status = ReminderStatus.COMPLETED.value
    session.add(reminder)
    await session.flush()
    return reminder


async def grant_consent(
    session: AsyncSession, reminder: MedicationReminder, now: datetime | None = None
) -> MedicationReminder:
    now = now or datetime.now(timezone.utc)
    reminder.consent_status = ReminderConsent.GRANTED.value
    reminder.next_run_at = compute_next_run(
        reminder.times, reminder.timezone, reminder.start_date, reminder.end_date, now
    )
    if reminder.next_run_at is None:
        reminder.status = ReminderStatus.COMPLETED.value
    session.add(reminder)
    return reminder


async def decline_consent(session: AsyncSession, reminder: MedicationReminder) -> MedicationReminder:
    reminder.consent_status = ReminderConsent.DECLINED.value
    reminder.status = ReminderStatus.STOPPED.value
    reminder.stopped_at = datetime.now(timezone.utc)
    reminder.next_run_at = None
    session.add(reminder)
    return reminder


async def pause_reminder(session: AsyncSession, reminder: MedicationReminder) -> MedicationReminder:
    if reminder.status != ReminderStatus.ACTIVE.value:
        raise ValueError("Only active reminders can be paused.")
    reminder.status = ReminderStatus.PAUSED.value
    reminder.paused_at = datetime.now(timezone.utc)
    reminder.next_run_at = None
    session.add(reminder)
    return reminder


async def resume_reminder(
    session: AsyncSession, reminder: MedicationReminder, now: datetime | None = None
) -> MedicationReminder:
    if reminder.status != ReminderStatus.PAUSED.value:
        raise ValueError("Only paused reminders can be resumed.")
    now = now or datetime.now(timezone.utc)
    reminder.status = ReminderStatus.ACTIVE.value
    reminder.paused_at = None
    reminder.next_run_at = compute_next_run(
        reminder.times, reminder.timezone, reminder.start_date, reminder.end_date, now
    )
    if reminder.next_run_at is None:
        reminder.status = ReminderStatus.COMPLETED.value
    session.add(reminder)
    return reminder


async def stop_reminder(session: AsyncSession, reminder: MedicationReminder) -> MedicationReminder:
    reminder.status = ReminderStatus.STOPPED.value
    reminder.stopped_at = datetime.now(timezone.utc)
    reminder.next_run_at = None
    session.add(reminder)
    return reminder


async def list_customer_reminders(
    session: AsyncSession, customer_id: UUID
) -> list[MedicationReminder]:
    return list(
        (
            await session.execute(
                select(MedicationReminder)
                .where(MedicationReminder.customer_id == customer_id)
                .order_by(MedicationReminder.created_at.desc())
            )
        ).scalars().all()
    )


def build_reminder_text(reminder: MedicationReminder) -> str:
    """Reminder message: name + verbatim stored instructions only."""
    lines = [f"⏰ Medication reminder: <b>{reminder.medicine_name}</b>"]
    if reminder.instructions_text:
        lines.append(reminder.instructions_text)
    if reminder.source == ReminderSource.PHARMACIST.value:
        lines.append("Set with you by a Peaceway pharmacist.")
    else:
        lines.append("You set this reminder.")
    lines.append("This is a reminder, not medical advice.")
    return "\n\n".join(lines)


async def collect_due(
    session: AsyncSession, now: datetime | None = None
) -> list[tuple[MedicationReminder, datetime, str]]:
    """Advance all due reminders and say what to do for each occurrence.

    Returns (reminder, scheduled_for, action) where action is "send" or
    "missed". Missed occurrences (older than MISSED_GRACE) get their audit
    event written here; "send" events are written by the dispatcher after the
    actual send attempt so the outcome (SENT/FAILED) is accurate.
    """
    now = now or datetime.now(timezone.utc)
    due = (
        await session.execute(
            select(MedicationReminder).where(
                MedicationReminder.status == ReminderStatus.ACTIVE.value,
                MedicationReminder.consent_status == ReminderConsent.GRANTED.value,
                MedicationReminder.next_run_at.is_not(None),
                MedicationReminder.next_run_at <= now,
            )
        )
    ).scalars().all()

    work: list[tuple[MedicationReminder, datetime, str]] = []
    for reminder in due:
        scheduled_for = reminder.next_run_at
        action = "missed" if (now - scheduled_for) > MISSED_GRACE else "send"
        if action == "missed":
            session.add(
                MedicationReminderEvent(
                    reminder_id=reminder.id,
                    scheduled_for=scheduled_for,
                    status=ReminderEventStatus.SKIPPED_MISSED.value,
                )
            )
        work.append((reminder, scheduled_for, action))

        reminder.next_run_at = compute_next_run(
            reminder.times, reminder.timezone, reminder.start_date, reminder.end_date, now
        )
        if reminder.next_run_at is None:
            reminder.status = ReminderStatus.COMPLETED.value
        session.add(reminder)

    return work


def record_send_result(
    session: AsyncSession,
    reminder: MedicationReminder,
    scheduled_for: datetime,
    *,
    error: str | None = None,
) -> MedicationReminderEvent:
    event = MedicationReminderEvent(
        reminder_id=reminder.id,
        scheduled_for=scheduled_for,
        sent_at=None if error else datetime.now(timezone.utc),
        status=ReminderEventStatus.FAILED.value if error else ReminderEventStatus.SENT.value,
        error=error,
    )
    session.add(event)
    return event
