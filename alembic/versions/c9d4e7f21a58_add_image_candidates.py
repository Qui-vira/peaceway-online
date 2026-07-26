"""add image_candidates staging table

Quarantine for scraped manufacturer images. The scraper writes here only; nothing
reaches products.image_id without staff approval in Telegram.

Revision ID: c9d4e7f21a58
Revises: b8f3a2d61c47
Create Date: 2026-07-26 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "c9d4e7f21a58"
down_revision = "b8f3a2d61c47"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # one op per statement (asyncpg rejects multiple statements per execute)
    op.create_table(
        "image_candidates",
        sa.Column("id", sa.UUID(), nullable=False),
        # Nullable: unmatched scraped items are kept on purpose — they are the
        # coverage gap, and dropping them would hide it.
        sa.Column("product_id", sa.UUID(), nullable=True),
        sa.Column("manufacturer", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=False),
        sa.Column("scraped_title", sa.String(length=500), nullable=False),
        sa.Column("scraped_strength", sa.String(length=100), nullable=True),
        sa.Column("scraped_form", sa.String(length=100), nullable=True),
        sa.Column("scraped_pack_size", sa.String(length=100), nullable=True),
        sa.Column("image_sha256", sa.String(length=64), nullable=True),
        sa.Column("match_basis", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("reviewed_by_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("scraped_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_foreign_key(
        "fk_image_candidates_product_id_products",
        "image_candidates", "products", ["product_id"], ["id"], ondelete="CASCADE",
    )
    op.create_index("ix_image_candidates_product_id", "image_candidates", ["product_id"])
    op.create_index("ix_image_candidates_manufacturer", "image_candidates", ["manufacturer"])
    op.create_index("ix_image_candidates_status", "image_candidates", ["status"])
    op.create_index("ix_image_candidates_image_sha256", "image_candidates", ["image_sha256"])
    op.create_unique_constraint(
        "uq_image_candidate_product_image", "image_candidates", ["product_id", "image_url"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_image_candidate_product_image", "image_candidates", type_="unique")
    op.drop_index("ix_image_candidates_image_sha256", table_name="image_candidates")
    op.drop_index("ix_image_candidates_status", table_name="image_candidates")
    op.drop_index("ix_image_candidates_manufacturer", table_name="image_candidates")
    op.drop_index("ix_image_candidates_product_id", table_name="image_candidates")
    op.drop_constraint("fk_image_candidates_product_id_products", "image_candidates", type_="foreignkey")
    op.drop_table("image_candidates")
