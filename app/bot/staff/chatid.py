"""One-off helper: /chatid returns the current chat id (System Owner only).

Run it inside the staff group to read the group's chat id, then set it as
STAFF_GROUP_CHAT_ID. No third-party bot required.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from app.core.security import get_role_keys, has

router = Router(name="staff-chatid")


@router.message(F.text.regexp(r"^/chatid(@\w+)?(\s|$)"))
async def chat_id_cmd(message: Message) -> None:
    role_keys = await get_role_keys(message.from_user.id)
    if not has(role_keys, "manage_admins"):  # System Owner only
        return
    chat = message.chat
    if chat.type in ("group", "supergroup"):
        await message.reply(
            f"This group's chat id is <code>{chat.id}</code>.\n"
            "Set it as <b>STAFF_GROUP_CHAT_ID</b> and the bot will post status here."
        )
    else:
        await message.reply(
            f"This chat id is <code>{chat.id}</code>. Run /chatid inside the staff group "
            "to read the group id."
        )
