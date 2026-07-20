"""Owner-only dispatch rider management: list, add, activate/deactivate.

Riders are external (dispatch_partners), so this uses `manage_admins` (System Owner
only) as the gate, consistent with staff management. Every mutation is audited.
"""
from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.staff.states import RiderFlow
from app.core.db import get_session
from app.core.security import get_role_keys, has, log_activity
from app.services import rider_admin
from app.services.customers import is_valid_email

router = Router(name="staff-riders")


async def _owner(obj) -> set[str] | None:
    role_keys = await get_role_keys(obj.from_user.id)
    return role_keys if has(role_keys, "manage_admins") else None


def _list_kb(riders) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    for r in riders:
        flag = "🟢" if r.is_active else "🔴"
        kb.button(text=f"{flag} {r.name}", callback_data=f"rdr:view:{r.id}")
    kb.button(text="➕ Add rider", callback_data="rdr:add")
    kb.button(text="⬅️ Back", callback_data="staff:home")
    kb.adjust(1)
    return kb


@router.callback_query(F.data == "staff:riders")
async def list_riders(call: CallbackQuery) -> None:
    if await _owner(call) is None:
        await call.answer("Not authorised.", show_alert=True)
        return
    async with get_session() as session:
        riders = await rider_admin.list_riders(session)
    text = "🛵 <b>Dispatch riders</b>" if riders else "🛵 <b>Dispatch riders</b>\n\nNo riders yet."
    await call.message.edit_text(text, reply_markup=_list_kb(riders).as_markup())
    await call.answer()


@router.callback_query(F.data.startswith("rdr:view:"))
async def view_rider(call: CallbackQuery) -> None:
    if await _owner(call) is None:
        await call.answer("Not authorised.", show_alert=True)
        return
    rid = UUID(call.data.split("rdr:view:", 1)[1])
    async with get_session() as session:
        r = await rider_admin.get_rider(session, rid)
    if r is None:
        await call.answer("Not found.", show_alert=True)
        return
    text = (
        f"🛵 <b>{r.name}</b>\n"
        f"Email: {r.portal_login_email}\n"
        f"Phone: {r.phone or '-'}\n"
        f"Status: {'🟢 active' if r.is_active else '🔴 inactive'}"
    )
    kb = InlineKeyboardBuilder()
    if r.is_active:
        kb.button(text="🔴 Deactivate", callback_data=f"rdr:off:{r.id}")
    else:
        kb.button(text="🟢 Activate", callback_data=f"rdr:on:{r.id}")
    kb.button(text="⬅️ Back", callback_data="staff:riders")
    kb.adjust(1)
    await call.message.edit_text(text, reply_markup=kb.as_markup())
    await call.answer()


async def _set_active(call: CallbackQuery, rid: UUID, active: bool) -> None:
    role_keys = await _owner(call)
    if role_keys is None:
        await call.answer("Not authorised.", show_alert=True)
        return
    async with get_session() as session:
        ok = await rider_admin.set_rider_active(session, rid, active)
    if not ok:
        await call.answer("Not found.", show_alert=True)
        return
    await log_activity(
        call.from_user.id, role_keys, "activate_rider" if active else "deactivate_rider",
        "dispatch_partner", str(rid),
    )
    # Re-render the detail view.
    call.data = f"rdr:view:{rid}"
    await view_rider(call)


@router.callback_query(F.data.startswith("rdr:on:"))
async def activate_rider(call: CallbackQuery) -> None:
    await _set_active(call, UUID(call.data.split("rdr:on:", 1)[1]), True)


@router.callback_query(F.data.startswith("rdr:off:"))
async def deactivate_rider(call: CallbackQuery) -> None:
    await _set_active(call, UUID(call.data.split("rdr:off:", 1)[1]), False)


@router.callback_query(F.data == "rdr:add")
async def add_start(call: CallbackQuery, state: FSMContext) -> None:
    if await _owner(call) is None:
        await call.answer("Not authorised.", show_alert=True)
        return
    await state.set_state(RiderFlow.add_details)
    await call.message.edit_text(
        "➕ <b>Add rider</b>\n\nSend the rider's details as: <i>Name, email, phone</i>\n"
        "The email is their portal login (their code is sent there). Phone is optional."
    )
    await call.answer()


@router.message(RiderFlow.add_details, F.text)
async def add_capture(message: Message, state: FSMContext) -> None:
    role_keys = await get_role_keys(message.from_user.id)
    if not has(role_keys, "manage_admins"):
        await state.clear()
        return
    parts = [p.strip() for p in message.text.split(",")]
    name = parts[0] if parts else ""
    email = parts[1] if len(parts) > 1 else ""
    phone = parts[2] if len(parts) > 2 else None
    if not name or not is_valid_email(email):
        await message.answer("Please send it as: <i>Name, email, phone</i> with a valid email.")
        return
    await state.clear()
    async with get_session() as session:
        rider, created = await rider_admin.add_rider(session, name=name, email=email, phone=phone)
        rid = rider.id
    await log_activity(
        message.from_user.id, role_keys, "add_rider" if created else "reactivate_rider",
        "dispatch_partner", str(rid),
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="🛵 Riders", callback_data="staff:riders")
    await message.answer(
        f"✅ Rider <b>{name}</b> {'added' if created else 'updated'} and active.\n"
        f"They can sign in at the dispatch portal with {email}.",
        reply_markup=kb.as_markup(),
    )
