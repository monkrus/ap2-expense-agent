"""List all users in the database with detailed information"""
from src.database import SessionLocal
from src.models import User, OrganizationMember, Organization

db = SessionLocal()

print('\n' + '=' * 80)
print('ALL USERS IN DATABASE - DETAILED VIEW')
print('=' * 80 + '\n')

users = db.query(User).all()
print(f'Total Users: {len(users)}\n')

for i, u in enumerate(users, 1):
    print(f'[{i}] Username:   {u.username}')
    print(f'    Full Name:  {u.full_name}')
    print(f'    Email:      {u.email}')
    print(f'    User ID:    {u.id}')
    print(f'    Is Active:  {u.is_active}')
    print(f'    Role:       {u.role}')
    print(f'    Created:    {u.created_at}')

    # Get organization memberships
    memberships = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == u.id,
        OrganizationMember.is_active == True
    ).all()

    if memberships:
        print(f'    Organizations ({len(memberships)}):')
        for m in memberships:
            org = db.query(Organization).filter(
                Organization.id == m.organization_id,
                Organization.is_active == True
            ).first()
            if org:
                print(f'      - {org.name} (Org Role: {m.role}, Org ID: {org.id})')
    else:
        print(f'    Organizations: None')

    print('-' * 80)

db.close()

print('\nSummary:')
print(f'  Active Users: {len([u for u in users if u.is_active])}')
print(f'  Inactive Users: {len([u for u in users if not u.is_active])}')
