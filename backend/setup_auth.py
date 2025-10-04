#!/usr/bin/env python3
"""
Setup script for AP2 Expense Management authentication system
This script initializes the database and creates a default admin user
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.database import init_db, SessionLocal
from src.models import User, UserRole
from src.auth import AuthService
import uuid

def create_default_admin():
    """Create a default admin user if none exists"""
    db = SessionLocal()

    try:
        # Check if admin exists
        admin = db.query(User).filter(User.role == UserRole.ADMIN).first()

        if admin:
            print("✓ Admin user already exists")
            return

        # Create default admin
        admin = User(
            id=str(uuid.uuid4()),
            email="admin@ap2expense.com",
            username="admin",
            full_name="System Administrator",
            hashed_password=AuthService.hash_password("Admin123!"),
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True
        )

        db.add(admin)
        db.commit()

        print("✓ Created default admin user:")
        print(f"  Username: admin")
        print(f"  Password: Admin123!")
        print(f"  Email: admin@ap2expense.com")
        print("\n⚠️  IMPORTANT: Change the admin password immediately after first login!")

    except Exception as e:
        print(f"✗ Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()

def main():
    print("AP2 Expense Management - Authentication Setup")
    print("=" * 50)

    print("\n1. Initializing database...")
    try:
        init_db()
        print("✓ Database initialized successfully")
    except Exception as e:
        print(f"✗ Error initializing database: {e}")
        return 1

    print("\n2. Creating default admin user...")
    create_default_admin()

    print("\n" + "=" * 50)
    print("Setup completed successfully!")
    print("\nNext steps:")
    print("1. Start the backend server: uvicorn src.api:app --reload")
    print("2. Access the API docs: http://localhost:8000/docs")
    print("3. Login with the admin credentials")
    print("4. Change the admin password")

    return 0

if __name__ == "__main__":
    sys.exit(main())
