"""
Create a new admin user on the Free plan for testing tier limits
"""
import sys
import os
import uuid
from datetime import datetime

# Change to backend directory
os.chdir('backend')

from src.database import SessionLocal
from src.models import User, Subscription, SubscriptionTier
from src.auth import get_password_hash

db = SessionLocal()

# Check if user already exists
existing_user = db.query(User).filter(User.username == 'admin1').first()
if existing_user:
    print(f"User 'admin1' already exists (ID: {existing_user.id})")
    print(f"Updating to ensure Free tier subscription...")
    user = existing_user
else:
    # Create new user
    hashed_password = get_password_hash("AgentTest!")

    user = User(
        id=str(uuid.uuid4()),
        username="admin1",
        email="admin1@test.com",
        full_name="Admin One",
        hashed_password=hashed_password,
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.flush()
    print(f"Created new user: admin1 (ID: {user.id})")

# Check if user has a subscription
existing_sub = db.query(Subscription).filter(
    Subscription.user_id == user.id
).first()

if existing_sub:
    print(f"Found existing subscription: {existing_sub.tier.value}")
    print(f"Updating to FREE tier...")
    existing_sub.tier = SubscriptionTier.FREE
    existing_sub.status = "active"
    existing_sub.max_users = 1
    existing_sub.max_expenses_per_month = 20
    existing_sub.max_ai_categorizations = 0
    existing_sub.max_ap2_transactions = 0
    db.commit()
    print("✓ Updated subscription to FREE tier")
else:
    # Create FREE tier subscription
    from src.billing.tier_limits import get_tier_limits

    free_limits = get_tier_limits(SubscriptionTier.FREE)
    subscription = Subscription(
        id=str(uuid.uuid4()),
        user_id=user.id,
        tier=SubscriptionTier.FREE,
        status="active",
        max_users=free_limits.max_users,
        max_expenses_per_month=free_limits.max_expenses_per_month,
        max_ai_categorizations=free_limits.max_ai_categorizations,
        max_ap2_transactions=free_limits.max_ap2_transactions,
    )
    db.add(subscription)
    db.commit()
    print("✓ Created FREE tier subscription")

print("\n" + "="*60)
print("SUCCESS: Admin user created/updated")
print("="*60)
print(f"Username: admin1")
print(f"Password: AgentTest!")
print(f"Email: admin1@test.com")
print(f"Tier: FREE")
print(f"Max Organizations: 1")
print(f"Max Users: 1")
print(f"Max Expenses/month: 20")
print("="*60)
print("\nYou can now:")
print("1. Log in with these credentials")
print("2. Create 1 organization (should succeed)")
print("3. Try to create a 2nd organization (should be blocked)")
print("="*60)

db.close()
