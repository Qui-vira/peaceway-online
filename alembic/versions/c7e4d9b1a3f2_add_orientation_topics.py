"""Add orientation topics + wire them into meetings.

Additions only. `orientation_topics` holds the fixed twelve-week rotation; `meetings`
gains the computed topic, the PA's worked example, and the swap audit columns
(swapped_from_topic_id + swapped_by). Behaviour (rotation compute, Sunday prep, swap)
lives in app code; this is the schema.

Chained after b6d3f8a2c1e5 (checklist + meeting tracker).

Revision ID: c7e4d9b1a3f2
Revises: b6d3f8a2c1e5
Create Date: 2026-07-20
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "c7e4d9b1a3f2"
down_revision = "b6d3f8a2c1e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "orientation_topics",
        # gen_random_uuid default so seed/raw inserts get an id (app inserts via ORM).
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("topic_text", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_orientation_topics_sort_order"), "orientation_topics", ["sort_order"])

    # meetings: one op per statement (asyncpg rejects multiple statements per execute).
    op.add_column("meetings", sa.Column("topic_id", sa.UUID(), nullable=True))
    op.add_column("meetings", sa.Column("example_text", sa.Text(), nullable=True))
    op.add_column("meetings", sa.Column("swapped_from_topic_id", sa.UUID(), nullable=True))
    op.add_column("meetings", sa.Column("swapped_by", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_meetings_topic_id", "meetings", "orientation_topics", ["topic_id"], ["id"])
    op.create_foreign_key(
        "fk_meetings_swapped_from_topic_id", "meetings", "orientation_topics",
        ["swapped_from_topic_id"], ["id"])
    op.create_foreign_key(
        "fk_meetings_swapped_by", "meetings", "admin_users", ["swapped_by"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_meetings_swapped_by", "meetings", type_="foreignkey")
    op.drop_constraint("fk_meetings_swapped_from_topic_id", "meetings", type_="foreignkey")
    op.drop_constraint("fk_meetings_topic_id", "meetings", type_="foreignkey")
    op.drop_column("meetings", "swapped_by")
    op.drop_column("meetings", "swapped_from_topic_id")
    op.drop_column("meetings", "example_text")
    op.drop_column("meetings", "topic_id")
    op.drop_index(op.f("ix_orientation_topics_sort_order"), table_name="orientation_topics")
    op.drop_table("orientation_topics")
