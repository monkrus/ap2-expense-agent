"""
Reset test user passwords to known values for automated testing

This script resets passwords for:
- admintest -> AdminTest123!
- testuser -> TestUser123!
- employee2 -> Employee2123!
- emptest -> Emptest123!
- emptest2 -> Emptest2123!
"""

from backend.src.database import SessionLocal
from backend.src.models import User
import bcrypt

def reset_test_passwords():
    """Reset passwords for test users"""
    db = SessionLocal()

    password_mapping = {
        "admintest": "AdminTest123!",
        "testuser": "TestUser123!",
        "employee2": "Employee2123!",
        "emptest": "Emptest123!",
        "emptest2": "Emptest2123!",
    }

    print("=" * 60)
    print("RESETTING TEST USER PASSWORDS")
    print("=" * 60)

    for username, new_password in password_mapping.items():
        user = db.query(User).filter(User.username == username).first()

        if not user:
            print(f"X {username}: USER NOT FOUND")
            continue

        # Hash new password
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        user.hashed_password = hashed_password.decode('utf-8')

        # Reset lockout if any
        user.failed_login_attempts = 0
        user.locked_until = None

        db.commit()

        print(f"OK {username}: Password reset to '{new_password}'")
        print(f"  Email: {user.email}")
        print(f"  Role: {user.role}")

    db.close()

    print("\n" + "=" * 60)
    print("PASSWORD RESET COMPLETE")
    print("=" * 60)
    print("\nYou can now run: python test_role_based_permissions.py")

if __name__ == "__main__":
    reset_test_passwords()
