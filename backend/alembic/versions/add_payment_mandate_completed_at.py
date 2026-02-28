"""add payment_mandate completed_at

Revision ID: add_pm_completed_at
Revises: e5448dd82726
Create Date: 2026-02-27
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_pm_completed_at'
down_revision = 'e5448dd82726'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('payment_mandates', sa.Column('completed_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('payment_mandates', 'completed_at')
