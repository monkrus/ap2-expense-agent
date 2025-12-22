from src.database import get_db
from src.models import User, Organization, OrganizationMember

db = next(get_db())

user = db.query(User).filter(User.username == 'admintest').first()
if not user:
    print("User 'admintest' not found")
    exit()

print(f"User ID: {user.id}")
print(f"Username: {user.username}")

# Count using the same query as the backend
owned_orgs_count = (
    db.query(OrganizationMember)
    .join(Organization, OrganizationMember.organization_id == Organization.id)
    .filter(OrganizationMember.user_id == user.id)
    .filter(OrganizationMember.role == 'owner')
    .filter(OrganizationMember.is_active == True)
    .filter(Organization.is_active == True)
    .count()
)

print(f"\nActive owned organizations count: {owned_orgs_count}")

# Get details
members = (
    db.query(OrganizationMember, Organization)
    .join(Organization, OrganizationMember.organization_id == Organization.id)
    .filter(OrganizationMember.user_id == user.id)
    .filter(OrganizationMember.role == 'owner')
    .all()
)

print(f"\nAll owned organizations:")
for member, org in members:
    print(f"  - Org: {org.name} (ID: {org.id})")
    print(f"    Member Active: {member.is_active}, Org Active: {org.is_active}")
