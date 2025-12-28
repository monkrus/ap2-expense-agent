from src.database import SessionLocal
from src.models import Expense, ExpenseStatus, User

db = SessionLocal()

# Check all pending expenses
pending = db.query(Expense).filter(Expense.status == ExpenseStatus.PENDING).all()
print(f'Total PENDING expenses in DB: {len(pending)}')

for e in pending:
    user = db.query(User).filter(User.id == e.user_id).first()
    print(f'  - ID: {e.id[:8]}...')
    print(f'    Amount: ${e.amount}')
    print(f'    User: {user.email if user else "Unknown"}')
    print(f'    Org ID: {e.organization_id}')
    print(f'    Status: {e.status.value}')
    print()

# Check all expenses
all_expenses = db.query(Expense).all()
print(f'\nTotal ALL expenses: {len(all_expenses)}')
statuses = {}
for e in all_expenses:
    status = e.status.value if hasattr(e.status, 'value') else str(e.status)
    statuses[status] = statuses.get(status, 0) + 1

print('Status breakdown:')
for status, count in statuses.items():
    print(f'  {status}: {count}')
