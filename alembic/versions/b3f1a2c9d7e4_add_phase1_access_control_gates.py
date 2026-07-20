"""Add Phase-1 access-control gates (additive, fulfilment-safe subset).

New append-only / control tables (prescription_verifications, dispensing_records,
break_glass_access, approvals, community_members), orders.handling_flag, audit_logs
compliance columns, and the fulfilment-SAFE triggers + masked dispatch view (append-only
guards, handling_flag/line-binding stamping, view — see app/core/gate_ddl.py).

DEFERRED — the Gate 1 dispatch-block trigger is intentionally NOT in this migration
(app/core/gate_ddl.GATE1_UPGRADE_STATEMENTS). Deploying it before the pharmacist verify
write-path exists would reject every POM dispatch. It ships in a follow-up migration
with that write-path + an approved-order backfill.

The REVOKE-from-app-role hardening and clinical RLS (Gate 4) belong to the
superuser-removal ticket — RLS cannot bite while the app connects as a Postgres
superuser. Gate 7 (discount-above-cap) ships with the future discount feature.

Revision ID: b3f1a2c9d7e4
Revises: f2a7d9c4e1b6
Create Date: 2026-07-20
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.core.gate_ddl import DOWNGRADE_STATEMENTS, UPGRADE_STATEMENTS

revision = "b3f1a2c9d7e4"
down_revision = "f2a7d9c4e1b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prescription_verifications",
        # DB-level default: the on_order_item_change trigger inserts SUPERSEDED rows
        # at the database level (no ORM), so id must default server-side.
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("pharmacist_user_id", sa.UUID(), nullable=True),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("amends_record_id", sa.UUID(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["pharmacist_user_id"], ["admin_users.id"]),
        sa.ForeignKeyConstraint(["amends_record_id"], ["prescription_verifications.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_prescription_verifications_order_id"), "prescription_verifications", ["order_id"])

    op.create_table(
        "dispensing_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("pharmacist_user_id", sa.UUID(), nullable=True),
        sa.Column("amends_record_id", sa.UUID(), nullable=True),
        sa.Column("dispensed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["pharmacist_user_id"], ["admin_users.id"]),
        sa.ForeignKeyConstraint(["amends_record_id"], ["dispensing_records.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dispensing_records_order_id"), "dispensing_records", ["order_id"])

    op.create_table(
        "break_glass_access",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("resource", sa.String(length=80), nullable=False),
        sa.Column("resource_id", sa.String(length=80), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["admin_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_break_glass_access_user_id"), "break_glass_access", ["user_id"])

    op.create_table(
        "approvals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("request_type", sa.String(length=40), nullable=False),
        sa.Column("resource_id", sa.String(length=80), nullable=True),
        sa.Column("requested_by", sa.UUID(), nullable=True),
        sa.Column("approved_by", sa.UUID(), nullable=True),
        sa.Column("decision", sa.String(length=20), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["requested_by"], ["admin_users.id"]),
        sa.ForeignKeyConstraint(["approved_by"], ["admin_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_approvals_request_type"), "approvals", ["request_type"])

    op.create_table(
        "community_members",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_community_members_telegram_user_id"), "community_members", ["telegram_user_id"])

    # orders.handling_flag (stamped by the order_items trigger; frozen at dispatch)
    op.add_column(
        "orders",
        sa.Column("handling_flag", sa.String(length=20), nullable=False, server_default="STANDARD"),
    )
    # Backfill existing orders so the flag is correct, not just the default.
    op.execute(
        "UPDATE orders o SET handling_flag = 'RX_ID_CHECK' "
        "WHERE EXISTS (SELECT 1 FROM order_items oi WHERE oi.order_id = o.id AND oi.requires_prescription = true)"
    )

    # audit_logs compliance columns
    op.add_column("audit_logs", sa.Column("actor_id", sa.UUID(), nullable=True))
    op.add_column("audit_logs", sa.Column("reason", sa.Text(), nullable=True))
    op.add_column("audit_logs", sa.Column("before_value", postgresql.JSONB(), nullable=True))
    op.add_column("audit_logs", sa.Column("after_value", postgresql.JSONB(), nullable=True))
    op.add_column("audit_logs", sa.Column("ip", sa.String(length=45), nullable=True))
    op.create_foreign_key(
        "fk_audit_logs_actor_id_admin_users", "audit_logs", "admin_users", ["actor_id"], ["id"]
    )

    # Functions, triggers, and the masked dispatch view (one statement at a time:
    # the async driver rejects multi-statement executes).
    for stmt in UPGRADE_STATEMENTS:
        op.execute(stmt)


def downgrade() -> None:
    for stmt in DOWNGRADE_STATEMENTS:
        op.execute(stmt)

    op.drop_constraint("fk_audit_logs_actor_id_admin_users", "audit_logs", type_="foreignkey")
    for col in ("ip", "after_value", "before_value", "reason", "actor_id"):
        op.drop_column("audit_logs", col)

    op.drop_column("orders", "handling_flag")

    op.drop_index(op.f("ix_community_members_telegram_user_id"), table_name="community_members")
    op.drop_table("community_members")
    op.drop_index(op.f("ix_approvals_request_type"), table_name="approvals")
    op.drop_table("approvals")
    op.drop_index(op.f("ix_break_glass_access_user_id"), table_name="break_glass_access")
    op.drop_table("break_glass_access")
    op.drop_index(op.f("ix_dispensing_records_order_id"), table_name="dispensing_records")
    op.drop_table("dispensing_records")
    op.drop_index(op.f("ix_prescription_verifications_order_id"), table_name="prescription_verifications")
    op.drop_table("prescription_verifications")
