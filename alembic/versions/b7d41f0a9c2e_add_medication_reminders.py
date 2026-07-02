"""add medication reminders

Revision ID: b7d41f0a9c2e
Revises: e3f9a7b2c1d8
Create Date: 2026-07-02

Additive only: two new tables, no changes to existing tables.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b7d41f0a9c2e"
down_revision: Union[str, None] = "e3f9a7b2c1d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "medication_reminders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("medicine_name", sa.String(length=255), nullable=False),
        sa.Column("instructions_text", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="CUSTOMER"),
        sa.Column("created_by_admin_id", sa.BigInteger(), nullable=True),
        sa.Column("consent_status", sa.String(length=20), nullable=False, server_default="GRANTED"),
        sa.Column("times", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="Africa/Lagos"),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("channel", sa.String(length=20), nullable=False, server_default="telegram"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("prescription_id", sa.Uuid(), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prescription_id"], ["prescriptions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_medication_reminders_customer_id", "medication_reminders", ["customer_id"])
    op.create_index("ix_medication_reminders_status", "medication_reminders", ["status"])
    op.create_index("ix_medication_reminders_next_run_at", "medication_reminders", ["next_run_at"])

    op.create_table(
        "medication_reminder_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reminder_id", sa.Uuid(), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["reminder_id"], ["medication_reminders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reminder_id", "scheduled_for", name="uq_reminder_occurrence"),
    )
    op.create_index(
        "ix_medication_reminder_events_reminder_id", "medication_reminder_events", ["reminder_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_medication_reminder_events_reminder_id", table_name="medication_reminder_events")
    op.drop_table("medication_reminder_events")
    op.drop_index("ix_medication_reminders_next_run_at", table_name="medication_reminders")
    op.drop_index("ix_medication_reminders_status", table_name="medication_reminders")
    op.drop_index("ix_medication_reminders_customer_id", table_name="medication_reminders")
    op.drop_table("medication_reminders")
