#!/usr/bin/env python3
"""Reset password for a user"""
import sys
sys.path.insert(0, ".")

from src.database import SessionLocal
from src.models import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

db = SessionLocal()
try:
    user = db.query(User).filter(User.username == "adminfree").first()
    if user:
        user.hashed_password = pwd_context.hash("Testme1!")
        db.commit()
        print(f"Password reset for user: {user.username}")
        print(f"Email: {user.email}")
        print(f"Role: {user.role}")
        print(f"New password: Testme1!")
    else:
        print("User 'adminfree' not found")
finally:
    db.close()
