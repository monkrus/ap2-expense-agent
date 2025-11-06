#!/usr/bin/env python
"""Run database seed script"""
import sys
sys.path.insert(0, '/home/user/ap2-expense-agent/backend')

from src.database import SessionLocal
from src.seed_data import seed_default_users

if __name__ == "__main__":
    db = SessionLocal()
    try:
        stats = seed_default_users(db)
        print(f"✅ Seed completed: {stats}")
    finally:
        db.close()
