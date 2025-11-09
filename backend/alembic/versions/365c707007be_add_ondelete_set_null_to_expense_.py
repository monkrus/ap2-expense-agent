"""Add ondelete SET NULL to expense foreign keys

Revision ID: 365c707007be
Revises: fa97e13a1889
Create Date: 2025-11-09 12:52:09.166073

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "365c707007be"
down_revision = "fa97e13a1889"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add ondelete SET NULL to scheduled_expenses.expense_id
    op.drop_constraint(
        "scheduled_expenses_expense_id_fkey", "scheduled_expenses", type_="foreignkey"
    )
    op.create_foreign_key(
        "scheduled_expenses_expense_id_fkey",
        "scheduled_expenses",
        "expenses",
        ["expense_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add ondelete SET NULL to expense_notifications.expense_id
    op.drop_constraint(
        "expense_notifications_expense_id_fkey",
        "expense_notifications",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "expense_notifications_expense_id_fkey",
        "expense_notifications",
        "expenses",
        ["expense_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add ondelete SET NULL to expense_notifications.template_id
    op.drop_constraint(
        "expense_notifications_template_id_fkey",
        "expense_notifications",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "expense_notifications_template_id_fkey",
        "expense_notifications",
        "recurring_expense_templates",
        ["template_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # Revert scheduled_expenses.expense_id
    op.drop_constraint(
        "scheduled_expenses_expense_id_fkey", "scheduled_expenses", type_="foreignkey"
    )
    op.create_foreign_key(
        "scheduled_expenses_expense_id_fkey",
        "scheduled_expenses",
        "expenses",
        ["expense_id"],
        ["id"],
    )

    # Revert expense_notifications.expense_id
    op.drop_constraint(
        "expense_notifications_expense_id_fkey",
        "expense_notifications",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "expense_notifications_expense_id_fkey",
        "expense_notifications",
        "expenses",
        ["expense_id"],
        ["id"],
    )

    # Revert expense_notifications.template_id
    op.drop_constraint(
        "expense_notifications_template_id_fkey",
        "expense_notifications",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "expense_notifications_template_id_fkey",
        "expense_notifications",
        "recurring_expense_templates",
        ["template_id"],
        ["id"],
    )
