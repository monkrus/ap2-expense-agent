"""
Delete ALL users from the database
WARNING: This is destructive and irreversible!
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from src.database import SessionLocal
# Import all models to avoid relationship issues
import src.models
import src.models_billing
import src.models_approval
from src.models import User, Organization, OrganizationMember, Session as UserSession


def delete_all_users():
    """Delete all users and related data from database"""
    db = SessionLocal()
    try:
        # Get counts before deletion
        user_count = db.query(User).count()
        session_count = db.query(UserSession).count()
        member_count = db.query(OrganizationMember).count()
        org_count = db.query(Organization).count()

        print(f"\n=== BEFORE DELETION ===")
        print(f"Users: {user_count}")
        print(f"Sessions: {session_count}")
        print(f"Organization Members: {member_count}")
        print(f"Organizations: {org_count}")

        if user_count == 0:
            print("\nNo users to delete.")
            return

        # Confirm deletion
        print(f"\nWARNING: About to delete {user_count} users and ALL related data!")
        response = input("Type 'DELETE ALL' to confirm: ")

        if response != "DELETE ALL":
            print("Deletion cancelled.")
            return

        # Delete in correct order (foreign key constraints)
        print("\nDeleting...")

        # 1. Delete sessions
        deleted_sessions = db.query(UserSession).delete()
        print(f"[OK] Deleted {deleted_sessions} sessions")

        # 2. Delete organization members
        deleted_members = db.query(OrganizationMember).delete()
        print(f"[OK] Deleted {deleted_members} organization members")

        # 3. Delete organizations
        deleted_orgs = db.query(Organization).delete()
        print(f"[OK] Deleted {deleted_orgs} organizations")

        # 4. Delete users
        deleted_users = db.query(User).delete()
        print(f"[OK] Deleted {deleted_users} users")

        db.commit()

        # Verify deletion
        remaining_users = db.query(User).count()
        print(f"\n=== AFTER DELETION ===")
        print(f"Users remaining: {remaining_users}")
        print(f"\n[SUCCESS] All users deleted successfully!")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Error deleting users: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    delete_all_users()
