"""Script to approve some expenses for testing archiving"""
from src.database import SessionLocal
from src.models import Expense, ExpenseStatus
from datetime import datetime

db = SessionLocal()

try:
    # Get first 10 pending expenses
    pending_expenses = db.query(Expense).filter(
        Expense.status == ExpenseStatus.PENDING
    ).limit(10).all()

    print(f"Found {len(pending_expenses)} pending expenses")

    if not pending_expenses:
        print("No pending expenses to approve")
    else:
        # Approve 7 expenses, reject 3
        for i, expense in enumerate(pending_expenses):
            if i < 7:
                expense.status = ExpenseStatus.APPROVED
                expense.approved_at = datetime.utcnow()
                expense.approved_by = expense.user_id  # Self-approve for testing
                print(f"[APPROVED] expense {expense.id[:8]}... (${expense.amount})")
            else:
                expense.status = ExpenseStatus.REJECTED
                expense.rejection_reason = "Testing rejection for archive testing"
                print(f"[REJECTED] expense {expense.id[:8]}... (${expense.amount})")

        db.commit()
        print(f"\n[SUCCESS] Updated {len(pending_expenses)} expenses")
        print("7 approved, 3 rejected - ready for archive testing!")

finally:
    db.close()
