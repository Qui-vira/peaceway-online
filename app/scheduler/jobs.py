"""APScheduler jobs, run by the dedicated scheduler worker (``app.run_scheduler``).

All state lives in the database - reminders via ``Reminder.next_run_at`` and the
post-delivery follow-up via ``Order.followup_due_at`` - so these are pure DB
pollers. There are no in-memory jobs and no persistent jobstore, which means the
web process holds no scheduler at all and can be scaled horizontally; the single
worker owns all scheduled work.
"""
from __future__ import annotations

from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.core.logging import get_logger
from app.core.timeutil import LAGOS

log = get_logger("scheduler")
scheduler = AsyncIOScheduler(timezone="UTC")

FOLLOWUP_TEXT = (
    "Hello, this is Peaceway Online. We are checking in to confirm you received "
    "your order and everything is okay."
)


def start_scheduler() -> None:
    """Start the scheduler and register the DB-driven pollers (idempotent)."""
    if not scheduler.running:
        scheduler.start()
        log.info("scheduler_started")

    from app.core.config import get_settings

    if get_settings().reminders_enabled and not scheduler.get_job("medication_reminders_dispatch"):
        scheduler.add_job(
            dispatch_due_reminders,
            "interval",
            seconds=60,
            id="medication_reminders_dispatch",
            max_instances=1,
            coalesce=True,
        )
        log.info("reminder_dispatcher_started")

    if not scheduler.get_job("order_followup_dispatch"):
        scheduler.add_job(
            dispatch_due_followups,
            "interval",
            seconds=60,
            id="order_followup_dispatch",
            max_instances=1,
            coalesce=True,
        )
        log.info("followup_dispatcher_started")

    # Staff checklist + meeting tracker (Africa/Lagos local clock). Cron so the
    # times track the pharmacy's day regardless of the server's UTC offset.
    if not scheduler.get_job("checklist_morning"):
        scheduler.add_job(
            checklist_morning, "cron", hour=6, minute=0, timezone=LAGOS,
            id="checklist_morning", max_instances=1, coalesce=True,
        )
    if not scheduler.get_job("checklist_monday_prep"):
        scheduler.add_job(
            checklist_monday_prep, "cron", day_of_week="mon", hour=8, minute=0, timezone=LAGOS,
            id="checklist_monday_prep", max_instances=1, coalesce=True,
        )
    if not scheduler.get_job("checklist_owner_summary"):
        scheduler.add_job(
            checklist_owner_summary, "cron", day_of_week="mon", hour=18, minute=0, timezone=LAGOS,
            id="checklist_owner_summary", max_instances=1, coalesce=True,
        )
    if not scheduler.get_job("checklist_nudge"):
        scheduler.add_job(
            checklist_nudge, "cron", day_of_week="mon-fri",
            hour=get_settings().staff_nudge_hour, minute=0, timezone=LAGOS,
            id="checklist_nudge", max_instances=1, coalesce=True,
        )
    if not scheduler.get_job("checklist_sunday_prep"):
        scheduler.add_job(
            checklist_sunday_prep, "cron", day_of_week="sun", hour=18, minute=0, timezone=LAGOS,
            id="checklist_sunday_prep", max_instances=1, coalesce=True,
        )
    log.info("checklist_jobs_started")


async def dispatch_due_reminders() -> None:
    """Every minute: fire reminders whose next_run_at is due.

    DB-driven (next_run_at column), so schedules survive restarts. Missed
    occurrences past the grace window are audited as skipped, not sent late.
    """
    from app.bot.dispatcher import build_bot
    from app.core.db import get_session
    from app.models import Customer
    from app.services.reminders import build_reminder_text, collect_due, record_send_result

    async with get_session() as session:
        work = await collect_due(session)
        sendable = [(r, at) for r, at, action in work if action == "send"]

        if sendable:
            bot = build_bot()
            try:
                for reminder, scheduled_for in sendable:
                    customer = await session.get(Customer, reminder.customer_id)
                    if not customer or not customer.telegram_id:
                        record_send_result(
                            session, reminder, scheduled_for,
                            error="customer has no Telegram channel",
                        )
                        continue
                    try:
                        await bot.send_message(customer.telegram_id, build_reminder_text(reminder))
                        record_send_result(session, reminder, scheduled_for)
                    except Exception as exc:  # noqa: BLE001
                        record_send_result(session, reminder, scheduled_for, error=str(exc))
                        log.error(
                            "reminder_send_failed",
                            reminder_id=str(reminder.id),
                            error=str(exc),
                        )
            finally:
                await bot.session.close()

        await session.commit()
        if work:
            log.info("reminders_dispatched", total=len(work), sent=len(sendable))


async def dispatch_due_followups() -> None:
    """Every minute: send the 24h post-delivery check-in for orders whose
    followup_due_at has passed and that have not been sent yet.

    The order rows are claimed (followup_sent_at stamped) inside a short locked
    transaction, then the Telegram messages are sent after the lock is released -
    so a slow send never holds row locks, and SKIP LOCKED keeps a second worker
    (e.g. during a deploy overlap) from grabbing the same rows. Fire-and-forget:
    a failed send is logged, not retried, matching the previous behaviour.
    """
    from app.core.db import get_session
    from app.models import Customer, Order

    now = datetime.now(timezone.utc)

    # 1) Claim due rows and collect their Telegram targets.
    targets: list[int] = []
    async with get_session() as session:
        due = (
            (
                await session.execute(
                    select(Order)
                    .where(
                        Order.followup_due_at.is_not(None),
                        Order.followup_due_at <= now,
                        Order.followup_sent_at.is_(None),
                    )
                    .order_by(Order.followup_due_at)
                    .with_for_update(skip_locked=True)
                    .limit(100)
                )
            )
            .scalars()
            .all()
        )
        for order in due:
            order.followup_sent_at = now
            customer = await session.get(Customer, order.customer_id)
            if customer and customer.telegram_id:
                targets.append(customer.telegram_id)
        # get_session commits on exit -> claim persists, locks released.

    if not targets:
        return

    # 2) Send outside the transaction.
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    from app.bot.dispatcher import build_bot

    kb = InlineKeyboardBuilder()
    kb.button(text="👍 Everything is okay", callback_data="fu:ok")
    kb.button(text="🆘 I need help", callback_data="fu:help")
    kb.button(text="🧑‍⚕️ Speak to a pharmacist", callback_data="fu:pharm")
    kb.adjust(1)
    markup = kb.as_markup()

    bot = build_bot()
    sent = 0
    try:
        for telegram_id in targets:
            try:
                await bot.send_message(telegram_id, FOLLOWUP_TEXT, reply_markup=markup)
                sent += 1
            except Exception as exc:  # noqa: BLE001
                log.error("followup_send_failed", telegram_id=telegram_id, error=str(exc))
    finally:
        await bot.session.close()

    log.info("followups_dispatched", claimed=len(targets), sent=sent)


def _group_chat_id() -> int | None:
    """Parsed STAFF_GROUP_CHAT_ID, or None if unset/blank (jobs then skip group posts)."""
    from app.core.config import get_settings

    raw = (get_settings().staff_group_chat_id or "").strip()
    try:
        return int(raw) if raw else None
    except ValueError:
        return None


async def checklist_morning() -> None:
    """06:00 Lagos: generate today's items and DM each staffer their fresh checklist.

    Generation is idempotent (one pending row per assignment), so a retry or a
    same-day redeploy never double-posts. Only staff who received NEW items are DM'd.
    """
    from app.bot.dispatcher import build_bot
    from app.bot.staff.checklist import _checklist_kb, _render_checklist
    from app.core.db import get_session
    from app.core.timeutil import lagos_today
    from app.models import AdminUser
    from app.services import checklist

    on = lagos_today()
    async with get_session() as session:
        created = await checklist.generate_instances(session, on)
        user_ids = {inst.assigned_user_id for inst in created}
        if not user_ids:
            log.info("checklist_morning_none")
            return
        # Render each affected staffer's full checklist for the DM.
        payloads: list[tuple[int, str, object]] = []
        for uid in user_ids:
            admin = await session.get(AdminUser, uid)
            if not admin or not admin.telegram_id:
                continue
            items = await checklist.latest_states(session, uid, on)
            payloads.append((admin.telegram_id, _render_checklist(items), _checklist_kb(items).as_markup()))

    if not payloads:
        return
    bot = build_bot()
    sent = 0
    try:
        for telegram_id, text, markup in payloads:
            try:
                await bot.send_message(telegram_id, text, reply_markup=markup)
                sent += 1
            except Exception as exc:  # noqa: BLE001
                log.error("checklist_dm_failed", telegram_id=telegram_id, error=str(exc))
    finally:
        await bot.session.close()
    log.info("checklist_morning_sent", staff=len(payloads), sent=sent)


async def checklist_monday_prep() -> None:
    """Mon 08:00 Lagos: post the open-decisions block to the staff group (aggregate-safe)."""
    chat_id = _group_chat_id()
    if chat_id is None:
        log.info("checklist_prep_skipped_no_group")
        return
    from app.bot.dispatcher import build_bot
    from app.core.db import get_session
    from app.core.timeutil import lagos_today
    from app.services import checklist
    from app.services.checklist_messages import build_monday_prep

    async with get_session() as session:
        text = build_monday_prep(await checklist.open_decisions(session, lagos_today()))
    bot = build_bot()
    try:
        await bot.send_message(chat_id, text)
    except Exception as exc:  # noqa: BLE001
        log.error("checklist_prep_failed", error=str(exc))
    finally:
        await bot.session.close()
    log.info("checklist_prep_posted")


async def checklist_owner_summary() -> None:
    """Mon 18:00 Lagos: DM the per-person weekly summary to each System Owner."""
    from datetime import timedelta

    from app.bot.dispatcher import build_bot
    from app.core import rbac
    from app.core.db import get_session
    from app.core.timeutil import lagos_now, lagos_today
    from app.services import checklist
    from app.services.checklist_messages import build_owner_summary
    from app.services.rbac_service import recipients_for_roles

    on = lagos_today()
    week_ago = lagos_now() - timedelta(days=7)
    async with get_session() as session:
        per_person = await checklist.per_person_status(session, on)
        closed = await checklist.decisions_closed_since(session, week_ago)
        overdue = await checklist.overdue_decisions(session, on)
        owner_ids, _ = await recipients_for_roles({rbac.SYSTEM_OWNER}, session)

    if not owner_ids:
        return
    text = build_owner_summary(per_person, closed, overdue)
    bot = build_bot()
    sent = 0
    try:
        for telegram_id in owner_ids:
            try:
                await bot.send_message(telegram_id, text)
                sent += 1
            except Exception as exc:  # noqa: BLE001
                log.error("owner_summary_failed", telegram_id=telegram_id, error=str(exc))
    finally:
        await bot.session.close()
    log.info("owner_summary_sent", owners=len(owner_ids), sent=sent)


async def checklist_nudge() -> None:
    """Weekday evening (default 18:00 Lagos): DM staff who still have outstanding items.

    Private DM only, NEVER the group. Lists only the person's pending items with the same
    Done/Skip buttons. Anyone at zero outstanding is not messaged - silence on completion
    is intentional. One nudge per person per day (idempotent via the audit trail), and no
    escalating reminders. Each send writes a checklist_nudge_sent audit row.
    """
    from app.bot.dispatcher import build_bot
    from app.bot.staff.checklist import _checklist_kb, _render_checklist
    from app.core.db import get_session
    from app.core.timeutil import lagos_today
    from app.models import AdminUser, AuditLog
    from app.services import checklist

    on = lagos_today()
    async with get_session() as session:
        pending = await checklist.admins_with_pending(session, on)
        already = await checklist.nudged_admin_ids(session, on)
        targets = [(uid, n) for uid, n in pending if uid not in already]
        if not targets:
            log.info("checklist_nudge_none")
            return
        payloads: list[tuple[int, str, object, str, int]] = []
        for uid, count in targets:
            admin = await session.get(AdminUser, uid)
            if not admin or not admin.telegram_id:
                continue
            items = [(t, i) for t, i in await checklist.latest_states(session, uid, on)
                     if i.status == "pending"]
            payloads.append(
                (admin.telegram_id, _render_checklist(items), _checklist_kb(items).as_markup(),
                 str(uid), count)
            )
        # Claim the nudge (audit row) inside this transaction so a retry won't re-send.
        for _tid, _text, _markup, uid_str, count in payloads:
            session.add(
                AuditLog(
                    action="checklist_nudge_sent",
                    entity="admin_user",
                    entity_id=uid_str,
                    detail={"due_date": on.isoformat(), "outstanding": count},
                )
            )

    if not payloads:
        return
    bot = build_bot()
    sent = 0
    try:
        for telegram_id, text, markup, _uid, _count in payloads:
            try:
                await bot.send_message(telegram_id, "🔔 <b>Still outstanding today</b>\n\n" + text,
                                       reply_markup=markup)
                sent += 1
            except Exception as exc:  # noqa: BLE001
                log.error("checklist_nudge_failed", telegram_id=telegram_id, error=str(exc))
    finally:
        await bot.session.close()
    log.info("checklist_nudge_sent", staff=len(payloads), sent=sent)


async def checklist_sunday_prep() -> None:
    """Sunday 18:00 Lagos: DM the PA the computed topic for the coming week + a prompt.

    The topic is computed from the rotation (never entered); any inactive topic skipped
    is audited. The PA fills the worked example - she cannot change the topic.
    """
    from datetime import timedelta

    from app.bot.dispatcher import build_bot
    from app.core import rbac
    from app.core.db import get_session
    from app.core.timeutil import lagos_today
    from app.services import orientation
    from app.services.rbac_service import recipients_for_roles

    # The upcoming week's Monday (Sunday + 1 day, then normalise to that week's Monday).
    upcoming_monday = orientation.monday_of(lagos_today() + timedelta(days=1))
    async with get_session() as session:
        chosen, skipped = await orientation.computed_topic(session, upcoming_monday)
        if skipped:
            await orientation.log_topic_skips(session, upcoming_monday, skipped)
        await orientation.ensure_week_meeting(session, upcoming_monday, chosen.id if chosen else None)
        pa_ids, _ = await recipients_for_roles({rbac.PA}, session)
        topic_text = chosen.topic_text if chosen else "⚠️ No active topic — set one via /orientationtopics."

    if not pa_ids:
        log.info("sunday_prep_no_pa")
        return
    text = (
        "🎓 <b>Orientation prep for next week</b>\n"
        f"Week of {upcoming_monday.isoformat()}\n\n"
        f"<b>Topic:</b> {topic_text}\n\n"
        "Reply in /orientation with this week's real worked example. "
        "The topic is fixed — only the example is yours to fill."
    )
    bot = build_bot()
    sent = 0
    try:
        for telegram_id in pa_ids:
            try:
                await bot.send_message(telegram_id, text)
                sent += 1
            except Exception as exc:  # noqa: BLE001
                log.error("sunday_prep_failed", telegram_id=telegram_id, error=str(exc))
    finally:
        await bot.session.close()
    log.info("sunday_prep_sent", pas=len(pa_ids), sent=sent)
