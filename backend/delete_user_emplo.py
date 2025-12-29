"""
Delete user 'emplo' to get back within free tier limit (2 users max)
"""
from src.database import SessionLocal
from src.models import User, OrganizationMember, Expense

db = SessionLocal()

try:
    # Find user 'emplo'
    user = db.query(User).filter(User.username == 'emplo').first()

    if not user:
        print("[INFO] User 'emplo' not found - already deleted?")
        exit(0)

    print(f"Found user: {user.username} ({user.email})")
    print(f"User ID: {user.id}")
    print()

    # Check if user has any expenses
    expense_count = db.query(Expense).filter(Expense.user_id == user.id).count()
    print(f"Expenses created by user: {expense_count}")

    # Delete organization memberships first
    memberships = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id
    ).all()

    for m in memberships:
        print(f"Deleting membership from organization: {m.organization_id}")
        db.delete(m)

    # Delete expenses if any
    if expense_count > 0:
        db.query(Expense).filter(Expense.user_id == user.id).delete()
        print(f"Deleted {expense_count} expenses")

    # Delete the user
    db.delete(user)
    db.commit()

    print()
    print(f"[SUCCESS] User '{user.username}' deleted successfully")

    # Verify remaining users
    remaining_users = db.query(User).filter(User.is_active == True).count()
    print(f"Remaining active users: {remaining_users}")

finally:
    db.close()
