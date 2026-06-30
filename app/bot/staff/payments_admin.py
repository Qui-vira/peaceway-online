"""Payments Review: proof queue, approve/reject, request clearer proof, history.

Approval rules:
  - approve_payment / reject_payment permissions gate the action buttons.
  - view_payment_status grants read-only access (Sales/Support): list + detail,
    no approve/reject/clearer buttons.
  - Every approve/reject is written to AuditLog (entity="payment").
  - Approving is blocked if the order's Rx items aren't pharmacist-cleared
    (enforced in app.services.payments_admin.approve_payment).
"""
from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from app.bot.staff.states import PaymentAdminFlow
from app.core.db import get_session
from app.core.logging import get_logger
from app.core.security import get_role_keys, has, primary_role
from app.models import AuditLog, Customer, Order, Payment, PaymentStatus
from app.services import alerts
from app.services import payments_admin as payments_admin_svc

router = Router(name="staff-payments-admin")
log = get_logger("payments-admin")

_DEFAULT_CLEARER_MSG = (
    "📸 We couldn't clearly verify your payment proof. Please send a clearer photo "
    "or screenshot showing the full transaction details (amount, date, reference)."
)


def _can_view(role_keys: set[str]) -> bool:
    return has(role_keys, "view_payment_status") or has(role_keys, "approve_payment") or has(role_keys, "reject_payment")


def _can_act(role_keys: set[str]) -> bool:
    return has(role_keys, "approve_payment") or has(role_keys, "reject_payment")


async def _guard(call: CallbackQuery) -> set[str] | None:
    role_keys = await get_role_keys(call.from_user.id)
    if not _can_view(role_keys):
        await call.answer("Not authorised.", show_alert=True)
        return None
    return role_keys


async def _audit(session, telegram_id: int, role_keys: set[str], action: str, payment_id: str, detail: dict | None = None) -> None:
    session.add(
        AuditLog(
            actor_telegram_id=telegram_id,
            actor_role=",".join(sorted(role_keys)) if role_keys else None,
            action=action,
            entity="payment",
            entity_id=payment_id,
            detail=detail,
        )
    )


# ── Menu ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "staff:payments")
async def payments_home(call: CallbackQuery, state: FSMContext) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        return
    await state.clear()
    kb = InlineKeyboardBuilder()
    kb.button(text="📥 Proof Queue", callback_data="payadm:queue")
    kb.button(text="🕐 Payment History", callback_data="payadm:history")
    kb.button(text="🏠 Staff Menu", callback_data="staff:home")
    kb.adjust(1)
    await call.message.edit_text("💵 <b>Payments</b>", reply_markup=kb.as_markup())
    await call.answer()


@router.callback_query(F.data == "staff:paystatus")
async def payments_status_view(call: CallbackQuery, state: FSMContext) -> None:
    """View-only entry for roles with view_payment_status but not approve/reject."""
    await payments_home(call, state)


# ── Queue / history lists ───────────────────────────────────────────────────

@router.callback_query(F.data == "payadm:queue")
async def proof_queue(call: CallbackQuery) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        return
    async with get_session() as session:
        payments = (
            await session.execute(
                select(Payment)
                .where(Payment.status == PaymentStatus.PENDING)
                .order_by(Payment.created_at.desc())
                .limit(20)
            )
        ).scalars().all()
        rows = []
        for p in payments:
            order = await session.get(Order, p.order_id)
            rows.append((p, order))

    kb = InlineKeyboardBuilder()
    for p, order in rows:
        code = order.code if order else "?"
        kb.button(text=f"{code} · ₦{p.amount:,.0f} · {p.method.value}", callback_data=f"payadm:view:{p.id}")
    kb.button(text="⬅️ Back", callback_data="staff:payments")
    kb.adjust(1)
    text = f"📥 <b>Proof Queue</b>\n({len(rows)} pending)" if rows else "📥 <b>Proof Queue</b>\nNothing pending."
    await call.message.edit_text(text, reply_markup=kb.as_markup())
    await call.answer()


@router.callback_query(F.data == "payadm:history")
async def payment_history(call: CallbackQuery) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        return
    async with get_session() as session:
        payments = (
            await session.execute(
                select(Payment)
                .where(Payment.status.in_([PaymentStatus.APPROVED, PaymentStatus.REJECTED]))
                .order_by(Payment.updated_at.desc())
                .limit(30)
            )
        ).scalars().all()
        rows = []
        for p in payments:
            order = await session.get(Order, p.order_id)
            rows.append((p, order))

    kb = InlineKeyboardBuilder()
    for p, order in rows:
        code = order.code if order else "?"
        icon = "✅" if p.status == PaymentStatus.APPROVED else "❌"
        kb.button(text=f"{icon} {code} · ₦{p.amount:,.0f}", callback_data=f"payadm:view:{p.id}")
    kb.button(text="⬅️ Back", callback_data="staff:payments")
    kb.adjust(1)
    text = f"🕐 <b>Payment History</b>\n({len(rows)} recent)" if rows else "🕐 <b>Payment History</b>\nNo records yet."
    await call.message.edit_text(text, reply_markup=kb.as_markup())
    await call.answer()


# ── Payment detail ───────────────────────────────────────────────────────────

async def _detail_text(payment: Payment, order: Order | None, customer: Customer | None) -> str:
    lines = [
        f"💵 <b>Payment</b> · {payment.status.value}",
        f"Order: {order.code if order else '?'}",
        f"Amount: ₦{payment.amount:,.0f}",
        f"Method: {payment.method.value}",
    ]
    if payment.provider_ref:
        lines.append(f"Reference: {payment.provider_ref}")
    if customer:
        lines.append("")
        lines.append(f"Customer: {customer.full_name or '-'}")
        lines.append(f"Telegram ID: <code>{customer.telegram_id}</code>")
        lines.append(f"Phone: {customer.phone or '-'}")
        lines.append(f"Email: {customer.email or 'not on file'}")
    if order:
        lines.append("")
        lines.append(f"Order status: {order.status.value}")
        if order.rx_status.value != "NOT_REQUIRED":
            lines.append(f"Rx status: {order.rx_status.value}")
    if payment.verified_by:
        lines.append("")
        lines.append(f"Verified by: {payment.verified_by}")
    if payment.note:
        lines.append(f"Note: {payment.note}")
    lines.append("")
    lines.append(f"Submitted: {payment.created_at.strftime('%Y-%m-%d %H:%M')}")
    return "\n".join(lines)


async def _show_payment(message_or_call, payment_id: UUID, role_keys: set[str], *, is_callback: bool) -> None:
    async with get_session() as session:
        payment = await session.get(Payment, payment_id)
        if payment is None:
            if is_callback:
                await message_or_call.answer("Payment not found.", show_alert=True)
            else:
                await message_or_call.answer("Payment not found.")
            return
        order = await session.get(Order, payment.order_id)
        customer = await session.get(Customer, order.customer_id) if order else None
        text = await _detail_text(payment, order, customer)
        proof_file_id = payment.proof_file_id

    kb = InlineKeyboardBuilder()
    if payment.status == PaymentStatus.PENDING:
        if has(role_keys, "approve_payment"):
            kb.button(text="✅ Approve", callback_data=f"payadm:approve:{payment_id}")
        if has(role_keys, "reject_payment"):
            kb.button(text="❌ Reject", callback_data=f"payadm:reject:{payment_id}")
            kb.button(text="📸 Request Clearer Proof", callback_data=f"payadm:clearer:{payment_id}")
    if has(role_keys, "message_customer"):
        kb.button(text="💬 Message Customer", callback_data=f"payadm:msg:{payment_id}")
    kb.button(text="⬅️ Back", callback_data="staff:payments")
    kb.adjust(1)

    target = message_or_call.message if is_callback else message_or_call
    if proof_file_id:
        await target.answer_photo(proof_file_id, caption=text, reply_markup=kb.as_markup())
    else:
        await target.answer(text, reply_markup=kb.as_markup())
    if is_callback:
        await message_or_call.answer()


@router.callback_query(F.data.startswith("payadm:view:"))
async def view_payment(call: CallbackQuery) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        return
    payment_id = UUID(call.data.split("payadm:view:", 1)[1])
    await _show_payment(call, payment_id, role_keys, is_callback=True)


# ── Approve / Reject ─────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("payadm:approve:"))
async def approve(call: CallbackQuery) -> None:
    role_keys = await get_role_keys(call.from_user.id)
    if not has(role_keys, "approve_payment"):
        await call.answer("Not authorised to approve payments.", show_alert=True)
        return
    payment_id = UUID(call.data.split("payadm:approve:", 1)[1])
    by = f"{primary_role(role_keys) or 'staff'}:{call.from_user.id}"

    async with get_session() as session:
        payment = await session.get(Payment, payment_id)
        if payment is None:
            await call.answer("Payment not found.", show_alert=True)
            return
        order = await session.get(Order, payment.order_id)
        if order is None:
            await call.answer("Order not found.", show_alert=True)
            return
        ok, err = await payments_admin_svc.approve_payment(session, order, payment, by)
        if not ok:
            await call.answer(err, show_alert=True)
            return
        await _audit(session, call.from_user.id, role_keys, "approve_payment", str(payment_id), {"order": order.code})
        customer = await session.get(Customer, order.customer_id)
        order_id, order_code = order.id, order.code
        customer_tid = customer.telegram_id if customer else None

    if customer_tid:
        try:
            await call.bot.send_message(
                customer_tid, f"✅ Payment approved for {order_code}. We're preparing your order."
            )
        except Exception as exc:  # noqa: BLE001
            log.error("customer_notify_failed", error=str(exc))

    try:
        await alerts.alert_payment_approved(call.bot, order_id)
    except Exception as exc:  # noqa: BLE001
        log.error("packaging_alert_failed", error=str(exc))

    await call.answer("Payment approved ✅")
    await _show_payment(call, payment_id, role_keys, is_callback=True)


@router.callback_query(F.data.startswith("payadm:reject:"))
async def reject(call: CallbackQuery) -> None:
    role_keys = await get_role_keys(call.from_user.id)
    if not has(role_keys, "reject_payment"):
        await call.answer("Not authorised to reject payments.", show_alert=True)
        return
    payment_id = UUID(call.data.split("payadm:reject:", 1)[1])
    by = f"{primary_role(role_keys) or 'staff'}:{call.from_user.id}"

    async with get_session() as session:
        payment = await session.get(Payment, payment_id)
        if payment is None:
            await call.answer("Payment not found.", show_alert=True)
            return
        order = await session.get(Order, payment.order_id)
        if order is None:
            await call.answer("Order not found.", show_alert=True)
            return
        await payments_admin_svc.reject_payment(session, order, payment, by, "Payment rejected")
        await _audit(session, call.from_user.id, role_keys, "reject_payment", str(payment_id), {"order": order.code})
        customer = await session.get(Customer, order.customer_id)
        order_code = order.code
        customer_tid = customer.telegram_id if customer else None

    if customer_tid:
        try:
            await call.bot.send_message(
                customer_tid, f"❌ Payment for {order_code} could not be verified. Please contact support."
            )
        except Exception as exc:  # noqa: BLE001
            log.error("customer_notify_failed", error=str(exc))

    await call.answer("Payment rejected")
    await _show_payment(call, payment_id, role_keys, is_callback=True)


# ── Request clearer proof ────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("payadm:clearer:"))
async def ask_clearer(call: CallbackQuery, state: FSMContext) -> None:
    role_keys = await get_role_keys(call.from_user.id)
    if not has(role_keys, "reject_payment"):
        await call.answer("Not authorised.", show_alert=True)
        return
    payment_id = call.data.split("payadm:clearer:", 1)[1]
    await state.set_state(PaymentAdminFlow.clearer)
    await state.update_data(payment_id=payment_id)
    kb = InlineKeyboardBuilder()
    kb.button(text="📤 Use Default Message", callback_data=f"payadm:clearerdefault:{payment_id}")
    kb.button(text="⬅️ Cancel", callback_data=f"payadm:view:{payment_id}")
    kb.adjust(1)
    await call.message.answer(
        "📸 Type a custom message asking for clearer proof, or use the default:",
        reply_markup=kb.as_markup(),
    )
    await call.answer()


async def _send_clearer_request(call_or_msg, payment_id: UUID, role_keys: set[str], text: str) -> None:
    async with get_session() as session:
        payment = await session.get(Payment, payment_id)
        if payment is None:
            return
        order = await session.get(Order, payment.order_id)
        customer = await session.get(Customer, order.customer_id) if order else None
        await _audit(session, call_or_msg.from_user.id, role_keys, "request_clearer_proof", str(payment_id))
        customer_tid = customer.telegram_id if customer else None

    if customer_tid:
        try:
            await call_or_msg.bot.send_message(customer_tid, text)
        except Exception as exc:  # noqa: BLE001
            log.error("clearer_request_failed", error=str(exc))


@router.callback_query(F.data.startswith("payadm:clearerdefault:"))
async def send_default_clearer(call: CallbackQuery, state: FSMContext) -> None:
    role_keys = await get_role_keys(call.from_user.id)
    if not has(role_keys, "reject_payment"):
        await call.answer("Not authorised.", show_alert=True)
        return
    payment_id = UUID(call.data.split("payadm:clearerdefault:", 1)[1])
    await state.clear()
    await _send_clearer_request(call, payment_id, role_keys, _DEFAULT_CLEARER_MSG)
    await call.answer("Request sent ✅")
    await _show_payment(call, payment_id, role_keys, is_callback=True)


@router.message(PaymentAdminFlow.clearer, F.text)
async def send_custom_clearer(message: Message, state: FSMContext) -> None:
    role_keys = await get_role_keys(message.from_user.id)
    if not has(role_keys, "reject_payment"):
        return
    data = await state.get_data()
    payment_id = UUID(data.get("payment_id"))
    await state.clear()
    await _send_clearer_request(message, payment_id, role_keys, message.text.strip())
    await message.answer("✅ Message sent to customer.")
    await _show_payment(message, payment_id, role_keys, is_callback=False)


# ── Message customer about a payment ─────────────────────────────────────────

@router.callback_query(F.data.startswith("payadm:msg:"))
async def ask_message(call: CallbackQuery, state: FSMContext) -> None:
    role_keys = await get_role_keys(call.from_user.id)
    if not has(role_keys, "message_customer"):
        await call.answer("Not authorised.", show_alert=True)
        return
    payment_id = call.data.split("payadm:msg:", 1)[1]
    await state.set_state(PaymentAdminFlow.message)
    await state.update_data(payment_id=payment_id)
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Cancel", callback_data=f"payadm:view:{payment_id}")
    await call.message.answer("💬 Type your message to the customer:", reply_markup=kb.as_markup())
    await call.answer()


@router.message(PaymentAdminFlow.message, F.text)
async def send_message(message: Message, state: FSMContext) -> None:
    role_keys = await get_role_keys(message.from_user.id)
    if not has(role_keys, "message_customer"):
        return
    data = await state.get_data()
    payment_id = UUID(data.get("payment_id"))
    await state.clear()

    async with get_session() as session:
        payment = await session.get(Payment, payment_id)
        if payment is None:
            await message.answer("Payment not found.")
            return
        order = await session.get(Order, payment.order_id)
        customer = await session.get(Customer, order.customer_id) if order else None
        customer_tid = customer.telegram_id if customer else None
        order_code = order.code if order else "?"

    if customer_tid:
        try:
            await message.bot.send_message(
                customer_tid, f"💬 Message from Peaceway about payment for {order_code}:\n\n{message.text.strip()}"
            )
            await message.answer("✅ Message sent.")
        except Exception as exc:  # noqa: BLE001
            log.error("payment_message_failed", error=str(exc))
            await message.answer("⚠️ Could not reach this customer via Telegram.")
    else:
        await message.answer("⚠️ Customer not found for this payment.")
    await _show_payment(message, payment_id, role_keys, is_callback=False)
