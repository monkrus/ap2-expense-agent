"""Check what expenses adminfree user should see"""
from src.database import SessionLocal
from src.models import User, Expense, Organization, OrganizationMember

db = SessionLocal()

print("=" * 70)
print("CHECKING ADMINFREE USER'S EXPENSES")
print("=" * 70)
print()

# Get adminfree user
user = db.query(User).filter(User.username == 'adminfree').first()
if user:
    print(f"User found: {user.username}")
    print(f"User ID: {user.id}")
    print(f"Email: {user.email}")
    print()

    # Get their organization
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.is_active == True
    ).first()

    if member:
        org = db.query(Organization).filter(Organization.id == member.organization_id).first()
        print(f"Organization: {org.name}")
        print(f"Organization ID: {org.id}")
        print()

        # Get expenses for this user in this org
        expenses = db.query(Expense).filter(
            Expense.user_id == user.id,
            Expense.organization_id == org.id
        ).order_by(Expense.created_at.desc()).all()

        print(f"Total expenses for this user: {len(expenses)}")
        print()

        if expenses:
            print("Recent expenses (should be visible in UI):")
            print("-" * 70)
            for i, exp in enumerate(expenses[:10], 1):
                print(f"{i}. ${exp.amount} - {exp.vendor} - {exp.status.value}")
                print(f"   Category: {exp.category.value if hasattr(exp.category, 'value') else exp.category}")
                print(f"   Auto-approved: {exp.auto_approved}")
                if exp.auto_approved:
                    print(f"   Auto-approved via: {exp.auto_approved_via}")
                print()
        else:
            print("NO EXPENSES FOUND FOR THIS USER!")
            print()
            print("This is why you don't see anything in the UI.")
            print()
            print("The test expense might be under a different user.")
    else:
        print("No organization membership found for this user")
        print("User cannot see any expenses without being in an organization")
else:
    print("User 'adminfree' not found in database")
    print()
    print("Available users:")
    users = db.query(User).filter(User.is_active == True).all()
    for u in users[:5]:
        print(f"  - {u.username}")

db.close()
