"""Staff management: list/search, add, activate, disable, remove admins + roles.

Viewing the directory only needs `view_staff_directory` (Lead Pharmacist gets
this, read-only). Every mutating action (activate/disable/remove/add/remove
role) requires `manage_admins` (System Owner only).
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from app.bot.staff.states import AdminFlow
from app.core import rbac
from app.core.db import get_session
from app.core.security import get_role_keys, has, log_activity
from app.models import AdminActivityLog, AdminUser
from app.models.admin import AdminStatus
from app.services import rbac_service

router = Router(name="staff-admins")

_STATUS_FLAG = {
    AdminStatus.ACTIVE: "🟢",
    AdminStatus.PENDING: "🟡",
    AdminStatus.DISABLED: "🔴",
    AdminStatus.REMOVED: "⚫",
}


async def _viewer(call_or_msg) -> set[str] | None:
    """Anyone with view_staff_directory or manage_admins may open the directory."""
    role_keys = await get_role_keys(call_or_msg.from_user.id)
    if not (has(role_keys, "view_staff_directory") or has(role_keys, "manage_admins")):
        return None
    return role_keys


async def _manager(call_or_msg) -> set[str] | None:
    role_keys = await get_role_keys(call_or_msg.from_user.id)
    if not has(role_keys, "manage_admins"):
        return None
    return role_keys


def _admins_kb(admins: list[AdminUser], can_manage: bool):
    kb = InlineKeyboardBuilder()
    for a in admins:
        roles = ",".join(sorted(x.role_key for x in a.assignments)) or "no roles"
        flag = _STATUS_FLAG.get(a.status, "")
        kb.button(text=f"{flag} {a.full_name or a.telegram_id} · {roles}", callback_data=f"adm:view:{a.telegram_id}")
    if can_manage:
        kb.button(text="🔎 Search Admin", callback_data="adm:search")
        kb.button(text="➕ Add Admin", callback_data="adm:add")
    kb.button(text="⬅️ Back", callback_data="staff:home")
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(F.data == "staff:admins")
async def list_admins(call: CallbackQuery) -> None:
    role_keys = await _viewer(call)
    if role_keys is None:
        await call.answer("Not authorised.", show_alert=True)
        return
    can_manage = has(role_keys, "manage_admins")
    async with get_session() as session:
        admins = (await session.execute(select(AdminUser).order_by(AdminUser.created_at))).scalars().unique().all()
    text = "👥 <b>Staff</b>" if admins else "👥 <b>Staff</b>\n\nNo admins yet."
    await call.message.edit_text(text, reply_markup=_admins_kb(admins, can_manage))
    await call.answer()


@router.callback_query(F.data == "adm:search")
async def ask_search(call: CallbackQuery, state: FSMContext) -> None:
    if await _manager(call) is None:
        await call.answer("Not authorised.", show_alert=True)
        return
    await state.set_state(AdminFlow.search)
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Back", callback_data="staff:admins")
    await call.message.edit_text("🔎 Type a name or numeric Telegram ID to search.", reply_markup=kb.as_markup())
    await call.answer()


@router.message(AdminFlow.search, F.text)
async def do_search(message: Message, state: FSMContext) -> None:
    await state.clear()
    results = await rbac_service.search_admins(message.text)
    if not results:
        await message.answer(f"No admins found for “{message.text}”.")
        return
    await message.answer("Results:", reply_markup=_admins_kb(results, True))


async def _admin_detail(tid: int, viewer_id: int, can_manage: bool):
    """Render the admin detail view. Returns (text, markup) or None if not found."""
    async with get_session() as session:
        admin = (await session.execute(select(AdminUser).where(AdminUser.telegram_id == tid))).scalar_one_or_none()
        if admin is None:
            return None
        roles = [x.role_key for x in admin.assignments]
        last = admin.last_activity_at.strftime("%Y-%m-%d %H:%M") if admin.last_activity_at else "never"
        text = (
            f"👤 <b>{admin.full_name or admin.telegram_id}</b>\n"
            f"Telegram ID: <code>{admin.telegram_id}</code>\n"
            f"Email: {admin.email or '-'}\n"
            f"Roles: {', '.join(rbac.role_label(r) for r in roles) or 'none'}\n"
            f"Status: {_STATUS_FLAG.get(admin.status, '')} {admin.status.value}\n"
            f"Last activity: {last}\n"
            f"Created: {admin.created_at.strftime('%Y-%m-%d')}"
        )
        status = admin.status

    kb = InlineKeyboardBuilder()
    if can_manage:
        is_self_owner = tid == viewer_id and rbac.SYSTEM_OWNER in roles
        if status == AdminStatus.PENDING:
            kb.button(text="✅ Activate", callback_data=f"adm:activate:{tid}")
        elif status == AdminStatus.ACTIVE:
            if not is_self_owner:
                kb.button(text="🔴 Disable", callback_data=f"adm:disable:{tid}")
        elif status == AdminStatus.DISABLED:
            kb.button(text="🟢 Reactivate", callback_data=f"adm:activate:{tid}")
        if status != AdminStatus.REMOVED and not is_self_owner:
            kb.button(text="🗑 Remove Admin", callback_data=f"adm:remove:{tid}")
        if roles and status != AdminStatus.REMOVED:
            for rk in roles:
                if rk == rbac.SYSTEM_OWNER and is_self_owner:
                    continue  # cannot remove your own owner role
                kb.button(text=f"➖ Remove role: {rbac.role_label(rk)}", callback_data=f"adm:rmrole:{rk}:{tid}")
        if status != AdminStatus.REMOVED:
            kb.button(text="➕ Add another role", callback_data=f"adm:addrole:{tid}")
    kb.button(text="⬅️ Back", callback_data="staff:admins")
    kb.adjust(1)
    return text, kb.as_markup()


async def _show_admin(call: CallbackQuery, tid: int, can_manage: bool) -> None:
    """Edit the current message to the admin detail view (post-action refresh)."""
    rendered = await _admin_detail(tid, call.from_user.id, can_manage)
    if rendered is None:
        return
    text, markup = rendered
    await call.message.edit_text(text, reply_markup=markup)


@router.callback_query(F.data.startswith("adm:view:"))
async def view_admin(call: CallbackQuery) -> None:
    role_keys = await _viewer(call)
    if role_keys is None:
        await call.answer("Not authorised.", show_alert=True)
        return
    tid = int(call.data.split("adm:view:", 1)[1])
    rendered = await _admin_detail(tid, call.from_user.id, has(role_keys, "manage_admins"))
    if rendered is None:
        await call.answer("Not found.", show_alert=True)
        return
    text, markup = rendered
    await call.message.edit_text(text, reply_markup=markup)
    await call.answer()


@router.callback_query(F.data.startswith("adm:activate:"))
async def activate(call: CallbackQuery) -> None:
    role_keys = await _manager(call)
    if role_keys is None:
        await call.answer("Not authorised.", show_alert=True)
        return
    tid = int(call.data.split("adm:activate:", 1)[1])
    await rbac_service.activate_admin(tid)
    await log_activity(call.from_user.id, role_keys, "activate_admin", "admin_user", str(tid))
    await _show_admin(call, tid, can_manage=True)
    await call.answer("Admin activated ✅")


@router.callback_query(F.data.startswith("adm:disable:"))
async def disable(call: CallbackQuery) -> None:
    role_keys = await _manager(call)
    if role_keys is None:
        await call.answer("Not authorised.", show_alert=True)
        return
    tid = int(call.data.split("adm:disable:", 1)[1])
    if tid == call.from_user.id:
        await call.answer("You cannot disable your own access.", show_alert=True)
        return
    await rbac_service.disable_admin(tid)
    await log_activity(call.from_user.id, role_keys, "disable_admin", "admin_user", str(tid))
    await _show_admin(call, tid, can_manage=True)
    await call.answer("Admin access disabled successfully.")


@router.callback_query(F.data.startswith("adm:remove:"))
async def remove(call: CallbackQuery) -> None:
    role_keys = await _manager(call)
    if role_keys is None:
        await call.answer("Not authorised.", show_alert=True)
        return
    tid = int(call.data.split("adm:remove:", 1)[1])
    if tid == call.from_user.id:
        await call.answer("You cannot remove your own access.", show_alert=True)
        return
    await rbac_service.remove_admin(tid)
    await log_activity(call.from_user.id, role_keys, "remove_admin", "admin_user", str(tid))
    await _show_admin(call, tid, can_manage=True)
    await call.answer("Admin removed.")


@router.callback_query(F.data.startswith("adm:rmrole:"))
async def remove_role(call: CallbackQuery) -> None:
    role_keys = await _manager(call)
    if role_keys is None:
        await call.answer("Not authorised.", show_alert=True)
        return
    _, _, role_key, tid_s = call.data.split(":", 3)
    tid = int(tid_s)
    await rbac_service.remove_admin_role(tid, role_key)
    await log_activity(call.from_user.id, role_keys, "remove_admin_role", "admin_user", str(tid), {"role": role_key})
    await _show_admin(call, tid, can_manage=True)
    await call.answer("Role removed ✅")


# ── Add-admin flow ───────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm:add")
async def add_start(call: CallbackQuery, state: FSMContext) -> None:
    if await _manager(call) is None:
        await call.answer("Not authorised.", show_alert=True)
        return
    await state.set_state(AdminFlow.add_telegram_id)
    await call.message.edit_text(
        "➕ <b>Add admin</b>\n\nSend the new staff member's numeric Telegram ID.\n"
        "<i>They get it by sending /myid to this bot.</i>"
    )
    await call.answer()


@router.message(AdminFlow.add_telegram_id, F.text)
async def add_got_id(message: Message, state: FSMContext) -> None:
    raw = message.text.strip()
    if not raw.isdigit():
        await message.answer("Please send a numeric Telegram ID (digits only).")
        return
    await state.update_data(new_admin_id=int(raw))
    await state.set_state(AdminFlow.add_role)
    kb = InlineKeyboardBuilder()
    for key, name in rbac.ROLES.items():
        kb.button(text=name, callback_data=f"adm:role:{key}")
    kb.adjust(1)
    await message.answer("Choose the role for this admin:", reply_markup=kb.as_markup())


@router.callback_query(AdminFlow.add_role, F.data.startswith("adm:role:"))
async def add_got_role(call: CallbackQuery, state: FSMContext) -> None:
    role_key = call.data.split("adm:role:", 1)[1]
    await state.update_data(new_admin_role=role_key)
    await state.set_state(AdminFlow.add_details)
    await call.message.edit_text(
        f"Role: <b>{rbac.role_label(role_key)}</b>\n\n"
        "Send the admin's details as: <i>Full Name, email</i>\n"
        "(or type <i>skip</i> to leave blank)"
    )
    await call.answer()


@router.message(AdminFlow.add_details, F.text)
async def add_got_details(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()
    tid = data["new_admin_id"]
    role_key = data["new_admin_role"]
    full_name, email = None, None
    if message.text.strip().lower() != "skip":
        parts = [p.strip() for p in message.text.split(",", 1)]
        full_name = parts[0] or None
        email = parts[1] if len(parts) > 1 else None

    await rbac_service.add_admin(tid, role_key, full_name=full_name, email=email)
    role_keys = await get_role_keys(message.from_user.id)
    await log_activity(message.from_user.id, role_keys, "add_admin", "admin_user", str(tid), {"role": role_key})
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Activate now", callback_data=f"adm:activate:{tid}")
    kb.button(text="👥 Staff list", callback_data="staff:admins")
    kb.adjust(1)
    await message.answer(
        f"✅ Added <b>{full_name or tid}</b> as <b>{rbac.role_label(role_key)}</b> - status: 🟡 PENDING.\n\n"
        "Tap <b>Activate now</b> to grant them access to /admin and the web panel.\n"
        "<i>If they have never messaged this bot, ask them to send /start once so "
        "they can receive alerts.</i>",
        reply_markup=kb.as_markup(),
    )


@router.callback_query(F.data.startswith("adm:addrole:"))
async def add_role_to_existing(call: CallbackQuery, state: FSMContext) -> None:
    if await _manager(call) is None:
        await call.answer("Not authorised.", show_alert=True)
        return
    tid = int(call.data.split("adm:addrole:", 1)[1])
    await state.update_data(new_admin_id=tid)
    await state.set_state(AdminFlow.add_role)
    kb = InlineKeyboardBuilder()
    for key, name in rbac.ROLES.items():
        kb.button(text=name, callback_data=f"adm:role:{key}")
    kb.adjust(1)
    await call.message.edit_text("Choose an additional role:", reply_markup=kb.as_markup())
    await call.answer()


# ── Logs view (System Owner) ──────────────────────────────────────────────────
@router.callback_query(F.data == "staff:logs")
async def view_logs(call: CallbackQuery) -> None:
    role_keys = await get_role_keys(call.from_user.id)
    if not has(role_keys, "view_all_logs"):
        await call.answer("Not authorised.", show_alert=True)
        return
    async with get_session() as session:
        logs = (
            await session.execute(select(AdminActivityLog).order_by(AdminActivityLog.created_at.desc()).limit(20))
        ).scalars().all()
    if not logs:
        await call.message.edit_text("🪵 No admin activity logged yet.")
    else:
        lines = ["🪵 <b>Recent admin activity</b>\n"]
        for lg in logs:
            when = lg.created_at.strftime("%m-%d %H:%M")
            lines.append(f"• {when} · {lg.roles or '?'} · {lg.action} {lg.entity_id or ''}")
        await call.message.edit_text("\n".join(lines))
    await call.answer()


@router.callback_query(F.data == "staff:home")
async def staff_home(call: CallbackQuery) -> None:
    from app.bot.staff.panel import render_panel

    role_keys = await get_role_keys(call.from_user.id)
    if not role_keys:
        await call.answer("Not authorised.", show_alert=True)
        return
    text, kb = await render_panel(role_keys)
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()
