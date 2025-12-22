"""add audit log hash chain fields

Revision ID: add_audit_chain_fields
Revises: add_revocation_fields
Create Date: 2025-11-10

Adds tamper-proof hash chain fields to audit_logs table
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_audit_chain_fields'
down_revision = 'add_revocation_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Add hash chain fields to audit_logs
    op.add_column('audit_logs', sa.Column('previous_hash', sa.String(64), nullable=True))
    op.add_column('audit_logs', sa.Column('entry_hash', sa.String(64), nullable=True, server_default=''))
    op.add_column('audit_logs', sa.Column('sequence_number', sa.Integer(), nullable=True, server_default='0'))

    # Create indexes for efficient chain verification
    op.create_index('idx_audit_logs_previous_hash', 'audit_logs', ['previous_hash'])
    op.create_index('idx_audit_logs_entry_hash', 'audit_logs', ['entry_hash'])
    op.create_index('idx_audit_logs_sequence_number', 'audit_logs', ['sequence_number'])


def downgrade():
    # Remove indexes
    op.drop_index('idx_audit_logs_sequence_number', table_name='audit_logs')
    op.drop_index('idx_audit_logs_entry_hash', table_name='audit_logs')
    op.drop_index('idx_audit_logs_previous_hash', table_name='audit_logs')

    # Remove columns
    op.drop_column('audit_logs', 'sequence_number')
    op.drop_column('audit_logs', 'entry_hash')
    op.drop_column('audit_logs', 'previous_hash')
