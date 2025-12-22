"""
Setup test organization and add users to it
"""

from src.database import SessionLocal
from src.models import User, Organization, OrganizationMember, UserRole, OrganizationRole
from sqlalchemy import select
import uuid

db = SessionLocal()

try:
    # Create test organization if it doesn't exist
    org = db.execute(select(Organization).where(Organization.name == "Test Organization")).scalar_one_or_none()

    if not org:
        org = Organization(
            id=f"org_{uuid.uuid4().hex[:16]}",
            name="Test Organization",
            slug="test-organization",
            is_active=True
        )
        db.add(org)
        db.commit()
        print(f"✅ Created organization: {org.name} ({org.id})")
    else:
        print(f"✅ Organization already exists: {org.name} ({org.id})")

    # Get all users
    users = db.execute(select(User)).scalars().all()

    for user in users:
        # Check if user is already a member
        membership = db.execute(
            select(OrganizationMember).where(
                OrganizationMember.user_id == user.id,
                OrganizationMember.organization_id == org.id
            )
        ).scalar_one_or_none()

        if not membership:
            # Determine role based on user role
            if user.role == UserRole.ADMIN:
                org_role = OrganizationRole.ADMIN
            elif user.role == UserRole.MANAGER:
                org_role = OrganizationRole.MANAGER
            else:
                org_role = OrganizationRole.MEMBER

            membership = OrganizationMember(
                id=f"orgmem_{uuid.uuid4().hex[:16]}",
                organization_id=org.id,
                user_id=user.id,
                role=org_role,
                is_active=True
            )
            db.add(membership)
            db.commit()
            print(f"✅ Added {user.username} ({user.role.value}) to organization as {org_role.value}")
        else:
            print(f"✓ {user.username} already in organization")

    print("\n✅ Test organization setup complete!")

finally:
    db.close()
