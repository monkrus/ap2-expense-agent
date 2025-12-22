"""add marketplace account, entitlement, and webhook idempotency tables

Revision ID: 007_marketplace_tables
Revises: 006_subscription_limits
Create Date: 2025-12-05
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "007_marketplace_tables"
down_revision = "006_subscription_limits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "marketplace_accounts",
        sa.Column("id", sa.String(length=255), primary_key=True),
        sa.Column("organization_id", sa.String(length=255), nullable=False),
        sa.Column("account_id", sa.String(length=255), nullable=False),
        sa.Column("consumer_id", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="linked",
        ),
        sa.Column(
            "linked_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.Column("account_metadata", sa.JSON(), nullable=True),
    )
    op.create_index(
        "ix_marketplace_accounts_org",
        "marketplace_accounts",
        ["organization_id"],
    )
    op.create_index(
        "ix_marketplace_accounts_account",
        "marketplace_accounts",
        ["account_id"],
        unique=True,
    )
    op.create_index(
        "ix_marketplace_accounts_consumer",
        "marketplace_accounts",
        ["consumer_id"],
        unique=True,
    )

    op.create_table(
        "marketplace_entitlements",
        sa.Column("id", sa.String(length=255), primary_key=True),
        sa.Column("entitlement_id", sa.String(length=255), nullable=False),
        sa.Column("account_id", sa.String(length=255), nullable=True),
        sa.Column("consumer_id", sa.String(length=255), nullable=True),
        sa.Column("organization_id", sa.String(length=255), nullable=False),
        sa.Column("plan", sa.String(length=100), nullable=False),
        sa.Column(
            "state",
            sa.String(length=50),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("current_period_end", sa.DateTime(), nullable=True),
        sa.Column("trial_start", sa.DateTime(), nullable=True),
        sa.Column("trial_end", sa.DateTime(), nullable=True),
        sa.Column("grace_start", sa.DateTime(), nullable=True),
        sa.Column("grace_end", sa.DateTime(), nullable=True),
        sa.Column("last_event_at", sa.DateTime(), nullable=True),
        sa.Column("entitlement_metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_marketplace_entitlements_org",
        "marketplace_entitlements",
        ["organization_id"],
    )
    op.create_index(
        "ix_marketplace_entitlements_state",
        "marketplace_entitlements",
        ["state"],
    )
    op.create_index(
        "ix_marketplace_entitlements_entitlement",
        "marketplace_entitlements",
        ["entitlement_id"],
        unique=True,
    )
    op.create_index(
        "ix_marketplace_entitlements_account",
        "marketplace_entitlements",
        ["account_id"],
    )
    op.create_index(
        "ix_marketplace_entitlements_consumer",
        "marketplace_entitlements",
        ["consumer_id"],
    )

    op.create_table(
        "marketplace_webhook_events",
        sa.Column("id", sa.String(length=255), primary_key=True),
        sa.Column("handler", sa.String(length=100), nullable=False),
        sa.Column("dedupe_key", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_marketplace_event_dedupe",
        "marketplace_webhook_events",
        ["handler", "dedupe_key"],
    )
    op.create_index(
        "ix_marketplace_webhook_handler_status",
        "marketplace_webhook_events",
        ["handler", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_marketplace_webhook_handler_status",
        table_name="marketplace_webhook_events",
    )
    op.drop_constraint(
        "uq_marketplace_event_dedupe",
        "marketplace_webhook_events",
        type_="unique",
    )
    op.drop_table("marketplace_webhook_events")

    op.drop_index(
        "ix_marketplace_entitlements_consumer",
        table_name="marketplace_entitlements",
    )
    op.drop_index(
        "ix_marketplace_entitlements_account",
        table_name="marketplace_entitlements",
    )
    op.drop_index(
        "ix_marketplace_entitlements_entitlement",
        table_name="marketplace_entitlements",
    )
    op.drop_index(
        "ix_marketplace_entitlements_state",
        table_name="marketplace_entitlements",
    )
    op.drop_index(
        "ix_marketplace_entitlements_org",
        table_name="marketplace_entitlements",
    )
    op.drop_table("marketplace_entitlements")

    op.drop_index(
        "ix_marketplace_accounts_consumer",
        table_name="marketplace_accounts",
    )
    op.drop_index(
        "ix_marketplace_accounts_account",
        table_name="marketplace_accounts",
    )
    op.drop_index("ix_marketplace_accounts_org", table_name="marketplace_accounts")
    op.drop_table("marketplace_accounts")
