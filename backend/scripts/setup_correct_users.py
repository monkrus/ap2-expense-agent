"""Setup the correct test users"""
import sys
from pathlib import Path
from datetime import datetime
import uuid

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from src.database import SessionLocal
from src.models import User, UserRole
from src.auth import AuthService

def setup_correct_users():
    """Create the correct test users"""
    db = SessionLocal()
    password = "AgentTest!"

    try:
        # Delete all existing users
        existing_users = db.query(User).all()
        if existing_users:
            print(f"Deleting {len(existing_users)} existing users...")
            for user in existing_users:
                print(f"  [-] Deleting: {user.username}")
                db.delete(user)
            db.commit()
            print()

        hashed_password = AuthService.hash_password(password)

        # Create the correct test users
        correct_users = [
            {
                "username": "admintest",
                "email": "admintest@example.com",
                "full_name": "Admin Test User",
                "role": UserRole.ADMIN
            },
            {
                "username": "testuser",
                "email": "testuser@example.com",
                "full_name": "Test Manager User",
                "role": UserRole.MANAGER
            },
            {
                "username": "emptest",
                "email": "emptest@example.com",
                "full_name": "Employee Test 1",
                "role": UserRole.EMPLOYEE
            },
            {
                "username": "emptest2",
                "email": "emptest2@example.com",
                "full_name": "Employee Test 2",
                "role": UserRole.EMPLOYEE
            }
        ]

        print(f"Creating {len(correct_users)} correct users with password: {password}")
        print("-" * 80)

        for user_data in correct_users:
            user = User(
                id=str(uuid.uuid4()),
                username=user_data["username"],
                email=user_data["email"],
                full_name=user_data["full_name"],
                role=user_data["role"],
                hashed_password=hashed_password,
                is_active=True,
                is_verified=True,
                failed_login_attempts=0,
                created_at=datetime.utcnow()
            )
            db.add(user)
            print(f"[+] Created: {user.username:<15} (email: {user.email:<30} role: {user.role.value})")

        db.commit()
        print("-" * 80)
        print(f"[+] Successfully created {len(correct_users)} users")
        print(f"    Password for all users: {password}")

    except Exception as e:
        db.rollback()
        print(f"[!] Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    setup_correct_users()
