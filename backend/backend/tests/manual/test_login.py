#!/usr/bin/env python3
"""Test login credentials"""
import sys
sys.path.insert(0, ".")

from src.database import SessionLocal
from src.models import User
from src.auth import AuthService

db = SessionLocal()
try:
    user = db.query(User).filter(User.username == "adminfree").first()
    if user:
        password = "Testme1!"
        result = AuthService.verify_password(password, user.hashed_password)
        print(f"Username: {user.username}")
        print(f"Email: {user.email}")
        print(f"Role: {user.role}")
        print(f"Is active: {user.is_active}")
        print(f"Is verified: {user.is_verified}")
        print(f"Failed login attempts: {user.failed_login_attempts}")
        print(f"\nPassword '{password}' verification: {result}")
    else:
        print("User not found")
finally:
    db.close()
