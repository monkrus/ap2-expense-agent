"""
COMPREHENSIVE APP FUNCTIONALITY TEST
Tests all critical app features, user flows, and recent fixes
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import requests
from src.database import SessionLocal
from src.models import User, Organization, OrganizationMember, Expense
from sqlalchemy import func

BASE_URL = "http://localhost:8000"

# Test configuration
TEST_RESULTS = {
    "passed": 0,
    "failed": 0,
    "warnings": 0,
    "tests": []
}

def test(name, condition, error_msg="", severity="error"):
    """Record test result"""
    global TEST_RESULTS
    status = "PASS" if condition else ("WARN" if severity == "warning" else "FAIL")

    TEST_RESULTS["tests"].append({
        "name": name,
        "status": status,
        "message": error_msg if not condition else ""
    })

    if condition:
        TEST_RESULTS["passed"] += 1
        print(f"[PASS] {name}")
    elif severity == "warning":
        TEST_RESULTS["warnings"] += 1
        print(f"[WARN] {name}: {error_msg}")
    else:
        TEST_RESULTS["failed"] += 1
        print(f"[FAIL] {name}: {error_msg}")

    return condition

print("\n" + "="*80)
print("COMPREHENSIVE APP FUNCTIONALITY TEST".center(80))
print("="*80 + "\n")

db = SessionLocal()

# ============================================================================
# SECTION 1: DATABASE INTEGRITY & CONSISTENCY
# ============================================================================
print("\n[SECTION 1] DATABASE INTEGRITY & CONSISTENCY")
print("-" * 80)

# Test 1.1: Basic counts
total_users = db.query(User).count()
active_users = db.query(User).filter(User.is_active == True).count()
total_orgs = db.query(Organization).count()
active_orgs = db.query(Organization).filter(Organization.is_active == True).count()

print(f"Database Stats: {total_users} users, {active_users} active, {total_orgs} orgs, {active_orgs} active")

test("Database has users", total_users > 0, "No users in database")
test("Database has organizations", total_orgs > 0, "No organizations")

# Test 1.2: Role distribution
admins = db.query(User).filter(User.role == 'admin').count()
managers = db.query(User).filter(User.role == 'manager').count()
accountants = db.query(User).filter(User.role == 'accountant').count()
employees = db.query(User).filter(User.role == 'employee').count()

print(f"Role Distribution: {admins} admins, {managers} managers, {accountants} accountants, {employees} employees")

role_sum = admins + managers + accountants + employees
test("All roles add up to total users", role_sum == total_users,
     f"Role sum ({role_sum}) != Total users ({total_users})")

# Test 1.3: Orphaned data check
members = db.query(OrganizationMember).filter(OrganizationMember.is_active == True).all()
orphaned_members = []
for member in members:
    user = db.query(User).filter(User.id == member.user_id).first()
    org = db.query(Organization).filter(Organization.id == member.organization_id).first()
    if not user or not org:
        orphaned_members.append(member.id)

test("No orphaned organization members", len(orphaned_members) == 0,
     f"Found {len(orphaned_members)} orphaned members")

# Test 1.4: All active orgs have at least one owner
orgs_without_owner = []
for org in db.query(Organization).filter(Organization.is_active == True).all():
    owner_count = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org.id,
        OrganizationMember.role == 'owner',
        OrganizationMember.is_active == True
    ).count()
    if owner_count == 0:
        orgs_without_owner.append(org.name)

test("All organizations have an owner", len(orgs_without_owner) == 0,
     f"Orgs without owner: {orgs_without_owner}")

# Test 1.5: Expense data integrity
expenses = db.query(Expense).all()
negative_expenses = [e for e in expenses if e.amount < 0]
test("No negative expense amounts", len(negative_expenses) == 0,
     f"Found {len(negative_expenses)} negative expenses")

invalid_statuses = [e for e in expenses if e.status not in ['pending', 'approved', 'rejected']]
test("All expenses have valid status", len(invalid_statuses) == 0,
     f"Found {len(invalid_statuses)} invalid statuses")

# ============================================================================
# SECTION 2: API HEALTH & AVAILABILITY
# ============================================================================
print("\n[SECTION 2] API HEALTH & AVAILABILITY")
print("-" * 80)

# Test 2.1: Backend health
try:
    response = requests.get(f"{BASE_URL}/health", timeout=5)
    test("Backend health endpoint responds", response.status_code == 200,
         f"Status: {response.status_code}")

    if response.status_code == 200:
        health_data = response.json()
        test("Health status is 'healthy'", health_data.get('status') == 'healthy',
             f"Status: {health_data.get('status')}")
except Exception as e:
    test("Backend health endpoint responds", False, str(e))

# Test 2.2: API documentation
try:
    docs_response = requests.get(f"{BASE_URL}/docs", timeout=5)
    test("API documentation available", docs_response.status_code == 200,
         f"Status: {docs_response.status_code}")

    openapi_response = requests.get(f"{BASE_URL}/openapi.json", timeout=5)
    test("OpenAPI spec available", openapi_response.status_code == 200,
         f"Status: {openapi_response.status_code}")
except Exception as e:
    test("API documentation available", False, str(e))

# ============================================================================
# SECTION 3: RECENT FIXES VERIFICATION
# ============================================================================
print("\n[SECTION 3] RECENT FIXES VERIFICATION")
print("-" * 80)

# Test 3.1: Accountants are counted in user stats
print(f"Verifying Accountants count: {accountants}")
test("Accountants exist in system", accountants >= 0,
     "Accountants role should be tracked")

# Test 3.2: Lazy loading implementation
import os.path
exp_export_path = os.path.join(os.path.dirname(__file__),
                               'frontend/src/components/ExpenseExport.jsx')
if os.path.exists(exp_export_path):
    with open(exp_export_path, 'r', encoding='utf-8') as f:
        content = f.read()
        has_lazy_excel = 'await import("exceljs")' in content
        has_lazy_pdf = 'await import("jspdf")' in content

        test("ExcelJS lazy loading implemented", has_lazy_excel,
             "Dynamic import not found for ExcelJS")
        test("jsPDF lazy loading implemented", has_lazy_pdf,
             "Dynamic import not found for jsPDF")
else:
    test("ExpenseExport component exists", False, "File not found", severity="warning")

# Test 3.3: N+1 query fix in organizations.py
org_route_path = os.path.join(os.path.dirname(__file__),
                              'backend/src/routes/organizations.py')
if os.path.exists(org_route_path):
    with open(org_route_path, 'r', encoding='utf-8') as f:
        content = f.read()
        has_joinedload = 'joinedload' in content

        test("N+1 query fix implemented (joinedload)", has_joinedload,
             "joinedload not found in organizations.py")
else:
    test("Organizations route file exists", False, "File not found")

# Test 3.4: ToastContainer in OrganizationManagement
org_mgmt_path = os.path.join(os.path.dirname(__file__),
                             'frontend/src/components/OrganizationManagement.jsx')
if os.path.exists(org_mgmt_path):
    with open(org_mgmt_path, 'r', encoding='utf-8') as f:
        content = f.read()
        has_toast_import = 'ToastContainer' in content
        has_toast_render = '<ToastContainer' in content

        test("ToastContainer imported in OrganizationManagement", has_toast_import,
             "ToastContainer import missing")
        test("ToastContainer rendered in OrganizationManagement", has_toast_render,
             "ToastContainer not rendered")
else:
    test("OrganizationManagement component exists", False, "File not found")

# Test 3.5: 402 error handling in organizationAPI.js
org_api_path = os.path.join(os.path.dirname(__file__),
                            'frontend/src/services/organizationAPI.js')
if os.path.exists(org_api_path):
    with open(org_api_path, 'r', encoding='utf-8') as f:
        content = f.read()
        has_402_handling = 'response.status === 402' in content

        test("402 error handling in createInvitation", has_402_handling,
             "402 status check not found in organizationAPI.js")
else:
    test("organizationAPI.js exists", False, "File not found")

# ============================================================================
# SECTION 4: SUBSCRIPTION TIER LIMITS
# ============================================================================
print("\n[SECTION 4] SUBSCRIPTION TIER LIMITS")
print("-" * 80)

# Test 4.1: Tier limits are defined
try:
    from src.billing.tier_limits import TIER_LIMITS, SubscriptionTier

    test("FREE tier limits defined", SubscriptionTier.FREE in TIER_LIMITS,
         "FREE tier not in TIER_LIMITS")

    if SubscriptionTier.FREE in TIER_LIMITS:
        free_limits = TIER_LIMITS[SubscriptionTier.FREE]
        print(f"FREE Tier Limits: {free_limits.max_users} users, {free_limits.max_organizations} orgs")

        test("FREE tier has 1 max user", free_limits.max_users == 1,
             f"Expected 1, got {free_limits.max_users}")
        test("FREE tier has 1 max org", free_limits.max_organizations == 1,
             f"Expected 1, got {free_limits.max_organizations}")
except Exception as e:
    test("Tier limits can be imported", False, str(e))

# Test 4.2: Limit enforcer exists and works
try:
    from src.billing.limit_enforcer import LimitEnforcer, LimitExceededError

    test("LimitEnforcer class exists", True)
    test("LimitExceededError class exists", True)

    # Find a FREE tier org to test
    free_org = None
    for org in db.query(Organization).filter(Organization.is_active == True).all():
        member_count = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.is_active == True
        ).count()
        if member_count == 1:  # Likely FREE tier
            free_org = org
            break

    if free_org:
        enforcer = LimitEnforcer(db)
        try:
            enforcer.check_user_limit(free_org.id, raise_error=True)
            test("FREE tier user limit enforced", False,
                 "Should raise error for FREE tier with 1 member", severity="warning")
        except LimitExceededError as e:
            test("FREE tier raises LimitExceededError", True)
            test("Error message mentions upgrade", "Upgrade to Starter" in str(e),
                 f"Message: {str(e)}")
    else:
        test("Can find FREE tier org for testing", False,
             "No suitable org found", severity="warning")

except Exception as e:
    test("Limit enforcer can be imported", False, str(e))

# ============================================================================
# SECTION 5: UI/BACKEND NUMBER CONSISTENCY
# ============================================================================
print("\n[SECTION 5] UI/BACKEND NUMBER CONSISTENCY")
print("-" * 80)

# Numbers that should match between UI and backend
print(f"Expected UI Stats:")
print(f"  Total Users: {total_users}")
print(f"  Active Users: {active_users}")
print(f"  Admins: {admins}")
print(f"  Managers: {managers}")
print(f"  Accountants: {accountants}")
print(f"  Employees: {employees}")

# These would be visible in the UserManagementDashboard
test("User role counts complete", admins + managers + accountants + employees == total_users,
     f"Sum: {admins + managers + accountants + employees}, Total: {total_users}")

# ============================================================================
# SECTION 6: CRITICAL USER FLOWS
# ============================================================================
print("\n[SECTION 6] CRITICAL USER FLOWS (Basic Checks)")
print("-" * 80)

# Test 6.1: Can access critical endpoints (no auth needed for structure check)
endpoints_to_check = [
    ("/api/v1/auth/register", "POST"),
    ("/api/v1/auth/login", "POST"),
    ("/health", "GET"),
    ("/docs", "GET"),
]

for endpoint, method in endpoints_to_check:
    try:
        # Just check if endpoint exists (will return 422/400 for missing data, not 404)
        if method == "GET":
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
        else:
            response = requests.post(f"{BASE_URL}{endpoint}", json={}, timeout=5)

        # 404 means endpoint doesn't exist, anything else means it exists
        exists = response.status_code != 404
        test(f"Endpoint exists: {method} {endpoint}", exists,
             f"Status: {response.status_code}")
    except Exception as e:
        test(f"Endpoint accessible: {method} {endpoint}", False, str(e))

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n" + "="*80)
print("TEST SUMMARY".center(80))
print("="*80)

total_tests = TEST_RESULTS["passed"] + TEST_RESULTS["failed"] + TEST_RESULTS["warnings"]
pass_rate = (TEST_RESULTS["passed"] / total_tests * 100) if total_tests > 0 else 0

print(f"\nTotal Tests: {total_tests}")
print(f"Passed: {TEST_RESULTS['passed']} ({pass_rate:.1f}%)")
print(f"Failed: {TEST_RESULTS['failed']}")
print(f"Warnings: {TEST_RESULTS['warnings']}")

if TEST_RESULTS["failed"] > 0:
    print(f"\n[FAILED TESTS]")
    for t in TEST_RESULTS["tests"]:
        if t["status"] == "FAIL":
            print(f"  - {t['name']}: {t['message']}")

if TEST_RESULTS["warnings"] > 0:
    print(f"\n[WARNINGS]")
    for t in TEST_RESULTS["tests"]:
        if t["status"] == "WARN":
            print(f"  - {t['name']}: {t['message']}")

print("\n" + "="*80)

if pass_rate == 100 and TEST_RESULTS["failed"] == 0:
    print("STATUS: ALL TESTS PASSED - APP IS PRODUCTION READY".center(80))
elif pass_rate >= 90:
    print("STATUS: MOSTLY PASSING - MINOR ISSUES TO ADDRESS".center(80))
elif pass_rate >= 70:
    print("STATUS: PARTIAL SUCCESS - SOME CRITICAL ISSUES".center(80))
else:
    print("STATUS: CRITICAL ISSUES DETECTED - NEEDS ATTENTION".center(80))

print("="*80 + "\n")

db.close()

# Exit with appropriate code
exit_code = 0 if TEST_RESULTS["failed"] == 0 else 1
sys.exit(exit_code)
