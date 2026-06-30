"""Admin Product Request CRM: view, transition status, message customer, thread.

Gated on `view_product_requests`. Status transitions that mark a medicine request
as "Available" or "Ready to Order" are additionally gated on `review_prescriptions`
(pharmacist-level clearance). "Convert to Order" is safety-blocked for medicine
requests that haven't been pharmacist-cleared yet.
"""
from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from app.bot.staff.states import RequestAdminFlow
from app.core.db import get_session
from app.core.logging import get_logger
from app.core.security import get_role_keys, has, log_activity
from app.models import Customer, ProductRequest
from app.models.ops import ProductRequestStatus
from app.services.customers import get_or_create_customer
from app.services.product_requests import (
    add_message,
    can_convert_to_order,
    get_thread,
    notify_available,
    notify_not_available,
    requires_pharmacist_clearance,
    transition_status,
)

router = Router(name="staff-requests")
log = get_logger("staff-requests")


async def _guard(event, *, also_require: str | None = None) -> set[str] | None:
    role_keys = await get_role_keys(event.from_user.id)
    if not has(role_keys, "view_product_requests"):
        return None
    if also_require and not has(role_keys, also_require):
        return None
    return role_keys


def _status_label(s: str) -> str:
    labels = {
        "NEW": "🆕 New",
        "CHECKING_AVAILABILITY": "🔎 Checking",
        "NEEDS_MORE_INFO": "❓ Needs info",
        "AVAILABLE": "✅ Available",
        "NOT_AVAILABLE": "🚫 Not available",
        "ORDERED_FROM_SUPPLIER": "📦 Ordered from supplier",
        "READY_TO_ORDER": "🛒 Ready to order",
        "CUSTOMER_NOTIFIED": "📣 Customer notified",
        "CONVERTED_TO_ORDER": "🧾 Converted",
        "FULFILLED": "🏁 Fulfilled",
        "CLOSED": "🔒 Closed",
        "REJECTED": "⛔ Rejected",
    }
    return labels.get(s, s)


@router.callback_query(F.data == "staff:requests")
async def list_requests(call: CallbackQuery) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        await call.answer("Not authorised.", show_alert=True)
        return
    async with get_session() as session:
        rows = (
            await session.execute(
                select(ProductRequest)
                .where(ProductRequest.status.not_in(["CLOSED", "REJECTED", "CONVERTED_TO_ORDER", "FULFILLED"]))
                .order_by(ProductRequest.created_at.desc())
                .limit(15)
            )
        ).scalars().all()
    kb = InlineKeyboardBuilder()
    for r in rows:
        kb.button(text=f"📝 {r.product_name[:35]} · {_status_label(r.status)}", callback_data=f"preqadm:open:{r.id}")
    kb.button(text="🏠 Staff Menu", callback_data="staff:home")
    kb.adjust(1)
    text = "📝 <b>Product Requests</b>" if rows else "📝 No open product requests."
    await call.message.edit_text(text, reply_markup=kb.as_markup())
    await call.answer()


async def _show_request(call: CallbackQuery, rid: UUID) -> None:
    role_keys = await get_role_keys(call.from_user.id)
    async with get_session() as session:
        req = await session.get(ProductRequest, rid)
        if req is None:
            await call.answer("Not found.", show_alert=True)
            return
        customer = await session.get(Customer, req.customer_id)
        thread = await get_thread(session, rid)
        can_convert, block_msg = can_convert_to_order(req)
        is_pharmacist = has(role_keys, "review_prescriptions")
        is_owner_or_support = has(role_keys, "view_customer_orders") or has(role_keys, "view_all_orders")

    # Build detail text.
    last = (req.last_admin_update_at or req.updated_at).strftime("%Y-%m-%d %H:%M")
    lines = [
        f"📝 <b>{req.product_name}</b>",
        f"Status: {_status_label(req.status)}",
        f"Last update: {last}",
    ]
    if req.strength: lines.append(f"Strength: {req.strength}")
    if req.form: lines.append(f"Form: {req.form}")
    if req.quantity: lines.append(f"Qty: {req.quantity}")
    if req.urgency: lines.append(f"Urgency: {req.urgency}")
    if req.delivery_area: lines.append(f"Area: {req.delivery_area}")
    lines.append("")
    if customer:
        lines.append(f"Customer: {customer.full_name or '-'} (id <code>{customer.telegram_id}</code>)")
        if req.customer_phone: lines.append(f"Phone: {req.customer_phone}")
        if req.customer_email: lines.append(f"Email: {req.customer_email}")
    lines.append("")
    if thread:
        lines.append("💬 <b>Thread:</b>")
        for m in thread[-5:]:
            who = "🧑" if m.sender_type == "customer" else "👨‍⚕️ Admin"
            when = m.created_at.strftime("%m-%d %H:%M")
            lines.append(f"<i>{when}</i> {who}: {m.message_text[:80]}")

    text = "\n".join(lines)
    kb = InlineKeyboardBuilder()

    # Status transition buttons (safety-aware).
    if req.status not in ("CLOSED", "REJECTED", "FULFILLED", "CONVERTED_TO_ORDER"):
        if req.status == "NEW":
            kb.button(text="🔎 Mark Checking", callback_data=f"preqact:checking:{rid}")
            kb.button(text="❓ Request More Info", callback_data=f"preqact:needsinfo:{rid}")
        if req.is_medicine and is_pharmacist or not req.is_medicine:
            kb.button(text="✅ Mark Available", callback_data=f"preqact:available:{rid}")
            kb.button(text="🛒 Mark Ready to Order", callback_data=f"preqact:ready:{rid}")
        kb.button(text="🚫 Mark Not Available", callback_data=f"preqact:notavailable:{rid}")
        kb.button(text="📦 Ordered from Supplier", callback_data=f"preqact:orderedsupplier:{rid}")
        kb.button(text="📣 Notify Available", callback_data=f"preqact:notifyavail:{rid}")
        kb.button(text="😔 Notify Not Available", callback_data=f"preqact:notifynotavail:{rid}")
        if can_convert:
            kb.button(text="🧾 Convert to Order", callback_data=f"preqact:convert:{rid}")
        kb.button(text="💰 Send Price to Customer", callback_data=f"preqact:sendprice:{rid}")
        kb.button(text="💬 Message Customer", callback_data=f"preqact:message:{rid}")
        kb.button(text="❓ Ask Follow-up Question", callback_data=f"preqact:followup:{rid}")
    kb.button(text="🔒 Close Request", callback_data=f"preqact:close:{rid}")
    kb.button(text="⛔ Reject Request", callback_data=f"preqact:reject:{rid}")
    kb.button(text="⬅️ Back", callback_data="staff:requests")
    kb.adjust(1)
    await call.message.edit_text(text, reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("preqadm:open:"))
async def open_request(call: CallbackQuery) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        await call.answer("Not authorised.", show_alert=True)
        return
    rid = UUID(call.data.split("preqadm:open:", 1)[1])
    await _show_request(call, rid)
    await call.answer()


# ── Status transitions ────────────────────────────────────────────────────────
_SIMPLE_TRANSITIONS = {
    "checking": "CHECKING_AVAILABILITY",
    "needsinfo": "NEEDS_MORE_INFO",
    "notavailable": "NOT_AVAILABLE",
    "orderedsupplier": "ORDERED_FROM_SUPPLIER",
    "ready": "READY_TO_ORDER",
    "close": "CLOSED",
    "reject": "REJECTED",
}


@router.callback_query(F.data.startswith("preqact:"))
async def handle_action(call: CallbackQuery, state: FSMContext) -> None:
    role_keys = await get_role_keys(call.from_user.id)
    if not has(role_keys, "view_product_requests"):
        await call.answer("Not authorised.", show_alert=True)
        return

    _, action, rid_s = call.data.split(":", 2)
    rid = UUID(rid_s)

    # FSM-capture actions: message/followup/price
    if action in ("message", "followup"):
        await state.set_state(RequestAdminFlow.message)
        await state.update_data(req_action=action, req_rid=rid_s)
        prompt = "💬 Type your message to the customer:" if action == "message" else "❓ Type your follow-up question for the customer:"
        kb = InlineKeyboardBuilder()
        kb.button(text="⬅️ Back", callback_data=f"preqadm:open:{rid}")
        await call.message.edit_text(prompt, reply_markup=kb.as_markup())
        await call.answer()
        return
    if action == "sendprice":
        await state.set_state(RequestAdminFlow.price)
        await state.update_data(req_rid=rid_s)
        kb = InlineKeyboardBuilder()
        kb.button(text="⬅️ Back", callback_data=f"preqadm:open:{rid}")
        await call.message.edit_text("💰 What is the price (₦)?", reply_markup=kb.as_markup())
        await call.answer()
        return

    # Notify actions (send specific notification template to customer).
    if action in ("notifyavail", "notifynotavail"):
        async with get_session() as session:
            req = await session.get(ProductRequest, rid)
            customer = await session.get(Customer, req.customer_id) if req else None
        if req is None or customer is None:
            await call.answer("Not found.", show_alert=True)
            return
        if action == "notifyavail":
            await notify_available(call.bot, customer.telegram_id, req, req.customer_visible_message or "?")
        else:
            await notify_not_available(call.bot, customer.telegram_id, req)
        await call.answer("Notification sent ✅")
        return

    # Available transition — requires pharmacist clearance for medicine.
    if action == "available":
        async with get_session() as session:
            req = await session.get(ProductRequest, rid)
        if req and requires_pharmacist_clearance(req, "AVAILABLE") and not has(role_keys, "review_prescriptions"):
            await call.answer("Only a pharmacist can mark a medicine request as Available.", show_alert=True)
            return

    # Convert to order — safety gate.
    if action == "convert":
        async with get_session() as session:
            req = await session.get(ProductRequest, rid)
        ok, msg = can_convert_to_order(req) if req else (False, "Not found.")
        if not ok:
            await call.answer(msg or "Cannot convert.", show_alert=True)
            return

    # All remaining simple transitions.
    new_status = _SIMPLE_TRANSITIONS.get(action)
    if action == "available":
        new_status = "AVAILABLE"
    elif action == "convert":
        new_status = "CONVERTED_TO_ORDER"

    if new_status is None:
        await call.answer("Unknown action.", show_alert=True)
        return

    async with get_session() as session:
        req = await session.get(ProductRequest, rid)
        if req is None:
            await call.answer("Not found.", show_alert=True)
            return
        await transition_status(session, req, new_status, call.from_user.id)
    await log_activity(call.from_user.id, role_keys, f"request_{action}", "product_request", rid_s)
    await call.answer("Updated ✅")
    await _show_request(call, rid)


@router.message(RequestAdminFlow.message, F.text)
async def send_message(message: Message, state: FSMContext) -> None:
    role_keys = await get_role_keys(message.from_user.id)
    data = await state.get_data()
    action = data.get("req_action")
    rid = UUID(data.get("req_rid"))
    await state.clear()
    body = message.text.strip()

    async with get_session() as session:
        req = await session.get(ProductRequest, rid)
        if req is None:
            await message.answer("Request not found.")
            return
        await add_message(session, req, "admin", body, sender_admin_id=message.from_user.id)
        if action == "message":
            req.customer_visible_message = body
        customer = await session.get(Customer, req.customer_id)
        chat_id = customer.telegram_id if customer else None

    if chat_id:
        try:
            await message.bot.send_message(chat_id, f"📩 Message from Peaceway:\n\n{body}")
        except Exception as exc:  # noqa: BLE001
            log.error("admin_message_failed", error=str(exc))
    await log_activity(message.from_user.id, role_keys, f"request_{action}", "product_request", str(rid))
    await message.answer("✅ Message sent and saved.")


@router.message(RequestAdminFlow.price, F.text)
async def send_price(message: Message, state: FSMContext) -> None:
    role_keys = await get_role_keys(message.from_user.id)
    data = await state.get_data()
    rid = UUID(data.get("req_rid"))
    await state.clear()
    raw = message.text.strip().replace(",", "").replace("₦", "")
    try:
        price = float(raw)
    except ValueError:
        await message.answer("Please enter a valid number.")
        return

    async with get_session() as session:
        req = await session.get(ProductRequest, rid)
        if req is None:
            await message.answer("Request not found.")
            return
        customer = await session.get(Customer, req.customer_id)
        chat_id = customer.telegram_id if customer else None
        body = f"Price for {req.product_name}: ₦{price:,.0f}"
        await add_message(session, req, "admin", body, sender_admin_id=message.from_user.id)
        req.customer_visible_message = body
        product_snapshot = req

    if chat_id:
        try:
            await notify_available(message.bot, chat_id, product_snapshot, price)
        except Exception as exc:  # noqa: BLE001
            log.error("price_notify_failed", error=str(exc))
    await log_activity(message.from_user.id, role_keys, "request_sendprice", "product_request", str(rid))
    await message.answer(f"✅ Price ₦{price:,.0f} sent to customer.")
