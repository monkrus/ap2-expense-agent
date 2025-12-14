"""
Create test users with different roles and subscription tiers
All users have password: Testme!
"""
import uuid
from datetime import datetime

from src.database import SessionLocal
from src.models import User, Subscription, SubscriptionTier, UserRole
from src.auth import pwd_context
from src.billing.tier_limits import get_tier_limits

db = SessionLocal()

# User specifications
users_to_create = [
    {
        "username": "adminfree",
        "email": "adminfree@test.com",
        "full_name": "Admin Free",
        "role": UserRole.ADMIN,
        "tier": SubscriptionTier.FREE,
    },
    {
        "username": "adminenter",
        "email": "adminenter@test.com",
        "full_name": "Admin Enterprise",
        "role": UserRole.ADMIN,
        "tier": SubscriptionTier.ENTERPRISE,
    },
    {
        "username": "user1",
        "email": "user1@test.com",
        "full_name": "User One",
        "role": UserRole.EMPLOYEE,
        "tier": SubscriptionTier.FREE,
    },
    {
        "username": "user2",
        "email": "user2@test.com",
        "full_name": "User Two",
        "role": UserRole.EMPLOYEE,
        "tier": SubscriptionTier.FREE,
    },
    {
        "username": "manager1",
        "email": "manager1@test.com",
        "full_name": "Manager One",
        "role": UserRole.MANAGER,
        "tier": SubscriptionTier.FREE,
    },
    {
        "username": "acc1",
        "email": "acc1@test.com",
        "full_name": "Accountant One",
        "role": UserRole.ACCOUNTANT,
        "tier": SubscriptionTier.FREE,
    },
]

PASSWORD = "Testme!"
hashed_password = pwd_context.hash(PASSWORD)

print("="*80)
print("Creating Test Users")
print("="*80)

created_users = []

for user_spec in users_to_create:
    # Check if user already exists
    existing = db.query(User).filter(User.username == user_spec["username"]).first()
    if existing:
        print(f"\nUser '{user_spec['username']}' already exists - skipping")
        continue

    # Create user
    user = User(
        id=str(uuid.uuid4()),
        username=user_spec["username"],
        email=user_spec["email"],
        full_name=user_spec["full_name"],
        hashed_password=hashed_password,
        role=user_spec["role"],
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.flush()

    # Get tier limits
    tier_limits = get_tier_limits(user_spec["tier"])

    # Create subscription
    subscription = Subscription(
        id=str(uuid.uuid4()),
        user_id=user.id,
        tier=user_spec["tier"],
        status="active",
        max_users=tier_limits.max_users,
        max_expenses_per_month=tier_limits.max_expenses_per_month,
        max_ai_categorizations=tier_limits.max_ai_categorizations,
        max_ap2_transactions=tier_limits.max_ap2_transactions,
    )
    db.add(subscription)

    created_users.append({
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "tier": user_spec["tier"].value,
        "user_id": user.id,
    })

    print(f"\nCreated: {user.username}")
    print(f"  Email: {user.email}")
    print(f"  Role: {user.role.value.upper()}")
    print(f"  Tier: {user_spec['tier'].value.upper()}")

db.commit()

print("\n" + "="*80)
print("SUCCESS: All Users Created!")
print("="*80)
print(f"\nTotal users created: {len(created_users)}")
print(f"Password for all users: {PASSWORD}")
print("\n" + "="*80)
print("USER SUMMARY")
print("="*80)

# Print summary table
print(f"\n{'Username':<15} {'Email':<25} {'Role':<12} {'Tier':<15} {'Max Orgs'}")
print("-"*80)

for u in created_users:
    tier_limits = get_tier_limits(SubscriptionTier[u["tier"].upper()])
    print(f"{u['username']:<15} {u['email']:<25} {u['role']:<12} {u['tier']:<15} {tier_limits.max_organizations}")

print("\n" + "="*80)
print("ADMIN USERS (can access admin portal)")
print("="*80)
admins = [u for u in created_users if u["role"] == "admin"]
for admin in admins:
    tier_limits = get_tier_limits(SubscriptionTier[admin["tier"].upper()])
    print(f"\nUsername: {admin['username']}")
    print(f"  Password: {PASSWORD}")
    print(f"  Tier: {admin['tier'].upper()}")
    print(f"  Max Organizations: {tier_limits.max_organizations}")
    print(f"  Max Users: {tier_limits.max_users}")
    print(f"  Max Expenses/month: {tier_limits.max_expenses_per_month}")

print("\n" + "="*80)
print("TEST SCENARIOS")
print("="*80)
print("\n1. FREE TIER LIMIT TEST:")
print("   - Log in as: adminfree / Testme!")
print("   - Create 1 organization -> Should succeed")
print("   - Try to create 2nd organization -> Should show upgrade prompt")
print("\n2. ENTERPRISE TIER TEST:")
print("   - Log in as: adminenter / Testme!")
print("   - Create multiple organizations -> Should succeed (up to 25)")
print("\n3. ROLE-BASED ACCESS TEST:")
print("   - manager1: Can manage expenses, approve")
print("   - acc1: Can view financial data")
print("   - user1, user2: Basic employee access")

print("\n" + "="*80)

db.close()
