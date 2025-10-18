"""
Update user email addresses in the database.
"""

import sys
import os

# Add the parent directory to the path so we can import from src
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database import get_db, engine
from src.models import User, Base
from sqlalchemy.orm import Session

def update_user_emails():
    """Update email addresses for specific users."""

    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    # Get database session
    db = next(get_db())

    try:
        # Email mappings: username -> new email
        email_updates = {
            'admintest': 'sergeigodev@gmail.com',    # admin
            'testuser': 'naftalinka@gmail.com',      # manager
            'emptest': 'sergeisqa@gmail.com',        # employee
            'employee2': 'mutabortrim@gmail.com'     # employee (emptest2)
        }

        updated_count = 0

        for username, new_email in email_updates.items():
            # Find user by username
            user = db.query(User).filter(User.username == username).first()

            if user:
                old_email = user.email
                user.email = new_email
                db.commit()
                print(f"[OK] Updated {username}: {old_email} -> {new_email}")
                updated_count += 1
            else:
                print(f"[ERROR] User not found: {username}")

        print(f"\n{updated_count} email(s) updated successfully!")

        # Display all users for verification
        print("\n--- All Users ---")
        users = db.query(User).all()
        for user in users:
            print(f"{user.username:20} | {user.email:35} | {user.role}")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    update_user_emails()
