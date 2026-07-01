"""Application configuration loaded from environment variables.

All secrets and tunables live here. Nothing is hardcoded elsewhere.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_ids(raw: str) -> set[int]:
    """Parse a comma-separated string of Telegram numeric IDs into a set of ints."""
    out: set[int] = set()
    for part in (raw or "").split(","):
        part = part.strip()
        if part:
            try:
                out.add(int(part))
            except ValueError:
                continue
    return out


def _parse_emails(raw: str) -> list[str]:
    return [e.strip() for e in (raw or "").split(",") if e.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # Telegram
    telegram_bot_token: str = ""
    webhook_base_url: str = ""

    # Databases
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/peaceway"
    pharmaos_database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/pharmaos"

    # Pharmacy identity
    pharmacy_name: str = "Peaceway Pharmacy"

    # Bank transfer (single, legacy) — used as fallback when bank_accounts is empty
    bank_account_name: str = ""
    bank_account_number: str = ""
    bank_name: str = ""
    # Multiple accounts: "Bank|Account Name|Number" entries separated by ";"
    bank_accounts: str = ""

    # Flutterwave
    flutterwave_secret_key: str = ""
    flutterwave_public_key: str = ""
    flutterwave_webhook_hash: str = ""

    # Role IDs (raw comma-separated strings from env)
    owner_telegram_ids: str = ""
    pharmacist_telegram_ids: str = ""
    packaging_staff_telegram_ids: str = ""
    dispatcher_telegram_ids: str = ""
    support_telegram_ids: str = ""

    # Role emails
    owner_emails: str = ""
    pharmacist_emails: str = ""
    packaging_staff_emails: str = ""
    dispatcher_emails: str = ""
    support_emails: str = ""

    # SMTP
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""

    # Optional staff group
    staff_group_chat_id: str = ""

    # Logistics provider keys (P2)
    kwik_api_key: str = ""
    fez_api_key: str = ""
    gokada_api_key: str = ""
    custom_api_key: str = ""

    # Crypto off-ramp (Phase 3 — optional, manual settlement)
    crypto_wallets: str = ""  # "NETWORK:TOKEN:ADDRESS" entries, comma-separated

    # Web API
    # Comma-separated origins allowed to call /api/v1/* from a browser.
    # Example: https://peacewayonline.com.ng,http://localhost:3000
    allowed_origins: str = "http://localhost:3000"
    # Random 32-char secret used to sign web session tokens (Phase 1+).
    # Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
    web_secret: str = ""

    # Runtime
    env: str = "development"
    log_level: str = "INFO"

    # ── Parsed helpers ──────────────────────────────────────────────────────
    @property
    def owner_ids(self) -> set[int]:
        return _parse_ids(self.owner_telegram_ids)

    @property
    def pharmacist_ids(self) -> set[int]:
        return _parse_ids(self.pharmacist_telegram_ids)

    @property
    def packaging_ids(self) -> set[int]:
        return _parse_ids(self.packaging_staff_telegram_ids)

    @property
    def dispatcher_ids(self) -> set[int]:
        return _parse_ids(self.dispatcher_telegram_ids)

    @property
    def support_ids(self) -> set[int]:
        return _parse_ids(self.support_telegram_ids)

    def emails_for(self, role: str) -> list[str]:
        mapping = {
            "owner": self.owner_emails,
            "pharmacist": self.pharmacist_emails,
            "packaging": self.packaging_staff_emails,
            "dispatcher": self.dispatcher_emails,
            "support": self.support_emails,
        }
        return _parse_emails(mapping.get(role, ""))

    @property
    def is_dev(self) -> bool:
        return self.env.lower() in {"dev", "development", "local"}

    @property
    def flutterwave_enabled(self) -> bool:
        return bool(self.flutterwave_secret_key and self.flutterwave_public_key)

    @property
    def email_enabled(self) -> bool:
        return bool(self.smtp_host and self.smtp_from_email)

    @property
    def bank_account_list(self) -> list[dict]:
        """Parsed list of payment accounts.

        From BANK_ACCOUNTS ("Bank|Name|Number;..."), falling back to the single
        legacy BANK_* fields. Returns [{bank, name, number}].
        """
        out: list[dict] = []
        for entry in (self.bank_accounts or "").split(";"):
            parts = [p.strip() for p in entry.split("|")]
            if len(parts) == 3 and parts[2]:
                out.append({"bank": parts[0], "name": parts[1], "number": parts[2]})
        if not out and self.bank_account_number:
            out.append({
                "bank": self.bank_name,
                "name": self.bank_account_name,
                "number": self.bank_account_number,
            })
        return out

    @property
    def crypto_wallet_list(self) -> list[dict]:
        """Parse CRYPTO_WALLETS ("NETWORK:TOKEN:ADDRESS,...") into dicts."""
        out: list[dict] = []
        for entry in (self.crypto_wallets or "").split(","):
            parts = [p.strip() for p in entry.split(":")]
            if len(parts) == 3 and all(parts):
                out.append({"network": parts[0], "token": parts[1], "address": parts[2]})
        return out

    @property
    def allowed_origin_list(self) -> list[str]:
        """Parse ALLOWED_ORIGINS (comma-separated) into a list for CORSMiddleware."""
        return [o.strip() for o in (self.allowed_origins or "").split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
