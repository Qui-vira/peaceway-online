"""Staff entry points: /myid (everyone) and /admin (role-specific panel)."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import func, select

from app.core import rbac
from app.core.db import get_session
from app.core.security import get_role_keys, has, primary_role, touch_activity
from app.models import AdminUser, Order, OrderStatus, PharmacistQuestion, Prescription, ProductRequest, RxStatus

router = Router(name="staff-panel")

# Menu callback -> count key, for badging menu labels with unread/pending counts.
_COUNT_TARGETS = {
    "staff:tickets": "tickets",
    "staff:prescriptions": "prescriptions",
    "staff:requests": "requests",
}


async def _pending_counts(role_keys: set[str]) -> dict[str, int]:
    counts = {"tickets": 0, "prescriptions": 0, "requests": 0}
    async with get_session() as session:
        if has(role_keys, "reply_pharmacist_tickets"):
            counts["tickets"] = (
                await session.execute(
                    select(func.count()).select_from(PharmacistQuestion).where(PharmacistQuestion.is_answered.is_(False))
                )
            ).scalar() or 0
        if has(role_keys, "review_prescriptions"):
            counts["prescriptions"] = (
                await session.execute(
                    select(func.count()).select_from(Prescription).where(Prescription.review_status == "PENDING")
                )
            ).scalar() or 0
        if has(role_keys, "view_product_requests"):
            # Needs attention if brand-new, or the customer's last message is
            # newer than the last admin response (an unread reply).
            counts["requests"] = (
                await session.execute(
                    select(func.count()).select_from(ProductRequest).where(
                        (ProductRequest.status == "NEW")
                        | (
                            ProductRequest.last_customer_update_at.is_not(None)
                            & (
                                ProductRequest.last_admin_update_at.is_(None)
                                | (ProductRequest.last_customer_update_at > ProductRequest.last_admin_update_at)
                            )
                        )
                    )
                )
            ).scalar() or 0
    return counts


async def render_panel(role_keys: set[str]) -> tuple[str, InlineKeyboardMarkup]:
    """Build the staff panel text + keyboard, with unread counts and an alert
    banner for pharmacist-relevant items. Shared by /admin and the 'Staff Menu'
    back button so both stay in sync."""
    items = rbac.menu_for(role_keys)
    counts = await _pending_counts(role_keys)
    total = counts["tickets"] + counts["prescriptions"] + counts["requests"]
    banner = f"⚠️ You have {total} new item(s) needing attention.\n\n" if total else ""

    kb = InlineKeyboardBuilder()
    for label, cb in items:
        count_key = _COUNT_TARGETS.get(cb)
        text = f"{label} ({counts[count_key]})" if count_key and counts.get(count_key) else label
        kb.button(text=text, callback_data=cb)
    kb.adjust(1)

    role_names = ", ".join(rbac.role_label(r) for r in sorted(role_keys))
    text = f"{banner}🛠 <b>Staff Panel</b>\nRoles: <b>{role_names}</b>"
    return text, kb.as_markup()


@router.message(Command("myid"))
async def my_id(message: Message) -> None:
    await message.answer(
        f"Your Telegram numeric ID is:\n<code>{message.from_user.id}</code>\n\n"
        "Send this to the System Owner to be added as staff."
    )


async def _no_access_message(telegram_id: int) -> str:
    """Distinguish 'never an admin' from a disabled/removed/pending one."""
    from app.models.admin import AdminStatus

    async with get_session() as session:
        admin = (
            await session.execute(select(AdminUser).where(AdminUser.telegram_id == telegram_id))
        ).scalar_one_or_none()
    if admin is None:
        return "⛔ You are not authorised to access the staff panel."
    if admin.status == AdminStatus.PENDING:
        return "⏳ Your admin access is pending approval from the System Owner."
    return "⛔ Your admin access is no longer active."


@router.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    role_keys = await get_role_keys(message.from_user.id)
    if not role_keys:
        await message.answer(await _no_access_message(message.from_user.id))
        return
    await touch_activity(message.from_user.id)
    text, kb = await render_panel(role_keys)
    await message.answer(text, reply_markup=kb)


def _order_list_kb(orders: list[Order]):
    kb = InlineKeyboardBuilder()
    for o in orders:
        kb.button(text=f"{o.code} · {o.status.value} · ₦{o.total:,.0f}", callback_data=f"staff:order:{o.code}")
    kb.adjust(1)
    return kb.as_markup()


# Menu callbacks that map to an "open orders" list, by the permission they need.
# Note: staff:orders, staff:payments, staff:paystatus have dedicated handlers in
# orders_admin.py / payments_admin.py (richer detail, filters, search) and are
# intentionally excluded here.
_ORDER_VIEWS = {
    "staff:dashboard": "view_all_orders",
    "staff:paid": "see_paid_orders",
    "staff:deliveries": "view_assigned_deliveries",
    "staff:medorders": "view_medicine_orders",
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


@router.callback_query(F.data.in_({"staff:rx", "staff:escalated", "staff:medorders"}))
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
