"""Global handler for unhandled exceptions raised inside bot handlers.

Without this, an exception in a handler is swallowed by aiogram's error middleware:
the callback is never answered, so an inline button just spins and then does nothing.
That is how the `fulfillment_status` enum bug hid - every "Confirm Order" tap failed
with no visible sign, for days. A silent failure is worse than a loud one.

This turns any unhandled exception into (a) a structured log line carrying the full
traceback, and (b) a short, generic apology to the user so a broken flow is reported
instead of mistaken for a dead button.

Two rules this module must never break:
  1. It must never raise. An exception here would mask the original error.
  2. It must never show internal error text to the user - only a generic message.
     Details go to the logs, which is where staff can act on them.

Message text is deliberately NOT logged: it routinely carries names, phone numbers and
delivery addresses. Only identifiers and the exception are recorded.
"""
from __future__ import annotations

import traceback

from aiogram.types import ErrorEvent

from app.core.logging import get_logger

log = get_logger("bot.errors")

# Kept under Telegram's ~200 char limit for callback alerts.
ALERT_TEXT = "⚠️ Something went wrong on our side. Please try again."
MESSAGE_TEXT = (
    "⚠️ Something went wrong on our side, and your last action did not go through. "
    "Nothing has been charged.\n\nPlease try again. If it keeps happening, send /start "
    "and our team will help."
)


async def on_bot_error(event: ErrorEvent) -> bool:
    """Log the failure with full context and tell the user something broke.

    Returns True so aiogram treats the error as handled.
    """
    exception = event.exception
    update = event.update
    callback = getattr(update, "callback_query", None)
    message = getattr(update, "message", None)

    user = getattr(callback or message, "from_user", None)

    try:
        tb = "".join(
            traceback.format_exception(type(exception), exception, exception.__traceback__)
        )
    except Exception:  # noqa: BLE001 - never let formatting break the handler
        tb = "<traceback unavailable>"

    log.error(
        "bot_handler_error",
        error_type=type(exception).__name__,
        error=str(exception),
        update_id=getattr(update, "update_id", None),
        telegram_id=getattr(user, "id", None),
        callback_data=getattr(callback, "data", None),
        traceback=tb,
    )

    # Always answer a callback query - an unanswered one leaves the button spinning,
    # which is exactly the symptom this handler exists to remove.
    try:
        if callback is not None:
            await callback.answer(ALERT_TEXT, show_alert=True)
        elif message is not None:
            await message.answer(MESSAGE_TEXT)
    except Exception as notify_exc:  # noqa: BLE001 - e.g. callback too old to answer
        log.error("bot_error_notify_failed", error=str(notify_exc))

    return True
