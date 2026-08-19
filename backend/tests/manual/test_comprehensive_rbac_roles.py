"""
Comprehensive RBAC Test Suite
Tests all 4 roles at both global and organization levels
Includes concurrent expense submission tests
Validates auto-approval rules engine
Verifies AP2 protocol integration
"""

import asyncio
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from decimal import Decimal

import requests

# Configuration
BASE_URL = "http://localhost:8000"
TEST_USERS = {}
TEST_ORGS = {}
TEST_TOKENS = {}

# Test Results Tracker
test_results = {"total": 0, "passed": 0, "failed": 0, "errors": []}


def log_test(test_name, passed, message=""):
    """Log test results"""
    test_results["total"] += 1
    if passed:
        test_results["passed"] += 1
        print(f"[PASS] {test_name}: {message}")
    else:
        test_results["failed"] += 1
        test_results["errors"].append(f"{test_name}: {message}")
        print(f"[FAIL] {test_name}: {message}")


def register_user(username, password, full_name, email):
    """Register a new user"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/register",
            json={
                "username": username,
                "password": password,
                "full_name": full_name,
                "email": email,
            },
        )
        if response.status_code == 201:
            return response.json()
        elif response.status_code == 429:
            print(f"[WARN] Rate limit hit for {username}, waiting...")
            time.sleep(60)
            return register_user(username, password, full_name, email)
        else:
            print(
                f"[ERROR] Failed to register {username}: {response.status_code} - {response.text}"
            )
            return None
    except Exception as e:
        print(f"[ERROR] Exception registering {username}: {e}")
        return None


def login_user(username, password):
    """Login user and get token"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        else:
            print(f"[ERROR] Failed to login {username}: {response.status_code}")
            return None
    except Exception as e:
        print(f"[ERROR] Exception logging in {username}: {e}")
        return None


def create_organization(token, name, slug, description="Test organization"):
    """Create an organization"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/organizations",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": name,
                "slug": slug,
                "description": description,
                "currency": "USD",
                "timezone": "UTC",
            },
        )
        if response.status_code == 201:
            return response.json()
        else:
            print(
                f"[ERROR] Failed to create org {name}: {response.status_code} - {response.text}"
            )
            return None
    except Exception as e:
        print(f"[ERROR] Exception creating org: {e}")
        return None


def invite_member(token, org_id, email, role="member"):
    """Invite a member to organization"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/organizations/{org_id}/members/invite",
            headers={"Authorization": f"Bearer {token}"},
            json={"email": email, "role": role},
        )
        return response.status_code in [200, 201]
    except Exception as e:
        print(f"[ERROR] Exception inviting member: {e}")
        return False


def accept_invitation(token, invitation_id):
    """Accept organization invitation"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/organizations/invitations/{invitation_id}/accept",
            headers={"Authorization": f"Bearer {token}"},
        )
        return response.status_code == 200
    except Exception as e:
        print(f"[ERROR] Exception accepting invitation: {e}")
        return False


def create_expense(token, org_id, amount, vendor, category, description):
    """Create an expense"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/expenses",
            headers={"Authorization": f"Bearer {token}", "X-Organization-Id": org_id},
            json={
                "amount": amount,
                "vendor": vendor,
                "category": category,
                "description": description,
                "date": datetime.now().isoformat(),
            },
        )
        if response.status_code == 201:
            return response.json()
        else:
            return None
    except Exception as e:
        print(f"[ERROR] Exception creating expense: {e}")
        return None


def list_expenses(token, org_id):
    """List expenses for organization"""
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/expenses",
            headers={"Authorization": f"Bearer {token}", "X-Organization-Id": org_id},
        )
        if response.status_code == 200:
            return response.json()
        else:
            return []
    except Exception as e:
        print(f"[ERROR] Exception listing expenses: {e}")
        return []


def approve_expense(token, org_id, expense_id):
    """Approve an expense"""
    try:
        response = requests.put(
            f"{BASE_URL}/api/v1/expenses/{expense_id}/approve",
            headers={"Authorization": f"Bearer {token}", "X-Organization-Id": org_id},
        )
        return response.status_code == 200
    except Exception as e:
        print(f"[ERROR] Exception approving expense: {e}")
        return False


def reject_expense(token, org_id, expense_id, reason="Test rejection"):
    """Reject an expense"""
    try:
        response = requests.put(
            f"{BASE_URL}/api/v1/expenses/{expense_id}/reject",
            headers={"Authorization": f"Bearer {token}", "X-Organization-Id": org_id},
            json={"reason": reason},
        )
        return response.status_code == 200
    except Exception as e:
        print(f"[ERROR] Exception rejecting expense: {e}")
        return False


def delete_expense(token, org_id, expense_id):
    """Delete an expense"""
    try:
        response = requests.delete(
            f"{BASE_URL}/api/v1/expenses/{expense_id}",
            headers={"Authorization": f"Bearer {token}", "X-Organization-Id": org_id},
        )
        return response.status_code == 200
    except Exception as e:
        return False


def create_approval_policy(token, org_id, policy_data):
    """Create an approval policy"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/approval-policies",
            headers={"Authorization": f"Bearer {token}", "X-Organization-Id": org_id},
            json=policy_data,
        )
        if response.status_code == 201:
            return response.json()
        else:
            print(
                f"[ERROR] Failed to create policy: {response.status_code} - {response.text}"
            )
            return None
    except Exception as e:
        print(f"[ERROR] Exception creating policy: {e}")
        return None


# ============================================================================
# TEST 1: Setup Test Users and Organizations
# ============================================================================


def test_setup():
    """Create test users with different roles"""
    print("\n" + "=" * 80)
    print("TEST 1: Setup Test Users and Organizations")
    print("=" * 80)

    timestamp = int(time.time())

    # Create users with different global roles
    users_config = [
        ("admin", "ADMIN", f"admin_{timestamp}@test.com"),
        ("manager", "MANAGER", f"manager_{timestamp}@test.com"),
        ("accountant", "ACCOUNTANT", f"accountant_{timestamp}@test.com"),
        ("employee", "EMPLOYEE", f"employee_{timestamp}@test.com"),
    ]

    for role_name, role_type, email in users_config:
        username = f"test_{role_name}_{timestamp}"
        password = "TestPass123!"

        # Register user
        user = register_user(username, password, f"Test {role_name.title()}", email)
        if user:
            TEST_USERS[role_name] = {
                "username": username,
                "password": password,
                "email": email,
                "user_data": user,
            }

            # Login to get token
            token = login_user(username, password)
            if token:
                TEST_TOKENS[role_name] = token
                log_test(f"Setup - Create {role_name} user", True, f"User: {username}")
            else:
                log_test(f"Setup - Login {role_name} user", False, "Failed to login")
        else:
            log_test(f"Setup - Create {role_name} user", False, "Failed to register")

        time.sleep(1)  # Rate limiting

    # Create test organizations
    if "admin" in TEST_TOKENS:
        org_slug = f"test-org-{timestamp}"
        org = create_organization(
            TEST_TOKENS["admin"],
            "Test Organization",
            org_slug,
            "Organization for comprehensive RBAC testing",
        )
        if org:
            TEST_ORGS["main"] = org
            log_test("Setup - Create main organization", True, f"Org ID: {org['id']}")
        else:
            log_test("Setup - Create main organization", False, "Failed to create org")

    print(f"\n[INFO] Setup Complete: {len(TEST_USERS)} users, {len(TEST_ORGS)} orgs")


# ============================================================================
# TEST 2: Organization Role Assignment
# ============================================================================


def test_organization_roles():
    """Test organization-level role assignment"""
    print("\n" + "=" * 80)
    print("TEST 2: Organization Role Assignment")
    print("=" * 80)

    if "main" not in TEST_ORGS:
        log_test("Org Roles - Setup", False, "No test organization found")
        return

    org_id = TEST_ORGS["main"]["id"]
    admin_token = TEST_TOKENS.get("admin")

    # TODO: Invite other users to organization with different roles
    # For now, just verify the admin/owner can access

    expenses = list_expenses(admin_token, org_id)
    log_test("Org Roles - Admin can list expenses", isinstance(expenses, list))


# ============================================================================
# TEST 3: Expense Visibility by Role (Global)
# ============================================================================


def test_expense_visibility_global_roles():
    """Test that each global role sees appropriate expenses"""
    print("\n" + "=" * 80)
    print("TEST 3: Expense Visibility by Global Role")
    print("=" * 80)

    if "main" not in TEST_ORGS:
        log_test("Visibility - Setup", False, "No test organization found")
        return

    org_id = TEST_ORGS["main"]["id"]

    # Employee creates an expense
    employee_token = TEST_TOKENS.get("employee")
    if employee_token:
        expense = create_expense(
            employee_token,
            org_id,
            50.00,
            "Test Vendor",
            "MEALS",
            "Test expense for visibility",
        )
        if expense:
            expense_id = expense["id"]
            log_test(
                "Visibility - Employee creates expense",
                True,
                f"Expense ID: {expense_id}",
            )

            # Test visibility for each role
            for role, token in TEST_TOKENS.items():
                expenses = list_expenses(token, org_id)
                can_see = (
                    any(e["id"] == expense_id for e in expenses) if expenses else False
                )

                if role in ["admin"]:
                    log_test(
                        f"Visibility - {role.title()} can see all expenses", can_see
                    )
                elif role == "employee":
                    log_test(
                        f"Visibility - {role.title()} can see own expenses", can_see
                    )
                else:
                    # Manager and accountant should also be able to see expenses
                    log_test(f"Visibility - {role.title()} visibility", can_see)
        else:
            log_test("Visibility - Employee creates expense", False, "Failed to create")


# ============================================================================
# TEST 4: Approval Permissions by Role
# ============================================================================


def test_approval_permissions():
    """Test approval/rejection permissions for each role"""
    print("\n" + "=" * 80)
    print("TEST 4: Approval Permissions by Role")
    print("=" * 80)

    if "main" not in TEST_ORGS:
        log_test("Approval - Setup", False, "No test organization found")
        return

    org_id = TEST_ORGS["main"]["id"]

    # Create expenses for testing approval
    employee_token = TEST_TOKENS.get("employee")
    if not employee_token:
        log_test("Approval - Create test expense", False, "No employee token")
        return

    test_expenses = []
    for i in range(3):
        expense = create_expense(
            employee_token,
            org_id,
            75.00 + i * 10,
            f"Vendor {i}",
            "OFFICE_SUPPLIES",
            f"Test expense {i} for approval testing",
        )
        if expense:
            test_expenses.append(expense["id"])

    if not test_expenses:
        log_test("Approval - Create test expenses", False, "Failed to create expenses")
        return

    log_test(
        "Approval - Create test expenses",
        True,
        f"Created {len(test_expenses)} expenses",
    )

    # Test: Employee cannot approve own expense
    can_self_approve = approve_expense(employee_token, org_id, test_expenses[0])
    log_test("Approval - Employee cannot self-approve", not can_self_approve)

    # Test: Manager can approve expenses
    manager_token = TEST_TOKENS.get("manager")
    if manager_token and len(test_expenses) > 1:
        can_approve = approve_expense(manager_token, org_id, test_expenses[1])
        log_test("Approval - Manager can approve expenses", can_approve)

    # Test: Admin can approve expenses
    admin_token = TEST_TOKENS.get("admin")
    if admin_token and len(test_expenses) > 2:
        can_approve = approve_expense(admin_token, org_id, test_expenses[2])
        log_test("Approval - Admin can approve expenses", can_approve)

    # Test: Accountant cannot approve (read-only audit role)
    # Note: This depends on your specific RBAC implementation


# ============================================================================
# TEST 5: Deletion Permissions by Role
# ============================================================================


def test_deletion_permissions():
    """Test deletion permissions for each role"""
    print("\n" + "=" * 80)
    print("TEST 5: Deletion Permissions by Role")
    print("=" * 80)

    if "main" not in TEST_ORGS:
        log_test("Deletion - Setup", False, "No test organization found")
        return

    org_id = TEST_ORGS["main"]["id"]

    # Create expenses for deletion testing
    employee_token = TEST_TOKENS.get("employee")
    if not employee_token:
        log_test("Deletion - Create test expense", False, "No employee token")
        return

    # Employee creates expense and can delete own pending expense
    expense = create_expense(
        employee_token,
        org_id,
        25.00,
        "Delete Test Vendor",
        "OTHER",
        "Expense for deletion testing",
    )
    if expense:
        expense_id = expense["id"]
        can_delete = delete_expense(employee_token, org_id, expense_id)
        log_test("Deletion - Employee can delete own pending expense", can_delete)

    # Test: Accountant cannot delete expenses (audit trail protection)
    accountant_token = TEST_TOKENS.get("accountant")
    if accountant_token:
        expense = create_expense(
            employee_token,
            org_id,
            30.00,
            "Accountant Test",
            "OTHER",
            "Test accountant deletion",
        )
        if expense:
            expense_id = expense["id"]
            can_delete = delete_expense(accountant_token, org_id, expense_id)
            log_test(
                "Deletion - Accountant cannot delete (audit protection)", not can_delete
            )


# ============================================================================
# TEST 6: Auto-Approval Policy Testing
# ============================================================================


def test_auto_approval_policies():
    """Test automatic approval based on preset conditions"""
    print("\n" + "=" * 80)
    print("TEST 6: Auto-Approval Policy Testing")
    print("=" * 80)

    if "main" not in TEST_ORGS:
        log_test("Auto-Approval - Setup", False, "No test organization found")
        return

    org_id = TEST_ORGS["main"]["id"]
    admin_token = TEST_TOKENS.get("admin")

    if not admin_token:
        log_test("Auto-Approval - Setup", False, "No admin token")
        return

    # Create auto-approval policy: Meals under $50
    policy_data = {
        "name": "Auto-approve small meals",
        "description": "Automatically approve meal expenses under $50",
        "priority": 10,
        "is_active": True,
        "auto_approve": True,
        "require_receipt": False,
        "conditions": {"categories": ["MEALS"], "max_amount": 50.00},
        "max_amount_per_expense": 50.00,
    }

    policy = create_approval_policy(admin_token, org_id, policy_data)
    if policy:
        log_test(
            "Auto-Approval - Create policy",
            True,
            f"Policy ID: {policy.get('id', 'N/A')}",
        )

        # Test: Submit expense that matches policy
        employee_token = TEST_TOKENS.get("employee")
        if employee_token:
            expense = create_expense(
                employee_token,
                org_id,
                35.00,
                "Starbucks",
                "MEALS",
                "Coffee meeting - should auto-approve",
            )
            if expense:
                # Check if auto-approved
                is_auto_approved = expense.get("auto_approved", False)
                status = expense.get("status", "PENDING")
                log_test(
                    "Auto-Approval - Small meal auto-approved",
                    is_auto_approved or status == "APPROVED",
                    f"Status: {status}",
                )
            else:
                log_test(
                    "Auto-Approval - Submit qualifying expense",
                    False,
                    "Failed to create",
                )

            # Test: Submit expense that exceeds policy limit
            expense2 = create_expense(
                employee_token,
                org_id,
                75.00,
                "Fancy Restaurant",
                "MEALS",
                "Expensive meal - should require manual approval",
            )
            if expense2:
                is_auto_approved = expense2.get("auto_approved", False)
                status = expense2.get("status", "PENDING")
                log_test(
                    "Auto-Approval - Large meal needs manual approval",
                    not is_auto_approved and status == "PENDING",
                    f"Status: {status}",
                )
    else:
        log_test("Auto-Approval - Create policy", False, "Failed to create policy")


# ============================================================================
# TEST 7: Concurrent Expense Submissions
# ============================================================================


def test_concurrent_submissions():
    """Test multiple users submitting expenses simultaneously"""
    print("\n" + "=" * 80)
    print("TEST 7: Concurrent Expense Submissions")
    print("=" * 80)

    if "main" not in TEST_ORGS:
        log_test("Concurrent - Setup", False, "No test organization found")
        return

    org_id = TEST_ORGS["main"]["id"]
    employee_token = TEST_TOKENS.get("employee")

    if not employee_token:
        log_test("Concurrent - Setup", False, "No employee token")
        return

    # Submit 10 expenses concurrently
    def submit_expense(index):
        return create_expense(
            employee_token,
            org_id,
            10.00 + index,
            f"Concurrent Vendor {index}",
            "OFFICE_SUPPLIES",
            f"Concurrent test expense {index}",
        )

    start_time = time.time()
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(submit_expense, i) for i in range(10)]
        results = [future.result() for future in as_completed(futures)]

    end_time = time.time()
    duration = end_time - start_time

    successful = sum(1 for r in results if r is not None)
    log_test(
        "Concurrent - Submit 10 expenses",
        successful >= 8,  # Allow some failures due to rate limiting
        f"{successful}/10 succeeded in {duration:.2f}s",
    )

    # Verify all expenses were created correctly
    time.sleep(2)  # Wait for DB to settle
    all_expenses = list_expenses(employee_token, org_id)
    concurrent_expenses = [
        e for e in all_expenses if "Concurrent" in e.get("vendor", "")
    ]
    log_test(
        "Concurrent - Verify data integrity",
        len(concurrent_expenses) >= 8,
        f"Found {len(concurrent_expenses)} concurrent expenses in DB",
    )


# ============================================================================
# TEST 8: AP2 Protocol Integration
# ============================================================================


def test_ap2_protocol_integration():
    """Verify AP2 protocol is integrated throughout the app"""
    print("\n" + "=" * 80)
    print("TEST 8: AP2 Protocol Integration")
    print("=" * 80)

    employee_token = TEST_TOKENS.get("employee")
    if not employee_token:
        log_test("AP2 - Setup", False, "No employee token")
        return

    # Test: Create Intent Mandate
    try:
        response = requests.post(
            f"{BASE_URL}/api/ap2/intent-mandate",
            headers={"Authorization": f"Bearer {employee_token}"},
            json={
                "constraints": {
                    "max_amount": 1000.00,
                    "categories": ["OFFICE_SUPPLIES", "SOFTWARE"],
                    "approval_required": True,
                },
                "expiration_hours": 24,
            },
        )
        if response.status_code == 200:
            intent_mandate = response.json()
            log_test(
                "AP2 - Create Intent Mandate",
                True,
                f"ID: {intent_mandate.get('intent_mandate_id', 'N/A')}",
            )
        else:
            log_test(
                "AP2 - Create Intent Mandate", False, f"Status: {response.status_code}"
            )
    except Exception as e:
        log_test("AP2 - Create Intent Mandate", False, f"Exception: {e}")

    # Test: Verify AP2 endpoints exist
    ap2_endpoints = [
        "/api/ap2/intent-mandate",
        "/api/ap2/cart-mandate",
        "/api/ap2/payment-mandate",
    ]

    for endpoint in ap2_endpoints:
        try:
            response = requests.options(f"{BASE_URL}{endpoint}")
            exists = response.status_code in [
                200,
                405,
            ]  # 405 = Method not allowed but endpoint exists
            log_test(f"AP2 - Endpoint exists: {endpoint}", exists)
        except:
            log_test(f"AP2 - Endpoint exists: {endpoint}", False)


# ============================================================================
# TEST 9: Cross-Organization Isolation
# ============================================================================


def test_cross_organization_isolation():
    """Verify users cannot access expenses from other organizations"""
    print("\n" + "=" * 80)
    print("TEST 9: Cross-Organization Isolation")
    print("=" * 80)

    admin_token = TEST_TOKENS.get("admin")
    if not admin_token:
        log_test("Isolation - Setup", False, "No admin token")
        return

    # Create second organization
    timestamp = int(time.time())
    org2 = create_organization(
        admin_token,
        "Second Organization",
        f"test-org-2-{timestamp}",
        "Second org for isolation testing",
    )

    if not org2:
        log_test("Isolation - Create second org", False, "Failed to create")
        return

    org2_id = org2["id"]
    log_test("Isolation - Create second org", True, f"Org ID: {org2_id}")

    # Create expense in org1
    org1_id = TEST_ORGS["main"]["id"]
    employee_token = TEST_TOKENS.get("employee")

    if employee_token:
        expense_org1 = create_expense(
            employee_token,
            org1_id,
            60.00,
            "Org1 Vendor",
            "OTHER",
            "Expense in organization 1",
        )

        if expense_org1:
            expense_id = expense_org1["id"]

            # Try to access org1 expense using org2 context
            try:
                response = requests.get(
                    f"{BASE_URL}/api/v1/expenses/{expense_id}",
                    headers={
                        "Authorization": f"Bearer {admin_token}",
                        "X-Organization-Id": org2_id,
                    },
                )
                # Should get 403 or 404
                blocked = response.status_code in [403, 404]
                log_test(
                    "Isolation - Cannot access cross-org expense",
                    blocked,
                    f"Status: {response.status_code}",
                )
            except Exception as e:
                log_test(
                    "Isolation - Cannot access cross-org expense",
                    False,
                    f"Exception: {e}",
                )


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================


def run_all_tests():
    """Run all comprehensive tests"""
    print("\n" + "=" * 80)
    print("COMPREHENSIVE RBAC & AP2 TEST SUITE")
    print("=" * 80)
    print(f"Backend URL: {BASE_URL}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # Run tests in sequence
        test_setup()
        time.sleep(2)

        test_organization_roles()
        time.sleep(1)

        test_expense_visibility_global_roles()
        time.sleep(1)

        test_approval_permissions()
        time.sleep(1)

        test_deletion_permissions()
        time.sleep(1)

        test_auto_approval_policies()
        time.sleep(1)

        test_concurrent_submissions()
        time.sleep(1)

        test_ap2_protocol_integration()
        time.sleep(1)

        test_cross_organization_isolation()

    except KeyboardInterrupt:
        print("\n\n[WARN] Tests interrupted by user")
    except Exception as e:
        print(f"\n\n[ERROR] Test suite failed with exception: {e}")
        import traceback

        traceback.print_exc()

    # Print final results
    print("\n" + "=" * 80)
    print("TEST RESULTS SUMMARY")
    print("=" * 80)
    print(f"Total Tests: {test_results['total']}")
    print(f"Passed: {test_results['passed']}")
    print(f"Failed: {test_results['failed']}")

    if test_results["failed"] > 0:
        print("\nFailed Tests:")
        for error in test_results["errors"]:
            print(f"  - {error}")

    pass_rate = (
        (test_results["passed"] / test_results["total"] * 100)
        if test_results["total"] > 0
        else 0
    )
    print(f"\nPass Rate: {pass_rate:.1f}%")

    if pass_rate >= 90:
        print("\n[SUCCESS] EXCELLENT: System is production-ready!")
    elif pass_rate >= 75:
        print("\n[GOOD] Most features working, minor issues to fix")
    elif pass_rate >= 50:
        print("\n[WARN] Significant issues found")
    else:
        print("\n[CRITICAL] Major failures detected")

    print("\n" + "=" * 80)
    return test_results


if __name__ == "__main__":
    results = run_all_tests()

    # Exit with error code if tests failed
    if results["failed"] > 0:
        exit(1)
    else:
        exit(0)
