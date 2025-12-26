"""
Create a test employee user for testing notifications
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from src.database import SessionLocal
from src.models import User, UserRole, Organization, OrganizationMember
from src.auth import AuthService
import uuid

db = SessionLocal()

# Check if emp1 already exists
existing = db.query(User).filter(User.username == "emp1").first()
if existing:
    print(f"User 'emp1' already exists!")
    print(f"  Username: emp1")
    print(f"  Email: {existing.email}")
    print(f"  Role: {existing.role}")
    print(f"  Password: Test!!!")
    db.close()
    sys.exit(0)

# Create employee user
employee = User(
    id=str(uuid.uuid4()),
    username="emp1",
    email="emp1@test.com",
    full_name="Test Employee",
    hashed_password=AuthService.hash_password("Test!!!"),
    role=UserRole.EMPLOYEE,
    is_active=True,
    is_verified=True
)

db.add(employee)
db.commit()
db.refresh(employee)

print(f"[OK] Created employee user:")
print(f"  Username: emp1")
print(f"  Password: Test!!!")
print(f"  Email: emp1@test.com")
print(f"  Role: EMPLOYEE")
print(f"  User ID: {employee.id}")

# Get admin's organization
admin = db.query(User).filter(User.username == "adminfree").first()
if admin:
    # Find admin's organization
    admin_membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == admin.id,
        OrganizationMember.is_active == True
    ).first()

    if admin_membership:
        org_id = admin_membership.organization_id
        org = db.query(Organization).filter(Organization.id == org_id).first()

        # Add employee to the same organization
        membership = OrganizationMember(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            user_id=employee.id,
            role="member",
            is_active=True
        )
        db.add(membership)
        db.commit()

        print(f"[OK] Added to organization: {org.name}")
        print(f"  Organization ID: {org_id}")
    else:
        print("[WARN] Admin not in any organization - employee created but not added to org")
else:
    print("[WARN] Admin 'adminfree' not found - employee created but not added to org")

db.close()

print("\n" + "="*60)
print("TEST CREDENTIALS:")
print("="*60)
print("Admin:")
print("  Username: adminfree")
print("  Password: (you need to know this)")
print("\nEmployee:")
print("  Username: emp1")
print("  Password: Test!!!")
print("="*60)
