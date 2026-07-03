"""add web admin auth tables

Revision ID: d7ef2ad71f22
Revises: a1f3e9d2b8c5
Create Date: 2026-07-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d7ef2ad71f22"
down_revision = "a1f3e9d2b8c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "web_admin_otps",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_web_admin_otps_telegram_id", "web_admin_otps", ["telegram_id"])

    op.create_table(
        "web_admin_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("admin_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["admin_id"], ["admin_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_web_admin_sessions_admin_id", "web_admin_sessions", ["admin_id"])


def downgrade() -> None:
    op.drop_index("ix_web_admin_sessions_admin_id", "web_admin_sessions")
    op.drop_table("web_admin_sessions")
    op.drop_index("ix_web_admin_otps_telegram_id", "web_admin_otps")
    op.drop_table("web_admin_otps")
