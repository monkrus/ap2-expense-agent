"""
Add employees to organization manually
"""
import uuid
from src.database import SessionLocal
from src.models import Organization, OrganizationMember, OrganizationRole, User

db = SessionLocal()

try:
    # Get the organization
    org = db.query(Organization).filter(
        Organization.slug == "organization",
        Organization.is_active == True
    ).first()

    if not org:
        print("[ERROR] Organization 'organization' not found")
        exit(1)

    print(f"Organization: {org.name} (ID: {org.id})")
    print()

    # Get employees not in organization
    employees = db.query(User).filter(
        User.role == "employee",
        User.is_active == True
    ).all()

    added_count = 0

    for emp in employees:
        # Check if already a member
        existing = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == emp.id,
            OrganizationMember.organization_id == org.id,
            OrganizationMember.is_active == True
        ).first()

        if existing:
            print(f"[SKIP] {emp.username} is already a member")
            continue

        # Add to organization
        membership = OrganizationMember(
            id=str(uuid.uuid4()),
            organization_id=org.id,
            user_id=emp.id,
            role=OrganizationRole.MEMBER,
            is_active=True
        )
        db.add(membership)
        print(f"[ADD] {emp.username} ({emp.email}) -> {org.name}")
        added_count += 1

    db.commit()

    print()
    print(f"[SUCCESS] Added {added_count} employee(s) to organization")

    # Verify
    total_members = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org.id,
        OrganizationMember.is_active == True
    ).count()

    print(f"Total members now: {total_members}/2 (FREE TIER LIMIT)")

    if total_members > 2:
        print("[WARN] Exceeded free tier limit of 2 users!")

finally:
    db.close()
