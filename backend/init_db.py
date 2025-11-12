#!/usr/bin/env python
"""Initialize database with tables and seed data"""
import sys
sys.path.insert(0, '/home/user/ap2-expense-agent/backend')

from src.database import engine, Base, SessionLocal
from src import models
from src.seed_data import seed_default_users

if __name__ == "__main__":
    # Create all tables
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")

    # Seed with default users
    print("\nSeeding default users...")
    db = SessionLocal()
    try:
        stats = seed_default_users(db)
        print(f"✅ Seed completed: {stats}")
    finally:
        db.close()

    print("\n✅ Database initialization complete!")
