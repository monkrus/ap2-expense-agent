"""Add auto_approved_via column to expenses table

Tracks HOW an expense was auto-approved:
- "intent_mandate" = AP2 Intent Mandate (premium, Tier 1)
- "approval_policy" = Organizational policy (free, Tier 2)
- NULL = not auto-approved (manual or pending)

Revision ID: add_auto_approved_via
Revises: ap2_2026_fields
"""

from alembic import op
import sqlalchemy as sa

revision = "add_auto_approved_via"
down_revision = "ap2_2026_fields"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("expenses") as batch_op:
        batch_op.add_column(
            sa.Column("auto_approved_via", sa.String(50), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("expenses") as batch_op:
        batch_op.drop_column("auto_approved_via")
