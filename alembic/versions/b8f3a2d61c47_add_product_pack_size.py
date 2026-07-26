"""add product pack_size

Separates pack size from strength. Both the PharmaOS import and the manual
"create from name" flow put pack sizes into products.strength ("200ml", "1000ml",
"130g"), which breaks search, filtering and any exact-match image pipeline.

This migration only ADDS the column. It deliberately does not parse existing
strength values into it: that would be inference on medicine data, and pack size
is set by staff through the backfill flow instead.

Revision ID: b8f3a2d61c47
Revises: a1c5e8d47b93
Create Date: 2026-07-26 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "b8f3a2d61c47"
down_revision = "a1c5e8d47b93"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # one op per statement (asyncpg rejects multiple statements per execute)
    op.add_column("products", sa.Column("pack_size", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "pack_size")
