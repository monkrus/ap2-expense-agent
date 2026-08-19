"""Direct test of subscription endpoint - bypasses browser cache"""

import sys

sys.path.insert(0, r"C:\Users\robot\Desktop\ap2-expense-agent\backend")

from src.database import SessionLocal
from src.models import User
from src.models_billing import BillingTier
from src.routes.billing_org import get_organization_subscription, get_user_organization
import json

# Get a test user
db = SessionLocal()

# Get first admin user
user = db.query(User).filter(User.role == "admin").first()

if not user:
    print("No admin user found!")
    exit(1)

print(f"Testing with user: {user.username} (ID: {user.id})")
print(f"=" * 60)

# Get organization
org_id = get_user_organization(db, user.id)
print(f"Organization ID: {org_id}")

# Call the subscription endpoint directly
result = get_organization_subscription(db=db, current_user=user)

print(f"\nAPI Response:")
print(json.dumps(result, indent=2, default=str))

print(f"\n" + "=" * 60)
print("Checking Free tier in database:")
free_tier = db.query(BillingTier).filter(BillingTier.tier_name == "free").first()
if free_tier:
    limits = (
        json.loads(free_tier.limits)
        if isinstance(free_tier.limits, str)
        else free_tier.limits
    )
    print(f"Free tier exists: {free_tier.display_name}")
    print(f"Limits: {json.dumps(limits, indent=2)}")
else:
    print("❌ Free tier NOT FOUND!")

db.close()
