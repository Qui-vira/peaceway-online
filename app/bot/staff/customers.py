"""Admin Customer CRM: search, profile, message customer, add note.

Permission gates:
  view_customers -> can see list/search/profile
  message_customer -> can send DMs (System Owner: any customer;
    Lead/Pharmacist Admin: only customers with open pharmacist tickets;
    Sales/Support: any customer with order/request context;
    Community Manager: only receive_community_updates=true customers;
    Packaging/Dispatcher/Finance: messaging blocked)
"""
from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from app.core import rbac
from app.core.db import get_session
from app.core.logging import get_logger
from app.core.security import get_role_keys, has, log_activity
from app.models import Customer, CustomerPreferences
from app.services.customer_admin import (
    add_customer_note,
    get_customer_profile,
    has_open_medicine_context,
    missing_email_customers,
    recent_customers,
    search_customers,
    send_customer_message,
)

router = Router(name="staff-customers")
log = get_logger("staff-customers")


class CustomerAdminFlow(StatesGroup):
    search = State()
    message = State()
    note = State()


async def _guard(call: CallbackQuery) -> set[str] | None:
    role_keys = await get_role_keys(call.from_user.id)
    if not has(role_keys, "view_customers"):
        await call.answer("Not authorised.", show_alert=True)
        return None
    return role_keys


def _can_message(role_keys: set[str]) -> bool:
    return has(role_keys, "message_customer") or has(role_keys, "view_customers")


def _message_scope(role_keys: set[str]) -> str:
    """Returns messaging scope label: 'any'|'medicine'|'community'|'none'."""
    if rbac.SYSTEM_OWNER in role_keys:
        return "any"
    if rbac.LEAD_PHARMACIST in role_keys or rbac.PHARMACIST_ADMIN in role_keys:
        return "medicine"
    if rbac.SALES_SUPPORT in role_keys:
        return "any"
    if rbac.COMMUNITY_MANAGER in role_keys:
        return "community"
    return "none"


# ── Main menu ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "staff:customers")
async def customers_menu(call: CallbackQuery, state: FSMContext) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        return
    await state.clear()
    kb = InlineKeyboardBuilder()
    kb.button(text="🔎 Search Customer", callback_data="custadm:search")
    kb.button(text="🕐 Recent Customers", callback_data="custadm:recent")
    kb.button(text="📧 Missing Email", callback_data="custadm:noemail")
    kb.button(text="🏠 Staff Menu", callback_data="staff:home")
    kb.adjust(1)
    await call.message.edit_text("👤 <b>Customer CRM</b>", reply_markup=kb.as_markup())
    await call.answer()


# ── Search ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "custadm:search")
async def ask_search(call: CallbackQuery, state: FSMContext) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        return
    await state.set_state(CustomerAdminFlow.search)
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Back", callback_data="staff:customers")
    await call.message.edit_text(
        "🔎 Enter name, phone, email, or Telegram ID:", reply_markup=kb.as_markup()
    )
    await call.answer()


@router.message(CustomerAdminFlow.search, F.text)
async def do_search(message: Message, state: FSMContext) -> None:
    role_keys = await get_role_keys(message.from_user.id)
    if not has(role_keys, "view_customers"):
        return
    await state.clear()
    async with get_session() as session:
        results = await search_customers(session, message.text)
    kb = InlineKeyboardBuilder()
    for c in results:
        label = f"{c.full_name or '(no name)'} · {c.phone or c.email or str(c.telegram_id)}"
        kb.button(text=label[:60], callback_data=f"custadm:view:{c.id}")
    kb.button(text="⬅️ Back", callback_data="staff:customers")
    kb.adjust(1)
    text = f"🔎 Search Results\n({len(results)} found)" if results else "🔎 No customers found."
    await message.answer(text, reply_markup=kb.as_markup())


# ── Lists ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "custadm:recent")
async def list_recent(call: CallbackQuery) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        return
    async with get_session() as session:
        customers = await recent_customers(session)
    await _show_list(call, customers, title="🕐 Recent Customers")


@router.callback_query(F.data == "custadm:noemail")
async def list_no_email(call: CallbackQuery) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        return
    async with get_session() as session:
        customers = await missing_email_customers(session)
    await _show_list(call, customers, title="📧 Missing Email")


async def _show_list(call: CallbackQuery, customers: list[Customer], title: str) -> None:
    kb = InlineKeyboardBuilder()
    for c in customers:
        label = f"{c.full_name or '(no name)'} · {c.phone or c.email or str(c.telegram_id)}"
        kb.button(text=label[:60], callback_data=f"custadm:view:{c.id}")
    kb.button(text="⬅️ Back", callback_data="staff:customers")
    kb.adjust(1)
    text = f"{title}\n({len(customers)} shown)" if customers else f"{title}\nNone found."
    await call.message.edit_text(text, reply_markup=kb.as_markup())
    await call.answer()


# ── Profile view ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("custadm:view:"))
async def view_customer(call: CallbackQuery, state: FSMContext) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        return
    cid = UUID(call.data.split("custadm:view:", 1)[1])

    async with get_session() as session:
        profile = await get_customer_profile(session, cid)
        if profile is None:
            await call.answer("Not found.", show_alert=True)
            return
        can_msg = _message_scope(role_keys) != "none"
        if _message_scope(role_keys) == "medicine":
            can_msg = await has_open_medicine_context(session, cid)
        elif _message_scope(role_keys) == "community":
            prefs = (
                await session.execute(
                    select(CustomerPreferences).where(CustomerPreferences.customer_id == cid)
                )
            ).scalar_one_or_none()
            can_msg = prefs is not None and prefs.receive_community_updates

    c: Customer = profile["customer"]
    lines = [
        f"👤 <b>{c.full_name or '(no name)'}</b>",
        f"TG ID: <code>{c.telegram_id}</code>",
    ]
    if c.phone:
        lines.append(f"Phone: {c.phone}")
    if c.email:
        lines.append(f"Email: {c.email}")
        lines.append(f"Opt-in: {'Yes' if c.email_opt_in else 'No'}")
    else:
        lines.append("Email: not set")
    lines.append("")
    lines.append(f"Orders: {profile['order_count']}")
    lines.append(f"Requests: {profile['request_count']}")
    lines.append(f"Pharm tickets: {profile['ticket_count']}")

    if profile["notes"]:
        lines.append("")
        lines.append("📝 <b>Notes:</b>")
        for n in profile["notes"]:
            when = n.created_at.strftime("%m-%d")
            lines.append(f"<i>{when}:</i> {n.note_text[:80]}")

    text = "\n".join(lines)
    kb = InlineKeyboardBuilder()
    if can_msg:
        kb.button(text="💬 Send Message", callback_data=f"custadm:msg:{cid}")
    kb.button(text="📝 Add Note", callback_data=f"custadm:note:{cid}")
    kb.button(text="⬅️ Back", callback_data="staff:customers")
    kb.adjust(1)
    await call.message.edit_text(text, reply_markup=kb.as_markup())
    await call.answer()


# ── Message customer ─────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("custadm:msg:"))
async def start_message(call: CallbackQuery, state: FSMContext) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        return
    cid = call.data.split("custadm:msg:", 1)[1]
    await state.set_state(CustomerAdminFlow.message)
    await state.update_data(cust_id=cid)
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Back", callback_data=f"custadm:view:{cid}")
    await call.message.edit_text(
        "💬 Type your message to the customer:", reply_markup=kb.as_markup()
    )
    await call.answer()


@router.message(CustomerAdminFlow.message, F.text)
async def deliver_message(message: Message, state: FSMContext) -> None:
    role_keys = await get_role_keys(message.from_user.id)
    if not has(role_keys, "view_customers"):
        return
    data = await state.get_data()
    cid = UUID(data.get("cust_id"))
    await state.clear()

    async with get_session() as session:
        customer = await session.get(Customer, cid)
        if customer is None:
            await message.answer("Customer not found.")
            return
        ok, err = await send_customer_message(
            message.bot, session, customer, message.text.strip(),
            sender_admin_id=message.from_user.id,
        )

    await log_activity(message.from_user.id, role_keys, "message_customer", "customer", str(cid))
    if ok:
        await message.answer("✅ Message sent.")
    else:
        await message.answer(
            f"⚠️ Could not reach this customer via Telegram.\n\n"
            f"If you need to contact them, try:\n"
            f"  Phone: {customer.phone or 'not on file'}\n"
            f"  Email: {customer.email or 'not on file'}\n\n"
            f"(The message has been recorded for your records.)"
        )


# ── Add note ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("custadm:note:"))
async def start_note(call: CallbackQuery, state: FSMContext) -> None:
    role_keys = await _guard(call)
    if role_keys is None:
        return
    cid = call.data.split("custadm:note:", 1)[1]
    await state.set_state(CustomerAdminFlow.note)
    await state.update_data(cust_id=cid)
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Back", callback_data=f"custadm:view:{cid}")
    await call.message.edit_text(
        "📝 Type your internal note (not visible to customer):", reply_markup=kb.as_markup()
    )
    await call.answer()


@router.message(CustomerAdminFlow.note, F.text)
async def save_note(message: Message, state: FSMContext) -> None:
    role_keys = await get_role_keys(message.from_user.id)
    if not has(role_keys, "view_customers"):
        return
    data = await state.get_data()
    cid = UUID(data.get("cust_id"))
    await state.clear()

    async with get_session() as session:
        await add_customer_note(session, cid, message.from_user.id, message.text.strip())

    await log_activity(message.from_user.id, role_keys, "add_customer_note", "customer", str(cid))
    await message.answer("✅ Note saved.")
