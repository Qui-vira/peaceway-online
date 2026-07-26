"""add media assets and product image

Revision ID: a1c5e8d47b93
Revises: c7e4d9b1a3f2
Create Date: 2026-07-26 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "a1c5e8d47b93"
down_revision = "c7e4d9b1a3f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Binary media stored in Postgres — this deployment has no object storage and no
    # writable runtime filesystem (Railway and Vercel are both ephemeral).
    # one op per statement (asyncpg rejects multiple statements per execute)
    op.create_table(
        "media_assets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("content_type", sa.String(length=50), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("uploaded_by_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_media_assets_sha256", "media_assets", ["sha256"], unique=True)

    # Nullable: every existing product keeps falling back to its dosage-form SVG icon.
    op.add_column("products", sa.Column("image_id", sa.UUID(), nullable=True))
    op.create_index("ix_products_image_id", "products", ["image_id"], unique=False)
    op.create_foreign_key(
        "fk_products_image_id_media_assets",
        "products",
        "media_assets",
        ["image_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_products_image_id_media_assets", "products", type_="foreignkey")
    op.drop_index("ix_products_image_id", table_name="products")
    op.drop_column("products", "image_id")
    op.drop_index("ix_media_assets_sha256", table_name="media_assets")
    op.drop_table("media_assets")
