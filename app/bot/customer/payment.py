"""Manual bank-transfer payment instructions and proof-of-payment upload."""
from __future__ import annotations

from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from app.bot.customer.states import PaymentFlow
from app.bot.keyboards.customer import back_to_menu
from app.core.config import get_settings
from app.core.db import get_session
from app.core.logging import get_logger
from app.models import Order, OrderStatus, Payment, PaymentMethod

router = Router(name="customer-payment")
log = get_logger("payment")


async def show_payment_instructions(call: CallbackQuery, order_code: str, total: Decimal) -> None:
    s = get_settings()
    bank_block = (
        f"🏦 <b>Bank Transfer</b>\n"
        f"Bank: {s.bank_name or '(set by admin)'}\n"
        f"Account Name: {s.bank_account_name or '(set by admin)'}\n"
        f"Account Number: <code>{s.bank_account_number or '(set by admin)'}</code>\n"
    )
    text = (
        f"💳 <b>Payment for {order_code}</b>\n\n"
        f"Amount: <b>₦{total:,.0f}</b>\n\n"
        f"{bank_block}\n"
        f"Use <b>{order_code}</b> as the transfer narration, then upload your proof of payment."
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="📤 Upload Proof of Payment", callback_data=f"pay:proof:{order_code}")
    kb.button(text="⬅️ Main Menu", callback_data="menu:home")
    kb.adjust(1)
    await call.message.edit_text(text, reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("pay:proof:"))
async def ask_proof(call: CallbackQuery, state: FSMContext) -> None:
    order_code = call.data.split("pay:proof:", 1)[1]
    await state.set_state(PaymentFlow.waiting_proof)
    await state.update_data(pay_order_code=order_code)
    await call.message.edit_text(
        "📤 Please send a photo or screenshot of your payment receipt.",
        reply_markup=back_to_menu(),
    )
    await call.answer()


@router.message(PaymentFlow.waiting_proof, F.photo)
async def got_proof(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    order_code = data.get("pay_order_code")
    file_id = message.photo[-1].file_id
    await state.clear()

    async with get_session() as session:
        order = (
            await session.execute(select(Order).where(Order.code == order_code))
        ).scalar_one_or_none()
        if order is None:
            await message.answer("Order not found. Please start again.", reply_markup=back_to_menu())
            return
        session.add(
            Payment(
                order_id=order.id,
                method=PaymentMethod.BANK_TRANSFER,
                amount=order.total,
                proof_file_id=file_id,
            )
        )
        from app.services.orders import transition_status

        order.payment_method = PaymentMethod.BANK_TRANSFER
        await transition_status(session, order, OrderStatus.PAYMENT_SUBMITTED, "customer", "Proof uploaded")
        order_id = order.id

    # Alert staff (best-effort).
    try:
        from app.services.alerts import alert_payment_submitted

        await alert_payment_submitted(message.bot, order_id)
    except Exception as exc:  # noqa: BLE001
        log.error("alert_failed", stage="payment_submitted", error=str(exc))

    await message.answer(
        f"✅ Thank you! Proof received for <b>{order_code}</b>.\n\n"
        "Our team will verify your payment and update you shortly.",
        reply_markup=back_to_menu(),
    )


@router.message(PaymentFlow.waiting_proof)
async def proof_not_photo(message: Message) -> None:
    await message.answer("Please send the receipt as a photo 📷.")
