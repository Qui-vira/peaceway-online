"""Web API: ask-a-pharmacist question endpoints.

Reuses the bot's pharmacist-inbox tables (pharmacist_questions /
pharmacist_messages) so web questions land in the same admin queue.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select

from app.api.deps import CurrentCustomer, DbSession
from app.models import PharmacistMessage, PharmacistQuestion

router = APIRouter(tags=["ask"])


class AskBody(BaseModel):
    question: str

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Question is required.")
        if len(v) > 2000:
            raise ValueError("Question must be 2 000 characters or fewer.")
        return v


class QuestionOut(BaseModel):
    id: str
    question: str
    answer: str | None
    is_answered: bool
    created_at: str

    model_config = {"from_attributes": True}


class ThreadMessageOut(BaseModel):
    id: str
    sender: str
    body: str
    created_at: str


class QuestionDetailOut(QuestionOut):
    thread: list[ThreadMessageOut]


def _question_out(q: PharmacistQuestion) -> QuestionOut:
    return QuestionOut(
        id=str(q.id),
        question=q.question,
        answer=q.answer,
        is_answered=q.is_answered,
        created_at=q.created_at.isoformat(),
    )


@router.post("/ask", status_code=status.HTTP_201_CREATED)
async def ask_question(
    body: AskBody,
    customer: CurrentCustomer,
    db: DbSession,
) -> QuestionOut:
    """Submit a question to the pharmacist inbox."""
    q = PharmacistQuestion(customer_id=customer.id, question=body.question)
    db.add(q)
    await db.flush()
    db.add(PharmacistMessage(question_id=q.id, sender="customer", body=body.question))
    return _question_out(q)


@router.get("/ask")
async def list_questions(
    customer: CurrentCustomer,
    db: DbSession,
) -> list[QuestionOut]:
    """List the authenticated customer's questions, newest first."""
    rows = (
        await db.execute(
            select(PharmacistQuestion)
            .where(PharmacistQuestion.customer_id == customer.id)
            .order_by(PharmacistQuestion.created_at.desc())
        )
    ).scalars().all()
    return [_question_out(q) for q in rows]


@router.get("/ask/{question_id}")
async def get_question(
    question_id: UUID,
    customer: CurrentCustomer,
    db: DbSession,
) -> QuestionDetailOut:
    """Return one question with its full message thread."""
    q = (
        await db.execute(
            select(PharmacistQuestion).where(
                PharmacistQuestion.id == question_id,
                PharmacistQuestion.customer_id == customer.id,
            )
        )
    ).scalar_one_or_none()
    if q is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    messages = (
        await db.execute(
            select(PharmacistMessage)
            .where(PharmacistMessage.question_id == q.id)
            .order_by(PharmacistMessage.created_at)
        )
    ).scalars().all()

    return QuestionDetailOut(
        **_question_out(q).model_dump(),
        thread=[
            ThreadMessageOut(
                id=str(m.id), sender=m.sender, body=m.body,
                created_at=m.created_at.isoformat(),
            )
            for m in messages
        ],
    )
