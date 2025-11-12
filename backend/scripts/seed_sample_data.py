"""
Seed sample expense data for development and testing.
Creates diverse expenses across categories, amounts, and statuses.
"""
import sys
import os
from datetime import datetime, timedelta
import uuid
import random

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import settings
from src.models import Expense, ExpenseStatus, ExpenseCategory, User

# Sample expense data
SAMPLE_EXPENSES = [
    # Travel expenses
    {"vendor": "United Airlines", "category": ExpenseCategory.TRAVEL, "amount": 450.00, "description": "Flight to client meeting in SF"},
    {"vendor": "Marriott Hotel", "category": ExpenseCategory.TRAVEL, "amount": 280.50, "description": "Hotel accommodation for conference"},
    {"vendor": "Uber", "category": ExpenseCategory.TRAVEL, "amount": 35.75, "description": "Airport transportation"},
    {"vendor": "Hertz Car Rental", "category": ExpenseCategory.TRAVEL, "amount": 150.00, "description": "Car rental for 2 days"},

    # Meals
    {"vendor": "Starbucks", "category": ExpenseCategory.MEALS, "amount": 15.50, "description": "Morning coffee with team"},
    {"vendor": "Chipotle", "category": ExpenseCategory.MEALS, "amount": 12.75, "description": "Working lunch"},
    {"vendor": "The Capital Grille", "category": ExpenseCategory.MEALS, "amount": 185.00, "description": "Client dinner meeting"},
    {"vendor": "Panera Bread", "category": ExpenseCategory.MEALS, "amount": 25.30, "description": "Team breakfast meeting"},

    # Software
    {"vendor": "GitHub", "category": ExpenseCategory.SOFTWARE, "amount": 21.00, "description": "Pro subscription monthly"},
    {"vendor": "Adobe Creative Cloud", "category": ExpenseCategory.SOFTWARE, "amount": 52.99, "description": "Design tools subscription"},
    {"vendor": "Microsoft 365", "category": ExpenseCategory.SOFTWARE, "amount": 12.50, "description": "Office suite license"},
    {"vendor": "Slack", "category": ExpenseCategory.SOFTWARE, "amount": 8.00, "description": "Team communication"},

    # Office Supplies
    {"vendor": "Staples", "category": ExpenseCategory.OFFICE_SUPPLIES, "amount": 45.99, "description": "Printer paper and pens"},
    {"vendor": "Office Depot", "category": ExpenseCategory.OFFICE_SUPPLIES, "amount": 78.50, "description": "Office furniture accessories"},
    {"vendor": "Amazon Business", "category": ExpenseCategory.OFFICE_SUPPLIES, "amount": 125.00, "description": "Desk organizers and supplies"},

    # Other
    {"vendor": "LinkedIn", "category": ExpenseCategory.OTHER, "amount": 79.99, "description": "Premium subscription for recruiting"},
    {"vendor": "Coursera", "category": ExpenseCategory.OTHER, "amount": 49.00, "description": "Professional development course"},
    {"vendor": "Conference Registration", "category": ExpenseCategory.OTHER, "amount": 399.00, "description": "AWS Re:Invent conference ticket"},
]

def seed_sample_expenses(db):
    """Seed sample expenses for all employees."""
    print("=" * 80)
    print("Seeding Sample Expenses")
    print("=" * 80)
    print()

    # Get all users
    users = db.query(User).all()

    if not users:
        print("❌ No users found. Please seed users first.")
        return {"created": 0, "skipped": 0}

    # Get employees and admin
    employees = [u for u in users if u.role.value in ["employee", "EMPLOYEE"]]
    admin = next((u for u in users if u.role.value in ["admin", "ADMIN"]), None)

    if not employees:
        print("❌ No employees found.")
        return {"created": 0, "skipped": 0}

    print(f"Found {len(employees)} employee(s) and {'1 admin' if admin else 'no admin'}")
    print()

    stats = {
        "created": 0,
        "skipped": 0
    }

    # Create org ID
    org_id = str(uuid.uuid4())

    # Distribute expenses across employees
    for i, expense_data in enumerate(SAMPLE_EXPENSES):
        employee = employees[i % len(employees)]

        # Vary the dates (last 30 days)
        days_ago = random.randint(1, 30)
        expense_date = datetime.utcnow() - timedelta(days=days_ago)

        # Vary the status (70% pending, 20% approved, 10% rejected)
        rand = random.random()
        if rand < 0.7:
            status = ExpenseStatus.PENDING
            approved_by = None
            approved_at = None
        elif rand < 0.9:
            status = ExpenseStatus.APPROVED
            approved_by = admin.id if admin else None
            approved_at = expense_date + timedelta(days=random.randint(1, 3))
        else:
            status = ExpenseStatus.REJECTED
            approved_by = admin.id if admin else None
            approved_at = expense_date + timedelta(days=random.randint(1, 3))

        # Create expense
        expense = Expense(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            user_id=employee.id,
            amount=expense_data["amount"],
            vendor=expense_data["vendor"],
            category=expense_data["category"],
            description=expense_data["description"],
            status=status,
            date=expense_date,
            approved_by=approved_by,
            approved_at=approved_at,
            ai_analysis=f"Category: {expense_data['category'].value}. Amount reasonable for vendor.",
            risk_level="LOW",
            compliance_check=True,
            created_at=expense_date,
            updated_at=expense_date
        )

        db.add(expense)

        status_symbol = "⏳" if status == ExpenseStatus.PENDING else ("✓" if status == ExpenseStatus.APPROVED else "✗")
        print(f"{status_symbol} ${expense_data['amount']:>7.2f} - {expense_data['vendor']:30} ({employee.username}) [{status.value}]")

        stats["created"] += 1

    db.commit()

    print()
    print("=" * 80)
    print("Seeding Complete")
    print("=" * 80)
    print(f"Created: {stats['created']} expenses")
    print()

    # Show summary by status
    print("Summary by Status:")
    print("-" * 80)
    pending = db.query(Expense).filter(Expense.status == ExpenseStatus.PENDING).count()
    approved = db.query(Expense).filter(Expense.status == ExpenseStatus.APPROVED).count()
    rejected = db.query(Expense).filter(Expense.status == ExpenseStatus.REJECTED).count()

    print(f"  Pending:  {pending}")
    print(f"  Approved: {approved}")
    print(f"  Rejected: {rejected}")
    print(f"  Total:    {pending + approved + rejected}")

    # Show summary by category
    print()
    print("Summary by Category:")
    print("-" * 80)
    for category in ExpenseCategory:
        count = db.query(Expense).filter(Expense.category == category).count()
        if count > 0:
            total = db.query(Expense).filter(Expense.category == category).all()
            total_amount = sum(e.amount for e in total)
            print(f"  {category.value:20} {count:3} expenses  ${total_amount:>8.2f}")

    return stats

def main():
    """Main function."""
    print()

    # Create engine and session
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        stats = seed_sample_expenses(db)

        print()
        print("✅ Sample data seeded successfully!")
        print()

        return 0
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error seeding sample data: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()

if __name__ == "__main__":
    sys.exit(main())
