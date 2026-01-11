"""Check all expenses in the database"""
import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from src.database import SessionLocal
from src.models import Expense, User

db = SessionLocal()

try:
    expenses = db.query(Expense).all()

    print("=" * 70)
    print(f"TOTAL EXPENSES IN DATABASE: {len(expenses)}")
    print("=" * 70)
    print()

    if len(expenses) == 0:
        print("No expenses found in database")
    else:
        for i, expense in enumerate(expenses, 1):
            user = db.query(User).filter(User.id == expense.user_id).first()

            print(f"Expense #{i}")
            print("-" * 70)
            print(f"  ID: {expense.id}")
            print(f"  Amount: ${float(expense.amount):.2f}")
            print(f"  Vendor: {expense.vendor}")
            print(f"  Category: {expense.category}")
            print(f"  Description: {expense.description}")
            print(f"  Status: {expense.status}")
            print(f"  User: {user.username if user else 'Unknown'} ({expense.user_id})")
            print(f"  Organization: {expense.organization_id}")
            print(f"  Auto-approved: {expense.auto_approved}")
            print(f"  Created at: {expense.created_at}")
            print()

    print("=" * 70)
finally:
    db.close()
