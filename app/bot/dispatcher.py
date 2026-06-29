"""Bot and Dispatcher construction + router registration."""
from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.core.config import get_settings


def build_bot() -> Bot:
    settings = get_settings()
    return Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())

    # Routers are imported lazily so model/db imports stay ordered.
    from app.bot.customer import cart, catalog, checkout, followup, menu, payment
    from app.bot.staff import orders as staff_orders
    from app.bot.staff import panel as staff_panel

    # Staff routers first so staff commands take precedence.
    dp.include_router(staff_panel.router)
    dp.include_router(staff_orders.router)
    dp.include_router(menu.router)
    dp.include_router(catalog.router)
    dp.include_router(cart.router)
    dp.include_router(checkout.router)
    dp.include_router(payment.router)
    dp.include_router(followup.router)
    return dp
