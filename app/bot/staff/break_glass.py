"""System-Owner break-glass command: /breakglass <reason>.

Grants the owner a 15-minute clinical read (RLS honours it) and audits the reason.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from app.core.db import get_session
from app.core.rbac import SYSTEM_OWNER
from app.core.security import get_admin_id, get_role_keys
from app.services.break_glass import DEFAULT_MINUTES, grant_break_glass

router = Router(name="staff-break-glass")


@router.message(F.text.regexp(r"^/breakglass(\s|$)"))
async def break_glass_cmd(message: Message) -> None:
    tid = message.from_user.id
    roles = await get_role_keys(tid)
    if SYSTEM_OWNER not in roles:
        await message.answer("⛔ Only the System Owner can use break-glass.")
        return

    reason = (message.text or "").partition(" ")[2].strip()
    if not reason:
        await message.answer("Usage: <code>/breakglass &lt;reason&gt;</code>\nA reason is required and is recorded in the audit log.")
        return

    async with get_session() as session:
        admin_id = await get_admin_id(tid, session)
        if admin_id is None:
            await message.answer(
                "Break-glass needs a registered admin account. The System Owner must exist in "
                "admin_users (not only as an env-bootstrap owner)."
            )
            return
        await grant_break_glass(session, user_id=admin_id, reason=reason)

    await message.answer(
        f"🔓 Break-glass granted for clinical data for {DEFAULT_MINUTES} minutes. "
        f"This access is audited.\nReason: {reason}"
    )
