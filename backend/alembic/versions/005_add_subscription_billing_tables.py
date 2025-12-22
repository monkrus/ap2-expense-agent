"""Add subscription and billing tables

Revision ID: 005_add_subscription_billing
Revises: 004_add_ap2_mandates
Create Date: 2025-10-05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '005_add_subscription_billing'
down_revision = '004_add_ap2_mandates'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create enum type for subscription tiers if it doesn't exist
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'subscriptiontier')"))
    type_exists = result.scalar()

    if not type_exists:
        subscriptiontier_enum = postgresql.ENUM('starter', 'professional', 'enterprise', 'enterprise_plus', name='subscriptiontier', create_type=False)
        subscriptiontier_enum.create(conn, checkfirst=False)

    # Subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('user_id', sa.String(255), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('tier', postgresql.ENUM('starter', 'professional', 'enterprise', 'enterprise_plus', name='subscriptiontier', create_type=False), nullable=False, server_default='starter'),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),

        # Stripe integration
        sa.Column('stripe_customer_id', sa.String(255), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(255), nullable=True),
        sa.Column('stripe_price_id', sa.String(255), nullable=True),

        # Billing
        sa.Column('current_period_start', sa.DateTime, nullable=True),
        sa.Column('current_period_end', sa.DateTime, nullable=True),
        sa.Column('trial_end', sa.DateTime, nullable=True),
        sa.Column('canceled_at', sa.DateTime, nullable=True),

        # Limits
        sa.Column('max_users', sa.Integer, nullable=False, server_default='25'),
        sa.Column('max_expenses_per_month', sa.Integer, nullable=True),
        sa.Column('max_ai_categorizations', sa.Integer, nullable=True),
        sa.Column('max_ap2_transactions', sa.Integer, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, onupdate=sa.func.now())
    )

    # Usage records table
    op.create_table(
        'usage_records',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('subscription_id', sa.String(255), sa.ForeignKey('subscriptions.id'), nullable=False),
        sa.Column('user_id', sa.String(255), sa.ForeignKey('users.id'), nullable=False),

        # Usage types
        sa.Column('usage_type', sa.String(50), nullable=False),
        sa.Column('quantity', sa.Integer, nullable=False, server_default='1'),

        # Billing
        sa.Column('billable', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('fee', sa.Numeric(10, 4), nullable=True),

        # Additional data
        sa.Column('extra_data', sa.Text, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )

    # Invoices table
    op.create_table(
        'invoices',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('subscription_id', sa.String(255), sa.ForeignKey('subscriptions.id'), nullable=False),
        sa.Column('user_id', sa.String(255), sa.ForeignKey('users.id'), nullable=False),

        # Stripe integration
        sa.Column('stripe_invoice_id', sa.String(255), nullable=True),

        # Invoice details
        sa.Column('period_start', sa.DateTime, nullable=False),
        sa.Column('period_end', sa.DateTime, nullable=False),

        # Amounts
        sa.Column('subscription_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('usage_amount', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('total_amount', sa.Numeric(10, 2), nullable=False),

        # Status
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('paid_at', sa.DateTime, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, onupdate=sa.func.now())
    )

    # Add indexes
    op.create_index('ix_subscriptions_user_id', 'subscriptions', ['user_id'])
    op.create_index('ix_subscriptions_status', 'subscriptions', ['status'])
    op.create_index('ix_subscriptions_stripe_customer_id', 'subscriptions', ['stripe_customer_id'])
    op.create_index('ix_subscriptions_stripe_subscription_id', 'subscriptions', ['stripe_subscription_id'])

    op.create_index('ix_usage_records_subscription_id', 'usage_records', ['subscription_id'])
    op.create_index('ix_usage_records_user_id', 'usage_records', ['user_id'])
    op.create_index('ix_usage_records_usage_type', 'usage_records', ['usage_type'])
    op.create_index('ix_usage_records_created_at', 'usage_records', ['created_at'])

    op.create_index('ix_invoices_subscription_id', 'invoices', ['subscription_id'])
    op.create_index('ix_invoices_user_id', 'invoices', ['user_id'])
    op.create_index('ix_invoices_stripe_invoice_id', 'invoices', ['stripe_invoice_id'])
    op.create_index('ix_invoices_status', 'invoices', ['status'])

def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_invoices_status')
    op.drop_index('ix_invoices_stripe_invoice_id')
    op.drop_index('ix_invoices_user_id')
    op.drop_index('ix_invoices_subscription_id')

    op.drop_index('ix_usage_records_created_at')
    op.drop_index('ix_usage_records_usage_type')
    op.drop_index('ix_usage_records_user_id')
    op.drop_index('ix_usage_records_subscription_id')

    op.drop_index('ix_subscriptions_stripe_subscription_id')
    op.drop_index('ix_subscriptions_stripe_customer_id')
    op.drop_index('ix_subscriptions_status')
    op.drop_index('ix_subscriptions_user_id')

    # Drop tables
    op.drop_table('invoices')
    op.drop_table('usage_records')
    op.drop_table('subscriptions')

    # Drop enum type
    sa.Enum(name='subscriptiontier').drop(op.get_bind())
