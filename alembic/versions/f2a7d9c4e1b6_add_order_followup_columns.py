"""add order followup scheduling columns

Revision ID: f2a7d9c4e1b6
Revises: d4b8f2c6e9a1
Create Date: 2026-07-14

The 24-hour post-delivery follow-up used to be an in-memory APScheduler date
job added inside the web process, which tied the scheduler to the web server
(no horizontal scaling) and lost pending follow-ups on every restart. It is now
DB-driven like reminders: marking an order delivered stamps ``followup_due_at``,
and a dedicated scheduler worker polls for due, unsent follow-ups. Existing
delivered orders have NULL ``followup_due_at`` and are simply never followed up
retroactively.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f2a7d9c4e1b6"
down_revision: Union[str, None] = "d4b8f2c6e9a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("orders")}
    if "followup_due_at" not in columns:
        op.add_column(
            "orders",
            sa.Column("followup_due_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "followup_sent_at" not in columns:
        op.add_column(
            "orders",
            sa.Column("followup_sent_at", sa.DateTime(timezone=True), nullable=True),
        )
    indexes = {ix["name"] for ix in inspector.get_indexes("orders")}
    if "ix_orders_followup_due" not in indexes:
        # Partial index so the worker's "due and unsent" poll stays cheap.
        op.create_index(
            "ix_orders_followup_due",
            "orders",
            ["followup_due_at"],
            postgresql_where=sa.text("followup_due_at IS NOT NULL AND followup_sent_at IS NULL"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("orders")}
    indexes = {ix["name"] for ix in inspector.get_indexes("orders")}
    if "ix_orders_followup_due" in indexes:
        op.drop_index("ix_orders_followup_due", table_name="orders")
    if "followup_sent_at" in columns:
        op.drop_column("orders", "followup_sent_at")
    if "followup_due_at" in columns:
        op.drop_column("orders", "followup_due_at")
