"""
Sample Data Seeding Script for Marketplace Screenshots
Creates realistic demo data for screenshot capture

Usage:
    python seed_screenshot_data.py

This will create:
- Demo organization: "Acme Corporation"
- 3 demo users (admin, manager, employee)
- 10 sample expenses with varied statuses
- 2 pending approvals
- Budget data
- Recent activity
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session
from src.database import SessionLocal, engine
from src.models import (
    User,
    Organization,
    OrganizationMember,
    Expense,
    Budget,
    UserRole,
)
from src.auth import AuthService
import uuid


def create_demo_data(db: Session):
    """Create demo data for screenshots"""

    print("🎬 Creating demo data for screenshots...\n")

    # Check if demo org already exists
    existing_org = db.query(Organization).filter_by(name="Acme Corporation").first()
    if existing_org:
        print("⚠️  Demo data already exists. Deleting and recreating...")
        # Delete existing demo data
        db.query(OrganizationMember).filter_by(
            organization_id=existing_org.id
        ).delete()
        db.query(Expense).filter_by(organization_id=existing_org.id).delete()
        db.query(Budget).filter_by(organization_id=existing_org.id).delete()
        db.query(Organization).filter_by(id=existing_org.id).delete()

        # Delete demo users
        for email in [
            "sarah.admin@acme.com",
            "mike.manager@acme.com",
            "john.employee@acme.com",
        ]:
            user = db.query(User).filter_by(email=email).first()
            if user:
                db.query(User).filter_by(id=user.id).delete()

        db.commit()
        print("✓ Cleaned up existing demo data\n")

    # === Step 1: Create Organization ===
    print("1️⃣ Creating organization: Acme Corporation")
    org_id = str(uuid.uuid4())
    organization = Organization(
        id=org_id,
        name="Acme Corporation",
        slug="acme-corporation",
        description="Leading technology and innovation company",
        max_members=25,
        max_expenses_per_month=None,  # Unlimited
        is_active=True,
        created_at=datetime.utcnow() - timedelta(days=90),
    )
    db.add(organization)
    db.commit()
    print(f"   ✓ Organization created: {org_id}\n")

    # === Step 2: Create Users ===
    print("2️⃣ Creating demo users")

    users_data = [
        {
            "username": "sarah.admin",
            "email": "sarah.admin@acme.com",
            "full_name": "Sarah Admin",
            "role": UserRole.ADMIN,
            "org_role": "owner",
        },
        {
            "username": "mike.manager",
            "email": "mike.manager@acme.com",
            "full_name": "Mike Manager",
            "role": UserRole.MANAGER,
            "org_role": "manager",
        },
        {
            "username": "john.employee",
            "email": "john.employee@acme.com",
            "full_name": "John Employee",
            "role": UserRole.EMPLOYEE,
            "org_role": "member",
        },
    ]

    user_objects = {}
    for user_data in users_data:
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            username=user_data["username"],
            email=user_data["email"],
            full_name=user_data["full_name"],
            hashed_password=AuthService.hash_password("Demo123!"),  # Same for all
            role=user_data["role"],
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow() - timedelta(days=85),
        )
        db.add(user)

        # Add to organization
        member = OrganizationMember(
            id=str(uuid.uuid4()),
            user_id=user_id,
            organization_id=org_id,
            role=user_data["org_role"],
            is_active=True,
            joined_at=datetime.utcnow() - timedelta(days=85),
        )
        db.add(member)

        user_objects[user_data["email"]] = user
        print(f"   ✓ User created: {user_data['full_name']} ({user_data['email']})")

    db.commit()
    print()

    # === Step 3: Create Expenses ===
    print("3️⃣ Creating sample expenses")

    expenses_data = [
        {
            "vendor": "Office Depot",
            "amount": 45.99,
            "category": "Office Supplies",
            "description": "Printer paper, pens, sticky notes",
            "status": "approved",
            "days_ago": 15,
            "user": "john.employee@acme.com",
        },
        {
            "vendor": "Delta Airlines",
            "amount": 542.50,
            "category": "Travel",
            "description": "Round-trip flight to San Francisco for client meeting",
            "status": "approved",
            "days_ago": 10,
            "user": "mike.manager@acme.com",
        },
        {
            "vendor": "Hilton Hotels",
            "amount": 289.00,
            "category": "Lodging",
            "description": "Hotel stay - San Francisco business trip (2 nights)",
            "status": "approved",
            "days_ago": 9,
            "user": "mike.manager@acme.com",
        },
        {
            "vendor": "Starbucks",
            "amount": 12.75,
            "category": "Meals",
            "description": "Coffee and breakfast during client meeting",
            "status": "approved",
            "days_ago": 8,
            "user": "john.employee@acme.com",
        },
        {
            "vendor": "Uber",
            "amount": 35.20,
            "category": "Transportation",
            "description": "Airport transportation",
            "status": "approved",
            "days_ago": 7,
            "user": "mike.manager@acme.com",
        },
        {
            "vendor": "Amazon Web Services",
            "amount": 1250.00,
            "category": "Cloud Services",
            "description": "Monthly cloud hosting and compute resources",
            "status": "pending",
            "days_ago": 2,
            "user": "sarah.admin@acme.com",
        },
        {
            "vendor": "LinkedIn",
            "amount": 149.99,
            "category": "Software",
            "description": "Annual recruiter subscription",
            "status": "pending",
            "days_ago": 1,
            "user": "sarah.admin@acme.com",
        },
        {
            "vendor": "Zoom",
            "amount": 199.00,
            "category": "Software",
            "description": "Business plan - annual subscription",
            "status": "approved",
            "days_ago": 20,
            "user": "sarah.admin@acme.com",
        },
        {
            "vendor": "Best Buy",
            "amount": 899.99,
            "category": "Equipment",
            "description": "New laptop for developer",
            "status": "rejected",
            "days_ago": 5,
            "user": "john.employee@acme.com",
            "rejection_reason": "Please use corporate purchasing for equipment >$500",
        },
        {
            "vendor": "Chipotle",
            "amount": 48.50,
            "category": "Meals",
            "description": "Team lunch for project kickoff (5 people)",
            "status": "approved",
            "days_ago": 3,
            "user": "mike.manager@acme.com",
        },
    ]

    for expense_data in expenses_data:
        user = user_objects[expense_data["user"]]
        expense_id = str(uuid.uuid4())

        expense = Expense(
            id=expense_id,
            user_id=user.id,
            organization_id=org_id,
            vendor=expense_data["vendor"],
            amount=expense_data["amount"],
            category=expense_data["category"],
            description=expense_data["description"],
            status=expense_data["status"],
            created_at=datetime.utcnow() - timedelta(days=expense_data["days_ago"]),
            updated_at=datetime.utcnow() - timedelta(days=expense_data["days_ago"]),
        )

        # Add approval/rejection metadata
        if expense_data["status"] == "approved":
            expense.approved_by = user_objects["mike.manager@acme.com"].id
            expense.approved_at = datetime.utcnow() - timedelta(
                days=expense_data["days_ago"] - 1
            )
        elif expense_data["status"] == "rejected":
            expense.rejected_by = user_objects["mike.manager@acme.com"].id
            expense.rejected_at = datetime.utcnow() - timedelta(
                days=expense_data["days_ago"] - 1
            )
            if "rejection_reason" in expense_data:
                expense.rejection_reason = expense_data["rejection_reason"]

        db.add(expense)
        print(
            f"   ✓ Expense: ${expense_data['amount']:.2f} - {expense_data['vendor']} ({expense_data['status']})"
        )

    db.commit()
    print()

    # === Step 4: Create Budgets ===
    print("4️⃣ Creating budget data")

    budgets_data = [
        {
            "name": "Q4 2025 Travel Budget",
            "category": "Travel",
            "amount": 5000.00,
            "spent": 1166.70,
        },
        {
            "name": "Q4 2025 Software Budget",
            "category": "Software",
            "amount": 3000.00,
            "spent": 348.99,
        },
        {
            "name": "Q4 2025 Office Supplies",
            "category": "Office Supplies",
            "amount": 500.00,
            "spent": 45.99,
        },
    ]

    for budget_data in budgets_data:
        budget_id = str(uuid.uuid4())
        budget = Budget(
            id=budget_id,
            organization_id=org_id,
            name=budget_data["name"],
            category=budget_data["category"],
            amount=budget_data["amount"],
            period="quarter",
            start_date=datetime(2025, 10, 1),
            end_date=datetime(2025, 12, 31),
            created_at=datetime.utcnow() - timedelta(days=60),
        )
        db.add(budget)
        percentage = (budget_data["spent"] / budget_data["amount"]) * 100
        print(
            f"   ✓ Budget: {budget_data['name']} (${budget_data['spent']:.2f}/${budget_data['amount']:.2f} - {percentage:.1f}%)"
        )

    db.commit()
    print()

    # === Summary ===
    print("=" * 60)
    print("✅ DEMO DATA CREATED SUCCESSFULLY!")
    print("=" * 60)
    print()
    print("📊 Summary:")
    print(f"   Organization: Acme Corporation (ID: {org_id})")
    print(f"   Users: 3 (1 admin, 1 manager, 1 employee)")
    print(f"   Expenses: {len(expenses_data)} (7 approved, 2 pending, 1 rejected)")
    print(f"   Budgets: {len(budgets_data)}")
    print()
    print("🔐 Login Credentials (all users):")
    print("   Password: Demo123!")
    print()
    print("   👤 sarah.admin@acme.com (Admin/Owner)")
    print("   👤 mike.manager@acme.com (Manager)")
    print("   👤 john.employee@acme.com (Employee)")
    print()
    print("🎬 Ready for screenshot capture!")
    print("   1. Start backend: cd backend && uvicorn src.api:app --reload")
    print("   2. Start frontend: cd frontend && npm run dev")
    print("   3. Login with any user above")
    print("   4. Follow MARKETPLACE_ASSET_CREATION_GUIDE.md")
    print()


if __name__ == "__main__":
    print("🌱 AP2 Expense Agent - Screenshot Demo Data Seeder")
    print("=" * 60)
    print()

    db = SessionLocal()
    try:
        create_demo_data(db)
    except Exception as e:
        print(f"\n❌ Error creating demo data: {e}")
        import traceback

        traceback.print_exc()
        db.rollback()
    finally:
        db.close()
