"""Verify Telegram Login Widget payloads for linking accounts to web customers.

The widget signs its payload with HMAC-SHA256 keyed on SHA256(bot_token); the
same scheme is documented at https://core.telegram.org/widgets/login. Only a
payload that verifies AND is fresh (auth_date within AUTH_MAX_AGE_SECONDS) may
be trusted — the browser is never the source of truth.
"""
from __future__ import annotations

import hashlib
import hmac
import time

AUTH_MAX_AGE_SECONDS = 5 * 60


def verify_telegram_login(payload: dict, bot_token: str, *, now: float | None = None) -> bool:
    """True if the Login Widget payload is authentic and fresh."""
    received_hash = payload.get("hash", "")
    data = {k: v for k, v in payload.items() if k != "hash" and v is not None}
    if not received_hash or "id" not in data or "auth_date" not in data:
        return False

    check_string = "\n".join(f"{k}={data[k]}" for k in sorted(data))
    secret = hashlib.sha256(bot_token.encode()).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        return False

    try:
        auth_date = int(data["auth_date"])
    except (TypeError, ValueError):
        return False
    current = now if now is not None else time.time()
    return (current - auth_date) <= AUTH_MAX_AGE_SECONDS
