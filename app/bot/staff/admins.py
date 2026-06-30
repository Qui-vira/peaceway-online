"""System Owner staff management: list, add, enable/disable admins; view activity.

Gated on the `manage_admins` permission (System Owner only).
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
from app.services import rbac_service

router = Router(name="staff-admins")


async def _require_owner(call_or_msg) -> set[str] | None:
    role_keys = await get_role_keys(call_or_msg.from_user.id)
    if not has(role_keys, "manage_admins"):
        return None
    return role_keys


def _admins_kb(admins: list[AdminUser]):
    kb = InlineKeyboardBuilder()
    for a in admins:
        roles = ",".join(sorted(x.role_key for x in a.assignments)) or "none"
        flag = "🟢" if a.is_active else "🔴"
        kb.button(text=f"{flag} {a.full_name or a.telegram_id} · {roles}", callback_data=f"adm:view:{a.telegram_id}")
    kb.button(text="➕ Add Admin", callback_data="adm:add")
    kb.button(text="⬅️ Back", callback_data="staff:home")
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(F.data == "staff:admins")
async def list_admins(call: CallbackQuery) -> None:
    if await _require_owner(call) is None:
        await call.answer("Only the System Owner can manage staff.", show_alert=True)
        return
    async with get_session() as session:
        admins = (await session.execute(select(AdminUser).order_by(AdminUser.created_at))).scalars().unique().all()
    text = "👥 <b>Staff</b>" if admins else "👥 <b>Staff</b>\n\nNo admins yet. Add the first one."
    await call.message.edit_text(text, reply_markup=_admins_kb(admins))
    await call.answer()


@router.callback_query(F.data.startswith("adm:view:"))
async def view_admin(call: CallbackQuery) -> None:
    if await _require_owner(call) is None:
        await call.answer("Not authorised.", show_alert=True)
        return
    tid = int(call.data.split("adm:view:", 1)[1])
    async with get_session() as session:
        admin = (await session.execute(select(AdminUser).where(AdminUser.telegram_id == tid))).scalar_one_or_none()
        if admin is None:
            await call.answer("Not found.", show_alert=True)
            return
        roles = ", ".join(rbac.role_label(x.role_key) for x in admin.assignments) or "none"
        last = admin.last_activity_at.strftime("%Y-%m-%d %H:%M") if admin.last_activity_at else "never"
        text = (
            f"👤 <b>{admin.full_name or admin.telegram_id}</b>\n"
            f"Telegram ID: <code>{admin.telegram_id}</code>\n"
            f"Email: {admin.email or '-'}\n"
            f"Roles: {roles}\n"
            f"Status: {'🟢 Active' if admin.is_active else '🔴 Disabled'}\n"
            f"Last activity: {last}\n"
            f"Created: {admin.created_at.strftime('%Y-%m-%d')}"
        )
        active = admin.is_active
    kb = InlineKeyboardBuilder()
    if active:
        kb.button(text="🔴 Disable", callback_data=f"adm:disable:{tid}")
    else:
        kb.button(text="🟢 Enable", callback_data=f"adm:enable:{tid}")
    kb.button(text="➕ Add another role", callback_data=f"adm:addrole:{tid}")
    kb.button(text="⬅️ Back", callback_data="staff:admins")
    kb.adjust(1)
    await call.message.edit_text(text, reply_markup=kb.as_markup())
    await call.answer()


@router.callback_query(F.data.startswith("adm:disable:") | F.data.startswith("adm:enable:"))
async def toggle_admin(call: CallbackQuery) -> None:
    role_keys = await _require_owner(call)
    if role_keys is None:
        await call.answer("Not authorised.", show_alert=True)
        return
    enable = call.data.startswith("adm:enable:")
    tid = int(call.data.rsplit(":", 1)[1])
    await rbac_service.set_admin_active(tid, enable)
    await log_activity(call.from_user.id, role_keys, "enable_admin" if enable else "disable_admin", "admin_user", str(tid))
    await call.answer("Updated ✅")
    call.data = f"adm:view:{tid}"
    await view_admin(call)


# ── Add-admin flow ───────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm:add")
async def add_start(call: CallbackQuery, state: FSMContext) -> None:
    if await _require_owner(call) is None:
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
    await message.answer(
        f"✅ Added <b>{full_name or tid}</b> as <b>{rbac.role_label(role_key)}</b>.\n\n"
        "⚠️ They must open the bot and send /start before they can receive alerts."
    )


@router.callback_query(F.data.startswith("adm:addrole:"))
async def add_role_to_existing(call: CallbackQuery, state: FSMContext) -> None:
    if await _require_owner(call) is None:
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
    from app.bot.staff.panel import admin_panel

    # Re-render the panel via a fresh message edit.
    role_keys = await get_role_keys(call.from_user.id)
    if not role_keys:
        await call.answer("Not authorised.", show_alert=True)
        return
    items = rbac.menu_for(role_keys)
    kb = InlineKeyboardBuilder()
    for label, cb in items:
        kb.button(text=label, callback_data=cb)
    kb.adjust(1)
    role_names = ", ".join(rbac.role_label(r) for r in sorted(role_keys))
    await call.message.edit_text(f"🛠 <b>Staff Panel</b>\nRoles: <b>{role_names}</b>", reply_markup=kb.as_markup())
    await call.answer()
