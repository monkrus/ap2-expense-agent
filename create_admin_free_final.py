"""
Create adminfree user (admin role, free tier)
Username: adminfree
Password: Testme1!
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from src.database import SessionLocal
from src.models import User, Subscription, SubscriptionTier, UserRole
from src.auth import AuthService
import uuid

db = SessionLocal()

try:
    # Check if user exists
    existing = db.query(User).filter(User.username == "adminfree").first()
    if existing:
        print(f"User 'adminfree' already exists!")
        db.close()
        sys.exit(1)

    # Create admin user
    user = User(
        id=str(uuid.uuid4()),
        username="adminfree",
        email="adminfree@test.com",
        full_name="Admin Free User",
        hashed_password=AuthService.hash_password("Testme1!"),
        is_active=True,
        role=UserRole.ADMIN  # Admin role
    )
    db.add(user)
    db.flush()

    # Create Free tier subscription
    subscription = Subscription(
        id=str(uuid.uuid4()),
        user_id=user.id,
        tier=SubscriptionTier.FREE,
        status="active",
        max_users=1,
        max_expenses_per_month=20,
        max_ai_categorizations=0,
        max_ap2_transactions=0
    )
    db.add(subscription)

    db.commit()

    print("SUCCESS: User created!")
    print(f"Username: adminfree")
    print(f"Password: Testme1!")
    print(f"Email: adminfree@test.com")
    print(f"Role: ADMIN")
    print(f"Tier: FREE")

except Exception as e:
    db.rollback()
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
