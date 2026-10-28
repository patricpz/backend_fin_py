"""add transactions user date status index

Revision ID: 003
Revises: 002
Create Date: 2026-10-25 20:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        'ix_transactions_user_date_status',
        'transactions',
        ['user_id', 'data', 'status'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_transactions_user_date_status', table_name='transactions')
