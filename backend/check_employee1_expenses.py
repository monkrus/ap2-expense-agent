import sys
sys.path.insert(0, 'src')

from src.database import SessionLocal
from src.models import User, Expense, Receipt

db = SessionLocal()

# Find employee1
employee1 = db.query(User).filter(User.username == 'employee1').first()

if not employee1:
    print("Employee1 not found!")
    sys.exit(1)

print(f"Employee1: {employee1.username} (ID: {employee1.id[:8]}...)")

# Get all expenses for employee1
expenses = db.query(Expense).filter(Expense.user_id == employee1.id).all()
print(f"\nTotal expenses: {len(expenses)}")

if expenses:
    print("\nExpenses:")
    for i, exp in enumerate(expenses, 1):
        # Check if expense has receipts
        receipts = db.query(Receipt).filter(Receipt.expense_id == exp.id).all()
        receipt_info = f" [{len(receipts)} receipt(s)]" if receipts else ""
        print(f"  {i}. {exp.vendor}: ${exp.amount} ({exp.status}) - {exp.date}{receipt_info}")
else:
    print("\nNo expenses found!")

db.close()
