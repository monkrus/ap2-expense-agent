from src.database import SessionLocal
from src.models import User, Organization, OrganizationMember

db = SessionLocal()

# Find admin users
admins = db.query(User).filter(User.role == 'admin').all()

print("Admin Users and Their Organizations:")
print("=" * 60)

for admin in admins:
    print(f"\nAdmin: {admin.full_name} ({admin.email})")
    print(f"User ID: {admin.id}")

    # Find orgs this admin belongs to
    memberships = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == admin.id
    ).all()

    if memberships:
        print(f"Member of {len(memberships)} organization(s):")
        for mem in memberships:
            org = db.query(Organization).filter(
                Organization.id == mem.organization_id
            ).first()
            if org:
                print(f"  - {org.name} (ID: {org.id})")
                print(f"    Role: {mem.role}")
                print(f"    Active: {org.is_active}")
    else:
        print("  NOT A MEMBER OF ANY ORGANIZATION!")

print("\n" + "=" * 60)
print("\nOrganizations with PENDING expenses:")
from src.models import Expense, ExpenseStatus

pending_org_ids = db.query(Expense.organization_id).filter(
    Expense.status == ExpenseStatus.PENDING
).distinct().all()

for (org_id,) in pending_org_ids:
    org = db.query(Organization).filter(Organization.id == org_id).first()
    count = db.query(Expense).filter(
        Expense.organization_id == org_id,
        Expense.status == ExpenseStatus.PENDING
    ).count()
    print(f"  - {org.name if org else 'Unknown'} ({org_id}): {count} pending")
