"""
Reset employee1 password to TempPass123! for testing
"""
from src.database import SessionLocal
from src.models import User
from src.auth import AuthService

db = SessionLocal()

try:
    # Find employee1
    user = db.query(User).filter(User.username == "employee1").first()

    if not user:
        print("[ERROR] User 'employee1' not found")
        exit(1)

    print(f"Found user: {user.username} ({user.email})")

    # Reset password
    new_password = "TempPass123!"
    user.hashed_password = AuthService.hash_password(new_password)

    db.commit()

    print(f"[SUCCESS] Password reset to: {new_password}")
    print("\nYou can now login with:")
    print(f"  Username: employee1")
    print(f"  Password: {new_password}")

finally:
    db.close()
