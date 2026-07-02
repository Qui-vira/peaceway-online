"""Web-specific customer operations.

Bot customers are identified by telegram_id.
Web customers are identified by phone number — looked up first,
then created if not found.
"""
from __future__ import annotations

import secrets
import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Customer, CustomerPreferences
from app.services.customers import is_valid_email, save_email

PHONE_RE = re.compile(r"^\+?[\d\s\-().]{7,20}$")


def is_valid_phone(value: str) -> bool:
    return bool(PHONE_RE.match(value.strip()))


def _generate_session_token() -> str:
    return secrets.token_urlsafe(48)  # 64 chars URL-safe base64


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


async def get_or_create_web_customer(
    session: AsyncSession,
    *,
    phone: str,
    full_name: str,
    email: str | None = None,
    delivery_area: str | None = None,
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

    # Always issue a fresh session token on web registration/login
    customer.web_session_token = _generate_session_token()

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
