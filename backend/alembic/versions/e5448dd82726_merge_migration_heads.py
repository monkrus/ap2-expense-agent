"""merge migration heads

Revision ID: e5448dd82726
Revises: tier_limit_protection, d0d824d79277
Create Date: 2026-01-06 15:31:14.064963

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e5448dd82726'
down_revision = ('tier_limit_protection', 'd0d824d79277')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
