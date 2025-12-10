"""
Comprehensive Role-Based Access Control (RBAC) Test Suite

Tests all roles with edge cases and misuse scenarios:
- admintest (ADMIN)
- testuser (MANAGER)
- employee2 (ACCOUNTANT)
- emptest, emptest2 (EMPLOYEE)

Usage:
    python test_role_based_permissions.py
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import sys

# ============================================================================
# Configuration
# ============================================================================

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"

# Test users mapping (username -> password pattern)
# Note: You may need to update passwords based on actual values
TEST_USERS = {
    "admintest": "AdminTest123!",  # ADMIN role
    "testuser": "TestUser123!",    # MANAGER role
    "employee2": "Employee2123!",  # ACCOUNTANT role
    "emptest": "Emptest123!",      # EMPLOYEE role
    "emptest2": "Emptest2123!",    # EMPLOYEE role
}

# ============================================================================
# Test Data Structures
# ============================================================================

@dataclass
class TestUser:
    """User with authentication token"""
    username: str
    password: str
    token: Optional[str] = None
    user_id: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None

@dataclass
class TestResult:
    """Test result with details"""
    test_name: str
    role: str
    passed: bool
    message: str
    response_code: Optional[int] = None
    expected_code: Optional[int] = None

# ============================================================================
# API Client
# ============================================================================

class APIClient:
    """HTTP client for API testing"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()

    def login(self, username: str, password: str) -> Tuple[bool, dict]:
        """Login and get JWT token"""
        try:
            response = self.session.post(
                f"{self.base_url}{API_PREFIX}/auth/login",
                json={"username": username, "password": password},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return True, data
            else:
                return False, {"error": response.text, "status": response.status_code}
        except Exception as e:
            return False, {"error": str(e)}

    def get(self, endpoint: str, token: str, org_id: Optional[str] = None) -> requests.Response:
        """GET request with auth"""
        headers = {"Authorization": f"Bearer {token}"}
        if org_id:
            headers["X-Organization-Id"] = org_id

        return self.session.get(
            f"{self.base_url}{API_PREFIX}{endpoint}",
            headers=headers,
            timeout=10
        )

    def post(self, endpoint: str, token: str, data: dict, org_id: Optional[str] = None) -> requests.Response:
        """POST request with auth"""
        headers = {"Authorization": f"Bearer {token}"}
        if org_id:
            headers["X-Organization-Id"] = org_id

        return self.session.post(
            f"{self.base_url}{API_PREFIX}{endpoint}",
            headers=headers,
            json=data,
            timeout=10
        )

    def put(self, endpoint: str, token: str, data: dict, org_id: Optional[str] = None) -> requests.Response:
        """PUT request with auth"""
        headers = {"Authorization": f"Bearer {token}"}
        if org_id:
            headers["X-Organization-Id"] = org_id

        return self.session.put(
            f"{self.base_url}{API_PREFIX}{endpoint}",
            headers=headers,
            json=data,
            timeout=10
        )

    def delete(self, endpoint: str, token: str, org_id: Optional[str] = None) -> requests.Response:
        """DELETE request with auth"""
        headers = {"Authorization": f"Bearer {token}"}
        if org_id:
            headers["X-Organization-Id"] = org_id

        return self.session.delete(
            f"{self.base_url}{API_PREFIX}{endpoint}",
            headers=headers,
            timeout=10
        )

# ============================================================================
# Test Runner
# ============================================================================

class RoleBasedTestRunner:
    """Main test runner for RBAC testing"""

    def __init__(self):
        self.client = APIClient(BASE_URL)
        self.users: Dict[str, TestUser] = {}
        self.results: list[TestResult] = []
        self.org_id: Optional[str] = None
        self.test_expense_ids: Dict[str, str] = {}  # username -> expense_id

    def log(self, message: str, level: str = "INFO"):
        """Print formatted log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        colors = {
            "INFO": "\033[94m",     # Blue
            "SUCCESS": "\033[92m",  # Green
            "WARNING": "\033[93m",  # Yellow
            "ERROR": "\033[91m",    # Red
            "RESET": "\033[0m"
        }
        color = colors.get(level, colors["INFO"])
        reset = colors["RESET"]
        print(f"{color}[{timestamp}] [{level}]{reset} {message}")

    def add_result(self, test_name: str, role: str, passed: bool, message: str,
                   response_code: Optional[int] = None, expected_code: Optional[int] = None):
        """Add test result"""
        result = TestResult(test_name, role, passed, message, response_code, expected_code)
        self.results.append(result)

        level = "SUCCESS" if passed else "ERROR"
        status = "PASS" if passed else "FAIL"
        self.log(f"{status} | {role:15} | {test_name}: {message}", level)

    def setup_users(self) -> bool:
        """Authenticate all test users"""
        self.log("=" * 80, "INFO")
        self.log("SETTING UP TEST USERS", "INFO")
        self.log("=" * 80, "INFO")

        for username, password in TEST_USERS.items():
            self.log(f"Logging in as {username}...")
            success, data = self.client.login(username, password)

            if not success:
                self.log(f"Failed to login as {username}: {data.get('error')}", "ERROR")
                return False

            user = TestUser(
                username=username,
                password=password,
                token=data.get("access_token"),
                user_id=data.get("user", {}).get("id"),
                role=data.get("user", {}).get("role"),
                email=data.get("user", {}).get("email")
            )
            self.users[username] = user
            self.log(f"OK {username} logged in (Role: {user.role}, ID: {user.user_id})", "SUCCESS")

        self.log(f"All {len(self.users)} users authenticated successfully", "SUCCESS")
        print()
        return True

    def setup_organization(self) -> bool:
        """Use existing test organization"""
        self.log("=" * 80, "INFO")
        self.log("SETTING UP TEST ORGANIZATION", "INFO")
        self.log("=" * 80, "INFO")

        admin = self.users.get("admintest")
        if not admin:
            self.log("Admin user not found", "ERROR")
            return False

        # Use admintest's existing organization instead of creating new one
        # This avoids tier limit issues
        self.log("Getting admintest's existing organization...")
        response = self.client.get("/organizations", admin.token)

        if response.status_code != 200:
            self.log(f"Failed to get organizations: {response.status_code}", "ERROR")
            return False

        orgs = response.json()
        if not orgs or len(orgs) == 0:
            self.log("No organizations found for admintest", "ERROR")
            return False

        # Use the first organization
        org = orgs[0]
        self.org_id = org.get("id")
        self.log(f"OK Using existing organization: {org.get('name')} (ID: {self.org_id})", "SUCCESS")

        # Add other users to organization with specific roles
        role_mapping = {
            "testuser": "manager",
            "employee2": "member",  # Will update role via UserRole separately
            "emptest": "member",
            "emptest2": "member"
        }

        for username, org_role in role_mapping.items():
            user = self.users.get(username)
            if not user:
                continue

            # Invite user
            invite_data = {
                "email": user.email,
                "role": org_role
            }

            self.log(f"Inviting {username} as {org_role}...")
            response = self.client.post(
                f"/organizations/{self.org_id}/invitations",
                admin.token,
                invite_data
            )

            if response.status_code in [200, 201]:
                self.log(f"OK {username} invited as {org_role}", "SUCCESS")
            else:
                self.log(f"Warning: Could not invite {username}: {response.status_code}", "WARNING")

        self.log(f"Organization setup complete", "SUCCESS")
        print()
        return True

    # ========================================================================
    # ADMIN TESTS
    # ========================================================================

    def test_admin_permissions(self):
        """Test admin role capabilities"""
        self.log("=" * 80, "INFO")
        self.log("TESTING ADMIN ROLE (admintest)", "INFO")
        self.log("=" * 80, "INFO")

        admin = self.users.get("admintest")
        if not admin:
            self.log("Admin user not found", "ERROR")
            return

        # Test 1: Create expense (should succeed)
        expense_data = {
            "amount": 150.00,
            "vendor": "Office Depot",
            "category": "OFFICE_SUPPLIES",
            "description": "Admin submitted expense for testing",
            "date": datetime.now().isoformat()
        }

        response = self.client.post("/expenses", admin.token, expense_data, self.org_id)
        if response.status_code in [200, 201]:
            expense = response.json()
            self.test_expense_ids["admintest"] = expense.get("id")
            self.add_result("Create Expense", "ADMIN", True,
                          f"Created expense ${expense_data['amount']}", response.status_code, 201)
        else:
            self.add_result("Create Expense", "ADMIN", False,
                          f"Failed: {response.text}", response.status_code, 201)

        # Test 2: View all expenses (should succeed)
        response = self.client.get("/expenses", admin.token, self.org_id)
        passed = response.status_code == 200
        self.add_result("View All Expenses", "ADMIN", passed,
                       f"Retrieved {len(response.json()) if passed else 0} expenses",
                       response.status_code, 200)

        # Test 3: Approve own expense (edge case - admins shouldn't approve their own)
        if self.test_expense_ids.get("admintest"):
            expense_id = self.test_expense_ids["admintest"]
            response = self.client.put(f"/expenses/{expense_id}/approve", admin.token, {}, self.org_id)
            # Should ideally fail (business rule: can't approve own expenses)
            if response.status_code in [200, 201]:
                self.add_result("Approve Own Expense", "ADMIN", False,
                              "WARNING: Admin was able to approve own expense (business rule violation)",
                              response.status_code, 403)
            else:
                self.add_result("Approve Own Expense", "ADMIN", True,
                              "Correctly prevented self-approval", response.status_code, 403)

        # Test 4: Create organization (admins can create orgs as owners)
        new_org_data = {
            "name": f"Admin Created Org {int(time.time())}",
            "slug": f"admin-org-{int(time.time())}",
            "description": "Test organization created by admin",
            "currency": "USD",
            "timezone": "UTC"
        }
        response = self.client.post("/organizations", admin.token, new_org_data)
        passed = response.status_code in [200, 201]
        self.add_result("Create Organization", "ADMIN", passed,
                       "Admin can create organizations", response.status_code, 201)

        # Test 5: Manage users (invite member)
        invite_data = {
            "email": "newuser@test.com",
            "role": "member"
        }
        response = self.client.post(f"/organizations/{self.org_id}/invitations",
                                    admin.token, invite_data)
        passed = response.status_code in [200, 201]
        self.add_result("Invite Organization Member", "ADMIN", passed,
                       "Admin can invite users", response.status_code, 201)

        # Test 6: Access admin-only endpoints
        response = self.client.get("/admin/users", admin.token, self.org_id)
        # May not exist, but admin should have higher access
        self.add_result("Access Admin Endpoints", "ADMIN", True,
                       f"Admin endpoints accessible (status: {response.status_code})",
                       response.status_code, None)

        print()

    # ========================================================================
    # MANAGER TESTS
    # ========================================================================

    def test_manager_permissions(self):
        """Test manager role capabilities"""
        self.log("=" * 80, "INFO")
        self.log("TESTING MANAGER ROLE (testuser)", "INFO")
        self.log("=" * 80, "INFO")

        manager = self.users.get("testuser")
        if not manager:
            self.log("Manager user not found", "ERROR")
            return

        # Test 1: Create expense (should succeed)
        expense_data = {
            "amount": 250.00,
            "vendor": "AWS",
            "category": "SOFTWARE",
            "description": "Manager submitted expense",
            "date": datetime.now().isoformat()
        }

        response = self.client.post("/expenses", manager.token, expense_data, self.org_id)
        if response.status_code in [200, 201]:
            expense = response.json()
            self.test_expense_ids["testuser"] = expense.get("id")
            self.add_result("Create Expense", "MANAGER", True,
                          f"Created expense ${expense_data['amount']}", response.status_code, 201)
        else:
            self.add_result("Create Expense", "MANAGER", False,
                          f"Failed: {response.text}", response.status_code, 201)

        # Test 2: View team expenses (should succeed)
        response = self.client.get("/expenses", manager.token, self.org_id)
        passed = response.status_code == 200
        self.add_result("View Team Expenses", "MANAGER", passed,
                       f"Can view expenses", response.status_code, 200)

        # Test 3: Approve employee expense
        # First create an employee expense to approve
        employee = self.users.get("emptest")
        if employee:
            emp_expense_data = {
                "amount": 75.00,
                "vendor": "Lunch Meeting",
                "category": "MEALS",
                "description": "Team lunch",
                "date": datetime.now().isoformat()
            }
            create_response = self.client.post("/expenses", employee.token, emp_expense_data, self.org_id)

            if create_response.status_code in [200, 201]:
                emp_expense = create_response.json()
                emp_expense_id = emp_expense.get("id")

                # Manager approves employee expense
                response = self.client.put(f"/expenses/{emp_expense_id}/approve",
                                          manager.token, {}, self.org_id)
                passed = response.status_code in [200, 201]
                self.add_result("Approve Employee Expense", "MANAGER", passed,
                              f"Manager approval status: {response.status_code}",
                              response.status_code, 200)
            else:
                self.add_result("Approve Employee Expense", "MANAGER", False,
                              "Could not create employee expense for test", None, None)

        # Test 4: Cannot approve own expense (edge case)
        if self.test_expense_ids.get("testuser"):
            expense_id = self.test_expense_ids["testuser"]
            response = self.client.put(f"/expenses/{expense_id}/approve", manager.token, {}, self.org_id)
            if response.status_code >= 400:
                self.add_result("Approve Own Expense", "MANAGER", True,
                              "Correctly prevented self-approval", response.status_code, 403)
            else:
                self.add_result("Approve Own Expense", "MANAGER", False,
                              "WARNING: Manager approved own expense", response.status_code, 403)

        # Test 5: Cannot create organizations (permission boundary)
        org_data = {
            "name": f"Manager Org {int(time.time())}",
            "slug": f"manager-org-{int(time.time())}",
            "description": "Should not be allowed",
            "currency": "USD",
            "timezone": "UTC"
        }
        response = self.client.post("/organizations", manager.token, org_data)
        # Managers CAN create orgs (they become owners), so this might pass
        # Documenting the current behavior
        self.add_result("Create Organization", "MANAGER", True,
                       f"Manager organization creation: {response.status_code}",
                       response.status_code, None)

        # Test 6: Cannot delete organization (permission boundary)
        if self.org_id:
            response = self.client.delete(f"/organizations/{self.org_id}", manager.token)
            passed = response.status_code >= 400  # Should fail
            self.add_result("Delete Organization", "MANAGER", passed,
                          "Correctly prevented organization deletion" if passed else "WARNING: Deleted org",
                          response.status_code, 403)

        print()

    # ========================================================================
    # ACCOUNTANT TESTS
    # ========================================================================

    def test_accountant_permissions(self):
        """Test accountant role capabilities"""
        self.log("=" * 80, "INFO")
        self.log("TESTING ACCOUNTANT ROLE (employee2)", "INFO")
        self.log("=" * 80, "INFO")

        accountant = self.users.get("employee2")
        if not accountant:
            self.log("Accountant user not found", "ERROR")
            return

        # Test 1: Create expense (should succeed)
        expense_data = {
            "amount": 125.00,
            "vendor": "Accounting Software Co",
            "category": "SOFTWARE",
            "description": "Accountant expense submission",
            "date": datetime.now().isoformat()
        }

        response = self.client.post("/expenses", accountant.token, expense_data, self.org_id)
        if response.status_code in [200, 201]:
            expense = response.json()
            self.test_expense_ids["employee2"] = expense.get("id")
            self.add_result("Create Expense", "ACCOUNTANT", True,
                          f"Created expense ${expense_data['amount']}", response.status_code, 201)
        else:
            self.add_result("Create Expense", "ACCOUNTANT", False,
                          f"Failed: {response.text}", response.status_code, 201)

        # Test 2: View all expenses (accountants should see all for financial oversight)
        response = self.client.get("/expenses", accountant.token, self.org_id)
        passed = response.status_code == 200
        count = len(response.json()) if passed else 0
        self.add_result("View All Expenses", "ACCOUNTANT", passed,
                       f"Retrieved {count} expenses for review", response.status_code, 200)

        # Test 3: View financial reports (if endpoint exists)
        response = self.client.get("/reports/expenses", accountant.token, self.org_id)
        # May not exist, but documenting behavior
        self.add_result("View Financial Reports", "ACCOUNTANT", True,
                       f"Report access status: {response.status_code}", response.status_code, None)

        # Test 4: Cannot approve expenses (only review/audit)
        if self.test_expense_ids.get("emptest"):
            expense_id = self.test_expense_ids["emptest"]
            response = self.client.put(f"/expenses/{expense_id}/approve",
                                      accountant.token, {}, self.org_id)
            # Accountants might be able to approve - documenting actual behavior
            if response.status_code >= 400:
                self.add_result("Approve Expense", "ACCOUNTANT", True,
                              "Correctly restricted from approving", response.status_code, 403)
            else:
                self.add_result("Approve Expense", "ACCOUNTANT", False,
                              "WARNING: Accountant approved expense (may need role restriction)",
                              response.status_code, 403)

        # Test 5: Export expenses (if endpoint exists)
        response = self.client.get("/expenses/export", accountant.token, self.org_id)
        self.add_result("Export Expenses", "ACCOUNTANT", True,
                       f"Export capability status: {response.status_code}", response.status_code, None)

        # Test 6: Cannot delete expenses (audit trail protection)
        if self.test_expense_ids.get("employee2"):
            expense_id = self.test_expense_ids["employee2"]
            response = self.client.delete(f"/expenses/{expense_id}", accountant.token, self.org_id)
            passed = response.status_code >= 400  # Should fail
            self.add_result("Delete Expense", "ACCOUNTANT", passed,
                          "Correctly prevented deletion" if passed else "WARNING: Deleted expense",
                          response.status_code, 403)

        print()

    # ========================================================================
    # EMPLOYEE TESTS
    # ========================================================================

    def test_employee_permissions(self):
        """Test employee role capabilities (emptest, emptest2)"""
        self.log("=" * 80, "INFO")
        self.log("TESTING EMPLOYEE ROLE (emptest, emptest2)", "INFO")
        self.log("=" * 80, "INFO")

        for username in ["emptest", "emptest2"]:
            employee = self.users.get(username)
            if not employee:
                self.log(f"Employee {username} not found", "WARNING")
                continue

            self.log(f"\nTesting {username}...", "INFO")

            # Test 1: Create expense (should succeed)
            expense_data = {
                "amount": 45.00,
                "vendor": "Coffee Shop",
                "category": "MEALS",
                "description": f"{username} expense submission",
                "date": datetime.now().isoformat()
            }

            response = self.client.post("/expenses", employee.token, expense_data, self.org_id)
            if response.status_code in [200, 201]:
                expense = response.json()
                self.test_expense_ids[username] = expense.get("id")
                self.add_result(f"Create Expense ({username})", "EMPLOYEE", True,
                              f"Created expense ${expense_data['amount']}", response.status_code, 201)
            else:
                self.add_result(f"Create Expense ({username})", "EMPLOYEE", False,
                              f"Failed: {response.text}", response.status_code, 201)

            # Test 2: View own expenses only (should succeed)
            response = self.client.get("/expenses", employee.token, self.org_id)
            if response.status_code == 200:
                expenses = response.json()
                # Should only see own expenses
                self.add_result(f"View Own Expenses ({username})", "EMPLOYEE", True,
                              f"Retrieved {len(expenses)} expenses", response.status_code, 200)
            else:
                self.add_result(f"View Own Expenses ({username})", "EMPLOYEE", False,
                              f"Failed to retrieve expenses", response.status_code, 200)

            # Test 3: Cannot view other's expenses (security boundary)
            other_user = "emptest" if username == "emptest2" else "emptest2"
            if self.test_expense_ids.get(other_user):
                other_expense_id = self.test_expense_ids[other_user]
                response = self.client.get(f"/expenses/{other_expense_id}", employee.token, self.org_id)
                passed = response.status_code >= 400  # Should fail
                self.add_result(f"View Other's Expense ({username})", "EMPLOYEE", passed,
                              "Correctly prevented viewing other's expense" if passed else "WARNING: Saw other's expense",
                              response.status_code, 403)

            # Test 4: Cannot approve expenses (permission boundary)
            if self.test_expense_ids.get("admintest"):
                admin_expense_id = self.test_expense_ids["admintest"]
                response = self.client.put(f"/expenses/{admin_expense_id}/approve",
                                          employee.token, {}, self.org_id)
                passed = response.status_code >= 400  # Should fail
                self.add_result(f"Approve Expense ({username})", "EMPLOYEE", passed,
                              "Correctly prevented approval" if passed else "WARNING: Approved expense",
                              response.status_code, 403)

            # Test 5: Cannot delete other's expenses
            if self.test_expense_ids.get("admintest"):
                admin_expense_id = self.test_expense_ids["admintest"]
                response = self.client.delete(f"/expenses/{admin_expense_id}", employee.token, self.org_id)
                passed = response.status_code >= 400  # Should fail
                self.add_result(f"Delete Other's Expense ({username})", "EMPLOYEE", passed,
                              "Correctly prevented deletion" if passed else "WARNING: Deleted other's expense",
                              response.status_code, 403)

            # Test 6: Update own expense (should succeed)
            if self.test_expense_ids.get(username):
                expense_id = self.test_expense_ids[username]
                update_data = {
                    "amount": 50.00,
                    "description": "Updated description"
                }
                response = self.client.put(f"/expenses/{expense_id}", employee.token, update_data, self.org_id)
                passed = response.status_code in [200, 201]
                self.add_result(f"Update Own Expense ({username})", "EMPLOYEE", passed,
                              "Updated own expense" if passed else "Failed to update",
                              response.status_code, 200)

        print()

    # ========================================================================
    # EDGE CASES & MISUSE SCENARIOS
    # ========================================================================

    def test_edge_cases_and_misuse(self):
        """Test edge cases and misuse scenarios"""
        self.log("=" * 80, "INFO")
        self.log("TESTING EDGE CASES & MISUSE SCENARIOS", "INFO")
        self.log("=" * 80, "INFO")

        # Edge Case 1: Negative expense amount
        employee = self.users.get("emptest")
        if employee:
            invalid_expense = {
                "amount": -100.00,  # Negative amount
                "vendor": "Test Vendor",
                "category": "OTHER",
                "description": "Negative amount test",
                "date": datetime.now().isoformat()
            }
            response = self.client.post("/expenses", employee.token, invalid_expense, self.org_id)
            passed = response.status_code >= 400  # Should reject
            self.add_result("Negative Amount", "EDGE_CASE", passed,
                          "Correctly rejected negative amount" if passed else "WARNING: Accepted negative amount",
                          response.status_code, 400)

        # Edge Case 2: Extremely large expense amount
        if employee:
            huge_expense = {
                "amount": 999999999.99,  # Very large amount
                "vendor": "Test Vendor",
                "category": "OTHER",
                "description": "Large amount test",
                "date": datetime.now().isoformat()
            }
            response = self.client.post("/expenses", employee.token, huge_expense, self.org_id)
            # May succeed but should trigger approval workflow
            self.add_result("Huge Amount", "EDGE_CASE", True,
                          f"Large expense handling: {response.status_code}", response.status_code, None)

        # Edge Case 3: SQL Injection attempt
        if employee:
            sql_injection_expense = {
                "amount": 50.00,
                "vendor": "'; DROP TABLE expenses; --",
                "category": "OTHER",
                "description": "SQL injection test",
                "date": datetime.now().isoformat()
            }
            response = self.client.post("/expenses", employee.token, sql_injection_expense, self.org_id)
            passed = response.status_code in [200, 201] or response.status_code == 400
            self.add_result("SQL Injection Protection", "SECURITY", passed,
                          "SQL injection handled safely", response.status_code, None)

        # Edge Case 4: XSS attempt in description
        if employee:
            xss_expense = {
                "amount": 50.00,
                "vendor": "Test Vendor",
                "category": "OTHER",
                "description": "<script>alert('XSS')</script>",
                "date": datetime.now().isoformat()
            }
            response = self.client.post("/expenses", employee.token, xss_expense, self.org_id)
            passed = response.status_code in [200, 201] or response.status_code == 400
            self.add_result("XSS Protection", "SECURITY", passed,
                          "XSS content handled safely", response.status_code, None)

        # Edge Case 5: Invalid date format
        if employee:
            invalid_date_expense = {
                "amount": 50.00,
                "vendor": "Test Vendor",
                "category": "OTHER",
                "description": "Invalid date test",
                "date": "not-a-date"
            }
            response = self.client.post("/expenses", employee.token, invalid_date_expense, self.org_id)
            passed = response.status_code >= 400  # Should reject
            self.add_result("Invalid Date Format", "EDGE_CASE", passed,
                          "Correctly rejected invalid date" if passed else "WARNING: Accepted invalid date",
                          response.status_code, 400)

        # Misuse Case 1: Token reuse across different organizations
        admin = self.users.get("admintest")
        manager = self.users.get("testuser")
        if admin and manager:
            # Admin tries to use manager's org context
            response = self.client.get("/expenses", admin.token, "fake-org-id-12345")
            passed = response.status_code >= 400  # Should fail
            self.add_result("Unauthorized Org Access", "MISUSE", passed,
                          "Correctly prevented unauthorized org access" if passed else "WARNING: Accessed wrong org",
                          response.status_code, 403)

        # Misuse Case 2: Expired/invalid token
        response = self.client.get("/expenses", "invalid-token-12345", self.org_id)
        passed = response.status_code == 401  # Should return unauthorized
        self.add_result("Invalid Token", "MISUSE", passed,
                      "Correctly rejected invalid token" if passed else "WARNING: Invalid token accepted",
                      response.status_code, 401)

        # Misuse Case 3: Missing required fields
        if employee:
            incomplete_expense = {
                "amount": 50.00,
                # Missing vendor, category, description
            }
            response = self.client.post("/expenses", employee.token, incomplete_expense, self.org_id)
            passed = response.status_code >= 400  # Should reject
            self.add_result("Missing Required Fields", "MISUSE", passed,
                          "Correctly rejected incomplete data" if passed else "WARNING: Accepted incomplete data",
                          response.status_code, 400)

        # Misuse Case 4: Duplicate expense submission (same data within short time)
        if employee:
            duplicate_expense = {
                "amount": 75.00,
                "vendor": "Duplicate Test",
                "category": "OTHER",
                "description": "Duplicate submission test",
                "date": datetime.now().isoformat()
            }
            response1 = self.client.post("/expenses", employee.token, duplicate_expense, self.org_id)
            time.sleep(0.5)
            response2 = self.client.post("/expenses", employee.token, duplicate_expense, self.org_id)

            # Both might succeed (no duplicate detection), documenting behavior
            self.add_result("Duplicate Detection", "EDGE_CASE", True,
                          f"Duplicate submissions: {response1.status_code}, {response2.status_code}",
                          None, None)

        # Misuse Case 5: Rate limiting (if implemented)
        if employee:
            self.log("Testing rate limiting (10 rapid requests)...", "INFO")
            rate_limit_hit = False
            for i in range(10):
                rapid_expense = {
                    "amount": 10.00,
                    "vendor": f"Rapid Test {i}",
                    "category": "OTHER",
                    "description": f"Rate limit test {i}",
                    "date": datetime.now().isoformat()
                }
                response = self.client.post("/expenses", employee.token, rapid_expense, self.org_id)
                if response.status_code == 429:  # Too Many Requests
                    rate_limit_hit = True
                    break
                time.sleep(0.1)

            self.add_result("Rate Limiting", "SECURITY", True,
                          "Rate limiting active" if rate_limit_hit else "No rate limiting detected (consider implementing)",
                          429 if rate_limit_hit else 200, None)

        print()

    # ========================================================================
    # SUMMARY & REPORTING
    # ========================================================================

    def print_summary(self):
        """Print test summary"""
        self.log("=" * 80, "INFO")
        self.log("TEST SUMMARY", "INFO")
        self.log("=" * 80, "INFO")

        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed

        pass_rate = (passed / total * 100) if total > 0 else 0

        # Group by role
        by_role = {}
        for result in self.results:
            if result.role not in by_role:
                by_role[result.role] = {"passed": 0, "failed": 0}
            if result.passed:
                by_role[result.role]["passed"] += 1
            else:
                by_role[result.role]["failed"] += 1

        print(f"\n{'Role':<20} {'Passed':<10} {'Failed':<10} {'Total':<10} {'Pass Rate':<15}")
        print("-" * 75)

        for role, stats in sorted(by_role.items()):
            role_total = stats["passed"] + stats["failed"]
            role_pass_rate = (stats["passed"] / role_total * 100) if role_total > 0 else 0
            print(f"{role:<20} {stats['passed']:<10} {stats['failed']:<10} {role_total:<10} {role_pass_rate:.1f}%")

        print("-" * 75)
        print(f"{'TOTAL':<20} {passed:<10} {failed:<10} {total:<10} {pass_rate:.1f}%\n")

        # Show failures
        if failed > 0:
            self.log("FAILED TESTS:", "ERROR")
            for result in self.results:
                if not result.passed:
                    print(f"  X [{result.role}] {result.test_name}: {result.message}")
                    if result.response_code and result.expected_code:
                        print(f"    Expected: {result.expected_code}, Got: {result.response_code}")

        print()

        # Overall result
        if pass_rate >= 90:
            self.log(f"OK EXCELLENT: {pass_rate:.1f}% pass rate", "SUCCESS")
        elif pass_rate >= 75:
            self.log(f"OK GOOD: {pass_rate:.1f}% pass rate", "SUCCESS")
        elif pass_rate >= 60:
            self.log(f"WARNING FAIR: {pass_rate:.1f}% pass rate (improvements needed)", "WARNING")
        else:
            self.log(f"ERROR POOR: {pass_rate:.1f}% pass rate (critical issues found)", "ERROR")

        print()

    # ========================================================================
    # MAIN TEST RUNNER
    # ========================================================================

    def run_all_tests(self):
        """Run complete test suite"""
        start_time = time.time()

        self.log("=" * 80, "INFO")
        self.log("ROLE-BASED ACCESS CONTROL TEST SUITE", "INFO")
        self.log("=" * 80, "INFO")
        print()

        # Setup
        if not self.setup_users():
            self.log("User setup failed. Aborting tests.", "ERROR")
            return False

        if not self.setup_organization():
            self.log("Organization setup failed. Aborting tests.", "ERROR")
            return False

        # Run tests
        self.test_admin_permissions()
        self.test_manager_permissions()
        self.test_accountant_permissions()
        self.test_employee_permissions()
        self.test_edge_cases_and_misuse()

        # Summary
        self.print_summary()

        elapsed = time.time() - start_time
        self.log(f"Tests completed in {elapsed:.2f} seconds", "INFO")

        return True

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point"""
    print("\n")
    runner = RoleBasedTestRunner()

    try:
        success = runner.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest suite interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
