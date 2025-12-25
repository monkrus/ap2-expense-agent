#!/usr/bin/env python3
"""Reset default admin password using proper seeding function"""
import sys
sys.path.insert(0, ".")

from src.database import SessionLocal
from src.seed_data import reset_default_users_passwords

db = SessionLocal()
try:
    reset_default_users_passwords(db)
    print("\nPassword reset complete!")
    print("Username: adminfree")
    print("Password: Testme1!")
finally:
    db.close()
