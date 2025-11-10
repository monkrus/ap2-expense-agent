"""add mandate revocation fields

Revision ID: add_revocation_fields
Revises: c26ccde02850
Create Date: 2025-11-10

Adds revocation fields to AP2 mandate tables for GDPR compliance
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_revocation_fields'
down_revision = 'c26ccde02850'
branch_labels = None
depends_on = None


def upgrade():
    # Add revocation fields to intent_mandates
    op.add_column('intent_mandates', sa.Column('revoked_at', sa.DateTime(), nullable=True))
    op.add_column('intent_mandates', sa.Column('revocation_reason', sa.Text(), nullable=True))

    # Add revocation fields to cart_mandates
    op.add_column('cart_mandates', sa.Column('revoked_at', sa.DateTime(), nullable=True))
    op.add_column('cart_mandates', sa.Column('revocation_reason', sa.Text(), nullable=True))

    # Add revocation fields to payment_mandates
    op.add_column('payment_mandates', sa.Column('revoked_at', sa.DateTime(), nullable=True))
    op.add_column('payment_mandates', sa.Column('revocation_reason', sa.Text(), nullable=True))

    # Create indexes for revocation queries
    op.create_index('idx_intent_mandates_revoked_at', 'intent_mandates', ['revoked_at'])
    op.create_index('idx_cart_mandates_revoked_at', 'cart_mandates', ['revoked_at'])
    op.create_index('idx_payment_mandates_revoked_at', 'payment_mandates', ['revoked_at'])


def downgrade():
    # Remove indexes
    op.drop_index('idx_payment_mandates_revoked_at', table_name='payment_mandates')
    op.drop_index('idx_cart_mandates_revoked_at', table_name='cart_mandates')
    op.drop_index('idx_intent_mandates_revoked_at', table_name='intent_mandates')

    # Remove columns
    op.drop_column('payment_mandates', 'revocation_reason')
    op.drop_column('payment_mandates', 'revoked_at')
    op.drop_column('cart_mandates', 'revocation_reason')
    op.drop_column('cart_mandates', 'revoked_at')
    op.drop_column('intent_mandates', 'revocation_reason')
    op.drop_column('intent_mandates', 'revoked_at')
