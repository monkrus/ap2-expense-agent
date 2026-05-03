"""Add AP2 2026 protocol fields: agent identity, agent signal, UCP reference

Revision ID: ap2_2026_fields
Revises: None (standalone)
"""

from alembic import op
import sqlalchemy as sa

revision = "ap2_2026_fields"
down_revision = "add_pm_completed_at"
branch_labels = None
depends_on = None


def upgrade():
    # IntentMandate: agent identity and A2A protocol fields
    with op.batch_alter_table("intent_mandates") as batch_op:
        batch_op.add_column(
            sa.Column("agent_id", sa.String(255), nullable=True, server_default="ap2-expense-agent")
        )
        batch_op.add_column(
            sa.Column("authorization_type", sa.String(50), nullable=True, server_default="human_delegated")
        )
        batch_op.add_column(
            sa.Column("a2a_protocol_version", sa.String(20), nullable=True, server_default="1.0")
        )

    # CartMandate: UCP reference and merchant agent signature
    with op.batch_alter_table("cart_mandates") as batch_op:
        batch_op.add_column(
            sa.Column("ucp_order_id", sa.String(255), nullable=True)
        )
        batch_op.add_column(
            sa.Column("merchant_agent_signature", sa.Text(), nullable=True)
        )

    # PaymentMandate: Agent Signal for HNP risk scoring
    with op.batch_alter_table("payment_mandates") as batch_op:
        batch_op.add_column(
            sa.Column("agent_signal", sa.Text(), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("payment_mandates") as batch_op:
        batch_op.drop_column("agent_signal")

    with op.batch_alter_table("cart_mandates") as batch_op:
        batch_op.drop_column("merchant_agent_signature")
        batch_op.drop_column("ucp_order_id")

    with op.batch_alter_table("intent_mandates") as batch_op:
        batch_op.drop_column("a2a_protocol_version")
        batch_op.drop_column("authorization_type")
        batch_op.drop_column("agent_id")
