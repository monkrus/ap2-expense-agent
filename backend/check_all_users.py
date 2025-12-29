from src.database import SessionLocal
from src.models import Organization, OrganizationMember, User

db = SessionLocal()

try:
    # Get all users
    users = db.query(User).all()
    print(f"Total users in system: {len(users)}")
    print()

    for user in users:
        print(f"User: {user.username}")
        print(f"  Email: {user.email}")
        print(f"  Role: {user.role}")
        print(f"  Active: {user.is_active}")

        # Get organization memberships
        memberships = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == user.id,
            OrganizationMember.is_active == True
        ).all()

        if memberships:
            for m in memberships:
                org = db.query(Organization).filter(
                    Organization.id == m.organization_id
                ).first()
                if org:
                    print(f"  Organization: {org.name} ({org.slug})")
                    print(f"    Org Role: {m.role}")
                    print(f"    Org Active: {org.is_active}")
        else:
            print("  [NO ORGANIZATIONS]")
        print()

finally:
    db.close()
