"""Reset all user passwords to a standard password"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from src.database import SessionLocal
from src.models import User
from src.auth import AuthService

def reset_all_passwords(new_password: str = "AgentTest!"):
    """Reset all user passwords to the specified password"""
    db = SessionLocal()
    try:
        users = db.query(User).all()

        if not users:
            print("No users found in database.")
            return

        print(f"Found {len(users)} users. Resetting all passwords to: {new_password}")
        print("-" * 80)

        hashed_password = AuthService.hash_password(new_password)

        for user in users:
            user.hashed_password = hashed_password
            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_failed_login = None

            print(f"✓ Reset password for: {user.username:<20} (email: {user.email:<30} role: {user.role})")

        db.commit()
        print("-" * 80)
        print(f"✓ Successfully reset passwords for {len(users)} users")
        print(f"  New password: {new_password}")

    except Exception as e:
        db.rollback()
        print(f"✗ Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    reset_all_passwords()
