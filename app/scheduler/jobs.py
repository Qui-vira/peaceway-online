"""APScheduler jobs — currently the 24-hour post-delivery follow-up.

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
