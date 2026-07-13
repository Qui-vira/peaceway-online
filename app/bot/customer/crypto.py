"""Customer crypto off-ramp flow (Phase 3 - optional, manual settlement)."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from app.bot.customer.states import CryptoFlow
from app.bot.keyboards.customer import back_to_menu
from app.core.db import get_session
from app.core.logging import get_logger
from app.models import CryptoPayment, FeeSetting, Order, OrderStatus, PaymentMethod
from app.services import orders as orders_svc
from app.services.payments.crypto import available_wallets, find_wallet, total_with_offramp

router = Router(name="customer-crypto")
log = get_logger("crypto")


@router.callback_query(F.data.startswith("pm:crypto:"))
async def choose_network(call: CallbackQuery) -> None:
    code = call.data.split("pm:crypto:", 1)[1]
    wallets = available_wallets()
    if not wallets:
        await call.answer("Crypto payment isn't configured yet.", show_alert=True)
        return
    kb = InlineKeyboardBuilder()
    for w in wallets:
        kb.button(text=f"{w['network']} · {w['token']}", callback_data=f"cw:{w['network']}:{w['token']}:{code}")
    kb.button(text="⬅️ Main Menu", callback_data="menu:home")
    kb.adjust(1)
    await call.message.edit_text(
        "🪙 <b>Crypto payment</b>\nChoose network & token:", reply_markup=kb.as_markup()
    )
    await call.answer()


@router.callback_query(F.data.startswith("cw:"))
async def show_wallet(call: CallbackQuery, state: FSMContext) -> None:
    _, network, token, code = call.data.split(":", 3)
    wallet = find_wallet(network, token)
    if wallet is None:
        await call.answer("That wallet is unavailable.", show_alert=True)
        return
    async with get_session() as session:
        order = (await session.execute(select(Order).where(Order.code == code))).scalar_one_or_none()
        if order is None:
            await call.answer("Order not found.", show_alert=True)
            return
        fee = await session.get(FeeSetting, 1)
        # Crypto adds the off-ramp fee on top; recompute + persist the new total.
        new_total = total_with_offramp(order, fee)
        order.payment_method = PaymentMethod.CRYPTO
        order.offramp_fee = fee.offramp_fee if fee else order.offramp_fee
        order.total = new_total
        cp = CryptoPayment(
            order_id=order.id,
            network=network,
            token=token,
            wallet_address=wallet["address"],
            expected_amount=new_total,
        )
        session.add(cp)

    await state.set_state(CryptoFlow.waiting_tx_hash)
    await state.update_data(crypto_order_code=code)
    text = (
        f"🪙 <b>Pay with {token} on {network}</b>\n\n"
        f"Order: {code}\n"
        f"Amount (incl. off-ramp fee): <b>₦{new_total:,.0f}</b>\n\n"
        f"Send the equivalent {token} to:\n<code>{wallet['address']}</code>\n\n"
        "After paying, reply with your <b>transaction hash</b>. "
        "An admin will confirm receipt before your order proceeds."
    )
    await call.message.edit_text(text, reply_markup=back_to_menu())
    await call.answer()


@router.message(CryptoFlow.waiting_tx_hash, F.text)
async def got_tx_hash(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    code = data.get("crypto_order_code")
    tx = message.text.strip()
    await state.clear()

    async with get_session() as session:
        order = (await session.execute(select(Order).where(Order.code == code))).scalar_one_or_none()
        if order is None:
            await message.answer("Order not found.", reply_markup=back_to_menu())
            return
        cp = (
            await session.execute(
                select(CryptoPayment).where(CryptoPayment.order_id == order.id).order_by(CryptoPayment.created_at.desc())
            )
        ).scalars().first()
        if cp:
            from app.models import CryptoStatus

            cp.tx_hash = tx
            cp.status = CryptoStatus.SUBMITTED
        await orders_svc.transition_status(session, order, OrderStatus.PAYMENT_SUBMITTED, "customer", "Crypto tx submitted")
        order_id = order.id

    try:
        from app.services.alerts import alert_payment_submitted

        await alert_payment_submitted(message.bot, order_id)
    except Exception as exc:  # noqa: BLE001
        log.error("crypto_alert_failed", error=str(exc))

    await message.answer(
        f"✅ Transaction hash received for {code}. We'll confirm on-chain and update you shortly.",
        reply_markup=back_to_menu(),
    )
