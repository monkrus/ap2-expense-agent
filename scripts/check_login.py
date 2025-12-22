"""
Script to check if all users can login with the same password.
"""
import sys
import os
import sqlite3
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from src.models import User
from werkzeug.security import check_password_hash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Database path
db_path = backend_dir / "expenses.db"
if not db_path.exists():
    print(f"Error: Database not found at {db_path}")
    sys.exit(1)

# Create database session
engine = create_engine(f"sqlite:///{db_path}")
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# Test password
test_password = "Testme1!"

print("=" * 80)
print("CHECKING USER LOGINS")
print("=" * 80)
print(f"Testing password: {test_password}")
print()

try:
    users = db.query(User).all()

    if not users:
        print("No users found in database!")
        sys.exit(0)

    print(f"Found {len(users)} users in database")
    print()

    success_count = 0
    fail_count = 0

    for user in users:
        can_login = check_password_hash(user.password_hash, test_password)
        status = "✓ CAN LOGIN" if can_login else "✗ CANNOT LOGIN"

        print(f"{user.username:<20} {user.email:<30} {user.role.value if hasattr(user.role, 'value') else str(user.role):<15} {status}")

        if can_login:
            success_count += 1
        else:
            fail_count += 1

    print()
    print("=" * 80)
    print(f"Summary: {success_count} users can login, {fail_count} users cannot login")
    print("=" * 80)

finally:
    db.close()
