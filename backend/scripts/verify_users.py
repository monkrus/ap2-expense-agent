"""Verify all users and test password login"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from src.database import SessionLocal
from src.models import User
from src.auth import AuthService

def verify_users():
    """Verify all users exist and can authenticate"""
    db = SessionLocal()
    password = "AgentTest!"

    try:
        users = db.query(User).all()

        if not users:
            print("[!] No users found in database!")
            return

        print(f"Found {len(users)} users in database:")
        print("-" * 80)

        for user in users:
            # Test password verification
            password_valid = AuthService.verify_password(password, user.hashed_password)
            status = "[OK]" if password_valid else "[FAIL]"

            print(f"{status} {user.username:<15} | {user.email:<30} | {user.role.value:<10} | Active: {user.is_active}")

        print("-" * 80)
        print(f"All users should be able to login with password: {password}")

    except Exception as e:
        print(f"[!] Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    verify_users()
