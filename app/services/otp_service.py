"""OTP generation, hashing, email delivery, and DB lifecycle."""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings

logger = logging.getLogger(__name__)

OTP_EXPIRY_MINUTES = 10
OTP_RATE_LIMIT = 3
OTP_RATE_WINDOW_MINUTES = 10


# ── Core helpers ──────────────────────────────────────────────────────────────

def generate_code() -> str:
    """Return a 6-digit zero-padded OTP string."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_code(code: str) -> str:
    """Return SHA-256 hex digest of the OTP code."""
    return hashlib.sha256(code.encode()).hexdigest()


# ── Email delivery ────────────────────────────────────────────────────────────

async def send_otp_email(to_email: str, code: str, pharmacy_name: str) -> None:
    """Send OTP code to *to_email* via Resend.

    Falls back to logging when RESEND_API_KEY is not configured (dev/test).
    """
    settings = get_settings()

    if not settings.resend_enabled:
        logger.info(
            "Resend not configured — OTP code for %s: %s (expires in %d min)",
            to_email,
            code,
            OTP_EXPIRY_MINUTES,
        )
        return

    subject = f"Your {pharmacy_name} verification code"
    html_body = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:24px;">
      <h2 style="color:#1a1a1a;">{pharmacy_name}</h2>
      <p style="color:#444;font-size:16px;">Your verification code is:</p>
      <div style="font-size:40px;font-weight:bold;letter-spacing:8px;color:#1a1a1a;
                  padding:16px 0;">{code}</div>
      <p style="color:#666;font-size:14px;">
        This code expires in {OTP_EXPIRY_MINUTES} minutes.<br>
        If you did not request this, you can safely ignore this email.
      </p>
    </div>
    """

    payload = {
        "from": settings.resend_from_email,
        "to": [to_email],
        "subject": subject,
        "html": html_body,
    }

    logger.info("Sending OTP email to %s via Resend (from=%s)", to_email, settings.resend_from_email)
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            "https://api.resend.com/emails",
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            },
        )
        if resp.status_code >= 400:
            logger.error(
                "Resend API error %s: %s", resp.status_code, resp.text
            )
            raise HTTPException(502, "Failed to send verification email. Please try again.")
        logger.info("Resend accepted email to %s — id=%s", to_email, resp.json().get("id"))


# ── DB operations ─────────────────────────────────────────────────────────────

async def create_otp_request(
    session: AsyncSession,
    *,
    phone: str,
    email: str,
    full_name: str | None,
) -> str:
    """Enforce rate limit, create an OTP row, and return the plaintext code."""
    # Rate limit: max OTP_RATE_LIMIT requests per phone in the last OTP_RATE_WINDOW_MINUTES
    window_start = datetime.now(timezone.utc) - timedelta(minutes=OTP_RATE_WINDOW_MINUTES)
    rate_result = await session.execute(
        text(
            """
            SELECT COUNT(*) FROM otp_requests
            WHERE phone = :phone AND created_at >= :window_start
            """
        ),
        {"phone": phone, "window_start": window_start},
    )
    count = rate_result.scalar_one()
    if count >= OTP_RATE_LIMIT:
        raise HTTPException(429, "Too many OTP requests. Please wait before trying again.")

    code = generate_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)

    await session.execute(
        text(
            """
            INSERT INTO otp_requests (phone, email, full_name, code_hash, expires_at)
            VALUES (:phone, :email, :full_name, :code_hash, :expires_at)
            """
        ),
        {
            "phone": phone,
            "email": email,
            "full_name": full_name,
            "code_hash": hash_code(code),
            "expires_at": expires_at,
        },
    )

    return code


async def verify_otp_request(
    session: AsyncSession,
    *,
    phone: str,
    code: str,
) -> tuple[str, str | None]:
    """Verify an OTP code for the given phone.

    Returns (email, full_name) on success.
    Raises HTTPException(400) on invalid/expired code.
    """
    now = datetime.now(timezone.utc)

    result = await session.execute(
        text(
            """
            SELECT id, code_hash, email, full_name
            FROM otp_requests
            WHERE phone = :phone
              AND used = FALSE
              AND expires_at > :now
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"phone": phone, "now": now},
    )
    row = result.mappings().first()

    if row is None:
        raise HTTPException(400, "Invalid or expired code.")

    if hash_code(code) != row["code_hash"]:
        # Invalidate on first wrong guess — prevents brute-force; resend flow is frictionless
        await session.execute(
            text("UPDATE otp_requests SET used = TRUE WHERE id = :id"),
            {"id": row["id"]},
        )
        raise HTTPException(400, "Invalid or expired code.")

    # Mark as used on success
    await session.execute(
        text("UPDATE otp_requests SET used = TRUE WHERE id = :id"),
        {"id": row["id"]},
    )

    return row["email"], row["full_name"]
