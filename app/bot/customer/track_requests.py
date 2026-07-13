"""Customer 'Track My Requests' - view status/history and reply on a product
request, so a request is a live conversation, not a fire-and-forget ticket."""
from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from app.bot.customer.states import TrackRequestsFlow
from app.bot.keyboards.customer import back_to_menu
from app.core import rbac
from app.core.db import get_session
from app.core.logging import get_logger
from app.models import Customer, ProductRequest
from app.services.product_requests import add_message, get_thread
from app.services.rbac_service import recipients_for_roles

router = Router(name="customer-track-requests")
log = get_logger("track_requests")

_STATUS_LABEL = {
    "NEW": "🆕 Received",
    "CHECKING_AVAILABILITY": "🔎 Checking availability",
    "NEEDS_MORE_INFO": "❓ Needs more info from you",
    "AVAILABLE": "✅ Available",
    "NOT_AVAILABLE": "🚫 Not available",
    "ORDERED_FROM_SUPPLIER": "📦 Ordered from supplier",
    "READY_TO_ORDER": "🛒 Ready to order",
    "CUSTOMER_NOTIFIED": "📣 We notified you",
    "CONVERTED_TO_ORDER": "🧾 Converted to an order",
    "FULFILLED": "🏁 Fulfilled",
    "CLOSED": "🔒 Closed",
    "REJECTED": "⛔ Rejected",
}


async def _render(call: CallbackQuery) -> None:
    async with get_session() as session:
        customer = (
            await session.execute(select(Customer).where(Customer.telegram_id == call.from_user.id))
        ).scalar_one_or_none()
        requests = []
        if customer:
            requests = (
                await session.execute(
                    select(ProductRequest)
                    .where(ProductRequest.customer_id == customer.id)
                    .order_by(ProductRequest.created_at.desc())
                    .limit(10)
                )
            ).scalars().all()
    if not requests:
        await call.message.edit_text(
            "📋 You have no product requests yet.", reply_markup=back_to_menu()
        )
        await call.answer()
        return
    kb = InlineKeyboardBuilder()
    for r in requests:
        label = _STATUS_LABEL.get(r.status, r.status)
        kb.button(text=f"{r.product_name[:30]} · {label}", callback_data=f"preqtrk:{r.id}")
    kb.button(text="🏠 Main Menu", callback_data="menu:home")
    kb.adjust(1)
    await call.message.edit_text("📋 <b>Track My Requests</b>", reply_markup=kb.as_markup())
    await call.answer()


@router.callback_query(F.data == "menu:track_requests")
async def track_requests_menu(call: CallbackQuery, state: FSMContext) -> None:
    from app.bot.customer.email_gate import ensure_email

    if not await ensure_email(call, state, source="product_request", resume=lambda: _render(call)):
        return
    await _render(call)


@router.callback_query(F.data.startswith("preqtrk:"))
async def view_request(call: CallbackQuery) -> None:
    rid = UUID(call.data.split("preqtrk:", 1)[1])
    async with get_session() as session:
        req = await session.get(ProductRequest, rid)
        if req is None:
            await call.answer("Not found.", show_alert=True)
            return
        last_update = (req.last_admin_update_at or req.updated_at).strftime("%Y-%m-%d %H:%M")
        label = _STATUS_LABEL.get(req.status, req.status)
        text = (
            f"📝 <b>{req.product_name}</b>\n"
            f"Status: {label}\n"
            f"Last update: {last_update}"
        )
        if req.customer_visible_message:
            text += f"\n\n💬 {req.customer_visible_message}"

    kb = InlineKeyboardBuilder()
    if req.status not in ("CLOSED", "REJECTED", "CONVERTED_TO_ORDER", "FULFILLED"):
        kb.button(text="✍️ Reply / Add Details", callback_data=f"preqtrk:reply:{rid}")
    kb.button(text="⬅️ Back", callback_data="menu:track_requests")
    kb.adjust(1)
    await call.message.edit_text(text, reply_markup=kb.as_markup())
    await call.answer()


@router.callback_query(F.data.startswith("preqtrk:reply:"))
async def ask_reply(call: CallbackQuery, state: FSMContext) -> None:
    rid = call.data.split("preqtrk:reply:", 1)[1]
    await state.set_state(TrackRequestsFlow.reply)
    await state.update_data(reply_request_id=rid)
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Back", callback_data=f"preqtrk:{rid}")
    await call.message.edit_text("✍️ Type your message or extra details:", reply_markup=kb.as_markup())
    await call.answer()


@router.message(TrackRequestsFlow.reply, F.text)
async def send_reply(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    rid = data.get("reply_request_id")
    await state.clear()

    async with get_session() as session:
        req = await session.get(ProductRequest, UUID(rid))
        if req is None:
            await message.answer("Request not found.")
            return
        await add_message(session, req, "customer", message.text.strip())
        is_medicine = req.is_medicine
        product_name = req.product_name

    try:
        roles = {rbac.SALES_SUPPORT, rbac.SYSTEM_OWNER}
        if is_medicine:
            roles |= {rbac.LEAD_PHARMACIST, rbac.PHARMACIST_ADMIN}
        telegram_ids, _emails = await recipients_for_roles(roles)
        text = f"💬 <b>Customer reply on request</b>: {product_name}\n\n{message.text.strip()}"
        for tid in telegram_ids:
            try:
                await message.bot.send_message(tid, text)
            except Exception:  # noqa: BLE001
                continue
    except Exception as exc:  # noqa: BLE001
        log.error("reply_alert_failed", error=str(exc))

    await message.answer("✅ Sent. Our team will follow up.", reply_markup=back_to_menu())


# ── Buttons on the "now available" / "not available" notifications ──────────
@router.callback_query(F.data.startswith("preqnotify:order:"))
async def notify_order_now(call: CallbackQuery, state: FSMContext) -> None:
    rid = call.data.split("preqnotify:order:", 1)[1]
    async with get_session() as session:
        req = await session.get(ProductRequest, UUID(rid))
        name = req.product_name if req else ""
    from app.bot.customer.catalog import render_search_results

    await state.update_data(last_query=name)
    await call.message.edit_text(f"🔎 Searching for “{name}”...")
    await call.answer()
    await render_search_results(call.message, state, name)


@router.callback_query(F.data.startswith("preqnotify:ask:"))
async def notify_ask_pharmacist(call: CallbackQuery, state: FSMContext) -> None:
    from app.bot.customer.support import ask_start

    await ask_start(call, state)


@router.callback_query(F.data.startswith("preqnotify:notnow:"))
async def notify_not_now(call: CallbackQuery) -> None:
    await call.message.edit_text("👍 No problem. Let us know if you change your mind.", reply_markup=back_to_menu())
    await call.answer()


@router.callback_query(F.data.startswith("preqnotify:keepupdated:"))
async def notify_keep_updated(call: CallbackQuery) -> None:
    await call.message.edit_text(
        "🔔 Got it. We'll keep checking and let you know as soon as it's available.",
        reply_markup=back_to_menu(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("preqnotify:cancel:"))
async def notify_cancel_request(call: CallbackQuery) -> None:
    rid = call.data.split("preqnotify:cancel:", 1)[1]
    async with get_session() as session:
        req = await session.get(ProductRequest, UUID(rid))
        if req is None:
            await call.answer("Not found.", show_alert=True)
            return
        from app.services.product_requests import transition_status

        await transition_status(session, req, "CLOSED", call.from_user.id, "Cancelled by customer")
    await call.message.edit_text("🚫 Request cancelled.", reply_markup=back_to_menu())
    await call.answer()
