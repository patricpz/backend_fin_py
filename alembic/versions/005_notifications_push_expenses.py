"""add notifications, preferences, push subscriptions, feedback and expense category column

Revision ID: 005
Revises: 004
Create Date: 2026-10-31 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Extensão da tabela transactions com category_name
    op.add_column('transactions', sa.Column('category_name', sa.String(100), nullable=True))

    # 2. Tabela notifications
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default=sa.text("'unread'")),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('dedupe_key', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('ix_notifications_user_status', 'notifications', ['user_id', 'status'])
    op.create_index('ix_notifications_user_created_at_id', 'notifications', ['user_id', 'created_at', 'id'])
    op.create_unique_constraint('uq_notifications_user_dedupe', 'notifications', ['user_id', 'dedupe_key'])

    # 3. Tabela notification_preferences
    op.create_table(
        'notification_preferences',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('enabled_types', sa.JSON(), nullable=False),
        sa.Column('channel_in_app', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('channel_push', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('sensitivity', sa.String(20), nullable=False, server_default=sa.text("'medium'")),
        sa.Column('quiet_hours_start', sa.String(5), nullable=True),
        sa.Column('quiet_hours_end', sa.String(5), nullable=True),
        sa.Column('timezone', sa.String(50), nullable=False, server_default=sa.text("'America/Fortaleza'")),
        sa.Column('daily_limit', sa.Integer(), nullable=False, server_default=sa.text('3')),
    )
    op.create_index('ix_notification_preferences_user_id', 'notification_preferences', ['user_id'], unique=True)

    # 4. Tabela push_subscriptions
    op.create_table(
        'push_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('endpoint', sa.Text(), nullable=False),
        sa.Column('p256dh', sa.Text(), nullable=False),
        sa.Column('auth', sa.Text(), nullable=False),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_push_subscriptions_user_id', 'push_subscriptions', ['user_id'])
    op.create_index('ix_push_subscriptions_endpoint', 'push_subscriptions', ['endpoint'], unique=True)

    # 5. Tabela notification_feedback
    op.create_table(
        'notification_feedback',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('notification_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('notifications.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_notification_feedback_notification_id', 'notification_feedback', ['notification_id'])
    op.create_index('ix_notification_feedback_user_id', 'notification_feedback', ['user_id'])


def downgrade() -> None:
    op.drop_table('notification_feedback')
    op.drop_table('push_subscriptions')
    op.drop_table('notification_preferences')
    op.drop_table('notifications')
    op.drop_column('transactions', 'category_name')
