"""Add usage_metrics table for GCP Marketplace metering

Revision ID: 009_usage_metrics
Revises: usage_tracking_001
Create Date: 2025-12-06

This migration adds the usage_metrics table that is referenced by
the GCPUsageReporter for aggregating usage data to report to GCP.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '009_usage_metrics'
down_revision = 'usage_tracking_001'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create usage_metrics table for GCP Marketplace metering
    """
    op.create_table(
        'usage_metrics',
        sa.Column('id', sa.String(255), primary_key=True),

        # Organization/Account identification
        sa.Column('organization_id', sa.String(255), nullable=False, index=True),
        sa.Column('account_id', sa.String(255), nullable=True),  # GCP account ID

        # Metric information
        sa.Column('metric_type', sa.String(100), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(50), nullable=False),

        # Time period
        sa.Column('period_start', sa.DateTime(), nullable=False, index=True),
        sa.Column('period_end', sa.DateTime(), nullable=False, index=True),

        # Reporting
        sa.Column('reported_at', sa.DateTime(), nullable=True),
        sa.Column('reported_to_gcp', sa.Boolean(), default=False, nullable=False),
        sa.Column('report_response', sa.JSON(), nullable=True),

        # Additional metadata
        sa.Column('additional_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),

        # Foreign key
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
    )

    # Create indexes for efficient querying
    op.create_index(
        'idx_usage_org_period',
        'usage_metrics',
        ['organization_id', 'period_start', 'period_end']
    )

    op.create_index(
        'idx_usage_reported',
        'usage_metrics',
        ['reported_to_gcp', 'period_end']
    )


def downgrade():
    """
    Drop usage_metrics table
    """
    op.drop_index('idx_usage_reported', table_name='usage_metrics')
    op.drop_index('idx_usage_org_period', table_name='usage_metrics')
    op.drop_table('usage_metrics')
