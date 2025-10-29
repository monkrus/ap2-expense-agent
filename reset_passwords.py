"""
Reset all default users' passwords to AgentTest!
"""
import sys
import os

# Change to backend directory so database path is correct
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
os.chdir(backend_dir)
sys.path.insert(0, backend_dir)

from src.database import SessionLocal
from src.seed_data import reset_default_users_passwords

def main():
    db = SessionLocal()
    try:
        print("Resetting default users' passwords to 'AgentTest!'...")
        reset_default_users_passwords(db)
        print("✅ Password reset complete!")
    finally:
        db.close()

if __name__ == "__main__":
    main()
