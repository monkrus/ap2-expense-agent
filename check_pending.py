import sys
sys.path.append('backend')
from src.database import SessionLocal
from src.models import Expense, ExpenseStatus

db = SessionLocal()
pending = db.query(Expense).filter(Expense.status == ExpenseStatus.PENDING).all()
print(f'Pending expenses: {len(pending)}')
for e in pending:
    print(f'  - {e.id}: {e.vendor} ${e.amount} (User: {e.user_id})')
db.close()
