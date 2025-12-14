#!/usr/bin/env python
"""Create admin1 user on FREE plan"""
import uuid
from datetime import datetime

from src.database import SessionLocal
from src.models import User, Subscription, SubscriptionTier
from src.auth import pwd_context
from src.billing.tier_limits import get_tier_limits

db = SessionLocal()

# Check if admin1 exists
user = db.query(User).filter(User.username == 'admin1').first()

if user:
    print(f"User 'admin1' already exists (ID: {user.id})")
else:
    # Create user
    user = User(
        id=str(uuid.uuid4()),
        username='admin1',
        email='admin1@test.com',
        full_name='Admin One',
        hashed_password=pwd_context.hash('AgentTest!'),
        is_active=True,
        created_at=datetime.utcnow()
    )
    db.add(user)
    db.flush()
    print(f"Created user 'admin1' (ID: {user.id})")

# Handle subscription
sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
free_limits = get_tier_limits(SubscriptionTier.FREE)

if sub:
    print(f"Updating subscription from {sub.tier.value} to FREE")
    sub.tier = SubscriptionTier.FREE
    sub.status = 'active'
else:
    print("Creating FREE subscription")
    sub = Subscription(
        id=str(uuid.uuid4()),
        user_id=user.id,
        tier=SubscriptionTier.FREE,
        status='active'
    )
    db.add(sub)

sub.max_users = free_limits.max_users
sub.max_expenses_per_month = free_limits.max_expenses_per_month
sub.max_ai_categorizations = free_limits.max_ai_categorizations
sub.max_ap2_transactions = free_limits.max_ap2_transactions

db.commit()

print("\n" + "=" * 60)
print("SUCCESS: Admin user on FREE plan created!")
print("=" * 60)
print("Username: admin1")
print("Password: AgentTest!")
print("Email: admin1@test.com")
print("Tier: FREE")
print(f"Max Organizations: {free_limits.max_organizations}")
print(f"Max Users: {free_limits.max_users}")
print(f"Max Expenses/month: {free_limits.max_expenses_per_month}")
print("=" * 60)
print("\nYou can now:")
print("1. Log in at http://localhost:5173/login")
print("2. Create your 1st organization (should succeed)")
print("3. Try to create a 2nd organization (should show upgrade prompt)")
print("=" * 60)

db.close()
