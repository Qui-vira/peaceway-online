"""Manual bank-transfer payment instructions and proof-of-payment upload."""
from __future__ import annotations

from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from sqlalchemy import select as _select

from app.bot.customer.states import PaymentFlow
from app.bot.keyboards.customer import back_to_menu
from app.core.config import get_settings
from app.core.db import get_session
from app.core.logging import get_logger
from app.models import FeeSetting, Order, OrderStatus, Payment, PaymentMethod
from app.services.payments.crypto import crypto_enabled

router = Router(name="customer-payment")
log = get_logger("payment")


async def show_payment_methods(call: CallbackQuery, order_code: str, total) -> None:
    """Offer enabled payment methods for an order."""
    async with get_session() as session:
        fee = await session.get(FeeSetting, 1)
    s = get_settings()
    kb = InlineKeyboardBuilder()
    if not fee or fee.enable_bank:
        kb.button(text="🏦 Bank Transfer", callback_data=f"pm:bank:{order_code}")
    if (not fee or fee.enable_flutterwave) and s.flutterwave_enabled:
        kb.button(text="💳 Pay with Flutterwave", callback_data=f"pm:flw:{order_code}")
    if crypto_enabled(fee):
        kb.button(text="🪙 Pay with Crypto", callback_data=f"pm:crypto:{order_code}")
    kb.button(text="⬅️ Main Menu", callback_data="menu:home")
    kb.adjust(1)
    await call.message.edit_text(
        f"💳 <b>Payment for {order_code}</b>\nAmount: <b>₦{total:,.0f}</b>\n\nChoose how to pay:",
        reply_markup=kb.as_markup(),
    )


@router.callback_query(F.data.startswith("pm:bank:"))
async def chose_bank(call: CallbackQuery) -> None:
    code = call.data.split("pm:bank:", 1)[1]
    async with get_session() as session:
        order = (await session.execute(_select(Order).where(Order.code == code))).scalar_one_or_none()
        if order is None:
            await call.answer("Order not found.", show_alert=True)
            return
        order.payment_method = PaymentMethod.BANK_TRANSFER
        total = order.total
    await show_payment_instructions(call, code, total)
    await call.answer()


@router.callback_query(F.data.startswith("pm:flw:"))
async def chose_flutterwave(call: CallbackQuery) -> None:
    code = call.data.split("pm:flw:", 1)[1]
    from app.services.payments.flutterwave import create_payment_link

    async with get_session() as session:
        order = (await session.execute(_select(Order).where(Order.code == code))).scalar_one_or_none()
        if order is None:
            await call.answer("Order not found.", show_alert=True)
            return
        order.payment_method = PaymentMethod.FLUTTERWAVE
        amount, name = order.total, order.delivery_name
    link = await create_payment_link(order_code=code, amount=amount, email="", name=name or "Customer")
    if not link:
        await call.answer("Flutterwave is not available right now. Please use bank transfer.", show_alert=True)
        return
    kb = InlineKeyboardBuilder()
    kb.button(text="💳 Pay Now", url=link)
    kb.button(text="⬅️ Main Menu", callback_data="menu:home")
    kb.adjust(1)
    await call.message.edit_text(
        f"💳 Tap below to pay ₦{amount:,.0f} for {code} securely via Flutterwave.",
        reply_markup=kb.as_markup(),
    )
    await call.answer()


async def show_payment_instructions(call: CallbackQuery, order_code: str, total: Decimal) -> None:
    s = get_settings()
    accounts = s.bank_account_list
    if accounts:
        blocks = []
        for a in accounts:
            blocks.append(
                f"🏦 <b>{a['bank'] or 'Bank'}</b>\n"
                f"Account Name: {a['name'] or '-'}\n"
                f"Account Number: <code>{a['number']}</code>"
            )
        bank_block = "\n\n".join(blocks)
    else:
        bank_block = "🏦 <b>Bank Transfer</b>\n(payment account being set up by admin)"
    text = (
        f"💳 <b>Payment for {order_code}</b>\n\n"
        f"Amount: <b>₦{total:,.0f}</b>\n\n"
        f"Transfer to any of these accounts:\n\n"
        f"{bank_block}\n\n"
        f"💡 You can pay from any bank or OPay app. Just transfer to the account number above.\n\n"
        f"Use <b>{order_code}</b> as the transfer narration/reference, then tap "
        f"<b>Upload Proof of Payment</b> below."
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="📤 Upload Proof of Payment", callback_data=f"pay:proof:{order_code}")
    kb.button(text="⬅️ Main Menu", callback_data="menu:home")
    kb.adjust(1)
    await call.message.edit_text(text, reply_markup=kb.as_markup())


async def _render_ask_proof(call: CallbackQuery, state: FSMContext, order_code: str) -> None:
    await state.set_state(PaymentFlow.waiting_proof)
    await state.update_data(pay_order_code=order_code)
    await call.message.edit_text(
        "📤 Please send a photo or screenshot of your payment receipt.",
        reply_markup=back_to_menu(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("pay:proof:"))
async def ask_proof(call: CallbackQuery, state: FSMContext) -> None:
    from app.bot.customer.email_gate import ensure_email

    order_code = call.data.split("pay:proof:", 1)[1]
    if not await ensure_email(
        call, state, source="payment", resume=lambda: _render_ask_proof(call, state, order_code)
    ):
        return
    await _render_ask_proof(call, state, order_code)


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
