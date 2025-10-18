from backend.src.database import SessionLocal
from backend.src.models import Expense

db = SessionLocal()
try:
    expenses = db.query(Expense).all()
    print(f'Total expenses in database: {len(expenses)}\n')

    for e in expenses:
        print(f'ID: {e.id}')
        print(f'  User: {e.user_id}')
        print(f'  Amount: ${e.amount}')
        print(f'  Vendor: {e.vendor}')
        print(f'  Status: {e.status.value}')
        print(f'  Created: {e.created_at}')
        print()
finally:
    db.close()
