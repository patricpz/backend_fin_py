"""initial migration

Revision ID: 001
Revises: 
Create Date: 2026-08-22 11:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('nome', sa.String(120), nullable=False),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('senha_hash', sa.String(255), nullable=False),
        sa.Column('ativo', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    op.create_table(
        'accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('nome', sa.String(120), nullable=False),
        sa.Column('tipo', sa.String(20), nullable=False),
        sa.Column('saldo_inicial', sa.Numeric(14, 2), nullable=False, server_default=sa.text('0')),
        sa.Column('moeda', sa.String(3), nullable=False, server_default=sa.text("'BRL'")),
        sa.Column('ativo', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_accounts_user_id', 'accounts', ['user_id'])
    op.create_index('ix_accounts_user_ativo', 'accounts', ['user_id', 'ativo'])

    op.create_table(
        'categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('categoria_pai_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True),
        sa.Column('nome', sa.String(80), nullable=False),
        sa.Column('tipo', sa.String(20), nullable=False),
        sa.Column('cor', sa.String(7), nullable=False, server_default=sa.text("'#6366F1'")),
        sa.Column('icone', sa.String(40), nullable=False, server_default=sa.text("'tag'")),
        sa.Column('ativo', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_categories_user_id', 'categories', ['user_id'])
    op.create_index('ix_categories_user_tipo_ativo', 'categories', ['user_id', 'tipo', 'ativo'])
    op.create_index('ix_categories_user_nome_tipo', 'categories', ['user_id', 'nome', 'tipo'], unique=True)

    op.create_table(
        'recurring_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('conta_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('categoria_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True),
        sa.Column('tipo', sa.String(20), nullable=False),
        sa.Column('valor', sa.Numeric(14, 2), nullable=False),
        sa.Column('frequencia', sa.String(20), nullable=False),
        sa.Column('dia_do_mes', sa.SmallInteger(), nullable=True),
        sa.Column('dia_semana', sa.SmallInteger(), nullable=True),
        sa.Column('data_inicio', sa.Date(), nullable=False),
        sa.Column('data_fim', sa.Date(), nullable=True),
        sa.Column('proxima_execucao', sa.Date(), nullable=False),
        sa.Column('descricao', sa.String(200), nullable=False),
        sa.Column('ativo', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_recurring_user_id', 'recurring_transactions', ['user_id'])
    op.create_index('ix_recurring_user_ativo_proxima', 'recurring_transactions', ['user_id', 'ativo', 'proxima_execucao'])

    op.create_table(
        'transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('conta_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('conta_destino_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='RESTRICT'), nullable=True),
        sa.Column('categoria_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True),
        sa.Column('tipo', sa.String(20), nullable=False),
        sa.Column('valor', sa.Numeric(14, 2), nullable=False),
        sa.Column('data', sa.Date(), nullable=False),
        sa.Column('descricao', sa.String(200), nullable=False),
        sa.Column('observacoes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default=sa.text("'confirmado'")),
        sa.Column('anexo_url', sa.String(500), nullable=True),
        sa.Column('recorrencia_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('recurring_transactions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('idempotency_key', postgresql.UUID(as_uuid=True), nullable=True, unique=True),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_transactions_user_id', 'transactions', ['user_id'])
    op.create_index('ix_transactions_user_data_desc', 'transactions', ['user_id', 'data'])
    op.create_index('ix_transactions_conta_data', 'transactions', ['conta_id', 'data'])
    op.create_index('ix_transactions_categoria_data', 'transactions', ['categoria_id', 'data'])
    op.create_index('ix_transactions_status_data', 'transactions', ['status', 'data'])

    op.create_table(
        'budgets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('categoria_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('categories.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('valor_limite', sa.Numeric(14, 2), nullable=False),
        sa.Column('mes', sa.SmallInteger(), nullable=False),
        sa.Column('ano', sa.SmallInteger(), nullable=False),
        sa.Column('alerta_percentual', sa.SmallInteger(), nullable=False, server_default=sa.text('80')),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_budgets_user_id', 'budgets', ['user_id'])
    op.create_index('ix_budgets_user_period', 'budgets', ['user_id', 'ano', 'mes'])
    op.create_unique_constraint('uq_budget_user_cat_period', 'budgets', ['user_id', 'categoria_id', 'mes', 'ano'])

    op.create_table(
        'goals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('nome', sa.String(120), nullable=False),
        sa.Column('descricao', sa.String(500), nullable=True),
        sa.Column('valor_alvo', sa.Numeric(14, 2), nullable=False),
        sa.Column('data_alvo', sa.Date(), nullable=True),
        sa.Column('categoria', sa.String(80), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default=sa.text("'em_andamento'")),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_goals_user_id', 'goals', ['user_id'])
    op.create_index('ix_goals_user_status', 'goals', ['user_id', 'status'])

    op.create_table(
        'goal_contributions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('goal_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('goals.id', ondelete='CASCADE'), nullable=False),
        sa.Column('valor', sa.Numeric(14, 2), nullable=False),
        sa.Column('tipo', sa.String(20), nullable=False),
        sa.Column('data', sa.Date(), nullable=False),
        sa.Column('observacao', sa.String(200), nullable=True),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_goal_contributions_goal_id', 'goal_contributions', ['goal_id'])
    op.create_index('ix_goal_contributions_goal_data', 'goal_contributions', ['goal_id', 'data'])

    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('jti', sa.String(36), nullable=False, unique=True),
        sa.Column('expira_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revogado', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'])
    op.create_index('ix_refresh_tokens_jti', 'refresh_tokens', ['jti'], unique=True)
    op.create_index('ix_refresh_tokens_user_revogado', 'refresh_tokens', ['user_id', 'revogado'])


def downgrade() -> None:
    op.drop_table('refresh_tokens')
    op.drop_table('goal_contributions')
    op.drop_table('goals')
    op.drop_table('budgets')
    op.drop_table('transactions')
    op.drop_table('recurring_transactions')
    op.drop_table('categories')
    op.drop_table('accounts')
    op.drop_table('users')