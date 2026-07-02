"""add web session expiry

Revision ID: c9e2a51b7f3d
Revises: b7d41f0a9c2e
Create Date: 2026-07-02

Sessions previously only expired client-side (cookie max-age); the token
stayed valid in the DB forever. This adds a server-side expiry checked on
every authenticated request. Existing sessions have NULL expiry and are
treated as expired — customers just re-enter their phone at /start.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9e2a51b7f3d"
down_revision: Union[str, None] = "b7d41f0a9c2e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column("web_session_expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("customers", "web_session_expires_at")
