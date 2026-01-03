"""
Test expense API response to see what data is being returned
"""
import sys
sys.path.insert(0, 'src')

from src.database import SessionLocal
from src.models import User, Expense
from src.routes.expenses import get_user_organization_role

db = SessionLocal()

# Get employee1
employee1 = db.query(User).filter(User.username == 'employee1').first()
if not employee1:
    print("Employee1 not found!")
    sys.exit(1)

# Get their expenses
expenses = db.query(Expense).filter(Expense.user_id == employee1.id).all()

print(f"Employee1: {employee1.full_name} ({employee1.email})")
print(f"User ID: {employee1.id}\n")
print(f"Total expenses: {len(expenses)}\n")

# Show last 10 expenses with user details
print("Recent expenses (as API would return them):\n")
for i, exp in enumerate(expenses[-10:], 1):
    # Get expense owner (should be employee1)
    owner = db.query(User).filter(User.id == exp.user_id).first()

    print(f"{i}. {exp.vendor} - ${exp.amount} ({exp.status})")
    print(f"   user_id: {exp.user_id[:8]}...")
    if owner:
        print(f"   user_name: {owner.full_name}")
        print(f"   user_email: {owner.email}")
    else:
        print(f"   user_name: Unknown User (owner not found!)")
        print(f"   user_email: unknown@example.com")
    print()

db.close()
