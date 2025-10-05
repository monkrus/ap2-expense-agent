"""Add AP2 mandate storage tables

Revision ID: 004_add_ap2_mandates
Revises: bd28e09de1fa
Create Date: 2025-10-05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '004_add_ap2_mandates'
down_revision = 'bd28e09de1fa'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Intent Mandates table
    op.create_table(
        'intent_mandates',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('user_id', sa.String(255), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('constraints', sa.JSON, nullable=False),
        sa.Column('timestamp', sa.DateTime, nullable=False),
        sa.Column('expiration', sa.DateTime, nullable=False),
        sa.Column('signature', sa.Text, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, onupdate=sa.func.now())
    )

    # Cart Mandates table
    op.create_table(
        'cart_mandates',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('intent_mandate_id', sa.String(255), sa.ForeignKey('intent_mandates.id'), nullable=False),
        sa.Column('items', sa.JSON, nullable=False),
        sa.Column('total', sa.Numeric(10, 2), nullable=False),
        sa.Column('merchant', sa.String(255), nullable=False),
        sa.Column('timestamp', sa.DateTime, nullable=False),
        sa.Column('user_signature', sa.Text, nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, onupdate=sa.func.now())
    )

    # Payment Mandates table
    op.create_table(
        'payment_mandates',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('cart_mandate_id', sa.String(255), sa.ForeignKey('cart_mandates.id'), nullable=False),
        sa.Column('payment_method', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('audit_trail', sa.JSON, nullable=False),
        sa.Column('timestamp', sa.DateTime, nullable=False),
        sa.Column('payment_processor_response', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, onupdate=sa.func.now())
    )

    # Add indexes
    op.create_index('ix_intent_mandates_user_id', 'intent_mandates', ['user_id'])
    op.create_index('ix_intent_mandates_status', 'intent_mandates', ['status'])
    op.create_index('ix_cart_mandates_intent_id', 'cart_mandates', ['intent_mandate_id'])
    op.create_index('ix_payment_mandates_cart_id', 'payment_mandates', ['cart_mandate_id'])
    op.create_index('ix_payment_mandates_status', 'payment_mandates', ['status'])

def downgrade() -> None:
    op.drop_index('ix_payment_mandates_status')
    op.drop_index('ix_payment_mandates_cart_id')
    op.drop_index('ix_cart_mandates_intent_id')
    op.drop_index('ix_intent_mandates_status')
    op.drop_index('ix_intent_mandates_user_id')
    op.drop_table('payment_mandates')
    op.drop_table('cart_mandates')
    op.drop_table('intent_mandates')
