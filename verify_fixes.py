"""
Verify that code fixes are in place and ready for testing
Run this AFTER restarting the backend server
"""

import sys
import os

def check_file_exists(filepath):
    """Check if file exists"""
    return os.path.exists(filepath)

def check_code_in_file(filepath, search_string):
    """Check if specific code exists in file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            return search_string in content
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return False

def main():
    print("=" * 80)
    print("VERIFYING CODE FIXES ARE IN PLACE")
    print("=" * 80)
    print()

    all_checks_passed = True

    # Check 1: Accountant delete permission fix
    print("1. Checking CRITICAL fix: Accountant delete permission...")
    expense_routes = "backend/src/routes/expenses.py"

    if not check_file_exists(expense_routes):
        print(f"   [FAIL] File not found: {expense_routes}")
        all_checks_passed = False
    elif check_code_in_file(expense_routes, "CRITICAL: Accountants cannot delete expenses"):
        print("   [PASS] Accountant delete check found")
        if check_code_in_file(expense_routes, "current_user.role == UserRole.ACCOUNTANT"):
            print("   [PASS] Role check implementation found")
        else:
            print("   [FAIL] Role check implementation missing")
            all_checks_passed = False
    else:
        print("   [FAIL] Accountant delete check not found")
        all_checks_passed = False

    print()

    # Check 2: ExpenseUpdate schema
    print("2. Checking fix: ExpenseUpdate schema for partial updates...")
    schemas_file = "backend/src/schemas.py"

    if not check_file_exists(schemas_file):
        print(f"   [FAIL] File not found: {schemas_file}")
        all_checks_passed = False
    elif check_code_in_file(schemas_file, "class ExpenseUpdate(BaseModel):"):
        print("   [PASS] ExpenseUpdate schema found")
        if check_code_in_file(schemas_file, "Schema for partial expense updates"):
            print("   [PASS] Schema documentation found")
        else:
            print("   [WARN] Schema documentation missing")
    else:
        print("   [FAIL] ExpenseUpdate schema not found")
        all_checks_passed = False

    print()

    # Check 3: Update endpoint uses ExpenseUpdate schema
    print("3. Checking fix: Update endpoint uses typed schema...")

    if check_code_in_file(expense_routes, "data: ExpenseUpdate"):
        print("   [PASS] Update endpoint uses ExpenseUpdate schema")
        if check_code_in_file(expense_routes, "from ..schemas import ExpenseSubmission, ExpenseUpdate"):
            print("   [PASS] ExpenseUpdate imported correctly")
        else:
            print("   [FAIL] ExpenseUpdate import missing")
            all_checks_passed = False
    else:
        print("   [FAIL] Update endpoint still uses generic dict")
        all_checks_passed = False

    print()

    # Check 4: Approval endpoint exists
    print("4. Verifying: Approval endpoint implementation...")

    if check_code_in_file(expense_routes, "async def approve_expense"):
        print("   [PASS] Approval endpoint found")
        if check_code_in_file(expense_routes, "expense.user_id == current_user.id"):
            print("   [PASS] Self-approval prevention found")
        else:
            print("   [WARN] Self-approval check may be missing")
    else:
        print("   [FAIL] Approval endpoint not found")
        all_checks_passed = False

    print()
    print("=" * 80)

    if all_checks_passed:
        print("[OK] ALL CHECKS PASSED - Code fixes are in place!")
        print()
        print("NEXT STEPS:")
        print("1. Restart the backend server:")
        print("   cd backend")
        print("   .venv\\Scripts\\python.exe -m uvicorn src.api:app --host 127.0.0.1 --port 8000 --reload")
        print()
        print("2. Run the test suite:")
        print("   python test_rbac_framework.py")
        print()
        print("3. Expected results:")
        print("   - Pass rate: 85.2% (23/27 tests)")
        print("   - Accountant delete: PASS (403 Forbidden)")
        print("   - Employee update: PASS (200 OK)")
        print()
        sys.exit(0)
    else:
        print("[ERROR] SOME CHECKS FAILED - Review errors above")
        print()
        print("Please verify the code changes were saved correctly.")
        print()
        sys.exit(1)

if __name__ == "__main__":
    main()
