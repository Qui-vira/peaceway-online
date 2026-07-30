"""Web-specific customer operations.

Bot customers are identified by telegram_id.
Web customers are identified by phone number - looked up first,
then created if not found.
"""
from __future__ import annotations

import secrets
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Customer, CustomerPreferences
from app.services.customers import is_valid_email, save_email

PHONE_RE = re.compile(r"^\+?[\d\s\-().]{7,20}$")

# Web sessions live this long; enforced server-side (web_session_expires_at)
# and mirrored in the cookie max-age.
SESSION_TTL_DAYS = 30


async def ensure_web_customer_columns(session: AsyncSession) -> None:
    """Backfill web-session columns that older databases may be missing.

    Guarded with a SELECT (which the runtime role always has) so it is a NO-OP
    when the column already exists — the restricted, non-superuser runtime role
    must never attempt an ALTER it isn't permitted to run. The column has shipped
    via migration c9e2a51b7f3d, so in practice this only ALTERs a pre-migration DB.
    """
    exists = (
        await session.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'customers' AND column_name = 'web_session_expires_at'"
            )
        )
    ).scalar()
    if exists:
        return
    await session.execute(
        text("ALTER TABLE customers ADD COLUMN IF NOT EXISTS web_session_expires_at TIMESTAMPTZ")
    )


def is_valid_phone(value: str) -> bool:
    return bool(PHONE_RE.match(value.strip()))


def _generate_session_token() -> str:
    return secrets.token_urlsafe(48)  # 64 chars URL-safe base64


def clear_web_session(customer: Customer) -> None:
    """Invalidate the customer's web session server-side (logout)."""
    customer.web_session_token = None
    customer.web_session_expires_at = None


def is_session_expired(customer: Customer, now: datetime | None = None) -> bool:
    """True when the session must be rejected. Legacy sessions with no expiry
    (created before c9e2a51b7f3d) count as expired - one re-login fixes them."""
    expires = customer.web_session_expires_at
    if expires is None:
        return True
    if expires.tzinfo is None:  # SQLite test sessions return naive datetimes
        expires = expires.replace(tzinfo=timezone.utc)
    return expires <= (now or datetime.now(timezone.utc))


def get_delivery_area(customer: Customer) -> str | None:
    """Delivery area lives in the addresses JSONB list: first entry's `area`."""
    if customer.addresses and isinstance(customer.addresses, list):
        first = customer.addresses[0]
        if isinstance(first, dict):
            return first.get("area")
    return None


def set_delivery_area(customer: Customer, area: str) -> None:
    addresses = list(customer.addresses) if customer.addresses else []
    if addresses and isinstance(addresses[0], dict):
        addresses[0] = {**addresses[0], "area": area}
    else:
        addresses.insert(0, {"area": area})
    customer.addresses = addresses


def _mint_referral_code(customer: Customer) -> str:
    """A short, shareable, collision-resistant code.

    Initials plus random suffix rather than initials plus phone digits: the old
    web-only version was `PW` + initials + the last three digits of the
    customer's own phone number, which is both guessable and a small leak of
    someone's number into anything they share publicly.
    """
    initials = "".join(w[0] for w in (customer.full_name or "").split() if w)[:3].upper()
    suffix = "".join(secrets.choice("ABCDEFGHJKMNPQRSTUVWXYZ23456789") for _ in range(4))
    return f"PW{initials}{suffix}"


async def ensure_referral_code(session: AsyncSession, customer: Customer) -> str:
    """Return this customer's referral code, minting one on first use.

    Server-side so the code is the same everywhere and, crucially, so it exists
    in the database at all: the web app used to derive a code at render time
    from the customer's name and phone, which meant the code it told people to
    share had never been stored and could never be matched to anyone.
    """
    if customer.referral_code:
        return customer.referral_code

    for _ in range(5):
        code = _mint_referral_code(customer)
        clash = (
            await session.execute(
                select(Customer.id).where(Customer.referral_code == code)
            )
        ).scalar_one_or_none()
        if clash is None:
            customer.referral_code = code
            await session.flush()
            return code

    # 30^4 collisions five times running means something is wrong with the
    # entropy source, not with this customer. Fall back to a longer code.
    code = f"PW{secrets.token_hex(5).upper()}"
    customer.referral_code = code
    await session.flush()
    return code


async def count_referrals(session: AsyncSession, customer: Customer) -> int:
    """How many customers named this one as their referrer."""
    return (
        await session.execute(
            select(func.count())
            .select_from(Customer)
            .where(Customer.referred_by_customer_id == customer.id)
        )
    ).scalar_one()


async def get_or_create_web_customer(
    session: AsyncSession,
    *,
    phone: str,
    full_name: str,
    email: str | None = None,
    delivery_area: str | None = None,
    referral_code: str | None = None,
) -> tuple[Customer, bool]:
    """Return (customer, created).

    If a customer with this phone already exists (bot or web), we update their
    name and email if provided and issue a new session token.
    If no match, a new Customer is created with telegram_id=NULL.
    """
    phone = phone.strip()
    full_name = full_name.strip()

    existing = (
        await session.execute(
            select(Customer).where(Customer.phone == phone)
        )
    ).scalar_one_or_none()

    if existing is not None:
        customer = existing
        created = False
        # Refresh name if the customer gave a better one
        if full_name and not customer.full_name:
            customer.full_name = full_name
    else:
        customer = Customer(
            telegram_id=None,
            phone=phone,
            full_name=full_name,
        )
        session.add(customer)
        await session.flush()
        session.add(CustomerPreferences(customer_id=customer.id))
        created = True

        # Attribution is recorded once, at creation. Letting an existing
        # customer acquire a referrer on a later sign-in would let anyone
        # reassign credit for a customer the pharmacy already had.
        if referral_code:
            referrer = (
                await session.execute(
                    select(Customer).where(
                        func.upper(Customer.referral_code) == referral_code.strip().upper()
                    )
                )
            ).scalar_one_or_none()
            # Self-referral is not a referral.
            if referrer is not None and referrer.id != customer.id:
                customer.referred_by_customer_id = referrer.id

    # Always issue a fresh session token on web registration/login
    customer.web_session_token = _generate_session_token()
    customer.web_session_expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)

    if delivery_area:
        set_delivery_area(customer, delivery_area)

    if email and is_valid_email(email):
        now = datetime.now(timezone.utc)
        customer.email = email
        if not customer.email_collected_at:
            customer.email_collected_at = now
        customer.email_source = "web_start"
        customer.email_updated_at = now
        if not customer.email_opt_in_at:
            customer.email_opt_in_at = now

    return customer, created
