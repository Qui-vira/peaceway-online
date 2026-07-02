"""Medication reminder models.

A reminder is created only from user-entered or pharmacist-entered
instructions — the system never generates dosage advice. Every send attempt
is recorded in MedicationReminderEvent for audit.
"""
from __future__ import annotations

import enum
from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import JSONB, Base, TimestampMixin


class ReminderStatus(str, enum.Enum):
    """Stored as a plain string column (same lightweight pattern as
    ProductRequestStatus) so adding a status never needs a type migration."""

    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    COMPLETED = "COMPLETED"  # end_date passed


class ReminderConsent(str, enum.Enum):
    GRANTED = "GRANTED"
    PENDING = "PENDING"  # pharmacist-created, awaiting customer acceptance
    DECLINED = "DECLINED"


class ReminderSource(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    PHARMACIST = "PHARMACIST"


class ReminderEventStatus(str, enum.Enum):
    SENT = "SENT"
    FAILED = "FAILED"
    SKIPPED_PAUSED = "SKIPPED_PAUSED"
    SKIPPED_MISSED = "SKIPPED_MISSED"  # due while app was down, past grace


class MedicationReminder(Base, TimestampMixin):
    __tablename__ = "medication_reminders"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Exactly as entered by the customer or pharmacist — never system-generated.
    medicine_name: Mapped[str] = mapped_column(String(255), nullable=False)
    instructions_text: Mapped[str | None] = mapped_column(Text)

    source: Mapped[str] = mapped_column(
        String(20), default=ReminderSource.CUSTOMER.value, nullable=False
    )
    created_by_admin_id: Mapped[int | None] = mapped_column(BigInteger)
    consent_status: Mapped[str] = mapped_column(
        String(20), default=ReminderConsent.GRANTED.value, nullable=False
    )

    # List of "HH:MM" strings in the reminder's local timezone.
    times: Mapped[list] = mapped_column(JSONB, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Africa/Lagos", nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)

    channel: Mapped[str] = mapped_column(String(20), default="telegram", nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=ReminderStatus.ACTIVE.value, nullable=False, index=True
    )
    # Next UTC instant this reminder should fire; the dispatcher's whole query
    # key. NULL when not schedulable (paused/stopped/completed/pending consent).
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    prescription_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("prescriptions.id", ondelete="SET NULL")
    )
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MedicationReminderEvent(Base, TimestampMixin):
    """Append-only audit of every scheduled occurrence outcome."""

    __tablename__ = "medication_reminder_events"
    __table_args__ = (
        UniqueConstraint("reminder_id", "scheduled_for", name="uq_reminder_occurrence"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    reminder_id: Mapped[UUID] = mapped_column(
        ForeignKey("medication_reminders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
