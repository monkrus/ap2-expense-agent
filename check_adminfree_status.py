import sys
sys.path.insert(0, 'backend')

from src.database import SessionLocal
from src.models import Organization, OrganizationMember, User

db = SessionLocal()

try:
    # Get adminfree user
    user = db.query(User).filter(User.username == 'adminfree').first()

    if not user:
        print("❌ User 'adminfree' not found")
        sys.exit(1)

    print(f"✅ User: {user.username} (ID: {user.id})")
    print(f"   Email: {user.email}")
    print(f"   Role: {user.role}")
    print()

    # Get user's organization memberships
    memberships = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.is_active == True
    ).all()

    print(f"Active organization memberships: {len(memberships)}")

    if memberships:
        for m in memberships:
            org = db.query(Organization).filter(Organization.id == m.organization_id).first()
            if org:
                print(f"  - {org.name} ({org.slug})")
                print(f"    Role: {m.role}")
                print(f"    Org ID: {org.id}")
                print()
    else:
        print("  ⚠️  No organizations found")
        print()

    # Count total active orgs in system
    total_orgs = db.query(Organization).filter(Organization.is_active == True).count()
    print(f"Total active organizations in system: {total_orgs}")

    # Free tier check
    print()
    print("=" * 60)
    print("FREE TIER LIMITS CHECK")
    print("=" * 60)
    print(f"Organizations owned: {len(memberships)}/1 (FREE TIER LIMIT)")

    if len(memberships) == 0:
        print("✅ Can create 1 organization")
    elif len(memberships) == 1:
        print("⚠️  At organization limit - cannot create more")
        print("   Need to add employee to existing org")
    else:
        print("❌ Exceeded free tier limit!")

finally:
    db.close()
