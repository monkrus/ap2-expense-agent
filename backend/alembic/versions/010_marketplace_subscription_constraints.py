"""Adjust marketplace subscription constraints and metadata storage

Revision ID: 010_marketplace_subscription_constraints
Revises: 009_usage_metrics
Create Date: 2025-12-14

Changes:
- Drop unique constraint on gcp_account_id (allow multiple entitlements per account)
- Add unique constraint on gcp_entitlement_id
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "010_marketplace_subscription_constraints"
down_revision = "009_usage_metrics"
branch_labels = None
depends_on = None


def _unique_constraints(conn):
    insp = sa.inspect(conn)
    try:
        return {c.get("name") for c in insp.get_unique_constraints("organization_subscriptions")}
    except Exception:
        return set()


def upgrade():
    conn = op.get_bind()
    existing = _unique_constraints(conn)

    # Drop unique on gcp_account_id if present
    for name in [
        "organization_subscriptions_gcp_account_id_key",
        "uq_org_sub_gcp_account_id",
        "organization_subscriptions_gcp_account_id_uq",
    ]:
        if name in existing:
            op.drop_constraint(
                name,
                "organization_subscriptions",
                type_="unique",
            )
            break

    # Ensure unique constraint on gcp_entitlement_id
    if "uq_org_sub_gcp_entitlement" not in existing:
        op.create_unique_constraint(
            "uq_org_sub_gcp_entitlement",
            "organization_subscriptions",
            ["gcp_entitlement_id"],
        )


def downgrade():
    conn = op.get_bind()
    existing = _unique_constraints(conn)

    if "uq_org_sub_gcp_entitlement" in existing:
        op.drop_constraint(
            "uq_org_sub_gcp_entitlement",
            "organization_subscriptions",
            type_="unique",
        )

    # Restore uniqueness on gcp_account_id (best-effort; name may vary)
    if "organization_subscriptions_gcp_account_id_key" not in existing:
        op.create_unique_constraint(
            "organization_subscriptions_gcp_account_id_key",
            "organization_subscriptions",
            ["gcp_account_id"],
        )
