"""Admin Customer CRM: search, profile, message, note."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from aiogram import Bot
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import Customer, CustomerMessage, CustomerNote, Order, ProductRequest
from app.models.ops import PharmacistQuestion

log = get_logger("customer_admin")


async def search_customers(session: AsyncSession, query: str) -> list[Customer]:
    q = query.strip()
    rows = (
        await session.execute(
            select(Customer)
            .where(
                or_(
                    Customer.full_name.ilike(f"%{q}%"),
                    Customer.phone.ilike(f"%{q}%"),
                    Customer.email.ilike(f"%{q}%"),
                    Customer.telegram_id == int(q) if q.lstrip("-").isdigit() else False,
                )
            )
            .order_by(Customer.updated_at.desc())
            .limit(15)
        )
    ).scalars().all()
    return list(rows)


async def recent_customers(session: AsyncSession, limit: int = 20) -> list[Customer]:
    rows = (
        await session.execute(
            select(Customer).order_by(Customer.updated_at.desc()).limit(limit)
        )
    ).scalars().all()
    return list(rows)


async def missing_email_customers(session: AsyncSession, limit: int = 20) -> list[Customer]:
    rows = (
        await session.execute(
            select(Customer)
            .where(Customer.email.is_(None))
            .order_by(Customer.updated_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return list(rows)


async def get_customer_profile(session: AsyncSession, customer_id: UUID) -> dict | None:
    customer = await session.get(Customer, customer_id)
    if customer is None:
        return None

    order_count = (
        await session.execute(
            select(func.count()).select_from(Order).where(Order.customer_id == customer_id)
        )
    ).scalar() or 0

    request_count = (
        await session.execute(
            select(func.count()).select_from(ProductRequest).where(ProductRequest.customer_id == customer_id)
        )
    ).scalar() or 0

    ticket_count = (
        await session.execute(
            select(func.count()).select_from(PharmacistQuestion)
            .where(PharmacistQuestion.customer_id == customer_id)
        )
    ).scalar() or 0

    notes = (
        await session.execute(
            select(CustomerNote)
            .where(CustomerNote.customer_id == customer_id)
            .order_by(CustomerNote.created_at.desc())
            .limit(5)
        )
    ).scalars().all()

    return {
        "customer": customer,
        "order_count": order_count,
        "request_count": request_count,
        "ticket_count": ticket_count,
        "notes": list(notes),
    }


async def has_open_medicine_context(session: AsyncSession, customer_id: UUID) -> bool:
    """True if the customer has any unanswered pharmacist ticket."""
    ticket = (
        await session.execute(
            select(PharmacistQuestion.id)
            .where(
                PharmacistQuestion.customer_id == customer_id,
                PharmacistQuestion.is_answered.is_(False),
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    return ticket is not None


async def send_customer_message(
    bot: Bot,
    session: AsyncSession,
    customer: Customer,
    text: str,
    sender_admin_id: int,
    purpose: str = "admin_message",
) -> tuple[bool, str | None]:
    """Send a DM to the customer and record it. Returns (success, error_msg)."""
    now = datetime.now(timezone.utc)
    msg = CustomerMessage(
        customer_id=customer.id,
        telegram_user_id=customer.telegram_id,
        sender_type="admin",
        sender_admin_id=sender_admin_id,
        message_text=text,
        message_purpose=purpose,
        delivery_status="pending",
    )
    session.add(msg)

    try:
        await bot.send_message(customer.telegram_id, text)
        msg.delivery_status = "sent"
        msg.sent_at = now
        return True, None
    except Exception as exc:  # noqa: BLE001
        err = str(exc)
        msg.delivery_status = "failed"
        msg.error_message = err
        log.error("customer_message_failed", customer_id=str(customer.id), error=err)
        return False, err


async def add_customer_note(
    session: AsyncSession, customer_id: UUID, admin_telegram_id: int, text: str
) -> CustomerNote:
    note = CustomerNote(
        customer_id=customer_id,
        admin_telegram_id=admin_telegram_id,
        note_text=text,
    )
    session.add(note)
    return note
