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
        "admintest": "AgentTest!",
        "testuser": "TestUser!",
        "emptest": "EmpTest!",
        "emptest2": "EmpTest2!"
    }

    for username, password in users_to_update.items():
        user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if user:
            user.hashed_password = AuthService.hash_password(password)
            db.commit()
            print(f"✅ Reset password for {username}")
        else:
            print(f"⚠️  User {username} not found")

    print("\n✅ Password reset complete!")

finally:
    db.close()
