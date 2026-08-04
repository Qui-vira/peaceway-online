"""Welcome flow and main menu handlers."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.bot.keyboards.customer import back_to_menu, help_menu, how_it_works_menu, main_menu
from app.core.db import get_session
from app.core.config import get_settings
from app.services.customers import get_or_create_customer

router = Router(name="customer-menu")

WELCOME = (
    "Welcome to <b>Peaceway Online</b>.\n\n"
    "A licensed pharmacy. Every order is reviewed by a registered pharmacist "
    "before it is dispensed.\n\n"
    "What do you need today?"
)

HELP_TEXT = (
    "ℹ️ <b>Peaceway Online Help</b>\n\n"
    "🛒 <b>How to order</b>\n"
    "Tap Order Medicine, search or browse, add to cart, then checkout.\n\n"
    "💳 <b>Payment</b>\n"
    "After checkout, transfer to our account and upload your proof of payment. "
    "We confirm it before preparing your order.\n\n"
    "🚚 <b>Delivery</b>\n"
    "Pick your area at checkout. The fee is shown before you pay.\n\n"
    "💬 <b>Ask the Pharmacist</b>\n"
    "Tap Ask the Pharmacist to send a question. Our pharmacist replies here in chat.\n\n"
    "📦 <b>Track your order</b>\n"
    "Tap Track Order or send /track to see your order status and delivery progress.\n\n"
    "👨‍⚕️ <b>Contact support</b>\n"
    "Tap Speak to Support for help with anything.\n\n"
    "💊 <b>Prescription safety</b>\n"
    "Prescription-only medicines are dispensed solely against a valid prescription from a "
    "licensed healthcare provider in Nigeria. Our Superintendent Pharmacist reviews every one.\n"
    "We do not give diagnosis or emergency advice. For serious symptoms, see a pharmacist "
    "in person or seek urgent medical care.\n\n"
    "Send /start anytime to return to the main menu."
)

HOW_IT_WORKS_TEXT = (
    "📋 <b>How It Works</b>\n\n"
    "1️⃣ <b>Order Medicine</b>\n"
    "Search or browse, then add items to your cart.\n\n"
    "2️⃣ <b>Checkout</b>\n"
    "Enter your details and pick your area. The delivery fee is shown before you pay.\n\n"
    "3️⃣ <b>Pay</b>\n"
    "Transfer to our account and upload your proof of payment.\n\n"
    "4️⃣ <b>Pharmacist review, then dispensing</b>\n"
    "A registered pharmacist checks the order before it is dispensed.\n\n"
    "5️⃣ <b>Delivered</b>\n"
    "We check in afterwards to confirm you received the right medicine.\n\n"
    "💊 Prescription-only medicines are not supplied without a valid prescription."
)


async def _ensure_customer(telegram_id: int, name: str | None) -> None:
    async with get_session() as session:
        await get_or_create_customer(session, telegram_id, name)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await _ensure_customer(message.from_user.id, message.from_user.full_name)
    await message.answer(WELCOME, reply_markup=main_menu())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=help_menu())


@router.message(Command("howitworks"))
async def cmd_how(message: Message) -> None:
    await message.answer(HOW_IT_WORKS_TEXT, reply_markup=how_it_works_menu())


@router.callback_query(F.data == "menu:how")
async def how_it_works(call: CallbackQuery) -> None:
    await call.message.edit_text(HOW_IT_WORKS_TEXT, reply_markup=how_it_works_menu())
    await call.answer()


@router.callback_query(F.data == "menu:help")
async def help_cb(call: CallbackQuery) -> None:
    await call.message.edit_text(HELP_TEXT, reply_markup=help_menu())
    await call.answer()


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
        lines = "\n".join(f"• <b>{z.name}</b>  ₦{z.fee:,.0f}" for z in zones)
        text = f"📍 <b>Delivery areas and fees</b>\n\n{lines}\n\nDon't see your area? Choose “Other Lagos areas”."
    else:
        text = "Delivery areas are being set up. Please check back shortly."
    await call.message.edit_text(text, reply_markup=back_to_menu())
    await call.answer()


async def _render_speak_to_human(call: CallbackQuery) -> None:
    name = get_settings().pharmacy_name
    text = (
        f"🧑‍⚕️ A team member from {name} will assist you.\n\n"
        "Please type your message and we'll get back to you. For emergencies, "
        "visit the nearest hospital or call emergency services."
    )
    await call.message.edit_text(text, reply_markup=back_to_menu())
    await call.answer()


@router.callback_query(F.data == "menu:human")
async def speak_to_human(call: CallbackQuery, state: FSMContext) -> None:
    from app.bot.customer.email_gate import ensure_email

    if not await ensure_email(call, state, source="support", resume=lambda: _render_speak_to_human(call)):
        return
    await _render_speak_to_human(call)
