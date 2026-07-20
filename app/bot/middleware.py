"""Bot middleware that stamps the acting identity onto the request context.

Resolves each incoming message/callback's Telegram user to a staff admin or a
customer and sets `current_actor` for the duration of the update, so any get_session
opened by the handler carries the actor for DB-layer access control (RLS).

Behaviour-neutral until Part 2b adds the clinical RLS policies that read the actor.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy import text

from app.core.db import current_actor, get_session

# One query: prefer an active admin identity, else a customer, for a Telegram id.
_RESOLVE_SQL = text(
    """
    SELECT id::text AS actor_id, atype FROM (
        SELECT id, 'admin'    AS atype, 0 AS ord FROM admin_users WHERE telegram_id = :tid AND is_active
        UNION ALL
        SELECT id, 'customer' AS atype, 1 AS ord FROM customers   WHERE telegram_id = :tid
    ) x ORDER BY ord LIMIT 1
    """
)


async def resolve_actor(telegram_id: int) -> tuple[str, str] | None:
    """(actor_id, actor_type) for a Telegram id, or None if neither admin nor customer."""
    async with get_session() as session:
        row = (await session.execute(_RESOLVE_SQL, {"tid": telegram_id})).first()
    return (row.actor_id, row.atype) if row else None


class ActorContextMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        token = None
        if user is not None:
            actor = await resolve_actor(user.id)
            if actor is not None:
                token = current_actor.set(actor)
        try:
            return await handler(event, data)
        finally:
            if token is not None:
                current_actor.reset(token)
