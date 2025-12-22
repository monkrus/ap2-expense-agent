"""add multi-tenancy organization models

Revision ID: aea3ed9130aa
Revises: 62ba85a4da82
Create Date: 2025-10-06 20:21:06.924969

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'aea3ed9130aa'
down_revision = '62ba85a4da82'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create organizationrole enum if it doesn't exist
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'organizationrole')"))
    if not result.scalar():
        op.execute("CREATE TYPE organizationrole AS ENUM ('owner', 'admin', 'manager', 'member')")

    # Create organizations table
    op.create_table(
        'organizations',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='USD'),
        sa.Column('timezone', sa.String(length=50), nullable=False, server_default='UTC'),
        sa.Column('subscription_id', sa.String(length=255), nullable=True),
        sa.Column('max_members', sa.Integer(), nullable=False, server_default='25'),
        sa.Column('max_expenses_per_month', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_organizations_created_at'), 'organizations', ['created_at'], unique=False)
    op.create_index(op.f('ix_organizations_slug'), 'organizations', ['slug'], unique=True)

    # Create organization_members table
    op.create_table(
        'organization_members',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('organization_id', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('role', postgresql.ENUM('owner', 'admin', 'manager', 'member', name='organizationrole', create_type=False), nullable=False, server_default='member'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('joined_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'user_id', name='unique_org_user')
    )
    op.create_index(op.f('ix_organization_members_organization_id'), 'organization_members', ['organization_id'], unique=False)
    op.create_index(op.f('ix_organization_members_user_id'), 'organization_members', ['user_id'], unique=False)

    # Create organization_invitations table
    op.create_table(
        'organization_invitations',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('organization_id', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('role', postgresql.ENUM('owner', 'admin', 'manager', 'member', name='organizationrole', create_type=False), nullable=False, server_default='member'),
        sa.Column('invited_by', sa.String(length=255), nullable=False),
        sa.Column('token', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['invited_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_organization_invitations_email'), 'organization_invitations', ['email'], unique=False)
    op.create_index(op.f('ix_organization_invitations_organization_id'), 'organization_invitations', ['organization_id'], unique=False)
    op.create_index(op.f('ix_organization_invitations_status'), 'organization_invitations', ['status'], unique=False)
    op.create_index(op.f('ix_organization_invitations_token'), 'organization_invitations', ['token'], unique=True)

    # Add organization_id to expenses table
    op.add_column('expenses', sa.Column('organization_id', sa.String(length=255), nullable=True))
    op.create_foreign_key('expenses_organization_id_fkey', 'expenses', 'organizations', ['organization_id'], ['id'])
    op.create_index(op.f('ix_expenses_organization_id'), 'expenses', ['organization_id'], unique=False)

    # Add foreign key from organizations to subscriptions
    op.create_foreign_key('organizations_subscription_id_fkey', 'organizations', 'subscriptions', ['subscription_id'], ['id'])


def downgrade() -> None:
    # Remove foreign keys and indexes
    op.drop_constraint('organizations_subscription_id_fkey', 'organizations', type_='foreignkey')
    op.drop_index(op.f('ix_expenses_organization_id'), table_name='expenses')
    op.drop_constraint('expenses_organization_id_fkey', 'expenses', type_='foreignkey')
    op.drop_column('expenses', 'organization_id')

    # Drop organization_invitations table
    op.drop_index(op.f('ix_organization_invitations_token'), table_name='organization_invitations')
    op.drop_index(op.f('ix_organization_invitations_status'), table_name='organization_invitations')
    op.drop_index(op.f('ix_organization_invitations_organization_id'), table_name='organization_invitations')
    op.drop_index(op.f('ix_organization_invitations_email'), table_name='organization_invitations')
    op.drop_table('organization_invitations')

    # Drop organization_members table
    op.drop_index(op.f('ix_organization_members_user_id'), table_name='organization_members')
    op.drop_index(op.f('ix_organization_members_organization_id'), table_name='organization_members')
    op.drop_table('organization_members')

    # Drop organizations table
    op.drop_index(op.f('ix_organizations_slug'), table_name='organizations')
    op.drop_index(op.f('ix_organizations_created_at'), table_name='organizations')
    op.drop_table('organizations')

    # Drop organizationrole enum
    op.execute("DROP TYPE organizationrole")
