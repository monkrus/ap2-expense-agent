"""Add usage tracking tables for GCP Marketplace metering

Revision ID: usage_tracking_001
Revises: [previous_revision]
Create Date: 2025-12-05

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'usage_tracking_001'
down_revision = None  # TODO: Update with actual previous revision
branch_labels = None
depends_on = None


def upgrade():
    """
    Create tables for usage tracking and metering
    """

    # Create usage_events table
    op.create_table(
        'usage_events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('occurred_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),

        # Foreign key to organizations
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),

        # Indexes for performance
        sa.Index('idx_usage_events_org_id', 'organization_id'),
        sa.Index('idx_usage_events_event_type', 'event_type'),
        sa.Index('idx_usage_events_occurred_at', 'occurred_at'),
        sa.Index('idx_usage_events_org_occurred', 'organization_id', 'occurred_at'),
    )

    # Create billing_events table (for overage tracking)
    op.create_table(
        'billing_events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('occurred_at', sa.DateTime(), nullable=False),
        sa.Column('processed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),

        # Foreign key to organizations
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),

        # Indexes
        sa.Index('idx_billing_events_org_id', 'organization_id'),
        sa.Index('idx_billing_events_occurred_at', 'occurred_at'),
        sa.Index('idx_billing_events_processed', 'processed'),
    )

    # Add GCP-specific columns to organization_subscriptions table (if not exist)
    # Check if columns already exist to make migration idempotent
    connection = op.get_bind()

    # Check if gcp_entitlement_features column exists
    result = connection.execute(sa.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name='organization_subscriptions'
        AND column_name='gcp_entitlement_features'
    """))

    if not result.fetchone():
        op.add_column(
            'organization_subscriptions',
            sa.Column('gcp_entitlement_features', sa.JSON(), nullable=True)
        )

    # Check if gcp_entitlement_state column exists
    result = connection.execute(sa.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name='organization_subscriptions'
        AND column_name='gcp_entitlement_state'
    """))

    if not result.fetchone():
        op.add_column(
            'organization_subscriptions',
            sa.Column('gcp_entitlement_state', sa.String(50), nullable=True)
        )

    # Create usage_reporting_log table (track what we've reported to GCP)
    op.create_table(
        'usage_reporting_log',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), nullable=False),
        sa.Column('report_date', sa.Date(), nullable=False),
        sa.Column('usage_data', sa.JSON(), nullable=False),
        sa.Column('reported_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),  # 'success', 'failed', 'pending'
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),

        # Foreign key
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),

        # Unique constraint to prevent duplicate reports
        sa.UniqueConstraint('organization_id', 'report_date', name='uq_usage_report'),

        # Indexes
        sa.Index('idx_usage_reporting_log_org_id', 'organization_id'),
        sa.Index('idx_usage_reporting_log_date', 'report_date'),
        sa.Index('idx_usage_reporting_log_status', 'status'),
    )

    print("✅ Created usage tracking tables")


def downgrade():
    """
    Drop usage tracking tables
    """

    # Drop tables in reverse order
    op.drop_table('usage_reporting_log')
    op.drop_table('billing_events')
    op.drop_table('usage_events')

    # Remove added columns
    op.drop_column('organization_subscriptions', 'gcp_entitlement_features')
    op.drop_column('organization_subscriptions', 'gcp_entitlement_state')

    print("✅ Dropped usage tracking tables")
