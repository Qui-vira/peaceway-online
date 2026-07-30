from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select

from app.api.deps import CurrentCustomer, DbSession, OptionalCustomer
from app.core.config import get_settings
from app.models import Customer
from app.services.customers import is_valid_email
from app.services.telegram_link import verify_telegram_login
from app.services.web_customers import (
    SESSION_TTL_DAYS,
    clear_web_session,
    count_referrals,
    ensure_referral_code,
    get_delivery_area,
    get_or_create_web_customer,
    is_valid_phone,
    set_delivery_area,
)

router = APIRouter(tags=["customers"])

SESSION_COOKIE = "pw_session"
COOKIE_MAX_AGE = SESSION_TTL_DAYS * 24 * 60 * 60  # mirrors server-side expiry


class RegisterRequest(BaseModel):
    full_name: str
    phone: str
    email: str
    delivery_area: str | None = None

    @field_validator("full_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Full name is required.")
        return v

    @field_validator("phone")
    @classmethod
    def phone_valid(cls, v: str) -> str:
        v = v.strip()
        if not is_valid_phone(v):
            raise ValueError("Enter a valid phone number.")
        return v

    @field_validator("email")
    @classmethod
    def email_required(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Email address is required.")
        if not is_valid_email(v):
            raise ValueError("Enter a valid email address.")
        return v


class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    email: str | None = None
    delivery_area: str | None = None

    @field_validator("full_name")
    @classmethod
    def name_not_blank(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Full name cannot be empty.")
        return v

    @field_validator("email")
    @classmethod
    def email_valid(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if v and not is_valid_email(v):
                raise ValueError("Enter a valid email address.")
        return v


class CustomerOut(BaseModel):
    id: str
    full_name: str | None
    phone: str | None
    email: str | None
    delivery_area: str | None = None
    telegram_username: str | None = None
    telegram_linked: bool = False
    # Absent unless the caller asked for it (see the /me endpoint). The referral
    # screen is the only surface that needs these, and counting referrals is a
    # query the sign-in path should not pay for.
    referral_code: str | None = None
    referral_count: int | None = None

    model_config = {"from_attributes": True}


def _customer_out(
    customer,
    *,
    referral_code: str | None = None,
    referral_count: int | None = None,
) -> CustomerOut:
    return CustomerOut(
        id=str(customer.id),
        full_name=customer.full_name,
        phone=customer.phone,
        email=customer.email,
        delivery_area=get_delivery_area(customer),
        telegram_username=customer.telegram_username,
        telegram_linked=customer.telegram_id is not None,
        referral_code=referral_code,
        referral_count=referral_count,
    )


@router.post("/customers", status_code=status.HTTP_200_OK)
async def register_or_login(
    body: RegisterRequest,
    response: Response,
    db: DbSession,
) -> CustomerOut:
    """Register a new web customer or refresh the session for a returning one.

    Identifies by phone number. Sets an httpOnly session cookie (pw_session).
    """
    customer, _created = await get_or_create_web_customer(
        db,
        phone=body.phone,
        full_name=body.full_name,
        email=body.email,
        delivery_area=body.delivery_area,
    )

    response.set_cookie(
        key=SESSION_COOKIE,
        value=customer.web_session_token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="none",  # cross-origin: Vercel frontend → Railway backend
        path="/",
    )

    return _customer_out(customer)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    db: DbSession,
    customer: OptionalCustomer,
) -> None:
    """Sign out: invalidate the session token server-side and clear the cookie.

    Idempotent - safe to call without a valid session.
    """
    if customer is not None:
        clear_web_session(customer)
        db.add(customer)
    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        secure=True,
        samesite="none",
        httponly=True,
    )


@router.get("/me")
async def get_me(
    customer: CurrentCustomer,
    db: DbSession,
    referral: bool = False,
) -> CustomerOut:
    """Return the authenticated customer's profile.

    `?referral=1` additionally mints (on first use) and returns the customer's
    referral code plus how many people they have brought in. It is opt-in
    because `/me` is called on nearly every page and the referral screen is the
    only one that needs the extra query.
    """
    if not referral:
        return _customer_out(customer)

    code = await ensure_referral_code(db, customer)
    count = await count_referrals(db, customer)
    await db.commit()
    return _customer_out(customer, referral_code=code, referral_count=count)


@router.patch("/me")
async def update_me(
    body: UpdateProfileRequest,
    customer: CurrentCustomer,
    db: DbSession,
) -> CustomerOut:
    """Update the authenticated customer's profile (name, email, delivery area)."""
    if body.full_name is not None:
        customer.full_name = body.full_name
    if body.email is not None and body.email:
        now = datetime.now(timezone.utc)
        customer.email = body.email
        if not customer.email_collected_at:
            customer.email_collected_at = now
        customer.email_source = "web_profile"
        customer.email_updated_at = now
    if body.delivery_area is not None and body.delivery_area.strip():
        set_delivery_area(customer, body.delivery_area.strip())

    db.add(customer)
    return _customer_out(customer)


class TelegramLinkRequest(BaseModel):
    """Raw Telegram Login Widget payload - verified server-side before use."""

    id: int
    auth_date: int
    hash: str
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None


@router.post("/me/telegram-link")
async def link_telegram(
    body: TelegramLinkRequest,
    customer: CurrentCustomer,
    db: DbSession,
) -> CustomerOut:
    """Connect the customer's Telegram account to their web profile.

    Verifies the Login Widget signature (HMAC keyed on the bot token) and
    freshness before trusting any field. One Telegram account per profile -
    enforced here and by the unique constraint on customers.telegram_id.
    """
    bot_token = get_settings().telegram_bot_token
    if not bot_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram linking is not available right now.",
        )
    if not verify_telegram_login(body.model_dump(exclude_none=True), bot_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram verification failed. Please try again.",
        )

    if customer.telegram_id is not None and customer.telegram_id != body.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This profile is already connected to a different Telegram account.",
        )
    other = (
        await db.execute(
            select(Customer).where(
                Customer.telegram_id == body.id, Customer.id != customer.id
            )
        )
    ).scalar_one_or_none()
    if other is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This Telegram account is already connected to another profile. "
                "Contact support if this is yours."
            ),
        )

    customer.telegram_id = body.id
    customer.telegram_username = body.username
    customer.telegram_linked_at = datetime.now(timezone.utc)
    db.add(customer)
    return _customer_out(customer)
