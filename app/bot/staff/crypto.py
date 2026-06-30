"""Staff crypto-payment review: confirm on-chain receipt and Naira settlement.

These are deliberately two separate manual confirmations — no automated
crypto->Naira settlement.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select

from app.core.db import get_session
from app.core.security import get_role_keys, has, primary_role
from app.models import (
    AuditLog,
    CryptoPayment,
    CryptoStatus,
    Order,
    OrderStatus,
    RxStatus,
)
from app.services import orders as orders_svc

router = Router(name="staff-crypto")


async def _load_crypto(session, order_id):
    return (
        await session.execute(
            select(CryptoPayment).where(CryptoPayment.order_id == order_id).order_by(CryptoPayment.created_at.desc())
        )
    ).scalars().first()


@router.callback_query(F.data.startswith("act:crypto_confirm:"))
async def confirm_onchain(call: CallbackQuery) -> None:
    role_keys = await get_role_keys(call.from_user.id)
    if not has(role_keys, "approve_payment"):
        await call.answer("Not authorised.", show_alert=True)
        return
    code = call.data.split("act:crypto_confirm:", 1)[1]
    by = f"{primary_role(role_keys) or 'staff'}:{call.from_user.id}"
    customer_chat = None
    async with get_session() as session:
        order = (await session.execute(select(Order).where(Order.code == code))).scalar_one_or_none()
        if order is None:
            await call.answer("Order not found.", show_alert=True)
            return
        cp = await _load_crypto(session, order.id)
        if cp:
            cp.status = CryptoStatus.CONFIRMED
            cp.reviewed_by = by
        await orders_svc.transition_status(session, order, OrderStatus.PAYMENT_APPROVED, by, "Crypto on-chain confirmed")
        if order.rx_status == RxStatus.NOT_REQUIRED:
            await orders_svc.transition_status(session, order, OrderStatus.PROCESSING, "system", "Auto: crypto confirmed")
        session.add(AuditLog(actor_telegram_id=call.from_user.id, actor_role=by, action="crypto_confirm", entity="order", entity_id=code))
        from app.models import Customer

        customer = await session.get(Customer, order.customer_id)
        customer_chat = customer.telegram_id if customer else None

    if customer_chat:
        try:
            await call.bot.send_message(customer_chat, f"✅ Crypto payment for {code} confirmed. We're preparing your order.")
        except Exception:  # noqa: BLE001
            pass
    await call.message.edit_text(f"🔗 On-chain payment confirmed for {code}. Awaiting Naira settlement confirmation.")
    await call.answer("Confirmed ✅")


@router.callback_query(F.data.startswith("act:crypto_settled:"))
async def confirm_settled(call: CallbackQuery) -> None:
    role_keys = await get_role_keys(call.from_user.id)
    if not has(role_keys, "edit_pricing"):  # owner-level
        await call.answer("Only the owner can confirm Naira settlement.", show_alert=True)
        return
    code = call.data.split("act:crypto_settled:", 1)[1]
    by = f"{primary_role(role_keys) or 'staff'}:{call.from_user.id}"
    async with get_session() as session:
        order = (await session.execute(select(Order).where(Order.code == code))).scalar_one_or_none()
        if order is None:
            await call.answer("Order not found.", show_alert=True)
            return
        cp = await _load_crypto(session, order.id)
        if cp:
            cp.status = CryptoStatus.SETTLED
            cp.naira_settled = True
            cp.reviewed_by = by
        session.add(AuditLog(actor_telegram_id=call.from_user.id, actor_role=by, action="crypto_settled", entity="order", entity_id=code))
    await call.message.edit_text(f"💵 Naira settlement confirmed for {code}.")
    await call.answer("Settled ✅")
