import sys
sys.path.insert(0, 'src')

from src.database import SessionLocal
from src.models import Expense, User

db = SessionLocal()

# Get all expenses
all_expenses = db.query(Expense).all()
print(f"Total expenses in database: {len(all_expenses)}\n")

# Check for expenses with missing or invalid user_id
unknown_expenses = []

for exp in all_expenses:
    if not exp.user_id:
        unknown_expenses.append((exp, "No user_id"))
    else:
        # Check if user exists
        user = db.query(User).filter(User.id == exp.user_id).first()
        if not user:
            unknown_expenses.append((exp, f"User {exp.user_id[:8]}... not found"))
        elif not user.is_active:
            unknown_expenses.append((exp, f"User {user.username} is inactive"))

if unknown_expenses:
    print(f"Found {len(unknown_expenses)} expenses with user issues:\n")
    for exp, issue in unknown_expenses:
        print(f"  - {exp.vendor}: ${exp.amount} ({exp.status})")
        print(f"    Issue: {issue}")
        print(f"    Expense ID: {exp.id[:16]}...")
        print(f"    Created: {exp.created_at}")
        print()
else:
    print("All expenses have valid users!")

db.close()
