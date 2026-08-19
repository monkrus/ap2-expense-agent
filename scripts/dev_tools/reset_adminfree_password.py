"""
Reset adminfree user password
"""
import sys
sys.path.append("backend/src")

from backend.src.database import SessionLocal
from backend.src.models import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

db = SessionLocal()

try:
    user = db.query(User).filter(User.username == "adminfree").first()

    if not user:
        print("[ERROR] User 'adminfree' not found")
        exit(1)

    # Reset password to AdminFree123!
    new_password = "AdminFree123!"
    user.hashed_password = pwd_context.hash(new_password)

    db.commit()

    print(f"[OK] Password reset for user: {user.username}")
    print(f"     New password: {new_password}")
    print(f"     Email: {user.email}")

finally:
    db.close()
