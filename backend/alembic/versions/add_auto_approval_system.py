"""Add auto-approval system

Revision ID: auto_approval_001
Revises:
Create Date: 2025-12-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql, sqlite

# revision identifiers, used by Alembic.
revision = 'auto_approval_001'
down_revision = '008_merge_heads'  # Latest revision
branch_labels = None
depends_on = None


def upgrade():
    """Add auto-approval tables and columns"""

    # Create approval_policies table
    op.create_table(
        'approval_policies',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('organization_id', sa.String(255), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('auto_approve', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('require_receipt', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('notify_on_auto_approve', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('conditions', sa.JSON(), nullable=True),
        sa.Column('max_amount_per_expense', sa.Numeric(10, 2), nullable=True),
        sa.Column('daily_limit_per_user', sa.Numeric(10, 2), nullable=True),
        sa.Column('monthly_limit_per_user', sa.Numeric(10, 2), nullable=True),
        sa.Column('yearly_limit_per_user', sa.Numeric(10, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_by', sa.String(255), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('updated_by', sa.String(255), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )

    # Add auto-approval columns to expenses table (no foreign key for SQLite compatibility)
    op.add_column('expenses', sa.Column('auto_approved', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('expenses', sa.Column('approval_policy_id', sa.String(255), nullable=True))

    # Create index on approval_policy_id for performance
    op.create_index('ix_expenses_approval_policy_id', 'expenses', ['approval_policy_id'])


def downgrade():
    """Remove auto-approval system"""

    # Drop index
    op.drop_index('ix_expenses_approval_policy_id', 'expenses')

    # Remove columns from expenses table
    op.drop_column('expenses', 'approval_policy_id')
    op.drop_column('expenses', 'auto_approved')

    # Drop approval_policies table
    op.drop_table('approval_policies')
