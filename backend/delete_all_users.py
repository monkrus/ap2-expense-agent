"""
Delete all users from the database

WARNING: This is a destructive operation that will delete ALL users
and their associated data (expenses, organizations, etc.)
"""
from src.database import SessionLocal
from src.models import User, Organization

db = SessionLocal()

try:
    # Count current users
    total_users = db.query(User).count()
    print(f"[INFO] Found {total_users} users in database")

    if total_users == 0:
        print("[INFO] No users to delete")
        db.close()
        exit(0)

    # Get all users for logging
    all_users = db.query(User).all()
    print("\nUsers to be deleted:")
    print("-" * 60)
    for user in all_users:
        print(f"  - {user.username} ({user.email}) [ID: {user.id}]")
    print("-" * 60)

    # Delete all users (cascade will handle related records)
    deleted_count = db.query(User).delete()

    # Verify organizations are also cleaned up
    org_count = db.query(Organization).count()
    if org_count > 0:
        print(f"\n[INFO] Also deleting {org_count} organizations...")
        db.query(Organization).delete()

    # Commit the transaction
    db.commit()

    print(f"\n[SUCCESS] Deleted {deleted_count} users from the database")

    # Verify deletion
    remaining = db.query(User).count()
    print(f"[INFO] Remaining users: {remaining}")

    if remaining == 0:
        print("[SUCCESS] All users successfully deleted")
    else:
        print(f"[WARNING] {remaining} users still remain")

except Exception as e:
    db.rollback()
    print(f"\n[ERROR] Failed to delete users: {str(e)}")
    raise
finally:
    db.close()
