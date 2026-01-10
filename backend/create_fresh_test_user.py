"""Create fresh test user with complete AP2 setup"""
import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from src.database import SessionLocal
from src.models import (
    User, Organization, OrganizationMember, IntentMandate,
    Expense, ExpenseStatus, ExpenseCategory
)
from src.auth import AuthService
from datetime import datetime, timedelta
import uuid
import json

db = SessionLocal()

print("=" * 70)
print("CREATING FRESH TEST USER WITH AP2 SETUP")
print("=" * 70)
print()

# Step 1: Create user
username = "testuser2"
password = "testpass123"
email = "testuser2@example.com"

print("1. Creating user...")
# Check if user exists
existing_user = db.query(User).filter(User.username == username).first()
if existing_user:
    print(f"   User '{username}' already exists. Deleting old data...")
    # Get organization memberships first
    memberships = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == existing_user.id
    ).all()

    org_ids = [m.organization_id for m in memberships]

    # Delete old expenses
    db.query(Expense).filter(Expense.user_id == existing_user.id).delete()
    # Delete old mandates
    db.query(IntentMandate).filter(IntentMandate.user_id == existing_user.id).delete()
    # Delete org memberships
    db.query(OrganizationMember).filter(OrganizationMember.user_id == existing_user.id).delete()
    # Delete organizations
    for org_id in org_ids:
        db.query(Organization).filter(Organization.id == org_id).delete()
    # Delete user
    db.delete(existing_user)
    db.commit()

# Also check for existing organization with same slug
existing_org = db.query(Organization).filter(Organization.slug == f"{username}-org").first()
if existing_org:
    print(f"   Organization slug '{username}-org' already exists. Deleting...")
    db.query(OrganizationMember).filter(OrganizationMember.organization_id == existing_org.id).delete()
    db.query(Expense).filter(Expense.organization_id == existing_org.id).delete()
    db.delete(existing_org)
    db.commit()

user = User(
    id=str(uuid.uuid4()),
    username=username,
    email=email,
    hashed_password=AuthService.hash_password(password),
    full_name="Test User 2",
    is_active=True
)
db.add(user)
db.commit()

print(f"   ✅ User created: {username}")
print(f"   Password: {password}")
print(f"   User ID: {user.id}")
print()

# Step 2: Create organization
print("2. Creating organization...")
org = Organization(
    id=str(uuid.uuid4()),
    name=f"{username}'s Organization",
    slug=f"{username}-org",
    is_active=True
)
db.add(org)
db.commit()

print(f"   ✅ Organization created: {org.name}")
print(f"   Org ID: {org.id}")
print()

# Step 3: Add user to organization as admin
print("3. Adding user to organization as admin...")
member = OrganizationMember(
    id=str(uuid.uuid4()),
    organization_id=org.id,
    user_id=user.id,
    role="admin",
    is_active=True
)
db.add(member)
db.commit()

print(f"   ✅ User is now admin of organization")
print()

# Step 4: Create Intent Mandate
print("4. Creating Intent Mandate...")
mandate = IntentMandate(
    id=str(uuid.uuid4()),
    user_id=user.id,
    status="active",
    constraints=json.dumps({
        "merchant": "Amazon",
        "category": "OFFICE_SUPPLIES",
        "max_amount": 200.0,
        "monthly_limit": 1000.0
    }),
    timestamp=datetime.utcnow(),
    expiration=datetime.utcnow() + timedelta(days=30)
)
db.add(mandate)
db.commit()

print(f"   ✅ Intent Mandate created")
print(f"   Mandate ID: {mandate.id}")
print(f"   Constraints:")
print(f"     - Merchant: Amazon")
print(f"     - Category: OFFICE_SUPPLIES")
print(f"     - Max Amount: $200")
print(f"     - Monthly Limit: $1,000")
print()

# Step 5: Create test expense (should auto-approve)
print("5. Creating test expense (should auto-approve)...")
expense = Expense(
    id=str(uuid.uuid4()),
    user_id=user.id,
    organization_id=org.id,
    amount=75.50,
    vendor="Amazon",
    category=ExpenseCategory.OFFICE_SUPPLIES,
    description="Wireless keyboard and mouse - Fresh test",
    date=datetime.utcnow(),
    status=ExpenseStatus.APPROVED,  # Manually set for testing
    auto_approved=True,
    auto_approved_via="intent_mandate",
    approved_by="ai_agent",
    intent_mandate_id=mandate.id
)
db.add(expense)
db.commit()

print(f"   ✅ Test expense created")
print(f"   Expense ID: {expense.id}")
print(f"   Amount: ${expense.amount}")
print(f"   Vendor: {expense.vendor}")
print(f"   Status: {expense.status.value}")
print(f"   Auto-approved: {expense.auto_approved}")
print(f"   Auto-approved via: {expense.auto_approved_via}")
print()

print("=" * 70)
print("SETUP COMPLETE!")
print("=" * 70)
print()
print("LOGIN CREDENTIALS:")
print(f"  Username: {username}")
print(f"  Password: {password}")
print()
print("DATABASE IDS:")
print(f"  User ID: {user.id}")
print(f"  Organization ID: {org.id}")
print(f"  Intent Mandate ID: {mandate.id}")
print(f"  Test Expense ID: {expense.id}")
print()
print("WHAT WAS CREATED:")
print("  ✅ User account (admin role)")
print("  ✅ Organization")
print("  ✅ Intent Mandate (Amazon, OFFICE_SUPPLIES, $200 max, $1000/month)")
print("  ✅ Test expense ($75.50 Amazon, auto-approved via intent_mandate)")
print()
print("NEXT STEPS:")
print("  1. Test API: python backend/test_fresh_user_api.py")
print("  2. Test UI: Login at http://localhost:5173")
print("     - Username: testuser2")
print("     - Password: testpass123")
print("  3. Look for purple '✨ AI Agent' badge on the $75.50 Amazon expense")
print()

db.close()
