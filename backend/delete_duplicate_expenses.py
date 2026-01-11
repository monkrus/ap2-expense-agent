"""Delete duplicate expenses - keep only the first one"""
import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from src.database import SessionLocal
from src.models import Expense

db = SessionLocal()

try:
    # Get all expenses
    expenses = db.query(Expense).order_by(Expense.created_at).all()

    print("=" * 70)
    print(f"Total expenses: {len(expenses)}")
    print("=" * 70)
    print()

    if len(expenses) <= 1:
        print("Only 1 or fewer expenses - nothing to delete")
    else:
        # Keep the first expense, delete the rest
        keep = expenses[0]
        delete = expenses[1:]

        print(f"Keeping expense #1:")
        print(f"  ID: {keep.id}")
        print(f"  Amount: ${float(keep.amount):.2f} - {keep.vendor}")
        print(f"  Created: {keep.created_at}")
        print()

        print(f"Deleting {len(delete)} duplicate expenses:")
        for i, expense in enumerate(delete, 2):
            print(f"  Expense #{i}: {expense.id} (${float(expense.amount):.2f} - {expense.vendor})")
            db.delete(expense)

        db.commit()

        print()
        print("=" * 70)
        print(f"✅ Deleted {len(delete)} duplicate expenses")
        print("=" * 70)

        # Verify
        remaining = db.query(Expense).count()
        print(f"Remaining expenses: {remaining}")

finally:
    db.close()
