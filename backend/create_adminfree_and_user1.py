"""Create two users: adminfree (admin) and user1 (user)"""
import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from src.database import SessionLocal
from src.models import User, Organization, OrganizationMember, UserRole, OrganizationRole
from src.auth import AuthService
import uuid

db = SessionLocal()

print("=" * 70)
print("CREATING USERS: adminfree AND user1")
print("=" * 70)
print()

password = "Passowrd123!"

# User 1: adminfree (admin)
print("1. Creating adminfree (admin)...")

# Check if user exists
existing = db.query(User).filter(User.username == "adminfree").first()
if existing:
    print(f"   User 'adminfree' already exists with ID: {existing.id}")
    print("   Skipping creation...")
else:
    user_admin = User(
        id=str(uuid.uuid4()),
        username="adminfree",
        email="sergeigodev@gmail.com",
        hashed_password=AuthService.hash_password(password),
        full_name="Admin Free",
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True
    )
    db.add(user_admin)
    db.commit()

    print(f"   ✅ User created: adminfree")
    print(f"   Email: sergeigodev@gmail.com")
    print(f"   Role: ADMIN")
    print(f"   User ID: {user_admin.id}")

    # Create organization for adminfree
    print("   Creating organization...")
    org_admin = Organization(
        id=str(uuid.uuid4()),
        name="adminfree's Organization",
        slug="adminfree-org",
        is_active=True,
        max_members=1
    )
    db.add(org_admin)
    db.commit()

    print(f"   ✅ Organization created: {org_admin.name}")
    print(f"   Org ID: {org_admin.id}")

    # Add user to organization as owner
    print("   Adding user to organization as owner...")
    member_admin = OrganizationMember(
        id=str(uuid.uuid4()),
        organization_id=org_admin.id,
        user_id=user_admin.id,
        role=OrganizationRole.OWNER,
        is_active=True
    )
    db.add(member_admin)
    db.commit()

    print(f"   ✅ User is now owner of organization")

print()

# User 2: user1 (user)
print("2. Creating user1 (user)...")

# Check if user exists
existing = db.query(User).filter(User.username == "user1").first()
if existing:
    print(f"   User 'user1' already exists with ID: {existing.id}")
    print("   Skipping creation...")
else:
    user_regular = User(
        id=str(uuid.uuid4()),
        username="user1",
        email="sergeisqa@gmail.com",
        hashed_password=AuthService.hash_password(password),
        full_name="User One",
        role=UserRole.EMPLOYEE,
        is_active=True,
        is_verified=True
    )
    db.add(user_regular)
    db.commit()

    print(f"   ✅ User created: user1")
    print(f"   Email: sergeisqa@gmail.com")
    print(f"   Role: USER")
    print(f"   User ID: {user_regular.id}")

    # Create organization for user1
    print("   Creating organization...")
    org_user = Organization(
        id=str(uuid.uuid4()),
        name="user1's Organization",
        slug="user1-org",
        is_active=True,
        max_members=1
    )
    db.add(org_user)
    db.commit()

    print(f"   ✅ Organization created: {org_user.name}")
    print(f"   Org ID: {org_user.id}")

    # Add user to organization as owner
    print("   Adding user to organization as owner...")
    member_user = OrganizationMember(
        id=str(uuid.uuid4()),
        organization_id=org_user.id,
        user_id=user_regular.id,
        role=OrganizationRole.OWNER,
        is_active=True
    )
    db.add(member_user)
    db.commit()

    print(f"   ✅ User is now owner of organization")

print()
print("=" * 70)
print("SETUP COMPLETE!")
print("=" * 70)
print()
print("LOGIN CREDENTIALS (Both Users):")
print(f"  Password: {password}")
print()
print("User 1 (Admin):")
print(f"  Username: adminfree")
print(f"  Email: sergeigodev@gmail.com")
print(f"  Role: ADMIN")
print()
print("User 2 (Regular User):")
print(f"  Username: user1")
print(f"  Email: sergeisqa@gmail.com")
print(f"  Role: USER")
print()

# Verify
total_users = db.query(User).count()
total_orgs = db.query(Organization).count()
print(f"Total users in database: {total_users}")
print(f"Total organizations in database: {total_orgs}")
print()

db.close()
