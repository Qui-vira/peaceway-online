"""add web customer fields

Revision ID: e3f9a7b2c1d8
Revises: 7bc3628c4cf8
Create Date: 2026-07-02 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e3f9a7b2c1d8'
down_revision: Union[str, None] = '7bc3628c4cf8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Web customers arrive without a Telegram account — make telegram_id optional.
    # Bot customers always supply it; the unique constraint still prevents collisions.
    op.alter_column('customers', 'telegram_id', nullable=True)

    # Session token set as an httpOnly cookie after web registration.
    op.add_column('customers', sa.Column(
        'web_session_token', sa.String(length=64), nullable=True
    ))
    op.create_index(
        'ix_customers_web_session_token',
        'customers', ['web_session_token'], unique=True
    )

    # Phone lookup index — web customers are identified by phone, not telegram_id.
    op.create_index(
        'ix_customers_phone',
        'customers', ['phone'], unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_customers_phone', table_name='customers')
    op.drop_index('ix_customers_web_session_token', table_name='customers')
    op.drop_column('customers', 'web_session_token')
    op.alter_column('customers', 'telegram_id', nullable=False)
