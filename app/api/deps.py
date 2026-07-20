"""FastAPI dependencies shared across all /api/v1 endpoints."""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_session, set_session_actor
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
    # Stamp the customer as the actor for this request's transaction (RLS reads it).
    await set_session_actor(db, customer.id, "customer")
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


async def _get_current_admin(
    db: DbSession,
    x_admin_session: Annotated[str, Header()] = "",
) -> "tuple[AdminUser, set[str]]":
    from app.services.admin_web_auth import get_session_admin

    result = await get_session_admin(db, x_admin_session)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session.",
        )
    # Stamp the admin as the actor for this request's transaction (RLS reads it).
    await set_session_actor(db, result[0].id, "admin")
    return result


AdminSessionDep = Annotated["tuple[AdminUser, set[str]]", Depends(_get_current_admin)]


async def _get_current_partner(
    db: DbSession,
    x_partner_session: Annotated[str, Header()] = "",
) -> "NetworkPartner":
    """Resolve the partner portal session token to a NetworkPartner.

    Separate auth domain from staff: this looks up `partner_portal_sessions`
    only, so an admin token can never authenticate here (and vice versa).
    """
    from app.services.partner_auth import get_session_partner

    partner = await get_session_partner(db, x_partner_session)
    if partner is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired partner session.",
        )
    return partner


PartnerSessionDep = Annotated["NetworkPartner", Depends(_get_current_partner)]
