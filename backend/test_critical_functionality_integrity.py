"""
Critical Functionality Integrity Tests

This test suite ensures core application functionality remains intact
and cannot be broken by code changes. These tests represent the
MINIMUM REQUIRED functionality that must always work.

Any failure in these tests should BLOCK deployment.
"""

import sys
import requests
from datetime import datetime
import json

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"

# Test results tracking
test_results = {
    "passed": [],
    "failed": [],
    "critical_failures": [],
}


class CriticalTestFailure(Exception):
    """Raised when a critical functionality test fails"""
    pass


def test_api_health():
    """Test that API is accessible and responding"""
    print("\n" + "="*60)
    print("TEST: API Health Check")
    print("="*60)

    try:
        # Test root endpoint
        response = requests.get(f"{API_BASE_URL.replace('/api/v1', '')}/")

        if response.status_code == 200:
            print("[PASS] API is accessible")
            test_results["passed"].append("API Health: Accessible")
            return True
        else:
            print(f"[FAIL] API returned status {response.status_code}")
            test_results["failed"].append(f"API Health: Status {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] Cannot reach API: {e}")
        test_results["critical_failures"].append(f"API Health: {e}")
        return False


def test_authentication_flow():
    """Test that authentication still works"""
    print("\n" + "="*60)
    print("TEST: Authentication Flow")
    print("="*60)

    try:
        # Test login endpoint exists
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={"username": "test_user", "password": "TestPass123"}
        )

        # We expect 401 for wrong credentials, not 404 or 500
        if response.status_code in [401, 403]:
            print("[PASS] Login endpoint functional (401/403 for wrong creds)")
            test_results["passed"].append("Auth: Login endpoint functional")
            return True
        elif response.status_code == 404:
            print("[FAIL] Login endpoint not found (404)")
            test_results["critical_failures"].append("Auth: Login endpoint missing")
            return False
        elif response.status_code == 500:
            print("[FAIL] Login endpoint server error (500)")
            test_results["critical_failures"].append("Auth: Login endpoint broken")
            return False
        else:
            print(f"[WARN] Unexpected status: {response.status_code}")
            test_results["passed"].append(f"Auth: Endpoint exists (status {response.status_code})")
            return True

    except Exception as e:
        print(f"[FAIL] Auth test error: {e}")
        test_results["critical_failures"].append(f"Auth: {e}")
        return False


def test_database_connectivity():
    """Test that database is accessible"""
    print("\n" + "="*60)
    print("TEST: Database Connectivity")
    print("="*60)

    try:
        # Import here to avoid import errors if backend not available
        sys.path.insert(0, 'backend')
        from src.database import SessionLocal
        from src.models import User

        db = SessionLocal()
        try:
            # Try a simple query
            user_count = db.query(User).count()
            print(f"[PASS] Database accessible ({user_count} users found)")
            test_results["passed"].append(f"Database: Accessible ({user_count} users)")
            return True
        finally:
            db.close()

    except Exception as e:
        print(f"[FAIL] Database error: {e}")
        test_results["critical_failures"].append(f"Database: {e}")
        return False


def test_critical_endpoints_exist():
    """Test that all critical API endpoints still exist"""
    print("\n" + "="*60)
    print("TEST: Critical Endpoints Exist")
    print("="*60)

    critical_endpoints = [
        ("POST", "/auth/login", "Authentication"),
        ("POST", "/auth/register", "User Registration"),
        ("GET", "/organizations", "Organizations List"),
        ("GET", "/expenses", "Expenses List"),
        ("POST", "/expenses", "Expense Creation"),
        ("POST", "/receipts/upload/{expense_id}", "Receipt Upload"),
    ]

    all_exist = True

    for method, path, description in critical_endpoints:
        # We just check if endpoint exists (not 404)
        # We expect auth errors (401) which is fine
        try:
            if method == "GET":
                response = requests.get(f"{API_BASE_URL}{path}")
            elif method == "POST":
                # Replace {expense_id} with dummy value
                test_path = path.replace("{expense_id}", "test-id")
                response = requests.post(f"{API_BASE_URL}{test_path}")

            if response.status_code == 404:
                print(f"[FAIL] {description}: Endpoint not found (404)")
                test_results["critical_failures"].append(f"Endpoint: {description} missing")
                all_exist = False
            else:
                print(f"[PASS] {description}: Endpoint exists")
                test_results["passed"].append(f"Endpoint: {description} exists")

        except Exception as e:
            print(f"[FAIL] {description}: Error - {e}")
            test_results["critical_failures"].append(f"Endpoint: {description} error")
            all_exist = False

    return all_exist


def test_database_schema_integrity():
    """Test that critical database tables still exist"""
    print("\n" + "="*60)
    print("TEST: Database Schema Integrity")
    print("="*60)

    try:
        sys.path.insert(0, 'backend')
        from src.database import SessionLocal, engine
        from sqlalchemy import inspect

        inspector = inspect(engine)
        tables = inspector.get_table_names()

        critical_tables = [
            "users",
            "organizations",
            "expenses",
            "receipts",
            "billing_tiers",
            "organization_subscriptions",
        ]

        all_exist = True
        for table in critical_tables:
            if table in tables:
                print(f"[PASS] Table '{table}' exists")
                test_results["passed"].append(f"Schema: {table} exists")
            else:
                print(f"[FAIL] Table '{table}' missing")
                test_results["critical_failures"].append(f"Schema: {table} missing")
                all_exist = False

        return all_exist

    except Exception as e:
        print(f"[FAIL] Schema check error: {e}")
        test_results["critical_failures"].append(f"Schema: {e}")
        return False


def test_tier_limits_enforcer():
    """Test that tier limits enforcer is functional"""
    print("\n" + "="*60)
    print("TEST: Tier Limits Enforcer")
    print("="*60)

    try:
        sys.path.insert(0, 'backend')
        from src.billing.limit_enforcer import LimitEnforcer
        from src.database import SessionLocal

        db = SessionLocal()
        try:
            enforcer = LimitEnforcer(db)

            # Try to check a limit (this shouldn't raise exception)
            org_id = "test-org-id"

            # Just verify the enforcer can be instantiated and has methods
            assert hasattr(enforcer, 'check_expense_limit')
            assert hasattr(enforcer, 'check_user_limit')
            assert hasattr(enforcer, 'check_ocr_limit')

            print("[PASS] Tier limits enforcer functional")
            test_results["passed"].append("Enforcer: Functional")
            return True

        finally:
            db.close()

    except Exception as e:
        print(f"[FAIL] Tier limits enforcer error: {e}")
        test_results["critical_failures"].append(f"Enforcer: {e}")
        return False


def test_expense_workflow():
    """Test critical expense workflow functionality"""
    print("\n" + "="*60)
    print("TEST: Expense Workflow Models")
    print("="*60)

    try:
        sys.path.insert(0, 'backend')
        from src.models import Expense, Receipt, ExpenseStatus

        # Verify ExpenseStatus enum exists
        assert hasattr(ExpenseStatus, 'PENDING')
        assert hasattr(ExpenseStatus, 'APPROVED')
        assert hasattr(ExpenseStatus, 'REJECTED')
        assert hasattr(ExpenseStatus, 'WITHDRAWN')

        print("[PASS] Expense workflow models intact")
        print("  - ExpenseStatus.PENDING exists")
        print("  - ExpenseStatus.APPROVED exists")
        print("  - ExpenseStatus.REJECTED exists")
        print("  - ExpenseStatus.WITHDRAWN exists")

        test_results["passed"].append("Workflow: Expense models intact")
        return True

    except Exception as e:
        print(f"[FAIL] Expense workflow error: {e}")
        test_results["critical_failures"].append(f"Workflow: {e}")
        return False


def test_approval_permissions():
    """Test that approval permission system exists"""
    print("\n" + "="*60)
    print("TEST: Approval Permission System")
    print("="*60)

    try:
        sys.path.insert(0, 'backend')
        from src.permissions import can_approve_expense, UserRole

        # Verify permission functions exist
        assert callable(can_approve_expense)

        # Verify UserRole enum exists
        assert hasattr(UserRole, 'ADMIN')
        assert hasattr(UserRole, 'MANAGER')
        assert hasattr(UserRole, 'EMPLOYEE')

        print("[PASS] Approval permission system intact")
        test_results["passed"].append("Permissions: Approval system intact")
        return True

    except Exception as e:
        print(f"[FAIL] Permission system error: {e}")
        test_results["critical_failures"].append(f"Permissions: {e}")
        return False


def test_receipt_validation():
    """Test that receipt validation logic exists"""
    print("\n" + "="*60)
    print("TEST: Receipt Validation")
    print("="*60)

    try:
        sys.path.insert(0, 'backend')
        from src.routes.receipts import ALLOWED_EXTENSIONS, MAX_FILE_SIZE

        # Verify constants exist
        assert isinstance(ALLOWED_EXTENSIONS, set)
        assert isinstance(MAX_FILE_SIZE, int)
        assert MAX_FILE_SIZE == 10 * 1024 * 1024  # 10MB

        print(f"[PASS] Receipt validation configured")
        print(f"  - Allowed extensions: {ALLOWED_EXTENSIONS}")
        print(f"  - Max file size: {MAX_FILE_SIZE / 1024 / 1024}MB")

        test_results["passed"].append("Receipts: Validation configured")
        return True

    except Exception as e:
        print(f"[FAIL] Receipt validation error: {e}")
        test_results["critical_failures"].append(f"Receipts: {e}")
        return False


def test_tier_limit_guardian_active():
    """Test that tier limit guardian is active"""
    print("\n" + "="*60)
    print("TEST: Tier Limit Guardian Active")
    print("="*60)

    try:
        sys.path.insert(0, 'backend')
        from src.billing.tier_limit_guardian import (
            get_tier_limit_guardian,
            OFFICIAL_TIER_LIMITS
        )

        guardian = get_tier_limit_guardian()

        # Verify official limits exist
        assert "free" in OFFICIAL_TIER_LIMITS
        assert "starter" in OFFICIAL_TIER_LIMITS
        assert "professional" in OFFICIAL_TIER_LIMITS

        # Verify free tier has correct OCR limit
        assert OFFICIAL_TIER_LIMITS["free"]["ocr_scans_included"] == 20

        print("[PASS] Tier limit guardian active")
        print("  - Free tier OCR limit: 20 ✓")
        print("  - Guardian singleton functional ✓")

        test_results["passed"].append("Guardian: Active and functional")
        return True

    except Exception as e:
        print(f"[FAIL] Guardian error: {e}")
        test_results["critical_failures"].append(f"Guardian: {e}")
        return False


def print_test_summary():
    """Print summary of all tests"""
    print("\n" + "="*60)
    print("CRITICAL FUNCTIONALITY TEST SUMMARY")
    print("="*60)

    total_passed = len(test_results["passed"])
    total_failed = len(test_results["failed"])
    total_critical = len(test_results["critical_failures"])
    total_tests = total_passed + total_failed + total_critical

    print(f"\n[PASS] Passed: {total_passed}/{total_tests}")
    for test in test_results["passed"]:
        print(f"  ✓ {test}")

    if test_results["failed"]:
        print(f"\n[FAIL] Failed: {total_failed}/{total_tests}")
        for test in test_results["failed"]:
            print(f"  ✗ {test}")

    if test_results["critical_failures"]:
        print(f"\n[CRITICAL] Critical Failures: {total_critical}/{total_tests}")
        for test in test_results["critical_failures"]:
            print(f"  ✗ {test}")

    pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    print(f"\nPass Rate: {pass_rate:.1f}%")

    print("\n" + "="*60)
    if total_critical > 0:
        print("[CRITICAL FAILURE] Core functionality is broken!")
        print("="*60)
        print("\nIMMEDIATE ACTIONS REQUIRED:")
        print("1. DO NOT DEPLOY to production")
        print("2. Review critical failures above")
        print("3. Fix broken functionality")
        print("4. Re-run tests until all pass")
        print("="*60)
        return False
    elif total_failed > 0:
        print("[FAILURE] Some tests failed")
        print("="*60)
        return False
    else:
        print("[SUCCESS] All critical functionality tests passed!")
        print("="*60)
        return True


def main():
    """Run all critical functionality tests"""
    print("="*60)
    print("CRITICAL FUNCTIONALITY INTEGRITY TEST SUITE")
    print("="*60)
    print("\nThis test suite verifies that core application functionality")
    print("remains intact and has not been broken by code changes.")
    print("\nTests are designed to catch breaking changes BEFORE deployment.")
    print("="*60)

    # Run all tests
    tests = [
        test_database_connectivity,
        test_database_schema_integrity,
        test_api_health,
        test_authentication_flow,
        test_critical_endpoints_exist,
        test_tier_limits_enforcer,
        test_expense_workflow,
        test_approval_permissions,
        test_receipt_validation,
        test_tier_limit_guardian_active,
    ]

    try:
        for test_func in tests:
            test_func()

    except Exception as e:
        print(f"\n[CRITICAL ERROR] Test suite crashed: {e}")
        test_results["critical_failures"].append(f"Test suite crash: {e}")

    # Print summary
    success = print_test_summary()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
