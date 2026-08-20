"""List all users in the database with their organization memberships"""
import sys
sys.path.insert(0, 'backend')

from src.database import SessionLocal
from src.models import User, OrganizationMember, Organization

db = SessionLocal()

print('\n' + '=' * 80)
print('ALL USERS IN DATABASE')
print('=' * 80 + '\n')

users = db.query(User).all()
print(f'Total Users: {len(users)}\n')

for u in users:
    print(f'Username:   {u.username}')
    print(f'Full Name:  {u.full_name}')
    print(f'Email:      {u.email}')
    print(f'User ID:    {u.id}')
    print(f'Is Active:  {u.is_active}')

    # Get organization memberships
    memberships = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == u.id,
        OrganizationMember.is_active == True
    ).all()

    print(f'Organizations: {len(memberships)}')
    for m in memberships:
        org = db.query(Organization).filter(Organization.id == m.organization_id).first()
        if org:
            print(f'  - {org.name} (Role: {m.role})')

    print('-' * 80)

db.close()
