"""Staff logistics actions: choose a provider and book a delivery."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from app.core.db import get_session
from app.core.security import get_role_keys, has
from app.models import Order
from app.services.delivery.registry import enabled_providers
from app.services.delivery.service import book_delivery

router = Router(name="staff-delivery")


@router.callback_query(F.data.startswith("act:book:"))
async def choose_provider(call: CallbackQuery) -> None:
    role_keys = await get_role_keys(call.from_user.id)
    if not has(role_keys, "assign_rider"):
        await call.answer("Not authorised.", show_alert=True)
        return
    code = call.data.split("act:book:", 1)[1]
    providers = enabled_providers()
    kb = InlineKeyboardBuilder()
    for p in providers:
        kb.button(text=f"🚀 {p.name}", callback_data=f"book:{p.key}:{code}")
    kb.button(text="⬅️ Back", callback_data=f"staff:order:{code}")
    kb.adjust(1)
    note = "" if len(providers) > 1 else "\n\n<i>Only Manual is active. Add partner API keys to enable Kwik/Fez/Gokada.</i>"
    await call.message.edit_text(
        f"🚀 <b>Book delivery for {code}</b>\nChoose a logistics provider:{note}",
        reply_markup=kb.as_markup(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("book:"))
async def do_book(call: CallbackQuery) -> None:
    role_keys = await get_role_keys(call.from_user.id)
    if not has(role_keys, "assign_rider"):
        await call.answer("Not authorised.", show_alert=True)
        return
    _, provider_key, code = call.data.split(":", 2)
    async with get_session() as session:
        order = (await session.execute(select(Order).where(Order.code == code))).scalar_one_or_none()
        if order is None:
            await call.answer("Order not found.", show_alert=True)
            return
        order_id = order.id

    delivery = await book_delivery(order_id, provider_key)
    if delivery is None:
        await call.answer("That provider is not available.", show_alert=True)
        return
    await call.message.edit_text(
        f"✅ Delivery booked for {code} via <b>{provider_key}</b>.\n"
        f"Reference: <code>{delivery.provider_delivery_id}</code>",
    )
    await call.answer("Booked ✅")
