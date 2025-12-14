"""
Create adminfree user with Free tier for testing
"""

import sys
import os
import io

# Fix Unicode encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from src.database import SessionLocal
from src.models import User, Subscription, SubscriptionTier
from src.auth import AuthService
import uuid

def create_adminfree_user():
    db = SessionLocal()

    try:
        # Check if user already exists
        existing = db.query(User).filter(User.username == "adminfree").first()
        if existing:
            print(f"❌ User 'adminfree' already exists")
            return

        # Create user
        user = User(
            id=str(uuid.uuid4()),
            username="adminfree",
            email="adminfree@test.com",
            full_name="Admin Free User",
            hashed_password=AuthService.hash_password("Testme!"),
            is_active=True,
            role="user"
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

        print(f"✅ User created successfully!")
        print(f"   Username: adminfree")
        print(f"   Password: Testme!")
        print(f"   Email: adminfree@test.com")
        print(f"   Tier: FREE")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    create_adminfree_user()
