"""Ask-the-Pharmacist flow (collects a question, alerts pharmacist, no medical advice)."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.bot.customer.states import AskFlow
from app.bot.keyboards.customer import back_to_menu
from app.core.db import get_session
from app.core.logging import get_logger
from app.models import Customer, PharmacistQuestion
from app.models.ops import StaffRole

router = Router(name="customer-support")
log = get_logger("support")

SAFETY = (
    "⚠️ I can pass your question to our pharmacist, but I can't give a diagnosis or "
    "emergency medical advice. For serious symptoms, please see a pharmacist in person "
    "or seek urgent medical care."
)


@router.callback_query(F.data == "menu:ask")
async def ask_start(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AskFlow.waiting_question)
    await call.message.edit_text(
        f"💬 <b>Ask the Pharmacist</b>\n\n{SAFETY}\n\nType your question below:",
        reply_markup=back_to_menu(),
    )
    await call.answer()


@router.message(AskFlow.waiting_question, F.text)
async def ask_received(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with get_session() as session:
        customer = (
            await session.execute(select(Customer).where(Customer.telegram_id == message.from_user.id))
        ).scalar_one_or_none()
        if customer is None:
            customer = Customer(telegram_id=message.from_user.id, full_name=message.from_user.full_name)
            session.add(customer)
            await session.flush()
        q = PharmacistQuestion(customer_id=customer.id, question=message.text.strip())
        session.add(q)
        cust_name = customer.full_name

    # Best-effort alert to pharmacist/owner.
    try:
        await _alert_pharmacist(message.bot, cust_name, message.from_user.id, message.text.strip())
    except Exception as exc:  # noqa: BLE001
        log.error("ask_alert_failed", error=str(exc))

    await message.answer(
        "✅ Thank you. Our pharmacist has received your question and will reply soon.",
        reply_markup=back_to_menu(),
    )


async def _alert_pharmacist(bot, cust_name, cust_id, text: str) -> None:
    from app.core.config import get_settings

    s = get_settings()
    recipients = s.pharmacist_ids | s.owner_ids
    body = (
        f"💬 <b>New pharmacist question</b>\n"
        f"From: {cust_name or 'customer'} (id <code>{cust_id}</code>)\n\n{text}"
    )
    for tid in recipients:
        try:
            await bot.send_message(tid, body)
        except Exception:  # noqa: BLE001
            continue
