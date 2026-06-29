"""FastAPI application hosting the Telegram webhook + provider webhooks + health.

In production (WEBHOOK_BASE_URL set) the bot runs in webhook mode. For local
development without a public URL, run ``python -m app.run_polling`` instead.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.bot.dispatcher import build_bot, build_dispatcher
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.webhooks import telegram as telegram_webhook

log = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()
    bot = build_bot()
    dp = build_dispatcher()
    app.state.bot = bot
    app.state.dp = dp

    from app.scheduler.jobs import start_scheduler

    start_scheduler()

    if settings.webhook_base_url:
        url = settings.webhook_base_url.rstrip("/") + "/webhook/telegram"
        await bot.set_webhook(url, drop_pending_updates=True)
        log.info("webhook_set", url=url)
    else:
        log.warning("no_webhook_base_url", note="Set a webhook or use run_polling for local dev.")

    try:
        yield
    finally:
        await bot.session.close()


app = FastAPI(title="Peaceway Online", lifespan=lifespan)
app.include_router(telegram_webhook.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "peaceway-online"}
