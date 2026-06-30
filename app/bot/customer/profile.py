"""Customer "My Profile": view phone/email, update/remove email, notification prefs."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.customer.states import ProfileFlow
from app.bot.keyboards.customer import back_to_menu
from app.core.db import get_session
from app.models import CustomerPreferences
from app.services.customers import get_or_create_customer, is_valid_email, remove_email, save_email

router = Router(name="customer-profile")

_PREF_LABELS = {
    "receive_order_updates": "📦 Order updates",
    "receive_product_request_updates": "📝 Product request updates",
    "receive_pharmacist_replies": "💬 Pharmacist replies",
    "receive_delivery_updates": "🚚 Delivery updates",
    "receive_promotions": "🎁 Promotions",
    "receive_community_updates": "📢 Community updates",
}


async def _render_profile(call: CallbackQuery) -> None:
    async with get_session() as session:
        customer = await get_or_create_customer(session, call.from_user.id, call.from_user.full_name)
        email = customer.email
        phone = customer.phone
        opt_in = customer.email_opt_in

    text = (
        "👤 <b>My Profile</b>\n\n"
        f"Phone: {phone or 'not saved'}\n"
        f"Email: {email or 'not saved'}\n"
        f"Email opt-in: {'✅ yes' if opt_in else '🚫 no'}"
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Update Email", callback_data="profile:update_email")
    if email:
        kb.button(text="🗑 Remove Email", callback_data="profile:remove_email")
    kb.button(text="🔔 Notification Preferences", callback_data="profile:prefs")
    kb.button(text="🏠 Main Menu", callback_data="menu:home")
    kb.adjust(1)
    await call.message.edit_text(text, reply_markup=kb.as_markup())
    await call.answer()


@router.callback_query(F.data == "menu:profile")
async def profile_home(call: CallbackQuery) -> None:
    await _render_profile(call)


@router.callback_query(F.data == "profile:update_email")
async def ask_update_email(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ProfileFlow.waiting_email)
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Back", callback_data="menu:profile")
    await call.message.edit_text("📧 Please type your new email address.", reply_markup=kb.as_markup())
    await call.answer()


@router.message(ProfileFlow.waiting_email, F.text)
async def got_update_email(message: Message, state: FSMContext) -> None:
    email = message.text.strip()
    if not is_valid_email(email):
        await message.answer(
            "That email does not look correct. Please enter a valid email like name@example.com."
        )
        return
    await state.clear()
    async with get_session() as session:
        customer = await get_or_create_customer(session, message.from_user.id, message.from_user.full_name)
        await save_email(session, customer, email, "profile", message.from_user.id)
    await message.answer("✅ Thank you. Your email has been saved.", reply_markup=back_to_menu())


@router.callback_query(F.data == "profile:remove_email")
async def do_remove_email(call: CallbackQuery) -> None:
    async with get_session() as session:
        customer = await get_or_create_customer(session, call.from_user.id, call.from_user.full_name)
        await remove_email(session, customer, call.from_user.id)
    await call.answer("Email removed.")
    await _render_profile(call)


@router.callback_query(F.data == "profile:prefs")
async def show_prefs(call: CallbackQuery) -> None:
    async with get_session() as session:
        customer = await get_or_create_customer(session, call.from_user.id, call.from_user.full_name)
        prefs = await session.get(CustomerPreferences, customer.id)
        if prefs is None:
            prefs = CustomerPreferences(customer_id=customer.id)
            session.add(prefs)
            await session.flush()
        values = {k: getattr(prefs, k) for k in _PREF_LABELS}

    kb = InlineKeyboardBuilder()
    for key, label in _PREF_LABELS.items():
        flag = "✅" if values[key] else "⬜"
        kb.button(text=f"{flag} {label}", callback_data=f"profile:togglepref:{key}")
    kb.button(text="⬅️ Back", callback_data="menu:profile")
    kb.adjust(1)
    await call.message.edit_text("🔔 <b>Notification Preferences</b>\nTap to toggle:", reply_markup=kb.as_markup())
    await call.answer()


@router.callback_query(F.data.startswith("profile:togglepref:"))
async def toggle_pref(call: CallbackQuery) -> None:
    key = call.data.split("profile:togglepref:", 1)[1]
    if key not in _PREF_LABELS:
        await call.answer("Unknown preference.", show_alert=True)
        return
    async with get_session() as session:
        customer = await get_or_create_customer(session, call.from_user.id, call.from_user.full_name)
        prefs = await session.get(CustomerPreferences, customer.id)
        if prefs is None:
            prefs = CustomerPreferences(customer_id=customer.id)
            session.add(prefs)
            await session.flush()
        setattr(prefs, key, not getattr(prefs, key))
    await call.answer("Updated ✅")
    await show_prefs(call)
