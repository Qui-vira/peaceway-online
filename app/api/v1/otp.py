"""OTP send / verify endpoints for web phone-based auth."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, field_validator
from sqlalchemy import select

from app.api.deps import DbSession
from app.api.v1.customers import (
    COOKIE_MAX_AGE,
    SESSION_COOKIE,
    CustomerOut,
    _customer_out,
)
from app.models import Customer
from app.services.customers import is_valid_email
from app.services.otp_service import (
    create_otp_request,
    send_otp_email,
    verify_otp_request,
)
from app.services.web_customers import get_or_create_web_customer, is_valid_phone
from app.core.config import get_settings

router = APIRouter(tags=["otp"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mask_email(email: str) -> str:
    """Mask an email address: keep first char, replace middle with ***, keep @domain.

    e.g.  kdammilare33@gmail.com → k***@gmail.com
    """
    local, _, domain = email.partition("@")
    return f"{local[0]}***@{domain}"


# ── Request / response models ─────────────────────────────────────────────────

class SendOtpRequest(BaseModel):
    phone: str
    email: str | None = None
    full_name: str | None = None
    mode: str  # "signup" | "login"

    @field_validator("phone")
    @classmethod
    def phone_valid(cls, v: str) -> str:
        v = v.strip()
        if not is_valid_phone(v):
            raise ValueError("Enter a valid phone number.")
        return v

    @field_validator("mode")
    @classmethod
    def mode_valid(cls, v: str) -> str:
        if v not in ("signup", "login"):
            raise ValueError("mode must be signup or login")
        return v


class SendOtpResponse(BaseModel):
    email_hint: str  # masked: "k***@gmail.com"


class VerifyOtpRequest(BaseModel):
    phone: str
    code: str
    # The `?ref=` code the customer arrived on, carried through the sign-up
    # round trip by the web app. Optional and unvalidated here: an unknown code
    # simply attributes nothing rather than blocking a registration.
    referral_code: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/otp/send")
async def send_otp(body: SendOtpRequest, db: DbSession) -> SendOtpResponse:
    """Send a 6-digit OTP to the customer's email address.

    - login mode: resolves email from the existing Customer record.
    - signup mode: requires email + full_name in the request body.
    """
    settings = get_settings()

    if body.mode == "login":
        # Look up customer by phone
        result = await db.execute(
            select(Customer).where(Customer.phone == body.phone)
        )
        customer = result.scalar_one_or_none()
        if customer is None:
            raise HTTPException(
                404,
                "No account found for this number. Please create one.",
            )
        if not customer.email:
            raise HTTPException(
                400,
                "No email on file for this account. Please create a new account.",
            )
        email = customer.email
        full_name = customer.full_name
    else:
        # signup mode - require email and full_name
        if not body.email or not body.email.strip():
            raise HTTPException(422, "email is required for signup.")
        if not is_valid_email(body.email.strip()):
            raise HTTPException(422, "Enter a valid email address.")
        if not body.full_name or not body.full_name.strip():
            raise HTTPException(422, "full_name is required for signup.")
        email = body.email.strip()
        full_name = body.full_name.strip()

    code = await create_otp_request(
        db,
        phone=body.phone,
        email=email,
        full_name=full_name,
    )
    await send_otp_email(email, code, settings.pharmacy_name)

    return SendOtpResponse(email_hint=_mask_email(email))


@router.post("/otp/verify", status_code=200)
async def verify_otp(
    body: VerifyOtpRequest,
    response: Response,
    db: DbSession,
) -> CustomerOut:
    """Verify OTP code, upsert the customer, and set the session cookie."""
    email, full_name = await verify_otp_request(
        db,
        phone=body.phone,
        code=body.code,
    )

    customer, _created = await get_or_create_web_customer(
        db,
        phone=body.phone,
        full_name=full_name,
        email=email,
        referral_code=body.referral_code,
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
