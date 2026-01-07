"""Quick script to check and test expense archiving"""
from src.database import SessionLocal
from src.models import Expense, ExpenseStatus, User

db = SessionLocal()

try:
    # Get all expenses
    expenses = db.query(Expense).all()
    print(f'Total expenses: {len(expenses)}')

    # Count by status
    pending = db.query(Expense).filter(Expense.status == ExpenseStatus.PENDING).count()
    approved = db.query(Expense).filter(Expense.status == ExpenseStatus.APPROVED).count()
    rejected = db.query(Expense).filter(Expense.status == ExpenseStatus.REJECTED).count()
    archived = db.query(Expense).filter(Expense.is_archived == True).count()

    print(f'Pending: {pending}')
    print(f'Approved: {approved}')
    print(f'Rejected: {rejected}')
    print(f'Archived: {archived}')

    # Show archivable expenses (non-pending)
    archivable = db.query(Expense).filter(
        Expense.status != ExpenseStatus.PENDING,
        Expense.is_archived == False
    ).all()

    print(f'\nArchivable expenses (non-pending, not archived): {len(archivable)}')

    if archivable:
        print('\nFirst 5 archivable expenses:')
        for e in archivable[:5]:
            print(f'  ID: {e.id[:8]}... | Status: {e.status.value} | Amount: ${e.amount:.2f}')

    # Check users
    users = db.query(User).all()
    print(f'\nTotal users: {len(users)}')
    for u in users[:3]:
        print(f'  {u.username} ({u.email}) - Role: {u.role.value}')

finally:
    db.close()
