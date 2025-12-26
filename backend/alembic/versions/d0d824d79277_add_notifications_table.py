"""Add notifications table

Revision ID: d0d824d79277
Revises: auto_approval_001
Create Date: 2025-12-26 08:55:51.532886

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'd0d824d79277'
down_revision = 'auto_approval_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create notifications table
    op.create_table('notifications',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('organization_id', sa.String(length=36), nullable=True),
    sa.Column('notification_type', sa.String(length=50), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('expense_id', sa.String(length=36), nullable=True),
    sa.Column('recurring_template_id', sa.String(length=36), nullable=True),
    sa.Column('is_read', sa.Boolean(), nullable=False),
    sa.Column('read_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['expense_id'], ['expenses.id'], ),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.ForeignKeyConstraint(['recurring_template_id'], ['recurring_expense_templates.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_created_at'), 'notifications', ['created_at'], unique=False)
    op.create_index(op.f('ix_notifications_is_read'), 'notifications', ['is_read'], unique=False)
    op.create_index(op.f('ix_notifications_notification_type'), 'notifications', ['notification_type'], unique=False)
    op.create_index(op.f('ix_notifications_organization_id'), 'notifications', ['organization_id'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop notifications table
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_organization_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_notification_type'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_is_read'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_created_at'), table_name='notifications')
    op.drop_table('notifications')
