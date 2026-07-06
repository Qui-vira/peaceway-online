"""Add partner portal auth tables (separate auth domain from staff).

Partners authenticate against `network_partners` directly via their own OTP and
session tables. This removes their dependence on `admin_users` — a partner
token can never resolve to a staff identity.

Revision ID: a1d9e6f3c2b8
Revises: 8f2c1d4b7a90
Create Date: 2026-07-06 12:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a1d9e6f3c2b8"
down_revision = "8f2c1d4b7a90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "partner_portal_otps",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("partner_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["partner_id"], ["network_partners.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_partner_portal_otps_partner_id"), "partner_portal_otps", ["partner_id"], unique=False)
    op.create_index(op.f("ix_partner_portal_otps_email"), "partner_portal_otps", ["email"], unique=False)

    op.create_table(
        "partner_portal_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("partner_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["partner_id"], ["network_partners.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_partner_portal_sessions_partner_id"), "partner_portal_sessions", ["partner_id"], unique=False
    )

    # Safety cleanup: staff admin rows that existed only to back the partner
    # portal are deactivated and their portal roles removed. (The sourcing
    # pilot has no live partners yet, so this is expected to be a no-op.)
    op.execute(
        """
        UPDATE admin_users
        SET is_active = false, status = 'REMOVED'
        WHERE id IN (
            SELECT admin_id FROM admin_role_assignments
            GROUP BY admin_id
            HAVING bool_and(role_key IN ('wholesaler_portal', 'supplier_portal'))
        )
        """
    )
    op.execute(
        "DELETE FROM admin_role_assignments WHERE role_key IN ('wholesaler_portal', 'supplier_portal')"
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_partner_portal_sessions_partner_id"), table_name="partner_portal_sessions")
    op.drop_table("partner_portal_sessions")

    op.drop_index(op.f("ix_partner_portal_otps_email"), table_name="partner_portal_otps")
    op.drop_index(op.f("ix_partner_portal_otps_partner_id"), table_name="partner_portal_otps")
    op.drop_table("partner_portal_otps")
    # Role-assignment cleanup is intentionally not reversed.
