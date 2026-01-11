"""Quick status check of the database"""
import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from src.database import SessionLocal
from src.models import User, Organization, Expense

db = SessionLocal()

try:
    users = db.query(User).all()
    orgs = db.query(Organization).all()
    expenses = db.query(Expense).all()

    print("=" * 70)
    print("DATABASE STATUS")
    print("=" * 70)
    print()

    print(f"👥 USERS: {len(users)}")
    for user in users:
        print(f"  ✓ {user.username} ({user.email}) - Role: {user.role}")
    print()

    print(f"🏢 ORGANIZATIONS: {len(orgs)}")
    for org in orgs:
        print(f"  ✓ {org.name} (max_members: {org.max_members})")
    print()

    print(f"💰 EXPENSES: {len(expenses)}")
    for expense in expenses:
        user = db.query(User).filter(User.id == expense.user_id).first()
        print(f"  ✓ ${float(expense.amount):.2f} - {expense.vendor} ({expense.status}) by {user.username if user else 'Unknown'}")
    print()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Total Users: {len(users)}")
    print(f"  Total Organizations: {len(orgs)}")
    print(f"  Total Expenses: {len(expenses)}")
    print()

finally:
    db.close()
