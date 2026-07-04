"""Unit tests for the Telegram Login Widget verification."""
from __future__ import annotations

import hashlib
import hmac
import time

from app.services.telegram_link import AUTH_MAX_AGE_SECONDS, verify_telegram_login

TOKEN = "123456:TEST-TOKEN"


def _sign(payload: dict, token: str = TOKEN) -> dict:
    data = {k: v for k, v in payload.items() if k != "hash" and v is not None}
    check = "\n".join(f"{k}={data[k]}" for k in sorted(data))
    secret = hashlib.sha256(token.encode()).digest()
    payload["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return payload


def test_valid_payload_passes():
    p = _sign({
        "id": 111,
        "first_name": "Ada",
        "username": "ada_o",
        "auth_date": int(time.time()),
    })
    assert verify_telegram_login(p, TOKEN) is True


def test_tampered_field_fails():
    p = _sign({"id": 111, "auth_date": int(time.time())})
    p["id"] = 999  # attacker swaps the telegram id after signing
    assert verify_telegram_login(p, TOKEN) is False


def test_stale_auth_date_fails():
    p = _sign({"id": 111, "auth_date": int(time.time()) - AUTH_MAX_AGE_SECONDS - 10})
    assert verify_telegram_login(p, TOKEN) is False


def test_missing_hash_fails():
    assert verify_telegram_login({"id": 111, "auth_date": int(time.time())}, TOKEN) is False


def test_wrong_bot_token_fails():
    p = _sign({"id": 111, "auth_date": int(time.time())})
    assert verify_telegram_login(p, "999999:OTHER-TOKEN") is False


def test_none_fields_excluded_from_check_string():
    # The endpoint dumps the pydantic model with exclude_none — a payload signed
    # without optional fields must still verify.
    p = _sign({"id": 111, "auth_date": int(time.time()), "username": None})
    assert verify_telegram_login(p, TOKEN) is True
