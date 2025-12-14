"""
Delete all users from the database
WARNING: This is destructive and cannot be undone!
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from src.database import SessionLocal
from src.models import User, Subscription, OrganizationMember, Organization, RefreshToken
from src.models import Session as UserSession

def delete_all_users():
    db = SessionLocal()

    try:
        # Count users before deletion
        user_count = db.query(User).count()
        print(f"\nFound {user_count} users to delete")

        if user_count == 0:
            print("No users to delete!")
            return

        # Delete related data first (to avoid foreign key constraints)

        # Delete refresh tokens
        token_count = db.query(RefreshToken).delete()
        print(f"Deleted {token_count} refresh tokens")

        # Delete user sessions
        session_count = db.query(UserSession).delete()
        print(f"Deleted {session_count} user sessions")

        # Delete organization members
        member_count = db.query(OrganizationMember).delete()
        print(f"Deleted {member_count} organization members")

        # Delete organizations
        org_count = db.query(Organization).delete()
        print(f"Deleted {org_count} organizations")

        # Delete subscriptions
        sub_count = db.query(Subscription).delete()
        print(f"Deleted {sub_count} subscriptions")

        # Finally delete users
        deleted_count = db.query(User).delete()
        print(f"Deleted {deleted_count} users")

        db.commit()

        print("\n" + "="*80)
        print("✓ ALL USERS AND RELATED DATA DELETED SUCCESSFULLY")
        print("="*80 + "\n")

    except Exception as e:
        db.rollback()
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    print("\n" + "="*80)
    print("WARNING: This will DELETE ALL USERS and related data!")
    print("="*80)

    delete_all_users()
