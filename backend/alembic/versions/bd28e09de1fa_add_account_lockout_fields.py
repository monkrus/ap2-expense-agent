"""add_account_lockout_fields

Revision ID: bd28e09de1fa
Revises: 001
Create Date: 2025-10-04 20:23:51.719934

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bd28e09de1fa'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add account lockout fields to users table
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('locked_until', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('last_failed_login', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Remove account lockout fields
    op.drop_column('users', 'last_failed_login')
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
