"""
Clean reset: Delete all users and organizations, create fresh admin user
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.config import settings
from src.models import User, Organization, OrganizationMember, Expense, Receipt
from src.models_billing import OrganizationSubscription
import bcrypt

def reset_database():
    print("=" * 80)
    print("DATABASE RESET - WARNING: This will delete ALL data")
    print("=" * 80)
    print()

    # Create engine and session
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Count existing data
        user_count = db.query(User).count()
        org_count = db.query(Organization).count()
        expense_count = db.query(Expense).count()

        print(f"Current data:")
        print(f"  Users: {user_count}")
        print(f"  Organizations: {org_count}")
        print(f"  Expenses: {expense_count}")
        print()

        # Confirm deletion
        print("This will DELETE ALL:")
        print("  - All users")
        print("  - All organizations")
        print("  - All expenses")
        print("  - All receipts")
        print("  - All organization memberships")
        print("  - All subscriptions")
        print()

        confirm = input("Type 'DELETE ALL' to confirm: ")
        if confirm != "DELETE ALL":
            print("Cancelled.")
            return False

        print()
        print("Deleting data...")

        # Delete in correct order (respecting foreign keys)

        # 1. Delete receipts
        receipt_count = db.query(Receipt).count()
        if receipt_count > 0:
            db.query(Receipt).delete()
            print(f"[+] Deleted {receipt_count} receipts")

        # 2. Delete expenses
        if expense_count > 0:
            db.query(Expense).delete()
            print(f"[+] Deleted {expense_count} expenses")

        # 3. Delete organization members
        member_count = db.query(OrganizationMember).count()
        if member_count > 0:
            db.query(OrganizationMember).delete()
            print(f"[+] Deleted {member_count} organization members")

        # 4. Delete subscriptions
        sub_count = db.query(OrganizationSubscription).count()
        if sub_count > 0:
            db.query(OrganizationSubscription).delete()
            print(f"[+] Deleted {sub_count} subscriptions")

        # 5. Delete organizations
        if org_count > 0:
            db.query(Organization).delete()
            print(f"[+] Deleted {org_count} organizations")

        # 6. Delete users
        if user_count > 0:
            db.query(User).delete()
            print(f"[+] Deleted {user_count} users")

        # Commit deletions
        db.commit()
        print()
        print("[+] All data deleted successfully!")
        print()

        # Create fresh admin user
        print("Creating fresh admin user...")
        print()
        print("Admin credentials:")
        print("  Username: adminfree")
        print("  Password: Admin123!")
        print()

        # Hash password
        password = "Admin123!"
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Create admin user
        import uuid
        from datetime import datetime
        from src.models import UserRole

        admin = User(
            id=str(uuid.uuid4()),
            username="adminfree",
            email="adminfree@example.com",
            hashed_password=hashed.decode('utf-8'),
            full_name="Admin User",
            role=UserRole.ADMIN,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.add(admin)
        db.commit()
        db.refresh(admin)

        print(f"[+] Admin user created!")
        print(f"    ID: {admin.id}")
        print(f"    Username: {admin.username}")
        print(f"    Email: {admin.email}")
        print(f"    Role: {admin.role}")
        print()

        print("=" * 80)
        print("RESET COMPLETE")
        print("=" * 80)
        print()
        print("Next steps:")
        print("1. Login at http://localhost:5173")
        print("   Username: adminfree")
        print("   Password: Admin123!")
        print()
        print("2. Create an organization")
        print("3. Invite an employee user (or register one)")
        print("4. Test approval workflow")
        print()

        return True

    except Exception as e:
        db.rollback()
        print(f"\n[X] Error during reset: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    try:
        success = reset_database()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[X] Fatal error: {str(e)}")
        sys.exit(1)
