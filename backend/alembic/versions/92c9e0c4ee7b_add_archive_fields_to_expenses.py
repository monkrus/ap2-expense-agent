"""add_archive_fields_to_expenses

Revision ID: 92c9e0c4ee7b
Revises: aea3ed9130aa
Create Date: 2025-10-24 22:16:36.839819

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '92c9e0c4ee7b'
down_revision = 'aea3ed9130aa'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add archive tracking fields to expenses table
    # Note: Foreign key constraint will be enforced at the SQLAlchemy ORM level
    op.add_column('expenses', sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('expenses', sa.Column('archived_at', sa.DateTime(), nullable=True))
    op.add_column('expenses', sa.Column('archived_by', sa.String(255), nullable=True))

    # Create index on is_archived for faster filtering
    op.create_index('ix_expenses_is_archived', 'expenses', ['is_archived'])


def downgrade() -> None:
    # Remove index
    op.drop_index('ix_expenses_is_archived', 'expenses')

    # Remove columns
    op.drop_column('expenses', 'archived_by')
    op.drop_column('expenses', 'archived_at')
    op.drop_column('expenses', 'is_archived')
