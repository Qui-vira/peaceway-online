"""add customer telegram link fields

Revision ID: e8a1c5d7f3b2
Revises: d7ef2ad71f22
Create Date: 2026-07-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "e8a1c5d7f3b2"
down_revision = "d7ef2ad71f22"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("customers")}
    if "telegram_username" not in columns:
        op.add_column("customers", sa.Column("telegram_username", sa.String(64), nullable=True))
    if "telegram_linked_at" not in columns:
        op.add_column("customers", sa.Column("telegram_linked_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("customers")}
    if "telegram_linked_at" in columns:
        op.drop_column("customers", "telegram_linked_at")
    if "telegram_username" in columns:
        op.drop_column("customers", "telegram_username")
