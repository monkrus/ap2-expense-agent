"""Delete all users, organizations, and related data from the database"""
from src.database import SessionLocal
from src.models import (
    User,
    Organization,
    OrganizationMember,
    Subscription,
    Expense,
    Receipt
)
from src.models_billing import OrganizationSubscription

db = SessionLocal()

try:
    print("Deleting all data from database...")

    # Delete in order (respecting foreign key constraints)

    # 1. Delete receipts
    receipt_count = db.query(Receipt).count()
    db.query(Receipt).delete()
    print(f"Deleted {receipt_count} receipts")

    # 2. Delete expenses
    expense_count = db.query(Expense).count()
    db.query(Expense).delete()
    print(f"Deleted {expense_count} expenses")

    # 3. Delete organization subscriptions
    org_sub_count = db.query(OrganizationSubscription).count()
    db.query(OrganizationSubscription).delete()
    print(f"Deleted {org_sub_count} organization subscriptions")

    # 4. Delete organization members
    member_count = db.query(OrganizationMember).count()
    db.query(OrganizationMember).delete()
    print(f"Deleted {member_count} organization members")

    # 5. Delete organizations
    org_count = db.query(Organization).count()
    db.query(Organization).delete()
    print(f"Deleted {org_count} organizations")

    # 6. Delete user subscriptions
    sub_count = db.query(Subscription).count()
    db.query(Subscription).delete()
    print(f"Deleted {sub_count} user subscriptions")

    # 7. Delete users
    user_count = db.query(User).count()
    users = db.query(User).all()
    for user in users:
        print(f"  - Deleting user: {user.username} (role: {user.role.value})")
    db.query(User).delete()
    print(f"Deleted {user_count} users total")

    # Commit all deletions
    db.commit()

    print("\n" + "="*60)
    print("SUCCESS: All users, organizations, and data deleted!")
    print("="*60)
    print("Database is now clean - ready for fresh start")
    print("="*60)

except Exception as e:
    db.rollback()
    print(f"\nERROR: {e}")
    raise
finally:
    db.close()
