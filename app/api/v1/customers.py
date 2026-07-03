from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, field_validator

from app.api.deps import CurrentCustomer, DbSession, OptionalCustomer
from app.services.customers import is_valid_email
from app.services.web_customers import (
    SESSION_TTL_DAYS,
    clear_web_session,
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

    model_config = {"from_attributes": True}


def _customer_out(customer) -> CustomerOut:
    return CustomerOut(
        id=str(customer.id),
        full_name=customer.full_name,
        phone=customer.phone,
        email=customer.email,
        delivery_area=get_delivery_area(customer),
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

    Idempotent — safe to call without a valid session.
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
async def get_me(customer: CurrentCustomer) -> CustomerOut:
    """Return the authenticated customer's profile."""
    return _customer_out(customer)


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
