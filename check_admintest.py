import sys
sys.path.insert(0, 'backend')

from backend.src.database import SessionLocal
from backend.src.models import Organization, OrganizationMember, User

db = SessionLocal()

user = db.query(User).filter(User.username == 'admintest').first()
print(f'User: {user.username} ({user.id})')
print(f'Role: {user.role}')

print('\nAll organizations owned by admintest:')
orgs = (
    db.query(Organization)
    .join(OrganizationMember)
    .filter(OrganizationMember.user_id == user.id)
    .filter(OrganizationMember.role == 'owner')
    .all()
)

for org in orgs:
    print(f'  {org.name}')
    print(f'    slug: {org.slug}')
    print(f'    active: {org.is_active}')
    print(f'    id: {org.id}')

active_count = (
    db.query(OrganizationMember)
    .join(Organization)
    .filter(OrganizationMember.user_id == user.id)
    .filter(OrganizationMember.role == 'owner')
    .filter(Organization.is_active == True)
    .filter(OrganizationMember.is_active == True)
    .count()
)

print(f'\nActive organization count: {active_count}')

# Check subscription
from backend.src.models import Subscription
subscription = db.query(Subscription).filter(Subscription.user_id == user.id).first()
if subscription:
    print(f'Subscription tier: {subscription.tier.value}')
else:
    print('No subscription (FREE tier)')

db.close()
