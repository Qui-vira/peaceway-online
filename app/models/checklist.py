"""Staff checklist + meeting-tracker models.

checklist_instances is APPEND ONLY (a BEFORE UPDATE/DELETE trigger blocks mutation,
same pattern as audit_logs / prescription_verifications). The morning job inserts a
`pending` row per assignment; ticking done or skip inserts a NEW row for the same
(template, user, due_date) with supersedes_id pointing at the row it replaces. The
effective state of an item is its latest row. This keeps historical completion rates
truthful: a number cannot change after the fact.

A CHECK constraint makes "only the assignee may complete/skip their own item" a DB
rule: any non-pending row must have completed_by = assigned_user_id.
"""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ChecklistTemplate(Base, TimestampMixin):
    __tablename__ = "checklist_templates"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    role_key: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    item_text: Mapped[str] = mapped_column(Text, nullable=False)
    cadence: Mapped[str] = mapped_column(String(10), nullable=False)  # daily | weekly
    weekday: Mapped[int | None] = mapped_column(Integer)  # 0..6 for weekly (Mon=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ChecklistInstance(Base):
    """APPEND ONLY. One row per (template, user, due_date) state transition."""

    __tablename__ = "checklist_instances"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    template_id: Mapped[UUID] = mapped_column(ForeignKey("checklist_templates.id"), nullable=False, index=True)
    assigned_user_id: Mapped[UUID] = mapped_column(ForeignKey("admin_users.id"), nullable=False, index=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False)  # pending | done | skipped
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_by: Mapped[UUID | None] = mapped_column(ForeignKey("admin_users.id"))
    skip_reason: Mapped[str | None] = mapped_column(Text)
    supersedes_id: Mapped[UUID | None] = mapped_column(ForeignKey("checklist_instances.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "status = 'pending' OR completed_by = assigned_user_id",
            name="ck_checklist_own_completion",
        ),
    )


class OrientationTopic(Base, TimestampMixin):
    """One weekly orientation topic on the fixed twelve-week rotation.

    The scheduler computes the week's topic from the calendar (rotation position), not
    from manual entry; ordering is by ``sort_order``. Deactivating a topic never
    silently drops it from the rotation - the computing job skips it to the next active
    topic and records an audit row for the skip.
    """

    __tablename__ = "orientation_topics"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    topic_text: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Meeting(Base, TimestampMixin):
    __tablename__ = "meetings"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    meeting_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    chaired_by: Mapped[UUID | None] = mapped_column(ForeignKey("admin_users.id"))
    numbers_posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    summary_posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Weekly orientation: the computed topic, the PA's real worked example, and (if the
    # owner swaps the computed topic) what it was swapped from and by whom.
    topic_id: Mapped[UUID | None] = mapped_column(ForeignKey("orientation_topics.id"))
    example_text: Mapped[str | None] = mapped_column(Text)
    swapped_from_topic_id: Mapped[UUID | None] = mapped_column(ForeignKey("orientation_topics.id"))
    swapped_by: Mapped[UUID | None] = mapped_column(ForeignKey("admin_users.id"))


class MeetingDecision(Base, TimestampMixin):
    __tablename__ = "meeting_decisions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    meeting_id: Mapped[UUID | None] = mapped_column(ForeignKey("meetings.id"), index=True)
    decision_text: Mapped[str] = mapped_column(Text, nullable=False)
    owner_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("admin_users.id"))
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(10), default="open", nullable=False)  # open | closed
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
