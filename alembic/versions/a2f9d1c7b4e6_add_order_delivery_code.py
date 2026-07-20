"""Add orders.delivery_code (one-time proof-of-delivery code).

Issued to the customer at pickup; the rider must key the customer's code to mark
the order delivered.

Revision ID: a2f9d1c7b4e6
Revises: f4b8c2e1a9d3
Create Date: 2026-07-20
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "a2f9d1c7b4e6"
down_revision = "f4b8c2e1a9d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("delivery_code", sa.String(length=6), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "delivery_code")
