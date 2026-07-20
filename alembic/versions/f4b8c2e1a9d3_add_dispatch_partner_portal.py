"""Add the dispatch-partner (rider) portal: identity, auth, assignment link, Gate 5.

- dispatch_partners (+ otp/session tables): external rider auth domain.
- rider_assignments.dispatch_partner_id: links an assignment to a rider identity.
- Gate 5 RLS on rider_assignments: a dispatch_partner actor sees ONLY its own
  assignments AND only while the order is non-terminal (row disappears on
  DELIVERED/FAILED/RETURNED). Staff (admin actor) and internal jobs (unset) are
  unaffected. Reuses the app_actor_type()/app_current_actor() helpers from the
  clinical-RLS migration.

Revision ID: f4b8c2e1a9d3
Revises: e9c4a1b7d2f5
Create Date: 2026-07-20
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "f4b8c2e1a9d3"
down_revision = "e9c4a1b7d2f5"
branch_labels = None
depends_on = None

_TERMINAL = "('DELIVERED','FAILED_DELIVERY','RETURNED_TO_PHARMACY')"
_NOT_RIDER = "app_actor_type() IS DISTINCT FROM 'dispatch_partner'"
_OWN_ACTIVE = (
    "(dispatch_partner_id = app_current_actor() AND EXISTS ("
    "  SELECT 1 FROM orders o WHERE o.id = rider_assignments.order_id "
    f"  AND o.delivery_status NOT IN {_TERMINAL}))"
)

_RLS = [
    "ALTER TABLE rider_assignments ENABLE ROW LEVEL SECURITY",
    f"CREATE POLICY ra_rls_select ON rider_assignments FOR SELECT USING ({_NOT_RIDER} OR {_OWN_ACTIVE})",
    f"CREATE POLICY ra_rls_insert ON rider_assignments FOR INSERT WITH CHECK ({_NOT_RIDER})",
    f"CREATE POLICY ra_rls_update ON rider_assignments FOR UPDATE "
    f"USING ({_NOT_RIDER} OR dispatch_partner_id = app_current_actor()) WITH CHECK (true)",
    f"CREATE POLICY ra_rls_delete ON rider_assignments FOR DELETE USING ({_NOT_RIDER})",
]


def upgrade() -> None:
    op.create_table(
        "dispatch_partners",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("portal_login_email", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dispatch_partners_portal_login_email"), "dispatch_partners", ["portal_login_email"], unique=True)

    op.create_table(
        "dispatch_partner_otps",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("dispatch_partner_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["dispatch_partner_id"], ["dispatch_partners.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dispatch_partner_otps_dispatch_partner_id"), "dispatch_partner_otps", ["dispatch_partner_id"])
    op.create_index(op.f("ix_dispatch_partner_otps_email"), "dispatch_partner_otps", ["email"])

    op.create_table(
        "dispatch_partner_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("dispatch_partner_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["dispatch_partner_id"], ["dispatch_partners.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dispatch_partner_sessions_dispatch_partner_id"), "dispatch_partner_sessions", ["dispatch_partner_id"])

    op.add_column("rider_assignments", sa.Column("dispatch_partner_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_rider_assignments_dispatch_partner_id", "rider_assignments", "dispatch_partners",
        ["dispatch_partner_id"], ["id"], ondelete="SET NULL",
    )

    for stmt in _RLS:
        op.execute(stmt)


def downgrade() -> None:
    for pol in ("select", "insert", "update", "delete"):
        op.execute(f"DROP POLICY IF EXISTS ra_rls_{pol} ON rider_assignments")
    op.execute("ALTER TABLE rider_assignments DISABLE ROW LEVEL SECURITY")
    op.drop_constraint("fk_rider_assignments_dispatch_partner_id", "rider_assignments", type_="foreignkey")
    op.drop_column("rider_assignments", "dispatch_partner_id")
    op.drop_index(op.f("ix_dispatch_partner_sessions_dispatch_partner_id"), table_name="dispatch_partner_sessions")
    op.drop_table("dispatch_partner_sessions")
    op.drop_index(op.f("ix_dispatch_partner_otps_email"), table_name="dispatch_partner_otps")
    op.drop_index(op.f("ix_dispatch_partner_otps_dispatch_partner_id"), table_name="dispatch_partner_otps")
    op.drop_table("dispatch_partner_otps")
    op.drop_index(op.f("ix_dispatch_partners_portal_login_email"), table_name="dispatch_partners")
    op.drop_table("dispatch_partners")
