"""merge heads into single lineage

Revision ID: 008_merge_heads
Revises: 007_marketplace_tables, add_approval_policies, add_audit_chain_fields, usage_tracking_001
Create Date: 2025-12-05
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "008_merge_heads"
down_revision = ("007_marketplace_tables", "add_approval_policies", "add_audit_chain_fields", "usage_tracking_001")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge point only; no schema changes.
    pass


def downgrade() -> None:
    # Merge point only; no schema changes.
    pass
