"""Local development entrypoint: run the bot via long-polling (no public URL needed).

Usage: python -m app.run_polling
"""
from __future__ import annotations

import asyncio

from app.bot.dispatcher import build_bot, build_dispatcher
from app.core.logging import configure_logging, get_logger

log = get_logger("run_polling")


async def main() -> None:
    configure_logging()
    from app.scheduler.jobs import start_scheduler

    start_scheduler()
    bot = build_bot()
    dp = build_dispatcher()
    await bot.delete_webhook(drop_pending_updates=True)
    log.info("polling_start")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
