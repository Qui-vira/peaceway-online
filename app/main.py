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
from app.webhooks import flutterwave as flutterwave_webhook
from app.webhooks import logistics as logistics_webhook
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
    from app.services.rbac_service import seed_roles_and_permissions

    start_scheduler()
    # Keep the roles/permissions catalog in sync with the code matrix.
    try:
        await seed_roles_and_permissions()
    except Exception as exc:  # noqa: BLE001
        log.error("rbac_seed_failed", error=str(exc))

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
app.include_router(logistics_webhook.router)
app.include_router(flutterwave_webhook.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "peaceway-online"}
