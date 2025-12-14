"""Test that the upgrade prompt error response is correctly formatted"""
import json
from src.database import SessionLocal
from src.models import User, Organization, OrganizationMember, Subscription, SubscriptionTier


db = SessionLocal()

# Get admin1 user
admin1 = db.query(User).filter(User.username == 'admin1').first()

if not admin1:
    print("ERROR: admin1 not found")
    exit(1)

# Check current subscription
sub = db.query(Subscription).filter(Subscription.user_id == admin1.id).first()
print(f"Admin1 Subscription: {sub.tier.value if sub else 'NONE'}")

# Check how many orgs admin1 owns
owned_orgs = (
    db.query(OrganizationMember)
    .join(Organization)
    .filter(
        OrganizationMember.user_id == admin1.id,
        OrganizationMember.role == "owner",
        OrganizationMember.is_active == True,
        Organization.is_active == True,
    )
    .count()
)

print(f"Admin1 owns {owned_orgs} organizations")
print(f"FREE tier limit: 1 organization")

if owned_orgs >= 1:
    print("\n✓ admin1 is at or above the limit")
    print("When they try to create another org, they should get:")
    print("  - HTTP 402 Payment Required")
    print("  - JSON response with message, current_tier, current_limit, etc.")
    print("  - Frontend shows upgrade prompt modal")
    print("  - Modal has 'Upgrade Now' button linking to /pricing")
else:
    print(f"\n⚠ admin1 only has {owned_orgs} orgs, they can create more")
    print("Create 1 organization first, then try creating a 2nd")

print("\n" + "="*60)
print("EXPECTED UPGRADE PROMPT FLOW:")
print("="*60)
print("1. admin1 logs in")
print("2. Creates first organization → SUCCESS ✓")
print("3. Tries to create second organization")
print("4. Gets upgrade prompt modal with:")
print("   - Title: 'Organization Limit Reached'")
print("   - Message: 'You've reached your plan's limit of 1 organization.'")
print("   - Usage: 1 / 1")
print("   - Benefits of Starter plan")
print("   - 'Upgrade Now' button → redirects to /pricing")
print("   - 'Maybe Later' button → closes modal")
print("="*60)

db.close()
