"""Minimal SMTP email sender (aiosmtplib). No-op if SMTP isn't configured."""
from __future__ import annotations

from email.message import EmailMessage

import aiosmtplib

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("email")


async def send_email(to: list[str], subject: str, body: str) -> bool:
    """Send a plain-text email. Returns True on success, False otherwise."""
    s = get_settings()
    if not s.email_enabled or not to:
        return False
    msg = EmailMessage()
    msg["From"] = s.smtp_from_email
    msg["To"] = ", ".join(to)
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        await aiosmtplib.send(
            msg,
            hostname=s.smtp_host,
            port=s.smtp_port,
            username=s.smtp_username or None,
            password=s.smtp_password or None,
            start_tls=s.smtp_port == 587,
            use_tls=s.smtp_port == 465,
        )
        return True
    except Exception as exc:  # noqa: BLE001
        log.error("email_send_failed", error=str(exc))
        return False
