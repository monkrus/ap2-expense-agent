from backend.src.database import SessionLocal
from backend.src.models import User, OrganizationMember, Organization

db = SessionLocal()

print('=== COMPLETE USER ROLES BREAKDOWN ===\n')

memberships = db.query(User, OrganizationMember, Organization).join(
    OrganizationMember, User.id == OrganizationMember.user_id
).join(
    Organization, OrganizationMember.organization_id == Organization.id
).filter(
    OrganizationMember.is_active == True,
    Organization.is_active == True
).order_by(OrganizationMember.role, User.username).all()

current_role = None
for user, membership, org in memberships:
    role = str(membership.role).replace('OrganizationRole.', '').upper()
    if role != current_role:
        print(f'\n{role}S:')
        current_role = role
    print(f'  {user.username:30} | {org.name:40} | {user.email}')

print(f'\n\nSUMMARY:')
print(f'Total Active Memberships: {len(memberships)}')

owners = [m for m in memberships if 'OWNER' in str(m[1].role)]
managers = [m for m in memberships if 'MANAGER' in str(m[1].role)]
members = [m for m in memberships if 'MEMBER' in str(m[1].role) and 'MANAGER' not in str(m[1].role)]
admins = [m for m in memberships if 'ADMIN' in str(m[1].role)]

print(f'\nOwners: {len(owners)}')
print(f'Managers: {len(managers)}')
print(f'Members: {len(members)}')
print(f'Admins: {len(admins)}')

db.close()
