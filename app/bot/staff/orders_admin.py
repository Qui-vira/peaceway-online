"""Orders Admin: filtered queues, search by reference, rich order detail.

Gated on view_all_orders (full detail + contact) or view_customer_orders /
view_order_totals (list access; contact details still privacy-gated per order_summary).
Action buttons (approve/reject/packaging/dispatch/cancel/message) are NOT
duplicated here — they reuse the existing act: handlers + order_actions()
keyboard in app/bot/staff/orders.py and app/bot/keyboards/staff.py.
"""
from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import func, select

from app.bot.keyboards.staff import order_actions
from app.bot.staff.states import OrderAdminFlow
from app.core.db import get_session
from app.core.logging import get_logger
from app.core.security import get_role_keys, has
from app.models import Customer, Order, OrderStatus

router = Router(name="staff-orders-admin")
log = get_logger("orders-admin")

# Tabs shown on the Orders home screen, in display order.
_STATUS_TABS: list[tuple[str, OrderStatus]] = [
    ("🆕 New", OrderStatus.NEW),
    ("⏳ Awaiting Payment", OrderStatus.AWAITING_PAYMENT),
    ("💳 Payment Submitted", OrderStatus.PAYMENT_SUBMITTED),
    ("📦 Processing", OrderStatus.PROCESSING),
    ("🚚 Dispatched", OrderStatus.DISPATCHED),
    ("🏁 Delivered", OrderStatus.DELIVERED),
]


def _can_view(role_keys: set[str]) -> bool:
    return (
        has(role_keys, "view_all_orders")
        or has(role_keys, "view_customer_orders")
        or has(role_keys, "view_order_totals")
    )


def _can_see_contact(role_keys: set[str]) -> bool:
    return (
        has(role_keys, "view_all_orders")
        or has(role_keys, "view_delivery_address")
        or has(role_keys, "message_customer")
    )


async def _guard(call: CallbackQuery) -> set[str] | None:
    role_keys = await get_role_keys(call.from_user.id)
    if not _can_view(role_keys):
        await call.answer("Not authorised.", show_alert=True)
        return None
    return role_keys


# ── Orders home: status tab counts ──────────────────────────────────────────

@router.callback_query(F.data == "staff:orders")
async def orders_home(call: CallbackQuery, state: FSMContext) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        return
    await state.clear()

    async with get_session() as session:
        counts: dict[OrderStatus, int] = {}
        for _, status in _STATUS_TABS:
            counts[status] = (
                await session.execute(
                    select(func.count()).select_from(Order).where(Order.status == status)
                )
            ).scalar() or 0

    kb = InlineKeyboardBuilder()
    for label, status in _STATUS_TABS:
        n = counts[status]
        text = f"{label} ({n})" if n else label
        kb.button(text=text, callback_data=f"ordadm:list:{status.value}")
    kb.button(text="🔎 Search by Reference", callback_data="ordadm:search")
    kb.button(text="🏠 Staff Menu", callback_data="staff:home")
    kb.adjust(1)
    await call.message.edit_text("🧾 <b>Orders</b>", reply_markup=kb.as_markup())
    await call.answer()


# ── Filtered list by status ──────────────────────────────────────────────────

@router.callback_query(F.data.startswith("ordadm:list:"))
async def list_by_status(call: CallbackQuery) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        return
    status_value = call.data.split("ordadm:list:", 1)[1]
    try:
        status = OrderStatus(status_value)
    except ValueError:
        await call.answer("Unknown status.", show_alert=True)
        return

    async with get_session() as session:
        orders = (
            await session.execute(
                select(Order)
                .where(Order.status == status)
                .order_by(Order.created_at.desc())
                .limit(20)
            )
        ).scalars().all()

    kb = InlineKeyboardBuilder()
    for o in orders:
        kb.button(text=f"{o.code} · ₦{o.total:,.0f}", callback_data=f"ordadm:view:{o.id}")
    kb.button(text="⬅️ Back", callback_data="staff:orders")
    kb.adjust(1)
    label = next((lbl for lbl, st in _STATUS_TABS if st == status), status.value)
    text = f"{label}\n({len(orders)} shown)" if orders else f"{label}\nNo orders in this status."
    await call.message.edit_text(text, reply_markup=kb.as_markup())
    await call.answer()


# ── Search by reference ──────────────────────────────────────────────────────

@router.callback_query(F.data == "ordadm:search")
async def ask_search(call: CallbackQuery, state: FSMContext) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        return
    await state.set_state(OrderAdminFlow.search)
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Back", callback_data="staff:orders")
    await call.message.edit_text(
        "🔎 Enter the order reference (e.g. <code>PW-7QK3M2</code>):", reply_markup=kb.as_markup()
    )
    await call.answer()


@router.message(OrderAdminFlow.search, F.text)
async def do_search(message: Message, state: FSMContext) -> None:
    role_keys = await get_role_keys(message.from_user.id)
    if not _can_view(role_keys):
        return
    await state.clear()
    query = message.text.strip().upper()

    async with get_session() as session:
        order = (
            await session.execute(select(Order).where(Order.code == query))
        ).scalar_one_or_none()

    if order is None:
        kb = InlineKeyboardBuilder()
        kb.button(text="🔎 Try Again", callback_data="ordadm:search")
        kb.button(text="⬅️ Back", callback_data="staff:orders")
        kb.adjust(1)
        await message.answer(f"😕 No order found with reference <code>{query}</code>.", reply_markup=kb.as_markup())
        return

    await _send_order_detail(message, order.id, role_keys)


# ── Order detail ─────────────────────────────────────────────────────────────

def _detail_text(order: Order, customer: Customer | None, show_contact: bool) -> str:
    lines = [
        f"🧾 <b>Order {order.code}</b>",
        f"Status: <b>{order.status.value}</b>",
    ]
    if order.rx_status.value != "NOT_REQUIRED":
        lines.append(f"Rx Status: {order.rx_status.value}")
    lines.append(f"Delivery: {order.delivery_status.value}")
    lines.append("")

    if customer:
        lines.append(f"Customer: {customer.full_name or '-'}")
        lines.append(f"Telegram ID: <code>{customer.telegram_id}</code>")
        if show_contact:
            lines.append(f"Phone: {customer.phone or order.delivery_phone or '-'}")
            lines.append(f"Email: {customer.email or 'not on file'}")
    if show_contact:
        lines.append(f"Address: {order.delivery_address or '-'}")
        lines.append(f"Area: {order.delivery_area or '-'}")
        if order.delivery_landmark:
            lines.append(f"Landmark: {order.delivery_landmark}")
    else:
        lines.append(f"Area: {order.delivery_area or '-'}")
    lines.append("")

    lines.append("<b>Items:</b>")
    for it in order.items:
        rx = " 💊Rx" if it.requires_prescription else ""
        lines.append(f"• {it.product_name} ×{it.quantity} · ₦{it.line_total:,.0f}{rx}")
    lines.append("")

    lines.append(f"Subtotal: ₦{order.subtotal:,.0f}")
    lines.append(f"Delivery fee: ₦{order.delivery_fee:,.0f}")
    if order.payment_fee:
        lines.append(f"Payment fee: ₦{order.payment_fee:,.0f}")
    if order.offramp_fee:
        lines.append(f"Off-ramp fee: ₦{order.offramp_fee:,.0f}")
    if order.handling_fee:
        lines.append(f"Handling fee: ₦{order.handling_fee:,.0f}")
    lines.append(f"<b>Total: ₦{order.total:,.0f}</b>")
    lines.append("")

    method = order.payment_method.value if order.payment_method else "not selected"
    lines.append(f"Payment method: {method}")
    lines.append(f"Created: {order.created_at.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"Last update: {order.updated_at.strftime('%Y-%m-%d %H:%M')}")

    return "\n".join(lines)


async def _send_order_detail(message: Message, order_id: UUID, role_keys: set[str]) -> None:
    async with get_session() as session:
        order = await session.get(Order, order_id)
        if order is None:
            await message.answer("Order not found.")
            return
        customer = await session.get(Customer, order.customer_id)
        show_contact = _can_see_contact(role_keys)
        text = _detail_text(order, customer, show_contact)
        kb_actions = order_actions(order, role_keys)

    kb = InlineKeyboardBuilder.from_markup(kb_actions)
    kb.button(text="⬅️ Back to Orders", callback_data="staff:orders")
    kb.adjust(2)
    await message.answer(text, reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("ordadm:view:"))
async def view_order(call: CallbackQuery) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        return
    order_id = UUID(call.data.split("ordadm:view:", 1)[1])

    async with get_session() as session:
        order = await session.get(Order, order_id)
        if order is None:
            await call.answer("Order not found.", show_alert=True)
            return
        customer = await session.get(Customer, order.customer_id)
        show_contact = _can_see_contact(role_keys)
        text = _detail_text(order, customer, show_contact)
        kb_actions = order_actions(order, role_keys)

    kb = InlineKeyboardBuilder.from_markup(kb_actions)
    kb.button(text="⬅️ Back to Orders", callback_data="staff:orders")
    kb.adjust(2)
    await call.message.edit_text(text, reply_markup=kb.as_markup())
    await call.answer()
