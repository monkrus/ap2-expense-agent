"""
Reset test user passwords to known values
"""

from src.database import SessionLocal
from src.models import User
from src.auth import AuthService
from sqlalchemy import select

db = SessionLocal()

try:
    # Update passwords for test users
    users_to_update = {
        "admintest": "Testme1!",
        "testuser": "Testme1!",
        "emptest": "Testme1!",
        "emptest2": "Testme1!",
        "adminfree": "AdminFree123!"
    }

    for username, password in users_to_update.items():
        user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if user:
            user.hashed_password = AuthService.hash_password(password)
            db.commit()
            print(f"[OK] Reset password for {username}")
        else:
            print(f"[WARN] User {username} not found")

    print("\n[OK] Password reset complete!")

finally:
    db.close()
