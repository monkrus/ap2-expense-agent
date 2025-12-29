from src.database import SessionLocal
from src.models import Organization, OrganizationMember, User
from sqlalchemy.exc import OperationalError

db = SessionLocal()

try:
    # Try to query user
    try:
        user = db.query(User).filter(User.username == 'adminfree').first()
    except OperationalError as e:
        if "no such table" in str(e):
            print("❌ Database not initialized - tables don't exist")
            print("\nYou need to:")
            print("1. Run migrations: cd backend && alembic upgrade head")
            print("2. Create a user via registration endpoint")
            exit(1)
        raise

    if not user:
        print("❌ User 'adminfree' not found in database")
        print("\nYou need to register this user first:")
        print("POST /api/v1/auth/register")
        exit(1)

    print(f"[OK] User: {user.username}")
    print(f"     Email: {user.email}")
    print(f"     Role: {user.role}")
    print()

    # Get memberships
    memberships = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.is_active == True
    ).all()

    print(f"Organization memberships: {len(memberships)}")
    if memberships:
        for m in memberships:
            org = db.query(Organization).filter(Organization.id == m.organization_id, Organization.is_active == True).first()
            if org:
                print(f"  [ORG] {org.name} ({org.slug}) - Role: {m.role}")
    else:
        print("  [INFO] No organizations (can create 1)")

    print()
    print("=" * 60)
    print("FREE TIER STATUS")
    print("=" * 60)
    print(f"Organizations: {len(memberships)}/1 (max for Free tier)")

    # Count total members if org exists
    if memberships:
        org_id = memberships[0].organization_id
        total_members = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.is_active == True
        ).count()
        print(f"Users in organization: {total_members}/2 (max for Free tier)")

        if total_members < 2:
            print(f"\n[OK] Can add {2 - total_members} more user(s) to organization")
        else:
            print("\n[WARN] At user limit - cannot add more members")

finally:
    db.close()
