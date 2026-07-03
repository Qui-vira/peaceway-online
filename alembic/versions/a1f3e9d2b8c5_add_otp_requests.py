"""add otp_requests

Revision ID: a1f3e9d2b8c5
Revises: c9e2a51b7f3d
Create Date: 2026-07-03

Stores one-time password requests for web phone-based login/signup.
Each row holds a hashed 6-digit code, expires in 10 minutes, and is
invalidated on first use (or on mismatch to prevent brute force).
"""
from typing import Sequence, Union

from alembic import op

revision: str = "a1f3e9d2b8c5"
down_revision: Union[str, None] = "c9e2a51b7f3d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE otp_requests (
            id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            phone      VARCHAR(30)  NOT NULL,
            email      VARCHAR(255) NOT NULL,
            full_name  VARCHAR(255),
            code_hash  VARCHAR(128) NOT NULL,
            expires_at TIMESTAMPTZ  NOT NULL,
            used       BOOLEAN      NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX ON otp_requests (phone, created_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS otp_requests")
