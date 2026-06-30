"""Pharmacist inbox ticket + thread helpers (single source of truth).

A PharmacistQuestion is the ticket header; PharmacistMessage rows are the full
conversation thread (customer + pharmacist turns). New customer messages append
to an existing OPEN ticket for the same customer + product where possible,
instead of always opening a new disconnected ticket.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PharmacistMessage, PharmacistQuestion


async def find_open_ticket(
    session: AsyncSession, customer_id: UUID, product_id: UUID | None
) -> PharmacistQuestion | None:
    return (
        await session.execute(
            select(PharmacistQuestion).where(
                PharmacistQuestion.customer_id == customer_id,
                PharmacistQuestion.product_id == product_id,
                PharmacistQuestion.is_answered.is_(False),
            )
        )
    ).scalar_one_or_none()


async def add_customer_message(
    session: AsyncSession, customer_id: UUID, telegram_id: int, body: str, product_id: UUID | None = None
) -> tuple[PharmacistQuestion, bool]:
    """Append to an open ticket for this customer/product, or create one.

    Returns (ticket, created) where created is True for a brand-new ticket.
    """
    ticket = await find_open_ticket(session, customer_id, product_id)
    created = ticket is None
    if ticket is None:
        ticket = PharmacistQuestion(customer_id=customer_id, product_id=product_id, question=body)
        session.add(ticket)
        await session.flush()
    session.add(
        PharmacistMessage(question_id=ticket.id, sender="customer", telegram_id=telegram_id, body=body)
    )
    return ticket, created


async def add_pharmacist_reply(
    session: AsyncSession, ticket: PharmacistQuestion, telegram_id: int, body: str, answered_by: str
) -> None:
    session.add(
        PharmacistMessage(question_id=ticket.id, sender="pharmacist", telegram_id=telegram_id, body=body)
    )
    ticket.answer = body
    ticket.answered_by = answered_by
    ticket.is_answered = True


async def get_thread(session: AsyncSession, question_id: UUID) -> list[PharmacistMessage]:
    return list(
        (
            await session.execute(
                select(PharmacistMessage)
                .where(PharmacistMessage.question_id == question_id)
                .order_by(PharmacistMessage.created_at)
            )
        ).scalars().all()
    )
