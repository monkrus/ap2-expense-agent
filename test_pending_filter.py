"""Test script to check pending expenses in the database"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Set environment variable for database
os.environ['DATABASE_URL'] = 'sqlite:///./test.db'

from backend.src.database import SessionLocal
from backend.src.models import Expense, ExpenseStatus

def check_expenses():
    db = SessionLocal()
    try:
        # Get all expenses
        all_expenses = db.query(Expense).all()
        print(f"\n=== Total Expenses in Database: {len(all_expenses)} ===\n")

        # Get pending expenses
        pending_expenses = db.query(Expense).filter(Expense.status == ExpenseStatus.PENDING).all()
        print(f"=== Pending Expenses: {len(pending_expenses)} ===\n")

        for exp in pending_expenses:
            print(f"ID: {exp.id}")
            print(f"  Amount: ${exp.amount}")
            print(f"  Vendor: {exp.vendor}")
            print(f"  Status: {exp.status.value}")
            print(f"  User ID: {exp.user_id}")
            print()

        # Check what the /expenses/all?status=pending would return
        print("\n=== Testing filter logic (status != WITHDRAWN and status == PENDING) ===\n")
        filtered = db.query(Expense).filter(
            Expense.status != ExpenseStatus.WITHDRAWN,
            Expense.status == ExpenseStatus.PENDING
        ).all()
        print(f"Would return {len(filtered)} expenses")

        # Check status values
        print("\n=== Status breakdown ===")
        for status in ExpenseStatus:
            count = db.query(Expense).filter(Expense.status == status).count()
            print(f"{status.value}: {count}")

    finally:
        db.close()

if __name__ == "__main__":
    check_expenses()
