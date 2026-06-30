"""Catch-all for staff menu buttons that don't yet have a dedicated handler.

Registered LAST among staff routers so it only fires for callbacks no other
handler consumed. Prevents menu buttons from silently doing nothing.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.core.security import get_role_keys

router = Router(name="staff-fallback")


@router.callback_query(F.data.startswith("staff:"))
async def coming_soon(call: CallbackQuery) -> None:
    if not await get_role_keys(call.from_user.id):
        await call.answer("Not authorised.", show_alert=True)
        return
    await call.answer("🚧 This section is coming soon.", show_alert=True)
