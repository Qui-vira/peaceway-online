"""Staff entry points: /myid (everyone) and /admin (role-gated panel)."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from app.core.db import get_session
from app.core.security import resolve_role
from app.models import Order, OrderStatus, RxStatus

router = Router(name="staff-panel")


@router.message(Command("myid"))
async def my_id(message: Message) -> None:
    await message.answer(
        f"Your Telegram numeric ID is:\n<code>{message.from_user.id}</code>\n\n"
        "Send this to the pharmacy owner to be added as staff."
    )


@router.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    role = resolve_role(message.from_user.id)
    if role is None:
        await message.answer("⛔ You are not authorised to access the staff panel.")
        return
    kb = InlineKeyboardBuilder()
    kb.button(text="🆕 New / Pending Orders", callback_data="staff:orders")
    if role.value in ("OWNER", "PHARMACIST"):
        kb.button(text="💊 Prescription Reviews", callback_data="staff:rx")
    if role.value == "OWNER":
        kb.button(text="💵 Pricing & Fees", callback_data="staff:pricing")
    kb.adjust(1)
    await message.answer(
        f"🛠 <b>Staff Panel</b>\nRole: <b>{role.value}</b>", reply_markup=kb.as_markup()
    )


def _order_list_kb(orders: list[Order]):
    kb = InlineKeyboardBuilder()
    for o in orders:
        kb.button(text=f"{o.code} · {o.status.value} · ₦{o.total:,.0f}", callback_data=f"staff:order:{o.code}")
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(F.data == "staff:orders")
async def list_orders(call: CallbackQuery) -> None:
    if resolve_role(call.from_user.id) is None:
        await call.answer("Not authorised.", show_alert=True)
        return
    open_statuses = [
        OrderStatus.PAYMENT_SUBMITTED,
        OrderStatus.PAYMENT_APPROVED,
        OrderStatus.PROCESSING,
        OrderStatus.DISPATCHED,
        OrderStatus.AWAITING_PAYMENT,
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
        await call.message.edit_text("🆕 <b>Open orders</b>", reply_markup=_order_list_kb(orders))
    await call.answer()


@router.callback_query(F.data == "staff:rx")
async def list_rx(call: CallbackQuery) -> None:
    role = resolve_role(call.from_user.id)
    if role is None or role.value not in ("OWNER", "PHARMACIST"):
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
        await call.message.edit_text("No prescription orders awaiting review.")
    else:
        await call.message.edit_text("💊 <b>Prescription reviews</b>", reply_markup=_order_list_kb(orders))
    await call.answer()


@router.callback_query(F.data.startswith("staff:order:"))
async def show_order(call: CallbackQuery) -> None:
    role = resolve_role(call.from_user.id)
    if role is None:
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
        text = order_summary(order)
        kb = order_actions(order, role)
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()
