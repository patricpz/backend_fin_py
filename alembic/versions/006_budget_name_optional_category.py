"""add nome and make categoria_id optional on budgets

Revision ID: 006
Revises: 005
Create Date: 2026-10-31 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    existing_budget_cols = {col["name"] for col in inspector.get_columns("budgets")} if "budgets" in existing_tables else set()

    # 1. Adiciona coluna nome
    if "nome" not in existing_budget_cols:
        op.add_column('budgets', sa.Column('nome', sa.String(100), nullable=True))

    # 2. Torna categoria_id opcional (nullable=True)
    op.alter_column(
        'budgets',
        'categoria_id',
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True
    )


def downgrade() -> None:
    # 1. Reverte categoria_id para NOT NULL
    op.alter_column(
        'budgets',
        'categoria_id',
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False
    )

    # 2. Remove coluna nome
    op.drop_column('budgets', 'nome')
