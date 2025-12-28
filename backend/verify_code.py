"""Verify the expenses endpoint code is loaded correctly"""
import sys
import inspect

# Import the actual function
from src.routes.expenses import list_expenses

# Get the source code
source = inspect.getsource(list_expenses)

# Check if it contains the new return format
if 'return {"expenses": expense_list}' in source:
    print("OK - Code is CORRECT - returns wrapped format")
    print("\nLooking for user details fetch...")
    if 'expense_owner = db.query(User).filter(User.id == e.user_id).first()' in source:
        print("OK - User details fetch is present")
    else:
        print("ERROR - User details fetch is MISSING")
else:
    print("ERROR - Code is WRONG - still using old return format")
    print("\nActual return statement:")
    for line in source.split('\n'):
        if 'return' in line and 'expense' in line.lower():
            print(f"  {line.strip()}")
