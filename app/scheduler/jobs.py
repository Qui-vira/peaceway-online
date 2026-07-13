"""APScheduler jobs - currently the 24-hour post-delivery follow-up.

The job stores only the order id and rebuilds a Bot at run time, so it does not
hold a live Bot reference (making a persistent jobstore an easy future upgrade).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

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


def schedule_followup(_bot, order_id: UUID, delay_hours: int = 24) -> None:
    run_date = datetime.now(timezone.utc) + timedelta(hours=delay_hours)
    scheduler.add_job(
        send_followup,
        "date",
        run_date=run_date,
        args=[str(order_id)],
        id=f"followup:{order_id}",
        replace_existing=True,
    )
    log.info("followup_scheduled", order_id=str(order_id), run_date=run_date.isoformat())


async def send_followup(order_id_str: str) -> None:
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    from app.bot.dispatcher import build_bot
    from app.core.db import get_session
    from app.models import Customer, Order

    async with get_session() as session:
        order = (
            await session.execute(select(Order).where(Order.id == UUID(order_id_str)))
        ).scalar_one_or_none()
        if order is None:
            return
        customer = await session.get(Customer, order.customer_id)
    if not customer:
        return

    kb = InlineKeyboardBuilder()
    kb.button(text="👍 Everything is okay", callback_data="fu:ok")
    kb.button(text="🆘 I need help", callback_data="fu:help")
    kb.button(text="🧑‍⚕️ Speak to a pharmacist", callback_data="fu:pharm")
    kb.adjust(1)

    bot = build_bot()
    try:
        await bot.send_message(customer.telegram_id, FOLLOWUP_TEXT, reply_markup=kb.as_markup())
    except Exception as exc:  # noqa: BLE001
        log.error("followup_send_failed", order_id=order_id_str, error=str(exc))
    finally:
        await bot.session.close()
