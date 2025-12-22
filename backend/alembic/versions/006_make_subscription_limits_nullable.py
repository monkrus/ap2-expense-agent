"""make subscription limits nullable for unlimited tiers

Revision ID: 006_subscription_limits
Revises: 005_add_subscription_billing
Create Date: 2025-11-13 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006_subscription_limits'
down_revision = '005_add_subscription_billing'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Make subscription limit columns nullable to support unlimited tiers"""

    # Make max_users nullable (was NOT NULL with default 25)
    op.alter_column('subscriptions', 'max_users',
                    existing_type=sa.Integer(),
                    nullable=True,
                    existing_server_default=None)

    # Ensure other limit columns are already nullable
    # max_expenses_per_month - should already be nullable
    # max_ai_categorizations - should already be nullable
    # max_ap2_transactions - should already be nullable

    # Update existing ENTERPRISE_PLUS subscriptions to have NULL limits
    op.execute("""
        UPDATE subscriptions
        SET max_users = NULL,
            max_expenses_per_month = NULL,
            max_ai_categorizations = NULL,
            max_ap2_transactions = NULL
        WHERE tier = 'enterprise_plus'
    """)

    # Update existing ENTERPRISE subscriptions
    op.execute("""
        UPDATE subscriptions
        SET max_users = 100,
            max_expenses_per_month = NULL,
            max_ai_categorizations = NULL,
            max_ap2_transactions = NULL
        WHERE tier = 'enterprise'
    """)

    # Update existing PROFESSIONAL subscriptions
    op.execute("""
        UPDATE subscriptions
        SET max_users = 25,
            max_expenses_per_month = NULL,
            max_ai_categorizations = 2000,
            max_ap2_transactions = 50
        WHERE tier = 'professional'
    """)

    # Update existing STARTER subscriptions to correct limits
    op.execute("""
        UPDATE subscriptions
        SET max_users = 5,
            max_expenses_per_month = 50,
            max_ai_categorizations = 100,
            max_ap2_transactions = 10
        WHERE tier = 'starter'
    """)


def downgrade() -> None:
    """Revert subscription limit columns to NOT NULL with default"""

    # Set default value for any NULL max_users
    op.execute("""
        UPDATE subscriptions
        SET max_users = 25
        WHERE max_users IS NULL
    """)

    # Make max_users NOT NULL again with default
    op.alter_column('subscriptions', 'max_users',
                    existing_type=sa.Integer(),
                    nullable=False,
                    server_default='25')
