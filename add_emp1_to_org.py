"""Add emp1 user to an organization"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from src.database import SessionLocal
from src.models import Organization, OrganizationMember, User, OrganizationRole
import uuid

db = SessionLocal()

try:
    # Get emp1 user
    emp = db.query(User).filter(User.username == 'emp1').first()
    if not emp:
        print("[ERROR] emp1 user not found!")
        sys.exit(1)

    print(f"Found emp1: {emp.username} (ID: {emp.id})")

    # Check if emp1 already has organization membership
    existing_membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == emp.id,
        OrganizationMember.is_active == True
    ).first()

    if existing_membership:
        org = db.query(Organization).filter(
            Organization.id == existing_membership.organization_id
        ).first()
        print(f"[INFO] emp1 already belongs to organization: {org.name if org else 'Unknown'}")
        print(f"  Organization ID: {existing_membership.organization_id}")
        print(f"  Role: {existing_membership.role}")
        sys.exit(0)

    # Get all active organizations
    orgs = db.query(Organization).filter(Organization.is_active == True).all()

    if not orgs:
        print("[ERROR] No active organizations found!")
        print("[INFO] Creating a default organization for emp1...")

        # Create a new organization
        new_org = Organization(
            id=str(uuid.uuid4()),
            name="Test Organization",
            slug="test-org",
            description="Default organization for testing",
            is_active=True
        )
        db.add(new_org)
        db.commit()
        db.refresh(new_org)

        org = new_org
        print(f"[SUCCESS] Created organization: {org.name} (ID: {org.id})")
    else:
        # Use the first active organization
        org = orgs[0]
        print(f"Found organization: {org.name} (ID: {org.id})")

    # Add emp1 to the organization
    membership = OrganizationMember(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        user_id=emp.id,
        role=OrganizationRole.MEMBER,
        is_active=True
    )

    db.add(membership)
    db.commit()

    print(f"\n[SUCCESS] Added emp1 to organization: {org.name}")
    print(f"  Organization ID: {org.id}")
    print(f"  User ID: {emp.id}")
    print(f"  Role: MEMBER")
    print("\nemp1 can now log in and access the expense management system!")

finally:
    db.close()
