from src.database import SessionLocal
from src.models import Expense, User, ExpenseStatus

db = SessionLocal()
try:
    admin = db.query(User).filter(User.username == 'adminfree').first()

    if admin:
        print(f'Admin user: {admin.username} (ID: {admin.id[:8]}...)')

        # Check expenses owned by admin
        admin_expenses = db.query(Expense).filter(Expense.user_id == admin.id).all()
        print(f'\nExpenses owned by admin: {len(admin_expenses)}')

        for e in admin_expenses:
            status_val = e.status.value if hasattr(e.status, 'value') else e.status
            print(f'  {e.id[:8]}... | Status: {status_val} | ${e.amount}')

        # Check pending expenses by anyone
        print('\n=== ALL PENDING EXPENSES ===')
        pending = db.query(Expense).filter(Expense.status == ExpenseStatus.PENDING).all()
        print(f'Total pending: {len(pending)}')

        for e in pending[:5]:
            user = db.query(User).filter(User.id == e.user_id).first()
            username = user.username if user else 'Unknown'
            print(f'  {e.id[:8]}... | Owner: {username} | ${e.amount}')

finally:
    db.close()
