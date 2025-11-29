import sys
sys.path.insert(0, 'backend')

from backend.src.database import SessionLocal
from backend.src.models import Organization, OrganizationMember, User

db = SessionLocal()

user = db.query(User).filter(User.username == 'admintest').first()
print(f'User: {user.username} ({user.id})')

print('\nAll organizations owned by admintest:')
orgs = (
    db.query(Organization)
    .join(OrganizationMember)
    .filter(OrganizationMember.user_id == user.id)
    .filter(OrganizationMember.role == 'owner')
    .all()
)

if not orgs:
    print('  No organizations found')
else:
    for org in orgs:
        print(f'  {org.name} (slug: {org.slug}, active: {org.is_active})')

active_orgs = [o for o in orgs if o.is_active]
print(f'\nActive organization count: {len(active_orgs)}')

db.close()
