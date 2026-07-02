"""Web API: product-availability request endpoints."""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select

from app.api.deps import CurrentCustomer, DbSession
from app.models import ProductRequest, ProductRequestMessage
from app.models.ops import ProductRequestStatus, RequestUrgency
from app.services.product_requests import add_message

router = APIRouter(tags=["requests"])

VALID_URGENCY = {u.value for u in RequestUrgency}


class CreateRequestBody(BaseModel):
    product_name: str
    strength: str | None = None
    form: str | None = None
    quantity: str | None = None
    urgency: str | None = None
    note: str | None = None

    @field_validator("product_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Product name is required.")
        if len(v) > 255:
            raise ValueError("Product name is too long.")
        return v

    @field_validator("urgency")
    @classmethod
    def urgency_valid(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_URGENCY:
            raise ValueError(f"urgency must be one of {sorted(VALID_URGENCY)}")
        return v

    @field_validator("note")
    @classmethod
    def note_length(cls, v: str | None) -> str | None:
        if v and len(v) > 1000:
            raise ValueError("Note must be 1 000 characters or fewer.")
        return v


class RequestOut(BaseModel):
    id: str
    product_name: str
    strength: str | None
    form: str | None
    quantity: str | None
    urgency: str | None
    note: str | None
    status: str
    customer_visible_message: str | None
    created_at: str

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: str
    sender_type: str
    message_text: str
    created_at: str

    model_config = {"from_attributes": True}


class RequestDetailOut(RequestOut):
    thread: list[MessageOut]


def _request_out(r: ProductRequest) -> RequestOut:
    return RequestOut(
        id=str(r.id),
        product_name=r.product_name,
        strength=r.strength,
        form=r.form,
        quantity=r.quantity,
        urgency=r.urgency,
        note=r.note,
        status=r.status,
        customer_visible_message=r.customer_visible_message,
        created_at=r.created_at.isoformat(),
    )


@router.post("/requests", status_code=status.HTTP_201_CREATED)
async def create_request(
    body: CreateRequestBody,
    customer: CurrentCustomer,
    db: DbSession,
) -> RequestOut:
    """Submit a product-availability request for the authenticated customer."""
    req = ProductRequest(
        customer_id=customer.id,
        product_name=body.product_name,
        strength=body.strength or None,
        form=body.form or None,
        quantity=body.quantity or None,
        urgency=body.urgency or None,
        note=body.note or None,
        customer_phone=customer.phone,
        customer_email=customer.email,
        delivery_area=customer.delivery_area,
        is_medicine=True,
        status=ProductRequestStatus.NEW.value,
    )
    db.add(req)
    await db.flush()  # populate req.id before add_message

    if body.note:
        await add_message(db, req, sender_type="customer", body=body.note)

    return _request_out(req)


@router.get("/requests")
async def list_requests(
    customer: CurrentCustomer,
    db: DbSession,
) -> list[RequestOut]:
    """List all product requests for the authenticated customer, newest first."""
    rows = (
        await db.execute(
            select(ProductRequest)
            .where(ProductRequest.customer_id == customer.id)
            .order_by(ProductRequest.created_at.desc())
        )
    ).scalars().all()
    return [_request_out(r) for r in rows]


@router.get("/requests/{request_id}")
async def get_request(
    request_id: UUID,
    customer: CurrentCustomer,
    db: DbSession,
) -> RequestDetailOut:
    """Return a single product request with its message thread."""
    req = (
        await db.execute(
            select(ProductRequest).where(
                ProductRequest.id == request_id,
                ProductRequest.customer_id == customer.id,
            )
        )
    ).scalar_one_or_none()

    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")

    messages = (
        await db.execute(
            select(ProductRequestMessage)
            .where(ProductRequestMessage.product_request_id == req.id)
            .order_by(ProductRequestMessage.created_at)
        )
    ).scalars().all()

    thread = [
        MessageOut(
            id=str(m.id),
            sender_type=m.sender_type,
            message_text=m.message_text,
            created_at=m.created_at.isoformat(),
        )
        for m in messages
    ]

    return RequestDetailOut(
        **_request_out(req).model_dump(),
        thread=thread,
    )
