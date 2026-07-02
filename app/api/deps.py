"""FastAPI dependencies shared across all /api/v1 endpoints."""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_session
from app.models import Customer


async def get_db() -> AsyncIterator[AsyncSession]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_optional_customer(
    db: DbSession,
    pw_session: Annotated[str | None, Cookie()] = None,
) -> Customer | None:
    """Return the Customer for the session cookie, or None if not authenticated.

    Sessions are validated server-side: an expired (or pre-expiry-era) token
    is rejected even if the browser still holds the cookie.
    """
    from app.services.web_customers import is_session_expired

    if not pw_session:
        return None
    customer = (
        await db.execute(
            select(Customer).where(Customer.web_session_token == pw_session)
        )
    ).scalar_one_or_none()
    if customer is None or is_session_expired(customer):
        return None
    return customer


async def get_current_customer(
    customer: Annotated[Customer | None, Depends(get_optional_customer)],
) -> Customer:
    """Return the authenticated Customer or raise 401."""
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Submit your details at /start first.",
        )
    return customer


OptionalCustomer = Annotated[Customer | None, Depends(get_optional_customer)]
CurrentCustomer = Annotated[Customer, Depends(get_current_customer)]
