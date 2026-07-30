"""add customer referral fields

Revision ID: a1f4c8e26b93
Revises: d2a6b9c4e137
Create Date: 2026-07-30 00:00:00.000000

The referral feature shipped as front-end only: `/referral` displayed a code
derived from the customer's own name and phone, on a link pointing at a domain
the pharmacy does not own, and nothing anywhere read the `?ref=` parameter. The
code could not be redeemed because it was never stored.

Two columns make it real: the code the customer shares, and who referred them.
Rewards are deliberately NOT modelled here - paying money out is an accounting
concern that needs its own ledger and a decision about when a referral counts as
earned. This migration records attribution truthfully; the UI shows only what
attribution can support.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a1f4c8e26b93"
down_revision = "d2a6b9c4e137"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("customers")}

    if "referral_code" not in columns:
        op.add_column(
            "customers", sa.Column("referral_code", sa.String(16), nullable=True)
        )
        op.create_index(
            "ix_customers_referral_code",
            "customers",
            ["referral_code"],
            unique=True,
        )

    if "referred_by_customer_id" not in columns:
        op.add_column(
            "customers",
            sa.Column(
                "referred_by_customer_id",
                sa.dialects.postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
        )
        op.create_foreign_key(
            "fk_customers_referred_by_customer_id",
            "customers",
            "customers",
            ["referred_by_customer_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index(
            "ix_customers_referred_by_customer_id",
            "customers",
            ["referred_by_customer_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("customers")}

    if "referred_by_customer_id" in columns:
        op.drop_index("ix_customers_referred_by_customer_id", table_name="customers")
        op.drop_constraint(
            "fk_customers_referred_by_customer_id", "customers", type_="foreignkey"
        )
        op.drop_column("customers", "referred_by_customer_id")

    if "referral_code" in columns:
        op.drop_index("ix_customers_referral_code", table_name="customers")
        op.drop_column("customers", "referral_code")
