"""add partner sourcing workflow

Revision ID: 3d4a8c7b91f2
Revises: fc06fc22b3ea
Create Date: 2026-07-04 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "3d4a8c7b91f2"
down_revision = "fc06fc22b3ea"
branch_labels = None
depends_on = None


partner_type = postgresql.ENUM("supplier", "wholesaler", name="partner_type", create_type=False)
partner_channel = postgresql.ENUM("api", "portal", name="partner_channel", create_type=False)
fulfillment_status = postgresql.ENUM(
    "in_stock",
    "source_from_network",
    "sourcing_requested",
    "partner_confirmed",
    "partner_rejected",
    "pack_ready",
    "dispatch_assigned",
    "picked_up",
    "delivered",
    "failed",
    name="fulfillment_status",
    create_type=False,
)
order_partner_type = postgresql.ENUM("supplier", "wholesaler", name="order_partner_type", create_type=False)
order_partner_channel = postgresql.ENUM("api", "portal", name="order_partner_channel", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    partner_type.create(bind, checkfirst=True)
    partner_channel.create(bind, checkfirst=True)
    fulfillment_status.create(bind, checkfirst=True)
    order_partner_type.create(bind, checkfirst=True)
    order_partner_channel.create(bind, checkfirst=True)
    tables = set(inspector.get_table_names())

    if "network_partners" not in tables:
        op.create_table(
            "network_partners",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("key", sa.String(length=80), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("partner_type", partner_type, nullable=False),
            sa.Column("channel_type", partner_channel, nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("api_base_url", sa.String(length=500), nullable=True),
            sa.Column("portal_contact", sa.String(length=255), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("key"),
        )
    network_indexes = {idx["name"] for idx in inspector.get_indexes("network_partners")} if "network_partners" in set(sa.inspect(bind).get_table_names()) else set()
    if op.f("ix_network_partners_key") not in network_indexes:
        op.create_index(op.f("ix_network_partners_key"), "network_partners", ["key"], unique=False)

    if "order_sourcing" not in set(sa.inspect(bind).get_table_names()):
        op.create_table(
            "order_sourcing",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("order_id", sa.Uuid(), nullable=False),
            sa.Column("fulfillment_status", fulfillment_status, nullable=False),
            sa.Column("sourcing_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("partner_id", sa.Uuid(), nullable=True),
            sa.Column("partner_type", order_partner_type, nullable=True),
            sa.Column("sourcing_channel", order_partner_channel, nullable=True),
            sa.Column("sourcing_request", sa.JSON(), nullable=True),
            sa.Column("requested_items", sa.JSON(), nullable=True),
            sa.Column("confirmed_items", sa.JSON(), nullable=True),
            sa.Column("confirmed_quantity", sa.Integer(), nullable=True),
            sa.Column("confirmed_price", sa.Numeric(12, 2), nullable=True),
            sa.Column("expiry_or_batch_confirmation", sa.Text(), nullable=True),
            sa.Column("ready_for_pickup_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("pickup_code", sa.String(length=40), nullable=True),
            sa.Column("pack_verification_photo", sa.Text(), nullable=True),
            sa.Column("pickup_proof", sa.Text(), nullable=True),
            sa.Column("delivery_proof", sa.Text(), nullable=True),
            sa.Column("customer_facing_status", sa.String(length=255), nullable=True),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("partner_response_raw", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["partner_id"], ["network_partners.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("order_id"),
        )
    order_indexes = {idx["name"] for idx in sa.inspect(bind).get_indexes("order_sourcing")} if "order_sourcing" in set(sa.inspect(bind).get_table_names()) else set()
    if op.f("ix_order_sourcing_order_id") not in order_indexes:
        op.create_index(op.f("ix_order_sourcing_order_id"), "order_sourcing", ["order_id"], unique=False)
    if op.f("ix_order_sourcing_fulfillment_status") not in order_indexes:
        op.create_index(op.f("ix_order_sourcing_fulfillment_status"), "order_sourcing", ["fulfillment_status"], unique=False)
    if op.f("ix_order_sourcing_pickup_code") not in order_indexes:
        op.create_index(op.f("ix_order_sourcing_pickup_code"), "order_sourcing", ["pickup_code"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "order_sourcing" in tables:
        order_indexes = {idx["name"] for idx in inspector.get_indexes("order_sourcing")}
        if op.f("ix_order_sourcing_pickup_code") in order_indexes:
            op.drop_index(op.f("ix_order_sourcing_pickup_code"), table_name="order_sourcing")
        if op.f("ix_order_sourcing_fulfillment_status") in order_indexes:
            op.drop_index(op.f("ix_order_sourcing_fulfillment_status"), table_name="order_sourcing")
        if op.f("ix_order_sourcing_order_id") in order_indexes:
            op.drop_index(op.f("ix_order_sourcing_order_id"), table_name="order_sourcing")
        op.drop_table("order_sourcing")
    if "network_partners" in tables:
        network_indexes = {idx["name"] for idx in inspector.get_indexes("network_partners")}
        if op.f("ix_network_partners_key") in network_indexes:
            op.drop_index(op.f("ix_network_partners_key"), table_name="network_partners")
        op.drop_table("network_partners")

    order_partner_channel.drop(bind, checkfirst=True)
    order_partner_type.drop(bind, checkfirst=True)
    fulfillment_status.drop(bind, checkfirst=True)
    partner_channel.drop(bind, checkfirst=True)
    partner_type.drop(bind, checkfirst=True)
