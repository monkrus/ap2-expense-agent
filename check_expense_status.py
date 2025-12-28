from backend.src.database import SessionLocal
from backend.src.models import Expense

db = SessionLocal()
expenses = db.query(Expense).order_by(Expense.created_at.desc()).limit(10).all()

print(f'Last 10 expenses:')
print('-' * 100)
print(f'{"ID":10} {"Vendor":25} {"Amount":10} {"Status":15} {"User"}')
print('-' * 100)

status_counts = {}
for e in expenses:
    status_str = str(e.status)
    status_counts[status_str] = status_counts.get(status_str, 0) + 1
    print(f'{e.id[:8]:10} {(e.vendor or "N/A")[:25]:25} ${e.amount:8.2f} {status_str:15} {e.user_id[:8]}...')

print()
print('Status Summary:')
for status, count in status_counts.items():
    print(f'  {status}: {count}')
    
db.close()
