"""Test the billing fallback fix"""
from src.database import SessionLocal
from src.models import User
from src.routes.billing_org import get_organization_subscription

db = SessionLocal()

# Get admintest user
user = db.query(User).filter(User.username == 'admintest').first()

if not user:
    print("ERROR: admintest user not found")
    exit(1)

print(f"Testing billing endpoint for user: {user.username}")
print("=" * 60)

# Simulate the API call
class FakeCurrentUser:
    def __init__(self, user):
        self.id = user.id
        self.username = user.username
        self.email = user.email

result = get_organization_subscription(db=db, current_user=FakeCurrentUser(user))

print("\nAPI Response:")
print(f"  has_subscription: {result.get('has_subscription')}")
print(f"  tier: {result.get('tier')}")
print(f"  tier_display_name: {result.get('tier_display_name')}")
print(f"  tier_price: ${result.get('tier_price', 0)}")
print(f"  status: {result.get('status')}")
print(f"  source: {result.get('source', 'organization_subscription')}")

print("\n" + "=" * 60)

if result.get('tier') == 'enterprise':
    print("✅ SUCCESS! The fallback is working correctly.")
    print("   Frontend will now show 'Enterprise' plan instead of 'Free'")
else:
    print(f"❌ FAILED! Expected 'enterprise', got '{result.get('tier')}'")

db.close()
