"""Unit tests for the bot actor-context middleware (no DB; resolver stubbed)."""
from __future__ import annotations

from app.bot import middleware as mw_mod
from app.core.db import current_actor


class _User:
    def __init__(self, uid: int):
        self.id = uid


async def test_middleware_sets_actor_during_handler_and_resets(monkeypatch):
    async def fake_resolve(_tid):
        return ("abc-123", "admin")

    monkeypatch.setattr(mw_mod, "resolve_actor", fake_resolve)
    seen = {}

    async def handler(event, data):
        seen["actor"] = current_actor.get()
        return "ok"

    mw = mw_mod.ActorContextMiddleware()
    assert current_actor.get() is None
    result = await mw(handler, event=object(), data={"event_from_user": _User(555)})

    assert result == "ok"
    assert seen["actor"] == ("abc-123", "admin")   # set for the handler
    assert current_actor.get() is None             # reset afterwards


async def test_middleware_noop_when_actor_unresolved(monkeypatch):
    async def fake_resolve(_tid):
        return None

    monkeypatch.setattr(mw_mod, "resolve_actor", fake_resolve)

    async def handler(event, data):
        assert current_actor.get() is None
        return "ok"

    mw = mw_mod.ActorContextMiddleware()
    await mw(handler, event=object(), data={"event_from_user": _User(1)})
    assert current_actor.get() is None


async def test_middleware_handles_missing_user(monkeypatch):
    async def boom(_tid):  # must not be called when there's no user
        raise AssertionError("resolve_actor should not run without a user")

    monkeypatch.setattr(mw_mod, "resolve_actor", boom)

    async def handler(event, data):
        return "ok"

    mw = mw_mod.ActorContextMiddleware()
    assert await mw(handler, event=object(), data={}) == "ok"
