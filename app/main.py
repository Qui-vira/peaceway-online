"""FastAPI application hosting the Telegram webhook + provider webhooks + health.

In production (WEBHOOK_BASE_URL set) the bot runs in webhook mode. For local
development without a public URL, run ``python -m app.run_polling`` instead.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.v1.router import router as api_v1_router
from app.bot.dispatcher import build_bot, build_dispatcher, set_bot_commands
from app.core.db import async_session
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
    from app.services.web_customers import ensure_web_customer_columns

    start_scheduler()
    # Keep older databases compatible with the current web auth schema.
    try:
        async with async_session() as session:
            await ensure_web_customer_columns(session)
            await session.commit()
    except Exception as exc:  # noqa: BLE001
        log.error("web_customer_schema_patch_failed", error=str(exc))

    # Keep the roles/permissions catalog in sync with the code matrix.
    try:
        await seed_roles_and_permissions()
    except Exception as exc:  # noqa: BLE001
        log.error("rbac_seed_failed", error=str(exc))

    try:
        await set_bot_commands(bot)
    except Exception as exc:  # noqa: BLE001
        log.error("set_commands_failed", error=str(exc))

    log.info(
        "resend_status",
        enabled=settings.resend_enabled,
        from_email=settings.resend_from_email or "(not set)",
    )

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

# CORS - allow the Vercel web frontend to call /api/v1/* from the browser.
# Origins are configured via ALLOWED_ORIGINS env var (comma-separated).
# Telegram webhooks are server-to-server and are unaffected by CORS.
_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.allowed_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    max_age=3600,
)

# Compress JSON/text responses (catalog + order lists are the payloads that
# benefit). Only kicks in above ~500 bytes and when the client sends
# Accept-Encoding: gzip, so small webhook acks stay uncompressed.
app.add_middleware(GZipMiddleware, minimum_size=500)

# Existing Telegram + payment + logistics webhooks - order and paths unchanged.
app.include_router(telegram_webhook.router)
app.include_router(logistics_webhook.router)
app.include_router(flutterwave_webhook.router)

# Web API - mounted under /api/v1 so it never collides with bot webhook paths.
app.include_router(api_v1_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "peaceway-online"}
