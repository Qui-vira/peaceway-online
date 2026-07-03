"""Web API: customer medication reminder endpoints.

All write operations delegate to app.services.reminders, which owns
scheduling logic and validation. The model is already deployed and dormant;
this file simply wires HTTP routes to the existing service functions.
"""
from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select

from app.api.deps import CurrentCustomer, DbSession
from app.models import MedicationReminder
from app.services import reminders as svc

router = APIRouter(prefix="/reminders", tags=["reminders"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class CreateReminderBody(BaseModel):
    medicine_name: str
    instructions_text: str | None = None
    times: list[str]
    start_date: date
    end_date: date | None = None
    timezone: str = "Africa/Lagos"

    @field_validator("medicine_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Medicine name is required.")
        if len(v) > 255:
            raise ValueError("Medicine name is too long.")
        return v

    @field_validator("times")
    @classmethod
    def times_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("At least one reminder time is required.")
        return v


class PatchReminderBody(BaseModel):
    action: Literal["pause", "resume", "stop"]


class ReminderOut(BaseModel):
    id: str
    medicine_name: str
    instructions_text: str | None
    times: list[str]
    start_date: str
    end_date: str | None
    status: str
    source: str
    next_run_at: str | None
    created_at: str

    model_config = {"from_attributes": True}


def _out(r: MedicationReminder) -> ReminderOut:
    return ReminderOut(
        id=str(r.id),
        medicine_name=r.medicine_name,
        instructions_text=r.instructions_text,
        times=r.times,
        start_date=r.start_date.isoformat(),
        end_date=r.end_date.isoformat() if r.end_date else None,
        status=r.status,
        source=r.source,
        next_run_at=r.next_run_at.isoformat() if r.next_run_at else None,
        created_at=r.created_at.isoformat(),
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("")
async def list_reminders(
    customer: CurrentCustomer,
    db: DbSession,
) -> list[ReminderOut]:
    """List all reminders for the authenticated customer, newest first."""
    rows = await svc.list_customer_reminders(db, customer.id)
    return [_out(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_reminder(
    body: CreateReminderBody,
    customer: CurrentCustomer,
    db: DbSession,
) -> ReminderOut:
    """Create a new medication reminder for the authenticated customer."""
    try:
        reminder = await svc.create_reminder(
            db,
            customer=customer,
            medicine_name=body.medicine_name,
            instructions_text=body.instructions_text,
            times=body.times,
            start_date=body.start_date,
            end_date=body.end_date,
            tz_name=body.timezone,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return _out(reminder)


@router.get("/{reminder_id}")
async def get_reminder(
    reminder_id: UUID,
    customer: CurrentCustomer,
    db: DbSession,
) -> ReminderOut:
    """Return one reminder owned by the authenticated customer."""
    row = (
        await db.execute(
            select(MedicationReminder).where(
                MedicationReminder.id == reminder_id,
                MedicationReminder.customer_id == customer.id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found.")
    return _out(row)


@router.patch("/{reminder_id}")
async def patch_reminder(
    reminder_id: UUID,
    body: PatchReminderBody,
    customer: CurrentCustomer,
    db: DbSession,
) -> ReminderOut:
    """Pause, resume, or stop a reminder."""
    row = (
        await db.execute(
            select(MedicationReminder).where(
                MedicationReminder.id == reminder_id,
                MedicationReminder.customer_id == customer.id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found.")

    try:
        if body.action == "pause":
            row = await svc.pause_reminder(db, row)
        elif body.action == "resume":
            row = await svc.resume_reminder(db, row)
        else:
            row = await svc.stop_reminder(db, row)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    return _out(row)


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder_id: UUID,
    customer: CurrentCustomer,
    db: DbSession,
) -> None:
    """Permanently delete a reminder."""
    row = (
        await db.execute(
            select(MedicationReminder).where(
                MedicationReminder.id == reminder_id,
                MedicationReminder.customer_id == customer.id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found.")
    await db.delete(row)
