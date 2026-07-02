from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, field_validator

from app.api.deps import CurrentCustomer, DbSession
from app.services.web_customers import get_or_create_web_customer, is_valid_phone

router = APIRouter(tags=["customers"])

SESSION_COOKIE = "pw_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


class RegisterRequest(BaseModel):
    full_name: str
    phone: str
    email: str | None = None
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


class CustomerOut(BaseModel):
    id: str
    full_name: str | None
    phone: str | None
    email: str | None
    delivery_area: str | None = None

    model_config = {"from_attributes": True}


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

    return CustomerOut(
        id=str(customer.id),
        full_name=customer.full_name,
        phone=customer.phone,
        email=customer.email,
        delivery_area=body.delivery_area,
    )


@router.get("/me")
async def get_me(customer: CurrentCustomer) -> CustomerOut:
    """Return the authenticated customer's profile."""
    return CustomerOut(
        id=str(customer.id),
        full_name=customer.full_name,
        phone=customer.phone,
        email=customer.email,
    )
