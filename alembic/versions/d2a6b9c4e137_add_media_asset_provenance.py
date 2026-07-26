"""add media asset provenance (source_url, match_basis)

Safety requirement: for any product image not photographed by staff, we must be able
to answer "where did this picture of a medicine come from, and on what basis was it
attached to this product?" Both columns are nullable because staff photos taken
through the bot need no provenance record — the answer is self-evident.

Revision ID: d2a6b9c4e137
Revises: c9d4e7f21a58
Create Date: 2026-07-26 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "d2a6b9c4e137"
down_revision = "c9d4e7f21a58"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # one op per statement (asyncpg rejects multiple statements per execute)
    op.add_column("media_assets", sa.Column("source_url", sa.Text(), nullable=True))
    op.add_column("media_assets", sa.Column("match_basis", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("media_assets", "match_basis")
    op.drop_column("media_assets", "source_url")
