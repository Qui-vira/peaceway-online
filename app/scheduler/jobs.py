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
