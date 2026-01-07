from src.database import SessionLocal
from src.models import Expense, User

db = SessionLocal()
try:
    # Get all expenses with user info
    expenses = db.query(Expense).all()
    users = db.query(User).all()

    print('=== USERS ===')
    for u in users:
        print(f'{u.username} ({u.id[:8]}...) - Role: {u.role}')

    print(f'\n=== EXPENSES (Total: {len(expenses)}) ===')
    for e in expenses[:10]:
        user = db.query(User).filter(User.id == e.user_id).first()
        username = user.username if user else 'Unknown'
        status_val = e.status.value if hasattr(e.status, 'value') else e.status
        print(f'{e.id[:8]}... | Owner: {username} | Status: {status_val} | ${e.amount}')
finally:
    db.close()
