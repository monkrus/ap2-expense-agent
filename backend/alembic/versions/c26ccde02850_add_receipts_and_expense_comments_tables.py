"""Add receipts and expense comments tables

Revision ID: c26ccde02850
Revises: fa97e13a1889
Create Date: 2025-11-09 13:18:31.898748

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c26ccde02850"
down_revision = "fa97e13a1889"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create receipts table
    op.create_table(
        "receipts",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("expense_id", sa.String(length=255), nullable=False),
        sa.Column("filename", sa.String(length=500), nullable=False),
        sa.Column("file_path", sa.String(length=1000), nullable=False),
        sa.Column("file_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column(
            "uploaded_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["expense_id"], ["expenses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_receipts_expense_id"), "receipts", ["expense_id"], unique=False
    )
    op.create_index(
        op.f("ix_receipts_uploaded_at"), "receipts", ["uploaded_at"], unique=False
    )

    # Create expense_comments table
    op.create_table(
        "expense_comments",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("expense_id", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["expense_id"], ["expenses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_expense_comments_created_at"),
        "expense_comments",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_expense_comments_expense_id"),
        "expense_comments",
        ["expense_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_expense_comments_user_id"),
        "expense_comments",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_expense_comments_user_id"), table_name="expense_comments")
    op.drop_index(op.f("ix_expense_comments_expense_id"), table_name="expense_comments")
    op.drop_index(op.f("ix_expense_comments_created_at"), table_name="expense_comments")
    op.drop_table("expense_comments")

    op.drop_index(op.f("ix_receipts_uploaded_at"), table_name="receipts")
    op.drop_index(op.f("ix_receipts_expense_id"), table_name="receipts")
    op.drop_table("receipts")
