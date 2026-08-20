"""
Delete ALL organizations for adminfree user (leave with 0 organizations)
"""
import sys
sys.path.append("backend/src")

from backend.src.database import SessionLocal
from backend.src.models import User, Organization, OrganizationMember, OrganizationRole

db = SessionLocal()

try:
    # Find adminfree user
    user = db.query(User).filter(User.username == "adminfree").first()

    if not user:
        print("[ERROR] User 'adminfree' not found")
        exit(1)

    print(f"[OK] Found user: {user.username}")

    # Get ALL active organizations owned by user
    orgs = (
        db.query(Organization)
        .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
        .filter(OrganizationMember.user_id == user.id)
        .filter(OrganizationMember.role == OrganizationRole.OWNER)
        .filter(OrganizationMember.is_active == True)
        .filter(Organization.is_active == True)
        .all()
    )

    print(f"\n[COUNT] Found {len(orgs)} active organizations")

    if len(orgs) == 0:
        print("[OK] User has no organizations - nothing to delete")
        exit(0)

    print(f"\n[DELETE] Soft-deleting ALL {len(orgs)} organizations:")

    for org in orgs:
        print(f"   - {org.name} (slug: {org.slug})")

        # Get members to deactivate
        members = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == org.id,
                OrganizationMember.is_active == True
            )
            .all()
        )

        # Soft delete organization
        org.is_active = False

        # Deactivate all members
        for member in members:
            member.is_active = False

    db.commit()

    print(f"\n[SUCCESS] Deleted all {len(orgs)} organizations")
    print(f"[OK] User '{user.username}' now has 0 organizations")
    print(f"[OK] User can now create 1 organization (free tier limit)")

finally:
    db.close()
