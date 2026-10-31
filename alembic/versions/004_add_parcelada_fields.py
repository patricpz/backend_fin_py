"""add parcelada fields to transaction model

Revision ID: 004
Revises: 003
Create Date: 2026-10-28 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('transactions', sa.Column('is_installment', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('transactions', sa.Column('installment_count', sa.Integer(), nullable=True))
    op.add_column('transactions', sa.Column('paid_installments', sa.Integer(), server_default=sa.text('0'), nullable=False))
    op.add_column('transactions', sa.Column('first_due_date', sa.Date(), nullable=True))
    op.create_index('ix_transactions_user_is_installment', 'transactions', ['user_id', 'is_installment'], unique=False)
    op.create_check_constraint(
        'ck_transactions_installment_count_min_2',
        'transactions',
        sa.text('installment_count IS NULL OR installment_count >= 2'),
    )
    op.create_check_constraint(
        'ck_transactions_paid_installments_non_negative',
        'transactions',
        sa.text('paid_installments >= 0'),
    )
    op.create_check_constraint(
        'ck_transactions_paid_installments_lte_count',
        'transactions',
        sa.text('paid_installments <= installment_count OR installment_count IS NULL'),
    )


def downgrade() -> None:
    op.drop_constraint('ck_transactions_paid_installments_lte_count', table_name='transactions')
    op.drop_constraint('ck_transactions_paid_installments_non_negative', table_name='transactions')
    op.drop_constraint('ck_transactions_installment_count_min_2', table_name='transactions')
    op.drop_index('ix_transactions_user_is_installment', table_name='transactions')
    op.drop_column('transactions', 'first_due_date')
    op.drop_column('transactions', 'paid_installments')
    op.drop_column('transactions', 'installment_count')
    op.drop_column('transactions', 'is_installment')