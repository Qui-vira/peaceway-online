"""add inventory scan session/image/item tables

Revision ID: d4b8f2c6e9a1
Revises: a1d9e6f3c2b8
Create Date: 2026-07-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'd4b8f2c6e9a1'
down_revision: Union[str, None] = 'a1d9e6f3c2b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSONB = postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite')


def upgrade() -> None:
    op.create_table(
        'inventory_scan_sessions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('admin_telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('scan_mode', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('warnings', JSONB, nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('analysis_summary', JSONB, nullable=True),
        sa.Column('commit_summary', JSONB, nullable=True),
        sa.Column('committed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_inventory_scan_sessions_admin_telegram_id'), 'inventory_scan_sessions', ['admin_telegram_id'], unique=False)
    op.create_index(op.f('ix_inventory_scan_sessions_status'), 'inventory_scan_sessions', ['status'], unique=False)

    op.create_table(
        'inventory_scan_images',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('session_id', sa.Uuid(), nullable=False),
        sa.Column('telegram_file_id', sa.String(length=255), nullable=False),
        sa.Column('file_unique_id', sa.String(length=128), nullable=False),
        sa.Column('media_group_id', sa.String(length=64), nullable=True),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['inventory_scan_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'file_unique_id', name='uq_scan_image_per_session'),
    )
    op.create_index(op.f('ix_inventory_scan_images_session_id'), 'inventory_scan_images', ['session_id'], unique=False)

    op.create_table(
        'inventory_scan_items',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('session_id', sa.Uuid(), nullable=False),
        sa.Column('item_index', sa.Integer(), nullable=False),
        sa.Column('product_name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('dosage', sa.String(length=100), nullable=True),
        sa.Column('prescription', sa.String(length=20), nullable=False),
        sa.Column('availability', sa.Boolean(), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('cost_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('selling_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('detected_stock', sa.Integer(), nullable=False),
        sa.Column('counting_notes', sa.Text(), nullable=True),
        sa.Column('source_images', JSONB, nullable=True),
        sa.Column('identity_confidence', sa.Float(), nullable=True),
        sa.Column('stock_count_confidence', sa.Float(), nullable=True),
        sa.Column('match_confidence', sa.Float(), nullable=True),
        sa.Column('match_type', sa.String(length=30), nullable=False),
        sa.Column('matched_product_id', sa.Uuid(), nullable=True),
        sa.Column('proposed_action', sa.String(length=30), nullable=False),
        sa.Column('review_status', sa.String(length=20), nullable=False),
        sa.Column('corrections', JSONB, nullable=True),
        sa.Column('committed', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['inventory_scan_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['matched_product_id'], ['products.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_inventory_scan_items_session_id'), 'inventory_scan_items', ['session_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_inventory_scan_items_session_id'), table_name='inventory_scan_items')
    op.drop_table('inventory_scan_items')
    op.drop_index(op.f('ix_inventory_scan_images_session_id'), table_name='inventory_scan_images')
    op.drop_table('inventory_scan_images')
    op.drop_index(op.f('ix_inventory_scan_sessions_status'), table_name='inventory_scan_sessions')
    op.drop_index(op.f('ix_inventory_scan_sessions_admin_telegram_id'), table_name='inventory_scan_sessions')
    op.drop_table('inventory_scan_sessions')
