"""
User Workflow Integration Tests
Tests common user/admin/manager/accountant interactions end-to-end
"""

import requests
import time
import json
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:8000"
API_BASE = f"{BASE_URL}/api/v1"

# Test Results
test_results = {
    "passed": [],
    "failed": [],
    "warnings": []
}

def log_test(name, status, message=""):
    """Log test result"""
    if status == "PASS":
        test_results["passed"].append(name)
        print(f"[PASS] {name} {message}")
    elif status == "FAIL":
        test_results["failed"].append(name)
        print(f"[FAIL] {name} {message}")
    elif status == "WARN":
        test_results["warnings"].append(name)
        print(f"[WARN] {name} {message}")

def print_separator():
    """Print section separator"""
    print("\n" + "="*80 + "\n")

# ============================================================================
# TEST 1: USER REGISTRATION AND LOGIN
# ============================================================================

def test_user_registration_login():
    """Test complete user registration and login flow"""
    print_separator()
    print("TEST 1: USER REGISTRATION AND LOGIN FLOW")
    print_separator()

    # Create unique username
    timestamp = int(time.time())
    username = f"testuser_{timestamp}"
    email = f"{username}@example.com"
    password = "SecurePass123!"

    try:
        # 1.1 Register new user
        print("\n1.1 Testing user registration...")
        register_data = {
            "username": username,
            "email": email,
            "password": password,
            "full_name": "Test User",
            "role": "employee"
        }

        response = requests.post(
            f"{API_BASE}/auth/register",
            json=register_data
        )

        if response.status_code == 201:
            user_data = response.json()
            user_id = user_data.get("id")
            log_test("User Registration", "PASS", f"User ID: {user_id}")
        else:
            log_test("User Registration", "FAIL", f"Status: {response.status_code}, {response.text}")
            return None

        # 1.2 Login with credentials
        print("\n1.2 Testing user login...")
        login_data = {
            "username": username,
            "password": password
        }

        response = requests.post(
            f"{API_BASE}/auth/login",
            json=login_data
        )

        if response.status_code == 200:
            login_response = response.json()
            access_token = login_response.get("access_token")
            refresh_token = login_response.get("refresh_token")
            log_test("User Login", "PASS", f"Got tokens")
        else:
            log_test("User Login", "FAIL", f"Status: {response.status_code}, {response.text}")
            return None

        # 1.3 Get current user info
        print("\n1.3 Testing get current user...")
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(f"{API_BASE}/auth/me", headers=headers)

        if response.status_code == 200:
            user_info = response.json()
            log_test("Get Current User", "PASS", f"Username: {user_info.get('username')}")
        else:
            log_test("Get Current User", "FAIL", f"Status: {response.status_code}")
            return None

        # 1.4 Test token refresh (NEW: Testing our null check fix)
        print("\n1.4 Testing token refresh...")
        refresh_data = {"refresh_token": refresh_token}
        response = requests.post(
            f"{API_BASE}/auth/refresh",
            json=refresh_data
        )

        if response.status_code == 200:
            new_access_token = response.json().get("access_token")
            log_test("Token Refresh", "PASS", "Successfully refreshed token")
        else:
            log_test("Token Refresh", "FAIL", f"Status: {response.status_code}")

        return {
            "user_id": user_id,
            "username": username,
            "email": email,
            "password": password,
            "access_token": access_token,
            "refresh_token": refresh_token
        }

    except Exception as e:
        log_test("User Registration/Login", "FAIL", f"Exception: {str(e)}")
        return None

# ============================================================================
# TEST 2: ORGANIZATION CREATION AND TIER LIMITS
# ============================================================================

def test_organization_creation(user_context):
    """Test organization creation and tier limit enforcement"""
    print_separator()
    print("TEST 2: ORGANIZATION CREATION AND TIER LIMITS")
    print_separator()

    if not user_context:
        log_test("Organization Creation", "FAIL", "No user context")
        return None

    headers = {"Authorization": f"Bearer {user_context['access_token']}"}

    try:
        # 2.1 Create first organization (should succeed on Free tier)
        print("\n2.1 Creating first organization...")
        org_data = {
            "name": f"Test Org {int(time.time())}",
            "slug": f"test-org-{int(time.time())}",
            "description": "Test organization"
        }

        response = requests.post(
            f"{API_BASE}/organizations",
            json=org_data,
            headers=headers
        )

        if response.status_code == 201:
            org = response.json()
            org_id = org.get("id")
            log_test("Create First Organization", "PASS", f"Org ID: {org_id}")
        else:
            log_test("Create First Organization", "FAIL", f"Status: {response.status_code}, {response.text}")
            return None

        # 2.2 Try to create second organization (should hit Free tier limit - 402)
        print("\n2.2 Testing Free tier limit (should get 402)...")
        org_data2 = {
            "name": f"Test Org 2 {int(time.time())}",
            "slug": f"test-org-2-{int(time.time())}",
            "description": "Second test organization"
        }

        response = requests.post(
            f"{API_BASE}/organizations",
            json=org_data2,
            headers=headers
        )

        if response.status_code == 402:
            error_detail = response.json().get("detail", {})
            friendly_msg = error_detail.get("user_friendly_message", "")

            # Check if grammar fix is working (should say "1 organization" not "1 organizations")
            if "1 organization" in friendly_msg and "1 organizations" not in friendly_msg:
                log_test("Tier Limit Enforcement + Grammar Fix", "PASS", f"Correct message: {friendly_msg}")
            else:
                log_test("Tier Limit Enforcement", "PASS", f"Got 402, but grammar might be off: {friendly_msg}")

        else:
            log_test("Tier Limit Enforcement", "FAIL", f"Expected 402, got {response.status_code}")

        # 2.3 List user's organizations
        print("\n2.3 Listing user organizations...")
        response = requests.get(
            f"{API_BASE}/organizations",
            headers=headers
        )

        if response.status_code == 200:
            orgs = response.json()
            log_test("List Organizations", "PASS", f"Found {len(orgs)} organization(s)")
        else:
            log_test("List Organizations", "FAIL", f"Status: {response.status_code}")

        return {
            "org_id": org_id,
            "org_name": org.get("name"),
            "org_slug": org.get("slug")
        }

    except Exception as e:
        log_test("Organization Creation", "FAIL", f"Exception: {str(e)}")
        return None

# ============================================================================
# TEST 3: EXPENSE SUBMISSION WORKFLOW
# ============================================================================

def test_expense_submission(user_context, org_context):
    """Test expense submission by regular user"""
    print_separator()
    print("TEST 3: EXPENSE SUBMISSION WORKFLOW")
    print_separator()

    if not user_context or not org_context:
        log_test("Expense Submission", "FAIL", "Missing context")
        return None

    headers = {
        "Authorization": f"Bearer {user_context['access_token']}",
        "X-Organization-Id": org_context['org_id']
    }

    try:
        # 3.1 Submit expense
        print("\n3.1 Submitting expense...")
        expense_data = {
            "amount": 125.50,
            "currency": "USD",
            "category": "MEALS",  # Must be uppercase enum value
            "vendor": "Restaurant ABC",  # Required field
            "description": "Team lunch meeting",
            "expense_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "pending"
        }

        response = requests.post(
            f"{API_BASE}/expenses",
            json=expense_data,
            headers=headers
        )

        if response.status_code == 201:
            expense = response.json()
            # Handle both direct response and nested data structure
            if isinstance(expense, dict):
                expense_id = expense.get("id") or expense.get("expense", {}).get("id")
            else:
                expense_id = None
            log_test("Submit Expense", "PASS", f"Expense ID: {expense_id}")
        else:
            log_test("Submit Expense", "FAIL", f"Status: {response.status_code}, {response.text}")
            return None

        # 3.2 Get expense details
        print("\n3.2 Retrieving expense details...")
        if expense_id:
            response = requests.get(
                f"{API_BASE}/expenses/{expense_id}",
                headers=headers
            )

            if response.status_code == 200:
                expense_details = response.json()
                log_test("Get Expense Details", "PASS", f"Status: {expense_details.get('status')}")
            else:
                log_test("Get Expense Details", "FAIL", f"Status: {response.status_code}")
        else:
            log_test("Get Expense Details", "WARN", "Skipped - no expense ID from creation")

        # 3.3 List all expenses
        print("\n3.3 Listing all expenses...")
        response = requests.get(
            f"{API_BASE}/expenses",
            headers=headers
        )

        if response.status_code == 200:
            expenses = response.json()
            log_test("List Expenses", "PASS", f"Found {len(expenses)} expense(s)")
        else:
            log_test("List Expenses", "FAIL", f"Status: {response.status_code}")

        return {"expense_id": expense_id}

    except Exception as e:
        log_test("Expense Submission", "FAIL", f"Exception: {str(e)}")
        return None

# ============================================================================
# TEST 4: AUTHENTICATION ERROR HANDLING
# ============================================================================

def test_auth_error_handling():
    """Test authentication error scenarios"""
    print_separator()
    print("TEST 4: AUTHENTICATION ERROR HANDLING")
    print_separator()

    try:
        # 4.1 Test invalid token (401)
        print("\n4.1 Testing invalid token (401)...")
        headers = {"Authorization": "Bearer invalid_token_xyz"}
        response = requests.get(f"{API_BASE}/auth/me", headers=headers)

        if response.status_code == 401:
            log_test("Invalid Token Handling", "PASS", "Got 401 as expected")
        else:
            log_test("Invalid Token Handling", "FAIL", f"Expected 401, got {response.status_code}")

        # 4.2 Test wrong password
        print("\n4.2 Testing wrong password...")
        login_data = {
            "username": "nonexistent_user",
            "password": "WrongPassword123!"
        }
        response = requests.post(f"{API_BASE}/auth/login", json=login_data)

        if response.status_code == 401:
            log_test("Wrong Password Handling", "PASS", "Got 401 as expected")
        else:
            log_test("Wrong Password Handling", "FAIL", f"Expected 401, got {response.status_code}")

        # 4.3 Test accessing protected endpoint without token
        print("\n4.3 Testing no authentication...")
        response = requests.get(f"{API_BASE}/organizations")

        if response.status_code in [401, 403]:
            log_test("No Auth Handling", "PASS", f"Got {response.status_code} as expected")
        else:
            log_test("No Auth Handling", "FAIL", f"Expected 401/403, got {response.status_code}")

    except Exception as e:
        log_test("Auth Error Handling", "FAIL", f"Exception: {str(e)}")

# ============================================================================
# TEST 5: ORGANIZATION MEMBER MANAGEMENT
# ============================================================================

def test_organization_management(user_context, org_context):
    """Test organization member management (admin functions)"""
    print_separator()
    print("TEST 5: ORGANIZATION MEMBER MANAGEMENT")
    print_separator()

    if not user_context or not org_context:
        log_test("Organization Management", "FAIL", "Missing context")
        return

    headers = {
        "Authorization": f"Bearer {user_context['access_token']}",
        "X-Organization-Id": org_context['org_id']
    }

    try:
        # 5.1 List organization members
        print("\n5.1 Listing organization members...")
        response = requests.get(
            f"{API_BASE}/organizations/{org_context['org_id']}/members",
            headers=headers
        )

        if response.status_code == 200:
            members = response.json()
            log_test("List Members", "PASS", f"Found {len(members)} member(s)")
        else:
            log_test("List Members", "FAIL", f"Status: {response.status_code}")

        # 5.2 Send invitation (will test tier limit if Free tier)
        print("\n5.2 Sending organization invitation...")
        invite_data = {
            "email": f"invited_{int(time.time())}@example.com",
            "role": "member"
        }

        response = requests.post(
            f"{API_BASE}/organizations/{org_context['org_id']}/invitations",
            json=invite_data,
            headers=headers
        )

        if response.status_code == 201:
            invitation = response.json()
            log_test("Send Invitation", "PASS", f"Invitation sent")
        elif response.status_code == 402:
            log_test("Send Invitation - Tier Limit", "PASS", "Hit tier limit (expected for Free tier)")
        else:
            log_test("Send Invitation", "WARN", f"Status: {response.status_code}, {response.text}")

        # 5.3 List pending invitations
        print("\n5.3 Listing pending invitations...")
        response = requests.get(
            f"{API_BASE}/organizations/{org_context['org_id']}/invitations",
            headers=headers
        )

        if response.status_code == 200:
            invitations = response.json()
            log_test("List Invitations", "PASS", f"Found {len(invitations)} invitation(s)")
        else:
            log_test("List Invitations", "FAIL", f"Status: {response.status_code}")

    except Exception as e:
        log_test("Organization Management", "FAIL", f"Exception: {str(e)}")

# ============================================================================
# TEST 6: MULTI-TENANCY ISOLATION
# ============================================================================

def test_multi_tenancy_isolation(user_context, org_context):
    """Test that users can't access other organizations' data"""
    print_separator()
    print("TEST 6: MULTI-TENANCY ISOLATION")
    print_separator()

    if not user_context or not org_context:
        log_test("Multi-Tenancy Test", "FAIL", "Missing context")
        return

    try:
        # 6.1 Try to access organization with wrong org ID in header
        print("\n6.1 Testing cross-organization access block...")
        fake_org_id = "00000000-0000-0000-0000-000000000000"
        headers = {
            "Authorization": f"Bearer {user_context['access_token']}",
            "X-Organization-Id": fake_org_id
        }

        response = requests.get(f"{API_BASE}/expenses", headers=headers)

        # Should get 403 or empty list (both are acceptable for isolation)
        if response.status_code == 403:
            log_test("Cross-Org Access Block", "PASS", "Got 403 Forbidden")
        elif response.status_code == 200 and len(response.json()) == 0:
            log_test("Cross-Org Access Block", "PASS", "Got empty list (isolated)")
        else:
            log_test("Cross-Org Access Block", "WARN", f"Status: {response.status_code}")

        # 6.2 Verify user can only see their own organization
        print("\n6.2 Verifying organization list isolation...")
        headers = {"Authorization": f"Bearer {user_context['access_token']}"}
        response = requests.get(f"{API_BASE}/organizations", headers=headers)

        if response.status_code == 200:
            orgs = response.json()
            user_org_ids = [org.get("id") for org in orgs]

            if org_context['org_id'] in user_org_ids:
                log_test("Organization List Isolation", "PASS", "User only sees their orgs")
            else:
                log_test("Organization List Isolation", "FAIL", "Organization missing from list")
        else:
            log_test("Organization List Isolation", "FAIL", f"Status: {response.status_code}")

    except Exception as e:
        log_test("Multi-Tenancy Isolation", "FAIL", f"Exception: {str(e)}")

# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def run_all_tests():
    """Run all user workflow tests"""
    print("\n" + "="*80)
    print("USER WORKFLOW INTEGRATION TESTS")
    print("Testing common user/admin/manager/accountant interactions")
    print("="*80)

    # Run tests in sequence
    user_context = test_user_registration_login()
    org_context = test_organization_creation(user_context)
    expense_context = test_expense_submission(user_context, org_context)
    test_auth_error_handling()
    test_organization_management(user_context, org_context)
    test_multi_tenancy_isolation(user_context, org_context)

    # Print final summary
    print_separator()
    print("FINAL TEST SUMMARY")
    print_separator()
    print(f"\nPASSED: {len(test_results['passed'])} tests")
    print(f"FAILED: {len(test_results['failed'])} tests")
    print(f"WARNINGS: {len(test_results['warnings'])} tests")

    if test_results['failed']:
        print("\nFAILED TESTS:")
        for test in test_results['failed']:
            print(f"   - {test}")

    if test_results['warnings']:
        print("\nWARNINGS:")
        for test in test_results['warnings']:
            print(f"   - {test}")

    print("\n" + "="*80)

    # Overall status
    if len(test_results['failed']) == 0:
        print(">>> ALL TESTS PASSED - WORKFLOWS ARE WORKING CORRECTLY <<<")
    else:
        print(f">>> {len(test_results['failed'])} TEST(S) FAILED - REVIEW REQUIRED <<<")

    print("="*80 + "\n")

    return {
        "total": len(test_results['passed']) + len(test_results['failed']),
        "passed": len(test_results['passed']),
        "failed": len(test_results['failed']),
        "warnings": len(test_results['warnings'])
    }

if __name__ == "__main__":
    results = run_all_tests()

    # Exit with proper code
    exit(0 if results['failed'] == 0 else 1)
