"""Add web-first operations email auth and partner portal identity.

Revision ID: 8f2c1d4b7a90
Revises: 4b7f6c2a91d1
Create Date: 2026-07-05 19:10:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8f2c1d4b7a90"
down_revision = "4b7f6c2a91d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("admin_users", "telegram_id", existing_type=sa.BigInteger(), nullable=True)

    op.create_table(
        "web_admin_email_otps",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("admin_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["admin_id"], ["admin_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_web_admin_email_otps_admin_id"), "web_admin_email_otps", ["admin_id"], unique=False)
    op.create_index(op.f("ix_web_admin_email_otps_email"), "web_admin_email_otps", ["email"], unique=False)

    with op.batch_alter_table("network_partners") as batch_op:
        batch_op.add_column(sa.Column("portal_login_email", sa.String(length=255), nullable=True))
    op.create_index(op.f("ix_network_partners_portal_login_email"), "network_partners", ["portal_login_email"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_network_partners_portal_login_email"), table_name="network_partners")
    with op.batch_alter_table("network_partners") as batch_op:
        batch_op.drop_column("portal_login_email")

    op.drop_index(op.f("ix_web_admin_email_otps_email"), table_name="web_admin_email_otps")
    op.drop_index(op.f("ix_web_admin_email_otps_admin_id"), table_name="web_admin_email_otps")
    op.drop_table("web_admin_email_otps")

    op.alter_column("admin_users", "telegram_id", existing_type=sa.BigInteger(), nullable=False)
