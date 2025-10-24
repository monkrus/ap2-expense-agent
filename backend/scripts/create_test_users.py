"""Create test users with standard password"""
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

def create_test_users():
    """Create test users with AgentTest! password"""
    db = SessionLocal()
    password = "AgentTest!"

    try:
        # Check if users already exist
        existing = db.query(User).count()
        if existing > 0:
            print(f"Database already has {existing} users. Skipping user creation.")
            return

        hashed_password = AuthService.hash_password(password)

        # Create test users
        test_users = [
            {
                "username": "admin",
                "email": "admin@example.com",
                "full_name": "Admin User",
                "role": UserRole.ADMIN
            },
            {
                "username": "manager",
                "email": "manager@example.com",
                "full_name": "Manager User",
                "role": UserRole.MANAGER
            },
            {
                "username": "employee",
                "email": "employee@example.com",
                "full_name": "Employee User",
                "role": UserRole.EMPLOYEE
            },
            {
                "username": "john",
                "email": "john@example.com",
                "full_name": "John Smith",
                "role": UserRole.EMPLOYEE
            },
            {
                "username": "jane",
                "email": "jane@example.com",
                "full_name": "Jane Doe",
                "role": UserRole.EMPLOYEE
            }
        ]

        print(f"Creating {len(test_users)} test users with password: {password}")
        print("-" * 80)

        for user_data in test_users:
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
            print(f"[+] Created: {user.username:<15} (email: {user.email:<25} role: {user.role.value})")

        db.commit()
        print("-" * 80)
        print(f"[+] Successfully created {len(test_users)} test users")
        print(f"    Password for all users: {password}")

    except Exception as e:
        db.rollback()
        print(f"[!] Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_test_users()
