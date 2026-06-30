"""Staff entry points: /myid (everyone) and /admin (role-specific panel)."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from app.core import rbac
from app.core.db import get_session
from app.core.security import get_role_keys, has, primary_role, touch_activity
from app.models import Order, OrderStatus, RxStatus

router = Router(name="staff-panel")


@router.message(Command("myid"))
async def my_id(message: Message) -> None:
    await message.answer(
        f"Your Telegram numeric ID is:\n<code>{message.from_user.id}</code>\n\n"
        "Send this to the System Owner to be added as staff."
    )


@router.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    role_keys = await get_role_keys(message.from_user.id)
    if not role_keys:
        await message.answer("⛔ You are not authorised to access the staff panel.")
        return
    await touch_activity(message.from_user.id)
    items = rbac.menu_for(role_keys)
    kb = InlineKeyboardBuilder()
    for label, cb in items:
        kb.button(text=label, callback_data=cb)
    kb.adjust(1)
    role_names = ", ".join(rbac.role_label(r) for r in sorted(role_keys))
    await message.answer(
        f"🛠 <b>Staff Panel</b>\nRoles: <b>{role_names}</b>", reply_markup=kb.as_markup()
    )


def _order_list_kb(orders: list[Order]):
    kb = InlineKeyboardBuilder()
    for o in orders:
        kb.button(text=f"{o.code} · {o.status.value} · ₦{o.total:,.0f}", callback_data=f"staff:order:{o.code}")
    kb.adjust(1)
    return kb.as_markup()


# Menu callbacks that map to an "open orders" list, by the permission they need.
_ORDER_VIEWS = {
    "staff:orders": "view_customer_orders",
    "staff:dashboard": "view_all_orders",
    "staff:payments": "approve_payment",
    "staff:paid": "see_paid_orders",
    "staff:deliveries": "view_assigned_deliveries",
    "staff:medorders": "view_medicine_orders",
    "staff:paystatus": "view_payment_status",
}


@router.callback_query(F.data.in_(set(_ORDER_VIEWS)))
async def list_orders(call: CallbackQuery) -> None:
    role_keys = await get_role_keys(call.from_user.id)
    perm = _ORDER_VIEWS[call.data]
    if not has(role_keys, perm):
        await call.answer("Not authorised.", show_alert=True)
        return
    open_statuses = [
        OrderStatus.PAYMENT_SUBMITTED, OrderStatus.PAYMENT_APPROVED,
        OrderStatus.PROCESSING, OrderStatus.DISPATCHED, OrderStatus.AWAITING_PAYMENT,
    ]
    async with get_session() as session:
        orders = (
            await session.execute(
                select(Order).where(Order.status.in_(open_statuses)).order_by(Order.created_at.desc()).limit(15)
            )
        ).scalars().all()
    if not orders:
        await call.message.edit_text("No open orders right now.")
    else:
        await call.message.edit_text("🧾 <b>Open orders</b>", reply_markup=_order_list_kb(orders))
    await call.answer()


@router.callback_query(F.data.in_({"staff:rx", "staff:tickets", "staff:escalated", "staff:medorders"}))
async def list_rx(call: CallbackQuery) -> None:
    role_keys = await get_role_keys(call.from_user.id)
    # Pharmacist inbox / reviews require a medicine-related permission.
    if not (has(role_keys, "approve_prescription") or has(role_keys, "view_medicine_orders") or has(role_keys, "reply_pharmacist_tickets")):
        await call.answer("Not authorised.", show_alert=True)
        return
    review_statuses = [RxStatus.PRESCRIPTION_REQUIRED, RxStatus.PRESCRIPTION_UPLOADED, RxStatus.PHARMACIST_REVIEW]
    async with get_session() as session:
        orders = (
            await session.execute(
                select(Order).where(Order.rx_status.in_(review_statuses)).order_by(Order.created_at.desc()).limit(15)
            )
        ).scalars().all()
    if not orders:
        await call.message.edit_text("💊 No prescription orders awaiting review.")
    else:
        await call.message.edit_text("💊 <b>Prescription reviews</b>", reply_markup=_order_list_kb(orders))
    await call.answer()


@router.callback_query(F.data.startswith("staff:order:"))
async def show_order(call: CallbackQuery) -> None:
    role_keys = await get_role_keys(call.from_user.id)
    if not role_keys:
        await call.answer("Not authorised.", show_alert=True)
        return
    code = call.data.split("staff:order:", 1)[1]
    from app.bot.keyboards.staff import order_actions
    from app.services.alerts import order_summary

    async with get_session() as session:
        order = (await session.execute(select(Order).where(Order.code == code))).scalar_one_or_none()
        if order is None:
            await call.answer("Order not found.", show_alert=True)
            return
        # Privacy: only roles that need delivery contact details see them.
        show_contact = has(role_keys, "view_delivery_address") or has(role_keys, "view_all_orders") or has(role_keys, "message_customer")
        text = order_summary(order, include_contact=show_contact)
        kb = order_actions(order, role_keys)
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()
