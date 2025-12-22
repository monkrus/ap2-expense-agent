from backend.src.database import SessionLocal
from backend.src.models import Organization, OrganizationMember, User

db = SessionLocal()

print("Users with deleted organizations:\n")
users = db.query(User).all()

for user in users:
    active = (
        db.query(OrganizationMember)
        .join(Organization)
        .filter(OrganizationMember.user_id == user.id)
        .filter(OrganizationMember.role == "owner")
        .filter(Organization.is_active == True)
        .count()
    )

    inactive = (
        db.query(OrganizationMember)
        .join(Organization)
        .filter(OrganizationMember.user_id == user.id)
        .filter(OrganizationMember.role == "owner")
        .filter(Organization.is_active == False)
        .count()
    )

    if inactive > 0:
        print(f"{user.username}: {active} active, {inactive} inactive (deleted)")

db.close()
