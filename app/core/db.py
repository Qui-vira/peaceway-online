"""Async database engine and session management."""
from __future__ import annotations

import contextvars
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

# Per-request acting identity for DB-layer access control (RLS reads these).
# (actor_id, actor_type) where actor_type is "admin" | "customer" | "system".
# Set at a request boundary (bot middleware / web auth dep); consumed by
# get_session so the transaction carries the actor. Unset => clinical RLS
# default-denies (safe). Nothing enforces on it yet — Part 2b adds the policies.
current_actor: contextvars.ContextVar[tuple[str, str] | None] = contextvars.ContextVar(
    "current_actor", default=None
)


async def set_session_actor(session: AsyncSession, actor_id, actor_type: str) -> None:
    """Stamp the acting identity onto the CURRENT transaction (transaction-local).

    Uses set_config(..., is_local=true) so it is parameterised (injection-safe) and
    auto-clears at commit/rollback. Web boundaries call this directly (the session is
    opened before auth resolves); the bot sets `current_actor` and get_session applies it.

    No-op on non-Postgres binds (SQLite unit-test sessions) — set_config is Postgres-only.
    """
    bind = session.bind
    if bind is None or bind.dialect.name != "postgresql":
        return
    await session.execute(
        text(
            "SELECT set_config('app.current_actor', :actor, true), "
            "set_config('app.current_actor_type', :atype, true)"
        ),
        {"actor": str(actor_id), "atype": actor_type},
    )


def _normalize_async_url(url: str) -> str:
    """Ensure the URL uses an async driver (asyncpg for Postgres)."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


_settings = get_settings()
engine = create_async_engine(
    _normalize_async_url(_settings.database_url),
    echo=False,
    pool_pre_ping=True,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a session, committing on success and rolling back on error.

    If a `current_actor` is set for this context (bot middleware), stamp it onto the
    transaction so DB-layer access control can see it. No-op when unset.
    """
    async with async_session() as session:
        actor = current_actor.get()
        if actor is not None:
            await set_session_actor(session, actor[0], actor[1])
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
