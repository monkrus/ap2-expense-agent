import sys
sys.path.insert(0, 'backend')

from src.database import SessionLocal
from src.models import User, Organization, OrganizationMember, Subscription
from src.models_billing import OrganizationSubscription

db = SessionLocal()

user = db.query(User).filter(User.username == 'admintest').first()

if not user:
    print("User 'admintest' not found")
    sys.exit(1)

print(f'User: {user.username} (ID: {user.id})')

# Check user-level subscription
user_sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
print(f'\nUser-level Subscription: {user_sub.tier.value if user_sub else "NONE"}')

# Check organizations
members = db.query(OrganizationMember).filter(
    OrganizationMember.user_id == user.id,
    OrganizationMember.is_active == True
).all()

print(f'\nOrganizations ({len(members)} total):')
for m in members:
    org = db.query(Organization).filter(Organization.id == m.organization_id).first()
    if org:
        org_sub = db.query(OrganizationSubscription).filter(
            OrganizationSubscription.organization_id == m.organization_id,
            OrganizationSubscription.status == 'active'
        ).first()
        print(f'  Org: {org.name} (ID: {org.id})')
        print(f'    Role: {m.role.value}')
        print(f'    OrganizationSubscription: {org_sub.tier_name if org_sub else "NONE"}')
        print()

db.close()
