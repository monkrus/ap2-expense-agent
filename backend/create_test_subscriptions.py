"""
Create test subscriptions for test users
"""
import sys
sys.path.insert(0, '/home/user/ap2-expense-agent/backend')

from src.database import get_db
from src.models import User, SubscriptionTier
from src.billing import SubscriptionService

def create_subscriptions():
    db = next(get_db())
    service = SubscriptionService(db)

    # Get all test users
    users = db.query(User).all()

    print("Creating test subscriptions...\n")

    for user in users:
        # Check if user already has subscription
        existing = service.get_active_subscription(user.id)

        if existing:
            print(f"✓ {user.email} already has subscription (tier: {existing.tier.value})")
            continue

        # Create subscription based on role
        tier = SubscriptionTier.STARTER
        if user.role.value == 'admin':
            tier = SubscriptionTier.ENTERPRISE
        elif user.role.value == 'manager':
            tier = SubscriptionTier.PROFESSIONAL

        subscription = service.create_subscription(
            user_id=user.id,
            tier=tier,
            trial_days=14
        )

        print(f"✓ Created {tier.value} subscription for {user.email}")
        print(f"  Subscription ID: {subscription.id}")
        print(f"  Status: {subscription.status}")
        print(f"  Trial ends: {subscription.trial_end}")
        print()

    print("All test subscriptions created!")

if __name__ == "__main__":
    create_subscriptions()
