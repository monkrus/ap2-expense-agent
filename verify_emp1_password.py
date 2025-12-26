"""Verify which password works for emp1"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from src.database import SessionLocal
from src.models import User
from src.auth import AuthService

db = SessionLocal()
user = db.query(User).filter(User.username == "emp1").first()

if not user:
    print("User emp1 not found!")
    sys.exit(1)

print("Testing passwords for emp1:")
test_passwords = ["Test!!!", "Testme!!!", "Password123"]

for pwd in test_passwords:
    result = AuthService.verify_password(pwd, user.hashed_password)
    status = "[CORRECT]" if result else "[WRONG]"
    print(f"  {status} {pwd}")

db.close()
