"""Welcome flow and main menu handlers."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.bot.keyboards.customer import back_to_menu, main_menu
from app.core.db import get_session
from app.core.config import get_settings
from app.models import Customer

router = Router(name="customer-menu")

WELCOME = (
    "Welcome to <b>Peaceway Online</b>.\n\n"
    "Your licensed pharmacy in Igando is now online and delivering across Lagos.\n\n"
    "What do you need today?"
)


async def _ensure_customer(telegram_id: int, name: str | None) -> None:
    async with get_session() as session:
        existing = (
            await session.execute(select(Customer).where(Customer.telegram_id == telegram_id))
        ).scalar_one_or_none()
        if existing is None:
            session.add(Customer(telegram_id=telegram_id, full_name=name))


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await _ensure_customer(message.from_user.id, message.from_user.full_name)
    await message.answer(WELCOME, reply_markup=main_menu())


@router.callback_query(F.data == "menu:home")
async def back_home(call: CallbackQuery) -> None:
    await call.message.edit_text(WELCOME, reply_markup=main_menu())
    await call.answer()


@router.callback_query(F.data == "menu:areas")
async def delivery_areas(call: CallbackQuery) -> None:
    from app.models import DeliveryZone

    async with get_session() as session:
        zones = (
            await session.execute(
                select(DeliveryZone).where(DeliveryZone.is_active.is_(True)).order_by(DeliveryZone.fee)
            )
        ).scalars().all()
    if zones:
        lines = "\n".join(f"• <b>{z.name}</b> — ₦{z.fee:,.0f}" for z in zones)
        text = f"📍 <b>Delivery areas & fees</b>\n\n{lines}\n\nDon't see your area? Choose “Other Lagos areas”."
    else:
        text = "Delivery areas are being set up. Please check back shortly."
    await call.message.edit_text(text, reply_markup=back_to_menu())
    await call.answer()


@router.callback_query(F.data == "menu:human")
async def speak_to_human(call: CallbackQuery) -> None:
    name = get_settings().pharmacy_name
    text = (
        f"🧑‍⚕️ A team member from {name} will assist you.\n\n"
        "Please type your message and we'll get back to you. For emergencies, "
        "visit the nearest hospital or call emergency services."
    )
    await call.message.edit_text(text, reply_markup=back_to_menu())
    await call.answer()
