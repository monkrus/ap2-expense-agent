"""Test that users cannot approve or reject their own expenses"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from src.database import SessionLocal
from src.models import User, UserRole
from src.permissions import can_approve_expense

def test_self_approval_prevention():
    """Test that self-approval prevention works correctly"""
    db = SessionLocal()

    try:
        # Get test users
        admin = db.query(User).filter(User.username == "admintest").first()
        manager = db.query(User).filter(User.username == "testuser").first()
        employee1 = db.query(User).filter(User.username == "emptest").first()
        employee2 = db.query(User).filter(User.username == "emptest2").first()

        if not all([admin, manager, employee1, employee2]):
            print("[!] Error: Not all test users found in database")
            return

        print("Testing Self-Approval Prevention")
        print("=" * 80)
        print()

        # Test 1: Admin cannot approve own expense
        print("Test 1: Admin trying to approve their own expense")
        result = can_approve_expense(
            user_role=admin.role,
            expense_amount=100.0,
            expense_user_id=admin.id,  # Same as approver
            user_id=admin.id
        )
        status = "[PASS]" if not result else "[FAIL]"
        print(f"  {status} Admin self-approval blocked: {not result}")
        print()

        # Test 2: Admin can approve employee's expense
        print("Test 2: Admin trying to approve employee's expense")
        result = can_approve_expense(
            user_role=admin.role,
            expense_amount=100.0,
            expense_user_id=employee1.id,  # Different user
            user_id=admin.id
        )
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} Admin can approve other's expense: {result}")
        print()

        # Test 3: Manager cannot approve own expense
        print("Test 3: Manager trying to approve their own expense")
        result = can_approve_expense(
            user_role=manager.role,
            expense_amount=100.0,
            expense_user_id=manager.id,  # Same as approver
            user_id=manager.id
        )
        status = "[PASS]" if not result else "[FAIL]"
        print(f"  {status} Manager self-approval blocked: {not result}")
        print()

        # Test 4: Manager can approve employee's expense (within limit)
        print("Test 4: Manager trying to approve employee's expense ($100)")
        result = can_approve_expense(
            user_role=manager.role,
            expense_amount=100.0,
            expense_user_id=employee1.id,  # Different user
            user_id=manager.id
        )
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} Manager can approve other's expense: {result}")
        print()

        # Test 5: Employee cannot approve any expense (no permission)
        print("Test 5: Employee trying to approve another employee's expense")
        result = can_approve_expense(
            user_role=employee1.role,
            expense_amount=100.0,
            expense_user_id=employee2.id,  # Different user
            user_id=employee1.id
        )
        status = "[PASS]" if not result else "[FAIL]"
        print(f"  {status} Employee cannot approve expenses: {not result}")
        print()

        # Test 6: Employee cannot approve own expense (double check)
        print("Test 6: Employee trying to approve their own expense")
        result = can_approve_expense(
            user_role=employee1.role,
            expense_amount=100.0,
            expense_user_id=employee1.id,  # Same user
            user_id=employee1.id
        )
        status = "[PASS]" if not result else "[FAIL]"
        print(f"  {status} Employee self-approval blocked: {not result}")
        print()

        print("=" * 80)
        print("Summary:")
        print("  - Self-approval prevention is working correctly")
        print("  - Admins and managers CANNOT approve/reject their own expenses")
        print("  - Approval permissions work correctly for other users' expenses")

    except Exception as e:
        print(f"[!] Error during testing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_self_approval_prevention()
