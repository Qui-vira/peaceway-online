"""add admin status enum

Revision ID: 2629724af28f
Revises: 8e089711d5fa
Create Date: 2026-06-30 17:39:13.623279
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2629724af28f'
down_revision: Union[str, None] = '8e089711d5fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing admins were implicitly "active" (is_active boolean only) — backfill
    # status from that so nobody's access changes as a result of this migration.
    # New rows going forward use the model's Python-side default (PENDING).
    status_enum = sa.Enum('PENDING', 'ACTIVE', 'DISABLED', 'REMOVED', name='admin_status')
    status_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'admin_users',
        sa.Column('status', status_enum, nullable=False, server_default='ACTIVE'),
    )
    op.execute("UPDATE admin_users SET status = 'DISABLED' WHERE is_active = false")
    op.alter_column('admin_users', 'status', server_default=None)


def downgrade() -> None:
    op.drop_column('admin_users', 'status')
    sa.Enum(name='admin_status').drop(op.get_bind(), checkfirst=True)
