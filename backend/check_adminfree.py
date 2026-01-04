"""Check adminfree user and organization membership"""

from src.database import SessionLocal
from src.models import User, OrganizationMember, Organization

db = SessionLocal()

try:
    # Find adminfree user
    adminfree = db.query(User).filter(User.username == "adminfree").first()

    if not adminfree:
        print("User 'adminfree' not found in database")
    else:
        print(f"User found: {adminfree.username} (ID: {adminfree.id[:12]}...)")
        print(f"   Email: {adminfree.email}")
        print(f"   Role: {adminfree.role}")
        print(f"   Active: {adminfree.is_active}")

        # Check organization membership
        memberships = (
            db.query(OrganizationMember)
            .filter(OrganizationMember.user_id == adminfree.id)
            .all()
        )

        print(f"\nOrganization memberships: {len(memberships)}")

        for membership in memberships:
            org = db.query(Organization).filter(Organization.id == membership.organization_id).first()
            print(f"   - {org.name if org else 'Unknown'} (ID: {membership.organization_id[:12]}...)")
            print(f"     Role: {membership.role}")
            print(f"     Active: {membership.is_active}")

finally:
    db.close()
