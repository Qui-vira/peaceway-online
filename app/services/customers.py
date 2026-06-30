"""Shared customer lookup + email capture (single source of truth).

Replaces the duplicated "find-or-create Customer" block that used to live in
five separate handler files.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Customer, CustomerContactEvent, CustomerPreferences

# Simple, permissive RFC-5322-ish check: local@domain.tld
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Sources where the soft gate re-asks every time it's missing (vs. once-per-session
# for low-stakes browsing actions).
HIGH_VALUE_SOURCES = {"payment", "product_request", "pharmacist", "follow_up"}


def is_valid_email(value: str) -> bool:
    return bool(EMAIL_RE.match(value.strip()))


async def get_or_create_customer(
    session: AsyncSession, telegram_id: int, full_name: str | None = None
) -> Customer:
    customer = (
        await session.execute(select(Customer).where(Customer.telegram_id == telegram_id))
    ).scalar_one_or_none()
    if customer is None:
        customer = Customer(telegram_id=telegram_id, full_name=full_name)
        session.add(customer)
        await session.flush()
        session.add(CustomerPreferences(customer_id=customer.id))
    return customer


async def _ensure_preferences(session: AsyncSession, customer: Customer) -> None:
    prefs = await session.get(CustomerPreferences, customer.id)
    if prefs is None:
        session.add(CustomerPreferences(customer_id=customer.id))


async def save_email(
    session: AsyncSession, customer: Customer, email: str, source: str, telegram_user_id: int
) -> None:
    old = customer.email
    now = datetime.now(timezone.utc)
    customer.email = email
    customer.email_verified = False
    if old is None:
        customer.email_collected_at = now
    customer.email_source = source
    customer.email_updated_at = now
    if customer.email_opt_in_at is None:
        customer.email_opt_in_at = now
    await _ensure_preferences(session, customer)
    session.add(
        CustomerContactEvent(
            customer_id=customer.id,
            telegram_user_id=telegram_user_id,
            event_type="updated" if old else "added",
            old_email=old,
            new_email=email,
            source_flow=source,
        )
    )


async def remove_email(session: AsyncSession, customer: Customer, telegram_user_id: int) -> None:
    old = customer.email
    customer.email = None
    customer.email_updated_at = datetime.now(timezone.utc)
    session.add(
        CustomerContactEvent(
            customer_id=customer.id,
            telegram_user_id=telegram_user_id,
            event_type="removed",
            old_email=old,
            new_email=None,
            source_flow="profile",
        )
    )
