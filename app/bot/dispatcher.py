"""Bot and Dispatcher construction + router registration."""
from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
)

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("dispatcher")

# Commands every customer sees in the Telegram "/" menu.
PUBLIC_COMMANDS = [
    BotCommand(command="start", description="Start / main menu"),
    BotCommand(command="help", description="How to use Peaceway Online"),
    BotCommand(command="howitworks", description="How ordering works"),
    BotCommand(command="track", description="Track my order"),
    BotCommand(command="myid", description="Show my Telegram ID"),
]

# Extra commands shown only to staff (added on top of the public set).
STAFF_EXTRA_COMMANDS = [BotCommand(command="admin", description="Staff panel")]


def build_bot() -> Bot:
    settings = get_settings()
    return Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


async def set_bot_commands(bot: Bot) -> None:
    """Register slash commands with Telegram so they appear in the '/' menu.

    Public set for all private chats; owners/staff additionally get /admin scoped
    to their own chat.
    """
    await bot.set_my_commands(PUBLIC_COMMANDS, scope=BotCommandScopeAllPrivateChats())

    # Owner(s) from env + any active admins get the staff command set in their chat.
    staff_ids: set[int] = set(get_settings().owner_ids)
    try:
        from sqlalchemy import select

        from app.core.db import get_session
        from app.models import AdminUser

        async with get_session() as session:
            rows = (
                await session.execute(select(AdminUser.telegram_id).where(AdminUser.is_active.is_(True)))
            ).scalars().all()
            staff_ids |= set(rows)
    except Exception as exc:  # noqa: BLE001
        log.error("staff_commands_lookup_failed", error=str(exc))

    for tid in staff_ids:
        try:
            await bot.set_my_commands(
                PUBLIC_COMMANDS + STAFF_EXTRA_COMMANDS, scope=BotCommandScopeChat(chat_id=tid)
            )
        except Exception as exc:  # noqa: BLE001
            log.error("set_staff_commands_failed", telegram_id=tid, error=str(exc))
    log.info("bot_commands_registered", public=len(PUBLIC_COMMANDS), staff_chats=len(staff_ids))


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())

    # Stamp the acting identity onto each update's context for DB-layer access
    # control. Registered on message + callback_query (where event_from_user exists).
    from app.bot.middleware import ActorContextMiddleware

    _actor_mw = ActorContextMiddleware()
    dp.message.middleware(_actor_mw)
    dp.callback_query.middleware(_actor_mw)

    # Routers are imported lazily so model/db imports stay ordered.
    from app.bot.customer import (
        cart,
        catalog,
        checkout,
        crypto,
        email_gate,
        followup,
        menu,
        payment,
        prescription,
        product_request,
        profile,
        support,
        track,
        track_requests,
    )
    from app.bot.staff import admins as staff_admins
    from app.bot.staff import break_glass as staff_break_glass
    from app.bot.staff import chatid as staff_chatid
    from app.bot.staff import checklist as staff_checklist
    from app.bot.staff import orientation as staff_orientation
    from app.bot.staff import crypto as staff_crypto
    from app.bot.staff import delivery as staff_delivery
    from app.bot.staff import fallback as staff_fallback
    from app.bot.staff import orders as staff_orders
    from app.bot.staff import panel as staff_panel
    from app.bot.staff import pharmacist as staff_pharmacist
    from app.bot.staff import prescriptions as staff_prescriptions
    from app.bot.staff import products as staff_products
    from app.bot.staff import products_backfill as staff_products_backfill
    from app.bot.staff import products_csv as staff_products_csv
    from app.bot.staff import riders as staff_riders
    from app.bot.staff import customers as staff_customers
    from app.bot.staff import orders_admin as staff_orders_admin
    from app.bot.staff import payments_admin as staff_payments_admin
    from app.bot.staff import requests as staff_requests
    from app.bot.staff import scan as staff_scan
    from app.bot.staff import inventory_scan as staff_inventory_scan

    # Staff routers first so staff commands take precedence.
    # staff_delivery & staff_crypto must precede staff_orders so their specific
    # `act:book:` / `act:crypto_*` callbacks aren't caught by the generic `act:` handler.
    dp.include_router(staff_panel.router)
    dp.include_router(staff_admins.router)
    dp.include_router(staff_break_glass.router)
    dp.include_router(staff_riders.router)
    dp.include_router(staff_chatid.router)
    dp.include_router(staff_checklist.router)
    dp.include_router(staff_orientation.router)
    dp.include_router(staff_products.router)
    dp.include_router(staff_products_backfill.router)
    dp.include_router(staff_products_csv.router)
    dp.include_router(staff_scan.router)
    dp.include_router(staff_inventory_scan.router)
    dp.include_router(staff_pharmacist.router)
    dp.include_router(staff_prescriptions.router)
    dp.include_router(staff_requests.router)
    dp.include_router(staff_customers.router)
    dp.include_router(staff_orders_admin.router)
    dp.include_router(staff_payments_admin.router)
    dp.include_router(staff_delivery.router)
    dp.include_router(staff_crypto.router)
    dp.include_router(staff_orders.router)
    # Fallback LAST so it only catches unhandled staff:* callbacks.
    dp.include_router(staff_fallback.router)
    dp.include_router(email_gate.router)
    dp.include_router(menu.router)
    dp.include_router(profile.router)
    dp.include_router(catalog.router)
    dp.include_router(cart.router)
    dp.include_router(checkout.router)
    dp.include_router(payment.router)
    dp.include_router(crypto.router)
    dp.include_router(track.router)
    dp.include_router(track_requests.router)
    dp.include_router(prescription.router)
    dp.include_router(product_request.router)
    dp.include_router(support.router)
    dp.include_router(followup.router)

    # Registered last: turns any unhandled handler exception into a logged traceback
    # plus a visible apology, instead of a silently dead button.
    from app.bot.errors import on_bot_error

    dp.errors.register(on_bot_error)
    return dp
