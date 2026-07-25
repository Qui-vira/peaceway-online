"""The global bot error handler must always answer and never raise."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.bot.errors import ALERT_TEXT, on_bot_error


class _Recorder:
    def __init__(self, raises: Exception | None = None):
        self.calls: list[tuple] = []
        self._raises = raises

    async def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self._raises is not None:
            raise self._raises


def _event(*, callback=None, message=None, exception=None):
    return SimpleNamespace(
        exception=exception or RuntimeError("boom"),
        update=SimpleNamespace(update_id=1, callback_query=callback, message=message),
    )


def _callback(answer):
    return SimpleNamespace(
        data="checkout:confirm",
        from_user=SimpleNamespace(id=42),
        answer=answer,
    )


async def test_callback_is_answered_so_the_button_never_hangs():
    answer = _Recorder()
    handled = await on_bot_error(_event(callback=_callback(answer)))

    assert handled is True
    assert len(answer.calls) == 1
    args, kwargs = answer.calls[0]
    assert args[0] == ALERT_TEXT
    assert kwargs.get("show_alert") is True


async def test_message_gets_a_reply():
    reply = _Recorder()
    msg = SimpleNamespace(from_user=SimpleNamespace(id=7), answer=reply)
    handled = await on_bot_error(_event(message=msg))

    assert handled is True
    assert len(reply.calls) == 1


async def test_generic_text_never_leaks_internal_error_detail():
    answer = _Recorder()
    secret = RuntimeError("relation customers does not exist at 10.0.0.4:5432")
    await on_bot_error(_event(callback=_callback(answer), exception=secret))

    sent = answer.calls[0][0][0]
    assert "relation customers" not in sent
    assert "5432" not in sent


async def test_handler_survives_a_failing_answer():
    """A stale callback can't be answered - that must not mask the original error."""
    answer = _Recorder(raises=RuntimeError("query is too old"))
    handled = await on_bot_error(_event(callback=_callback(answer)))
    assert handled is True  # did not propagate


async def test_handler_survives_an_update_with_neither_message_nor_callback():
    handled = await on_bot_error(_event())
    assert handled is True


def test_handler_is_registered_on_the_dispatcher():
    """Wiring guard: the unit tests above pass even if registration is dropped."""
    from app.bot.dispatcher import build_dispatcher

    dp = build_dispatcher()
    assert on_bot_error in [h.callback for h in dp.errors.handlers]
