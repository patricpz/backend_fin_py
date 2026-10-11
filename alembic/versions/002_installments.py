"""add installments

Revision ID: 002
Revises: 001
Create Date: 2026-09-05 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'installments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('transactions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('parcela_numero', sa.Integer(), nullable=False),
        sa.Column('valor', sa.Numeric(14, 2), nullable=False),
        sa.Column('data_vencimento', sa.Date(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default=sa.text("'pendente'")),
        sa.Column('observacoes', sa.String(500), nullable=True),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_installments_transaction_parcela', 'installments', ['transaction_id', 'parcela_numero'], unique=True)

    op.add_column('transactions', sa.Column('installments_total_count', sa.SmallInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column('transactions', 'installments_total_count')
    op.drop_index('ix_installments_transaction_parcela', table_name='installments')
    op.drop_index('ix_installments_transaction_id', table_name='installments')
    op.drop_table('installments')
