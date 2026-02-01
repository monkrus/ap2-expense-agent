"""Reset all user passwords to Testme1!"""

from src.database import SessionLocal
from src.models import User
from src.auth import AuthService


def reset_all_passwords():
    """Reset all user passwords to Testme1!"""
    db = SessionLocal()
    try:
        # Get all users
        users = db.query(User).all()

        if not users:
            print("No users found in database")
            return

        print(f"Found {len(users)} users. Resetting all passwords to 'Testme1!'...\n")

        # Reset password for each user
        new_password = "Testme1!"
        updated_count = 0

        for user in users:
            user.hashed_password = AuthService.hash_password(new_password)
            # Also reset any login locks/failures
            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_failed_login = None
            user.is_active = True

            print(f"[OK] Reset password for: {user.username} ({user.email}) - Role: {user.role.value}")
            updated_count += 1

        db.commit()
        print(f"\n[SUCCESS] Reset passwords for {updated_count} users to 'Testme1!'")
        print("\nYou can now login with:")
        print("  Password: Testme1!")
        print("\nUser list:")
        for user in users:
            print(f"  - {user.username}")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error resetting passwords: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    reset_all_passwords()
