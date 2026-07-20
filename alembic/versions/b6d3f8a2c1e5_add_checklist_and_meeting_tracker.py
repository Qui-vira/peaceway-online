"""Add staff checklist + meeting tracker.

Additions only. checklist_instances is APPEND ONLY (trg_checklist_append_only reuses
the deny_mutation() function already created for the audit / clinical tables), and a
CHECK makes "only the assignee may complete/skip their own item" a DB rule.

Behaviour (scheduler jobs, handlers, message builders) ships separately; this is the
schema. Nothing here posts messages or reads customer data.

Revision ID: b6d3f8a2c1e5
Revises: a2f9d1c7b4e6
Create Date: 2026-07-20
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "b6d3f8a2c1e5"
down_revision = "a2f9d1c7b4e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "checklist_templates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("role_key", sa.String(length=40), nullable=False),
        sa.Column("item_text", sa.Text(), nullable=False),
        sa.Column("cadence", sa.String(length=10), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_checklist_templates_role_key"), "checklist_templates", ["role_key"])

    op.create_table(
        "checklist_instances",
        # gen_random_uuid default so trigger/raw inserts get an id (app inserts via ORM).
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("template_id", sa.UUID(), nullable=False),
        sa.Column("assigned_user_id", sa.UUID(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by", sa.UUID(), nullable=True),
        sa.Column("skip_reason", sa.Text(), nullable=True),
        sa.Column("supersedes_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["template_id"], ["checklist_templates.id"]),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["admin_users.id"]),
        sa.ForeignKeyConstraint(["completed_by"], ["admin_users.id"]),
        sa.ForeignKeyConstraint(["supersedes_id"], ["checklist_instances.id"]),
        sa.CheckConstraint(
            "status = 'pending' OR completed_by = assigned_user_id",
            name="ck_checklist_own_completion",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_checklist_instances_template_id"), "checklist_instances", ["template_id"])
    op.create_index(op.f("ix_checklist_instances_assigned_user_id"), "checklist_instances", ["assigned_user_id"])
    op.create_index(op.f("ix_checklist_instances_due_date"), "checklist_instances", ["due_date"])

    op.create_table(
        "meetings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("meeting_date", sa.Date(), nullable=False),
        sa.Column("chaired_by", sa.UUID(), nullable=True),
        sa.Column("numbers_posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary_posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["chaired_by"], ["admin_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_meetings_meeting_date"), "meetings", ["meeting_date"])

    op.create_table(
        "meeting_decisions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("meeting_id", sa.UUID(), nullable=True),
        sa.Column("decision_text", sa.Text(), nullable=False),
        sa.Column("owner_user_id", sa.UUID(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=10), nullable=False, server_default=sa.text("'open'")),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"]),
        sa.ForeignKeyConstraint(["owner_user_id"], ["admin_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_meeting_decisions_meeting_id"), "meeting_decisions", ["meeting_id"])

    # Append-only: block UPDATE/DELETE on completion history (reuses deny_mutation()).
    op.execute(
        "CREATE TRIGGER trg_checklist_append_only BEFORE UPDATE OR DELETE ON checklist_instances "
        "FOR EACH ROW EXECUTE FUNCTION deny_mutation()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_checklist_append_only ON checklist_instances")
    op.drop_index(op.f("ix_meeting_decisions_meeting_id"), table_name="meeting_decisions")
    op.drop_table("meeting_decisions")
    op.drop_index(op.f("ix_meetings_meeting_date"), table_name="meetings")
    op.drop_table("meetings")
    op.drop_index(op.f("ix_checklist_instances_due_date"), table_name="checklist_instances")
    op.drop_index(op.f("ix_checklist_instances_assigned_user_id"), table_name="checklist_instances")
    op.drop_index(op.f("ix_checklist_instances_template_id"), table_name="checklist_instances")
    op.drop_table("checklist_instances")
    op.drop_index(op.f("ix_checklist_templates_role_key"), table_name="checklist_templates")
    op.drop_table("checklist_templates")
