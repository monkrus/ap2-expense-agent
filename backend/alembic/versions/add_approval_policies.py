"""Add approval policies and rules

Revision ID: add_approval_policies
Revises: fa97e13a1889
Create Date: 2025-11-10 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_approval_policies'
down_revision = 'fa97e13a1889'
branch_labels = None
depends_on = None


def upgrade():
    # Create approval_policies table
    op.create_table(
        'approval_policies',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),

        # Auto-approval settings
        sa.Column('auto_approve', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('require_receipt', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notify_on_auto_approve', sa.Boolean(), nullable=False, server_default='true'),

        # Conditions (JSON for flexibility)
        sa.Column('conditions', sa.JSON(), nullable=True),

        # Limits
        sa.Column('max_amount_per_expense', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('daily_limit_per_user', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('monthly_limit_per_user', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('yearly_limit_per_user', sa.Numeric(precision=10, scale=2), nullable=True),

        # Metadata
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('updated_by', sa.String(), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL'),
    )

    # Create index for faster lookups
    op.create_index('ix_approval_policies_org_active', 'approval_policies',
                    ['organization_id', 'is_active', 'priority'])

    # Add auto_approved and approval_policy_id columns to expenses table
    op.add_column('expenses', sa.Column('auto_approved', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('expenses', sa.Column('approval_policy_id', sa.String(), nullable=True))
    op.create_foreign_key('fk_expenses_approval_policy', 'expenses', 'approval_policies',
                          ['approval_policy_id'], ['id'], ondelete='SET NULL')

    # Create index for auto-approved expenses
    op.create_index('ix_expenses_auto_approved', 'expenses', ['auto_approved', 'approved_at'])


def downgrade():
    op.drop_index('ix_expenses_auto_approved', table_name='expenses')
    op.drop_constraint('fk_expenses_approval_policy', 'expenses', type_='foreignkey')
    op.drop_column('expenses', 'approval_policy_id')
    op.drop_column('expenses', 'auto_approved')
    op.drop_index('ix_approval_policies_org_active', table_name='approval_policies')
    op.drop_table('approval_policies')
