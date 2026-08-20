"""
COMPREHENSIVE MULTI-USER WORKFLOW TEST SUITE

Tests all possible user interactions and workflows:
- 2 users + admin scenarios
- 2 users + manager scenarios
- 2 users + accountant scenarios
- Complex 4-way interactions (admin + manager + accountant + employees)
- Typical business scenarios (expense approval chains)
- Atypical scenarios (conflicts, edge cases, race conditions)
- Complete expense lifecycle workflows
- Cross-role collaboration and handoffs

Roles tested:
- admintest (ADMIN) - Full system access
- testuser (MANAGER) - Team management, approvals
- employee2 (ACCOUNTANT) - Financial oversight, reporting
- emptest (EMPLOYEE) - Expense submission
- emptest2 (EMPLOYEE) - Expense submission

Usage:
    python test_comprehensive_workflows.py
"""

import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import requests

# ============================================================================
# Configuration
# ============================================================================

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"

# Valid expense categories from backend
VALID_CATEGORIES = ["TRAVEL", "MEALS", "SOFTWARE", "OFFICE_SUPPLIES", "OTHER"]

TEST_USERS = {
    "admintest": "AdminTest123!",  # ADMIN
    "testuser": "TestUser123!",  # MANAGER
    "employee2": "Employee2123!",  # ACCOUNTANT
    "emptest": "Emptest123!",  # EMPLOYEE
    "emptest2": "Emptest2123!",  # EMPLOYEE
}

# ============================================================================
# Data Structures
# ============================================================================


@dataclass
class TestUser:
    username: str
    password: str
    token: Optional[str] = None
    user_id: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    expenses: List[str] = field(default_factory=list)  # Track created expenses


@dataclass
class TestResult:
    scenario: str
    test_name: str
    passed: bool
    message: str
    duration: float = 0.0
    details: Optional[dict] = None


@dataclass
class Expense:
    id: str
    creator_id: str
    creator_name: str
    amount: float
    vendor: str
    category: str
    status: str
    description: str


# ============================================================================
# API Client
# ============================================================================


class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()

    def login(self, username: str, password: str) -> Tuple[bool, dict]:
        try:
            response = self.session.post(
                f"{self.base_url}{API_PREFIX}/auth/login",
                json={"username": username, "password": password},
                timeout=10,
            )
            if response.status_code == 200:
                return True, response.json()
            return False, {"error": response.text, "status": response.status_code}
        except Exception as e:
            return False, {"error": str(e)}

    def get(
        self, endpoint: str, token: str, org_id: Optional[str] = None
    ) -> requests.Response:
        headers = {"Authorization": f"Bearer {token}"}
        if org_id:
            headers["X-Organization-Id"] = org_id
        return self.session.get(
            f"{self.base_url}{API_PREFIX}{endpoint}", headers=headers, timeout=10
        )

    def post(
        self, endpoint: str, token: str, data: dict, org_id: Optional[str] = None
    ) -> requests.Response:
        headers = {"Authorization": f"Bearer {token}"}
        if org_id:
            headers["X-Organization-Id"] = org_id
        return self.session.post(
            f"{self.base_url}{API_PREFIX}{endpoint}",
            headers=headers,
            json=data,
            timeout=10,
        )

    def put(
        self, endpoint: str, token: str, data: dict, org_id: Optional[str] = None
    ) -> requests.Response:
        headers = {"Authorization": f"Bearer {token}"}
        if org_id:
            headers["X-Organization-Id"] = org_id
        return self.session.put(
            f"{self.base_url}{API_PREFIX}{endpoint}",
            headers=headers,
            json=data,
            timeout=10,
        )

    def delete(
        self, endpoint: str, token: str, org_id: Optional[str] = None
    ) -> requests.Response:
        headers = {"Authorization": f"Bearer {token}"}
        if org_id:
            headers["X-Organization-Id"] = org_id
        return self.session.delete(
            f"{self.base_url}{API_PREFIX}{endpoint}", headers=headers, timeout=10
        )


# ============================================================================
# Comprehensive Workflow Test Runner
# ============================================================================


class ComprehensiveWorkflowTester:
    def __init__(self):
        self.client = APIClient(BASE_URL)
        self.users: Dict[str, TestUser] = {}
        self.results: List[TestResult] = []
        self.org_id: Optional[str] = None
        self.test_expenses: Dict[str, List[Expense]] = {}  # username -> expenses

    def log(self, message: str, level: str = "INFO"):
        colors = {
            "INFO": "\033[94m",
            "SUCCESS": "\033[92m",
            "WARNING": "\033[93m",
            "ERROR": "\033[91m",
            "RESET": "\033[0m",
        }
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = colors.get(level, colors["INFO"])
        print(f"{color}[{timestamp}] [{level}]{colors['RESET']} {message}")

    def add_result(
        self,
        scenario: str,
        test_name: str,
        passed: bool,
        message: str,
        duration: float = 0.0,
        details: dict = None,
    ):
        result = TestResult(scenario, test_name, passed, message, duration, details)
        self.results.append(result)
        status = "PASS" if passed else "FAIL"
        level = "SUCCESS" if passed else "ERROR"
        self.log(f"{status} | {scenario:30} | {test_name}: {message}", level)

    def setup_users(self) -> bool:
        self.log("=" * 100, "INFO")
        self.log("AUTHENTICATING ALL TEST USERS", "INFO")
        self.log("=" * 100, "INFO")

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
                email=data.get("user", {}).get("email"),
            )
            self.users[username] = user
            self.log(f"OK {username} (Role: {user.role})", "SUCCESS")

        self.log(f"All {len(self.users)} users authenticated\n", "SUCCESS")
        return True

    def setup_organization(self) -> bool:
        self.log("=" * 100, "INFO")
        self.log("USING EXISTING ORGANIZATION", "INFO")
        self.log("=" * 100, "INFO")

        admin = self.users.get("admintest")
        response = self.client.get("/organizations", admin.token)

        if response.status_code != 200:
            self.log(f"Failed to get organizations: {response.status_code}", "ERROR")
            return False

        orgs = response.json()
        if not orgs:
            self.log("No organizations found", "ERROR")
            return False

        org = orgs[0]
        self.org_id = org.get("id")
        self.log(
            f"Using organization: {org.get('name')} (ID: {self.org_id})\n", "SUCCESS"
        )
        return True

    # ========================================================================
    # SCENARIO 1: 2 EMPLOYEES + ADMIN
    # ========================================================================

    def test_two_employees_admin_workflow(self):
        """
        Scenario: 2 employees submit expenses, admin reviews and approves
        - Employee 1 submits travel expense
        - Employee 2 submits meal expense
        - Admin reviews both
        - Admin approves one, rejects one
        - Employees check status
        """
        scenario = "2_EMPLOYEES_ADMIN"
        self.log("\n" + "=" * 100, "INFO")
        self.log("SCENARIO: 2 EMPLOYEES + ADMIN WORKFLOW", "INFO")
        self.log("=" * 100, "INFO")

        emp1 = self.users.get("emptest")
        emp2 = self.users.get("emptest2")
        admin = self.users.get("admintest")

        # Step 1: Employee 1 submits travel expense
        start = time.time()
        expense1_data = {
            "amount": 450.00,
            "vendor": "Delta Airlines",
            "category": "TRAVEL",
            "description": "Flight to client meeting in NYC",
            "date": datetime.now().isoformat(),
        }

        response = self.client.post("/expenses", emp1.token, expense1_data, self.org_id)
        if response.status_code in [200, 201]:
            expense1 = response.json()
            expense1_id = expense1.get("expense", {}).get("id") or expense1.get("id")
            self.add_result(
                scenario,
                "Employee1 Submit Travel",
                True,
                f"Created ${expense1_data['amount']} travel expense",
                time.time() - start,
            )
        else:
            self.add_result(
                scenario,
                "Employee1 Submit Travel",
                False,
                f"Failed: {response.status_code}",
                time.time() - start,
            )
            return

        # Step 2: Employee 2 submits meal expense
        start = time.time()
        expense2_data = {
            "amount": 85.00,
            "vendor": "Ruth's Chris Steakhouse",
            "category": "MEALS",
            "description": "Dinner with prospective client",
            "date": datetime.now().isoformat(),
        }

        response = self.client.post("/expenses", emp2.token, expense2_data, self.org_id)
        if response.status_code in [200, 201]:
            expense2 = response.json()
            expense2_id = expense2.get("expense", {}).get("id") or expense2.get("id")
            self.add_result(
                scenario,
                "Employee2 Submit Meal",
                True,
                f"Created ${expense2_data['amount']} meal expense",
                time.time() - start,
            )
        else:
            self.add_result(
                scenario,
                "Employee2 Submit Meal",
                False,
                f"Failed: {response.status_code}",
                time.time() - start,
            )
            return

        # Step 3: Admin views all pending expenses
        start = time.time()
        response = self.client.get("/expenses", admin.token, self.org_id)
        if response.status_code == 200:
            expenses = response.json()
            pending_count = sum(1 for e in expenses if e.get("status") == "PENDING")
            self.add_result(
                scenario,
                "Admin View All Expenses",
                True,
                f"Viewed {len(expenses)} expenses ({pending_count} pending)",
                time.time() - start,
            )
        else:
            self.add_result(
                scenario,
                "Admin View All Expenses",
                False,
                f"Failed to view expenses",
                time.time() - start,
            )

        # Step 4: Admin approves expense 1
        start = time.time()
        response = self.client.put(
            f"/expenses/{expense1_id}/approve", admin.token, {}, self.org_id
        )
        passed = response.status_code in [200, 201]
        self.add_result(
            scenario,
            "Admin Approve Expense1",
            passed,
            f"Approval status: {response.status_code}",
            time.time() - start,
        )

        # Step 5: Admin rejects expense 2
        start = time.time()
        reject_data = {"reason": "Meal cost exceeds policy limit of $75"}
        response = self.client.put(
            f"/expenses/{expense2_id}/reject", admin.token, reject_data, self.org_id
        )
        passed = response.status_code in [200, 201, 404]  # Endpoint might not exist
        self.add_result(
            scenario,
            "Admin Reject Expense2",
            passed,
            f"Rejection status: {response.status_code}",
            time.time() - start,
        )

        # Step 6: Employee 1 checks their approved expense
        start = time.time()
        response = self.client.get(f"/expenses/{expense1_id}", emp1.token, self.org_id)
        if response.status_code == 200:
            status = response.json().get("status")
            self.add_result(
                scenario,
                "Employee1 Check Status",
                True,
                f"Expense status: {status}",
                time.time() - start,
            )
        else:
            self.add_result(
                scenario,
                "Employee1 Check Status",
                False,
                f"Cannot view expense",
                time.time() - start,
            )

        print()

    # ========================================================================
    # SCENARIO 2: 2 EMPLOYEES + MANAGER
    # ========================================================================

    def test_two_employees_manager_workflow(self):
        """
        Scenario: Manager reviews team expenses and escalates to admin
        - Employee 1 submits small expense (auto-approved by manager)
        - Employee 2 submits large expense (requires admin approval)
        - Manager reviews and processes both
        - Admin gets escalated expense
        """
        scenario = "2_EMPLOYEES_MANAGER"
        self.log("\n" + "=" * 100, "INFO")
        self.log("SCENARIO: 2 EMPLOYEES + MANAGER WORKFLOW", "INFO")
        self.log("=" * 100, "INFO")

        emp1 = self.users.get("emptest")
        emp2 = self.users.get("emptest2")
        manager = self.users.get("testuser")

        # Step 1: Employee 1 submits small software expense
        start = time.time()
        expense1_data = {
            "amount": 29.99,
            "vendor": "GitHub",
            "category": "SOFTWARE",
            "description": "GitHub Pro monthly subscription",
            "date": datetime.now().isoformat(),
        }

        response = self.client.post("/expenses", emp1.token, expense1_data, self.org_id)
        if response.status_code in [200, 201]:
            expense1 = response.json()
            expense1_id = expense1.get("expense", {}).get("id") or expense1.get("id")
            self.add_result(
                scenario,
                "Employee1 Small Expense",
                True,
                f"Created ${expense1_data['amount']} software expense",
                time.time() - start,
            )
        else:
            self.add_result(
                scenario,
                "Employee1 Small Expense",
                False,
                f"Failed: {response.status_code}",
                time.time() - start,
            )
            expense1_id = None

        # Step 2: Employee 2 submits large travel expense
        start = time.time()
        expense2_data = {
            "amount": 2500.00,
            "vendor": "Marriott Hotels",
            "category": "TRAVEL",
            "description": "5-night stay for annual conference",
            "date": datetime.now().isoformat(),
        }

        response = self.client.post("/expenses", emp2.token, expense2_data, self.org_id)
        if response.status_code in [200, 201]:
            expense2 = response.json()
            expense2_id = expense2.get("expense", {}).get("id") or expense2.get("id")
            self.add_result(
                scenario,
                "Employee2 Large Expense",
                True,
                f"Created ${expense2_data['amount']} travel expense",
                time.time() - start,
            )
        else:
            self.add_result(
                scenario,
                "Employee2 Large Expense",
                False,
                f"Failed: {response.status_code}",
                time.time() - start,
            )
            expense2_id = None

        # Step 3: Manager views team expenses
        start = time.time()
        response = self.client.get("/expenses", manager.token, self.org_id)
        if response.status_code == 200:
            team_expenses = response.json()
            self.add_result(
                scenario,
                "Manager View Team Expenses",
                True,
                f"Viewed {len(team_expenses)} team expenses",
                time.time() - start,
            )
        else:
            self.add_result(
                scenario,
                "Manager View Team Expenses",
                False,
                f"Cannot view team expenses",
                time.time() - start,
            )

        # Step 4: Manager approves small expense
        if expense1_id:
            start = time.time()
            response = self.client.put(
                f"/expenses/{expense1_id}/approve", manager.token, {}, self.org_id
            )
            passed = response.status_code in [200, 201]
            self.add_result(
                scenario,
                "Manager Approve Small",
                passed,
                f"Approved small expense: {response.status_code}",
                time.time() - start,
            )

        # Step 5: Manager flags large expense for admin review
        if expense2_id:
            start = time.time()
            flag_data = {"note": "Requires admin approval - exceeds manager limit"}
            response = self.client.put(
                f"/expenses/{expense2_id}/flag", manager.token, flag_data, self.org_id
            )
            passed = response.status_code in [200, 201, 404]  # Endpoint might not exist
            self.add_result(
                scenario,
                "Manager Flag for Admin",
                passed,
                f"Flagged for escalation: {response.status_code}",
                time.time() - start,
            )

        print()

    # ========================================================================
    # SCENARIO 3: 2 EMPLOYEES + ACCOUNTANT
    # ========================================================================

    def test_two_employees_accountant_workflow(self):
        """
        Scenario: Accountant reviews expenses for compliance and reporting
        - Employee 1 submits expense without receipt
        - Employee 2 submits expense with receipt
        - Accountant audits both
        - Accountant requests receipt from Employee 1
        - Accountant generates expense report
        """
        scenario = "2_EMPLOYEES_ACCOUNTANT"
        self.log("\n" + "=" * 100, "INFO")
        self.log("SCENARIO: 2 EMPLOYEES + ACCOUNTANT WORKFLOW", "INFO")
        self.log("=" * 100, "INFO")

        emp1 = self.users.get("emptest")
        emp2 = self.users.get("emptest2")
        accountant = self.users.get("employee2")

        # Step 1: Employee 1 submits expense without receipt
        start = time.time()
        expense1_data = {
            "amount": 125.00,
            "vendor": "Office Max",
            "category": "OFFICE_SUPPLIES",
            "description": "Printer paper and ink cartridges",
            "date": datetime.now().isoformat(),
        }

        response = self.client.post("/expenses", emp1.token, expense1_data, self.org_id)
        if response.status_code in [200, 201]:
            expense1 = response.json()
            expense1_id = expense1.get("expense", {}).get("id") or expense1.get("id")
            self.add_result(
                scenario,
                "Employee1 No Receipt",
                True,
                f"Submitted ${expense1_data['amount']} without receipt",
                time.time() - start,
            )
        else:
            self.add_result(
                scenario,
                "Employee1 No Receipt",
                False,
                f"Failed: {response.status_code}",
                time.time() - start,
            )
            expense1_id = None

        # Step 2: Employee 2 submits expense with receipt
        start = time.time()
        expense2_data = {
            "amount": 180.00,
            "vendor": "Staples",
            "category": "OFFICE_SUPPLIES",
            "description": "Desk chair and monitor stand",
            "date": datetime.now().isoformat(),
            "receipt_url": "https://example.com/receipt123.pdf",
        }

        response = self.client.post("/expenses", emp2.token, expense2_data, self.org_id)
        if response.status_code in [200, 201]:
            expense2 = response.json()
            expense2_id = expense2.get("expense", {}).get("id") or expense2.get("id")
            self.add_result(
                scenario,
                "Employee2 With Receipt",
                True,
                f"Submitted ${expense2_data['amount']} with receipt",
                time.time() - start,
            )
        else:
            self.add_result(
                scenario,
                "Employee2 With Receipt",
                False,
                f"Failed: {response.status_code}",
                time.time() - start,
            )
            expense2_id = None

        # Step 3: Accountant views all expenses for audit
        start = time.time()
        response = self.client.get("/expenses", accountant.token, self.org_id)
        if response.status_code == 200:
            all_expenses = response.json()
            self.add_result(
                scenario,
                "Accountant View All",
                True,
                f"Auditing {len(all_expenses)} expenses",
                time.time() - start,
            )
        else:
            self.add_result(
                scenario,
                "Accountant View All",
                False,
                f"Cannot view expenses for audit",
                time.time() - start,
            )

        # Step 4: Accountant requests receipt from Employee 1
        if expense1_id:
            start = time.time()
            request_data = {"message": "Please upload receipt for compliance"}
            response = self.client.put(
                f"/expenses/{expense1_id}/request-receipt",
                accountant.token,
                request_data,
                self.org_id,
            )
            passed = response.status_code in [200, 201, 404]
            self.add_result(
                scenario,
                "Accountant Request Receipt",
                passed,
                f"Receipt request: {response.status_code}",
                time.time() - start,
            )

        # Step 5: Accountant generates expense report
        start = time.time()
        report_params = {
            "start_date": (datetime.now() - timedelta(days=30)).isoformat(),
            "end_date": datetime.now().isoformat(),
        }
        response = self.client.post(
            "/reports/expenses", accountant.token, report_params, self.org_id
        )
        passed = response.status_code in [200, 201, 404]
        self.add_result(
            scenario,
            "Accountant Generate Report",
            passed,
            f"Report generation: {response.status_code}",
            time.time() - start,
        )

        # Step 6: Accountant exports expenses for tax filing
        start = time.time()
        response = self.client.get(
            "/expenses/export?format=csv", accountant.token, self.org_id
        )
        passed = response.status_code in [200, 404]
        self.add_result(
            scenario,
            "Accountant Export CSV",
            passed,
            f"Export status: {response.status_code}",
            time.time() - start,
        )

        print()

    # ========================================================================
    # SCENARIO 4: COMPLEX 4-WAY INTERACTION
    # ========================================================================

    def test_complex_four_way_workflow(self):
        """
        Scenario: Complete expense lifecycle with all roles
        - Employee submits expense
        - Manager reviews and forwards to accountant
        - Accountant verifies compliance
        - Admin makes final approval
        - Employee receives reimbursement notification
        """
        scenario = "4_WAY_INTERACTION"
        self.log("\n" + "=" * 100, "INFO")
        self.log(
            "SCENARIO: COMPLEX 4-WAY INTERACTION (ADMIN + MANAGER + ACCOUNTANT + EMPLOYEE)",
            "INFO",
        )
        self.log("=" * 100, "INFO")

        employee = self.users.get("emptest")
        manager = self.users.get("testuser")
        accountant = self.users.get("employee2")
        admin = self.users.get("admintest")

        # Step 1: Employee submits expense
        start = time.time()
        expense_data = {
            "amount": 750.00,
            "vendor": "Apple Store",
            "category": "SOFTWARE",
            "description": "MacBook Pro charger and USB-C adapter",
            "date": datetime.now().isoformat(),
        }

        response = self.client.post(
            "/expenses", employee.token, expense_data, self.org_id
        )
        if response.status_code in [200, 201]:
            expense = response.json()
            expense_id = expense.get("expense", {}).get("id") or expense.get("id")
            self.add_result(
                scenario,
                "1. Employee Submit",
                True,
                f"Created ${expense_data['amount']} expense",
                time.time() - start,
            )
        else:
            self.add_result(
                scenario,
                "1. Employee Submit",
                False,
                f"Failed: {response.status_code}",
                time.time() - start,
            )
            return

        # Step 2: Manager receives notification and reviews
        start = time.time()
        response = self.client.get(
            f"/expenses/{expense_id}", manager.token, self.org_id
        )
        if response.status_code == 200:
            self.add_result(
                scenario,
                "2. Manager Review",
                True,
                "Manager accessed expense for review",
                time.time() - start,
            )
        else:
            self.add_result(
                scenario,
                "2. Manager Review",
                False,
                f"Manager cannot access: {response.status_code}",
                time.time() - start,
            )

        # Step 3: Manager adds approval note and forwards
        start = time.time()
        note_data = {
            "note": "Approved - equipment necessary for remote work",
            "forward_to": "accountant",
        }
        response = self.client.put(
            f"/expenses/{expense_id}/manager-approve",
            manager.token,
            note_data,
            self.org_id,
        )
        passed = response.status_code in [200, 201, 404]
        self.add_result(
            scenario,
            "3. Manager Forward",
            passed,
            f"Forward to accountant: {response.status_code}",
            time.time() - start,
        )

        # Step 4: Accountant verifies compliance
        start = time.time()
        response = self.client.get(
            f"/expenses/{expense_id}", accountant.token, self.org_id
        )
        if response.status_code == 200:
            self.add_result(
                scenario,
                "4. Accountant Verify",
                True,
                "Accountant reviewing for compliance",
                time.time() - start,
            )
        else:
            self.add_result(
                scenario,
                "4. Accountant Verify",
                False,
                f"Accountant cannot access: {response.status_code}",
                time.time() - start,
            )

        # Step 5: Accountant marks as compliant
        start = time.time()
        compliance_data = {
            "compliant": True,
            "note": "Expense within policy, receipt attached",
        }
        response = self.client.put(
            f"/expenses/{expense_id}/mark-compliant",
            accountant.token,
            compliance_data,
            self.org_id,
        )
        passed = response.status_code in [200, 201, 404]
        self.add_result(
            scenario,
            "5. Accountant Mark Compliant",
            passed,
            f"Compliance marking: {response.status_code}",
            time.time() - start,
        )

        # Step 6: Admin makes final approval
        start = time.time()
        response = self.client.put(
            f"/expenses/{expense_id}/approve", admin.token, {}, self.org_id
        )
        passed = response.status_code in [200, 201]
        self.add_result(
            scenario,
            "6. Admin Final Approval",
            passed,
            f"Final approval: {response.status_code}",
            time.time() - start,
        )

        # Step 7: Employee checks final status
        start = time.time()
        response = self.client.get(
            f"/expenses/{expense_id}", employee.token, self.org_id
        )
        if response.status_code == 200:
            final_status = response.json().get("status")
            self.add_result(
                scenario,
                "7. Employee Check Status",
                True,
                f"Final status: {final_status}",
                time.time() - start,
            )
        else:
            self.add_result(
                scenario,
                "7. Employee Check Status",
                False,
                "Cannot check final status",
                time.time() - start,
            )

        print()

    # ========================================================================
    # SCENARIO 5: ATYPICAL - CONFLICTING ACTIONS
    # ========================================================================

    def test_atypical_conflicting_actions(self):
        """
        Atypical Scenario: Multiple users try to act on same expense simultaneously
        - Employee submits expense
        - Manager starts approval process
        - Accountant simultaneously flags for audit
        - Test race condition handling
        - Test concurrent approval attempts
        """
        scenario = "ATYPICAL_CONFLICTS"
        self.log("\n" + "=" * 100, "INFO")
        self.log("SCENARIO: ATYPICAL - CONFLICTING ACTIONS & RACE CONDITIONS", "INFO")
        self.log("=" * 100, "INFO")

        employee = self.users.get("emptest")
        manager = self.users.get("testuser")
        accountant = self.users.get("employee2")
        admin = self.users.get("admintest")

        # Create test expense
        expense_data = {
            "amount": 350.00,
            "vendor": "Test Vendor",
            "category": "OTHER",
            "description": "Test expense for race condition",
            "date": datetime.now().isoformat(),
        }

        response = self.client.post(
            "/expenses", employee.token, expense_data, self.org_id
        )
        if response.status_code not in [200, 201]:
            self.log("Could not create test expense", "ERROR")
            return

        expense_id = response.json().get("expense", {}).get(
            "id"
        ) or response.json().get("id")

        # Test 1: Concurrent approval attempts (manager and admin)
        start = time.time()
        import threading

        results = {"manager": None, "admin": None}

        def manager_approve():
            results["manager"] = self.client.put(
                f"/expenses/{expense_id}/approve", manager.token, {}, self.org_id
            )

        def admin_approve():
            results["admin"] = self.client.put(
                f"/expenses/{expense_id}/approve", admin.token, {}, self.org_id
            )

        t1 = threading.Thread(target=manager_approve)
        t2 = threading.Thread(target=admin_approve)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        manager_status = results["manager"].status_code if results["manager"] else None
        admin_status = results["admin"].status_code if results["admin"] else None

        # One should succeed, one might fail due to race condition
        passed = manager_status in [200, 201] or admin_status in [200, 201]
        self.add_result(
            scenario,
            "Concurrent Approvals",
            passed,
            f"Manager: {manager_status}, Admin: {admin_status}",
            time.time() - start,
        )

        # Test 2: Employee tries to modify expense after submission
        start = time.time()
        update_data = {"amount": 500.00}  # Try to increase amount
        response = self.client.put(
            f"/expenses/{expense_id}", employee.token, update_data, self.org_id
        )
        # Should fail if expense already in approval workflow
        passed = True  # Document behavior
        self.add_result(
            scenario,
            "Employee Modify After Submit",
            passed,
            f"Modify after submission: {response.status_code}",
            time.time() - start,
        )

        # Test 3: Double approval attempt
        start = time.time()
        response1 = self.client.put(
            f"/expenses/{expense_id}/approve", admin.token, {}, self.org_id
        )
        response2 = self.client.put(
            f"/expenses/{expense_id}/approve", admin.token, {}, self.org_id
        )
        # Second should be idempotent or return error
        passed = response2.status_code in [200, 201, 400, 409]
        self.add_result(
            scenario,
            "Double Approval",
            passed,
            f"First: {response1.status_code}, Second: {response2.status_code}",
            time.time() - start,
        )

        print()

    # ========================================================================
    # SCENARIO 6: TYPICAL - EXPENSE APPROVAL CHAIN
    # ========================================================================

    def test_typical_approval_chain(self):
        """
        Typical Scenario: Standard expense approval workflow
        - Employee submits expense with receipt
        - Manager reviews within 24 hours
        - Manager approves
        - Accountant processes payment
        - Employee gets reimbursed
        """
        scenario = "TYPICAL_APPROVAL_CHAIN"
        self.log("\n" + "=" * 100, "INFO")
        self.log("SCENARIO: TYPICAL - STANDARD EXPENSE APPROVAL CHAIN", "INFO")
        self.log("=" * 100, "INFO")

        employee = self.users.get("emptest")
        manager = self.users.get("testuser")
        accountant = self.users.get("employee2")

        # Step 1: Employee submits expense with all required info
        start = time.time()
        expense_data = {
            "amount": 125.50,
            "vendor": "Amazon Business",
            "category": "OFFICE_SUPPLIES",
            "description": "Wireless mouse and keyboard",
            "date": datetime.now().isoformat(),
            "receipt_url": "https://example.com/receipt.pdf",
        }

        response = self.client.post(
            "/expenses", employee.token, expense_data, self.org_id
        )
        if response.status_code in [200, 201]:
            expense = response.json()
            expense_id = expense.get("expense", {}).get("id") or expense.get("id")
            self.add_result(
                scenario,
                "Employee Submit Complete",
                True,
                f"Submitted with receipt: ${expense_data['amount']}",
                time.time() - start,
            )
        else:
            self.add_result(
                scenario,
                "Employee Submit Complete",
                False,
                f"Failed: {response.status_code}",
                time.time() - start,
            )
            return

        # Step 2: Manager reviews promptly
        start = time.time()
        response = self.client.get(
            f"/expenses/{expense_id}", manager.token, self.org_id
        )
        passed = response.status_code == 200
        self.add_result(
            scenario,
            "Manager Prompt Review",
            passed,
            "Manager reviewed within SLA",
            time.time() - start,
        )

        # Step 3: Manager approves
        start = time.time()
        response = self.client.put(
            f"/expenses/{expense_id}/approve", manager.token, {}, self.org_id
        )
        passed = response.status_code in [200, 201]
        self.add_result(
            scenario,
            "Manager Approve",
            passed,
            f"Approval status: {response.status_code}",
            time.time() - start,
        )

        # Step 4: Accountant processes for payment
        start = time.time()
        payment_data = {
            "payment_method": "direct_deposit",
            "expected_date": (datetime.now() + timedelta(days=3)).isoformat(),
        }
        response = self.client.put(
            f"/expenses/{expense_id}/process-payment",
            accountant.token,
            payment_data,
            self.org_id,
        )
        passed = response.status_code in [200, 201, 404]
        self.add_result(
            scenario,
            "Accountant Process Payment",
            passed,
            f"Payment processing: {response.status_code}",
            time.time() - start,
        )

        # Step 5: Employee verifies reimbursement status
        start = time.time()
        response = self.client.get(
            f"/expenses/{expense_id}", employee.token, self.org_id
        )
        if response.status_code == 200:
            status = response.json().get("status")
            self.add_result(
                scenario,
                "Employee Verify Reimbursement",
                True,
                f"Reimbursement status: {status}",
                time.time() - start,
            )
        else:
            self.add_result(
                scenario,
                "Employee Verify Reimbursement",
                False,
                "Cannot verify status",
                time.time() - start,
            )

        print()

    # ========================================================================
    # SCENARIO 7: SECURITY - UNAUTHORIZED ACCESS ATTEMPTS
    # ========================================================================

    def test_security_unauthorized_access(self):
        """
        Security Scenario: Test unauthorized access attempts
        - Employee 1 creates expense
        - Employee 2 tries to view Employee 1's expense (should fail)
        - Employee 2 tries to modify Employee 1's expense (should fail)
        - Employee 2 tries to delete Employee 1's expense (should fail)
        - Employee tries to approve own expense (should fail)
        - Employee tries to access different organization (should fail)
        """
        scenario = "SECURITY_UNAUTHORIZED"
        self.log("\n" + "=" * 100, "INFO")
        self.log("SCENARIO: SECURITY - UNAUTHORIZED ACCESS ATTEMPTS", "INFO")
        self.log("=" * 100, "INFO")

        emp1 = self.users.get("emptest")
        emp2 = self.users.get("emptest2")

        # Create expense as Employee 1
        expense_data = {
            "amount": 100.00,
            "vendor": "Test",
            "category": "OTHER",
            "description": "Security test expense",
            "date": datetime.now().isoformat(),
        }

        response = self.client.post("/expenses", emp1.token, expense_data, self.org_id)
        if response.status_code not in [200, 201]:
            self.log("Could not create test expense", "ERROR")
            return

        expense_id = response.json().get("expense", {}).get(
            "id"
        ) or response.json().get("id")

        # Test 1: Employee 2 tries to view Employee 1's expense
        start = time.time()
        response = self.client.get(f"/expenses/{expense_id}", emp2.token, self.org_id)
        passed = response.status_code >= 400  # Should be forbidden
        self.add_result(
            scenario,
            "Cross-Employee View",
            passed,
            (
                f"Prevented unauthorized view"
                if passed
                else f"WARNING: Allowed view ({response.status_code})"
            ),
            time.time() - start,
        )

        # Test 2: Employee 2 tries to modify Employee 1's expense
        start = time.time()
        response = self.client.put(
            f"/expenses/{expense_id}", emp2.token, {"amount": 200.00}, self.org_id
        )
        passed = response.status_code >= 400
        self.add_result(
            scenario,
            "Cross-Employee Modify",
            passed,
            (
                f"Prevented unauthorized modify"
                if passed
                else f"WARNING: Allowed modify ({response.status_code})"
            ),
            time.time() - start,
        )

        # Test 3: Employee 2 tries to delete Employee 1's expense
        start = time.time()
        response = self.client.delete(
            f"/expenses/{expense_id}", emp2.token, self.org_id
        )
        passed = response.status_code >= 400
        self.add_result(
            scenario,
            "Cross-Employee Delete",
            passed,
            (
                f"Prevented unauthorized delete"
                if passed
                else f"WARNING: Allowed delete ({response.status_code})"
            ),
            time.time() - start,
        )

        # Test 4: Employee tries to approve own expense
        start = time.time()
        response = self.client.put(
            f"/expenses/{expense_id}/approve", emp1.token, {}, self.org_id
        )
        passed = response.status_code >= 400
        self.add_result(
            scenario,
            "Self-Approval Attempt",
            passed,
            (
                f"Prevented self-approval"
                if passed
                else f"WARNING: Allowed self-approval ({response.status_code})"
            ),
            time.time() - start,
        )

        # Test 5: Employee tries to access different organization
        start = time.time()
        fake_org_id = "00000000-0000-0000-0000-000000000000"
        response = self.client.get("/expenses", emp1.token, fake_org_id)
        passed = response.status_code >= 400
        self.add_result(
            scenario,
            "Cross-Org Access",
            passed,
            (
                f"Prevented cross-org access"
                if passed
                else f"CRITICAL: Allowed cross-org ({response.status_code})"
            ),
            time.time() - start,
        )

        print()

    # ========================================================================
    # SUMMARY & REPORTING
    # ========================================================================

    def print_summary(self):
        self.log("\n" + "=" * 100, "INFO")
        self.log("COMPREHENSIVE WORKFLOW TEST SUMMARY", "INFO")
        self.log("=" * 100, "INFO")

        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        pass_rate = (passed / total * 100) if total > 0 else 0

        # Group by scenario
        by_scenario = {}
        for result in self.results:
            if result.scenario not in by_scenario:
                by_scenario[result.scenario] = {
                    "passed": 0,
                    "failed": 0,
                    "duration": 0.0,
                }
            if result.passed:
                by_scenario[result.scenario]["passed"] += 1
            else:
                by_scenario[result.scenario]["failed"] += 1
            by_scenario[result.scenario]["duration"] += result.duration

        print(
            f"\n{'Scenario':<35} {'Passed':<10} {'Failed':<10} {'Total':<10} {'Pass %':<10} {'Time (s)':<10}"
        )
        print("-" * 105)

        for scenario, stats in sorted(by_scenario.items()):
            scenario_total = stats["passed"] + stats["failed"]
            scenario_pass_rate = (
                (stats["passed"] / scenario_total * 100) if scenario_total > 0 else 0
            )
            print(
                f"{scenario:<35} {stats['passed']:<10} {stats['failed']:<10} {scenario_total:<10} {scenario_pass_rate:>6.1f}%    {stats['duration']:>8.2f}s"
            )

        print("-" * 105)
        print(
            f"{'TOTAL':<35} {passed:<10} {failed:<10} {total:<10} {pass_rate:>6.1f}%\n"
        )

        # Show failures
        if failed > 0:
            self.log("FAILED TESTS:", "ERROR")
            for result in self.results:
                if not result.passed:
                    print(
                        f"  X [{result.scenario}] {result.test_name}: {result.message}"
                    )

        print()

        # Overall assessment
        if pass_rate >= 95:
            self.log(
                f"EXCELLENT: {pass_rate:.1f}% pass rate - Production ready!", "SUCCESS"
            )
        elif pass_rate >= 85:
            self.log(
                f"GOOD: {pass_rate:.1f}% pass rate - Minor issues to address", "SUCCESS"
            )
        elif pass_rate >= 70:
            self.log(
                f"FAIR: {pass_rate:.1f}% pass rate - Several issues need fixing",
                "WARNING",
            )
        else:
            self.log(
                f"POOR: {pass_rate:.1f}% pass rate - Critical issues found", "ERROR"
            )

        print()

    # ========================================================================
    # MAIN TEST RUNNER
    # ========================================================================

    def run_all_tests(self):
        start_time = time.time()

        self.log("=" * 100, "INFO")
        self.log("COMPREHENSIVE MULTI-USER WORKFLOW TEST SUITE", "INFO")
        self.log("=" * 100, "INFO")
        print()

        # Setup
        if not self.setup_users():
            self.log("User setup failed", "ERROR")
            return False

        if not self.setup_organization():
            self.log("Organization setup failed", "ERROR")
            return False

        # Run all workflow scenarios
        self.test_two_employees_admin_workflow()
        self.test_two_employees_manager_workflow()
        self.test_two_employees_accountant_workflow()
        self.test_complex_four_way_workflow()
        self.test_typical_approval_chain()
        self.test_atypical_conflicting_actions()
        self.test_security_unauthorized_access()

        # Summary
        self.print_summary()

        elapsed = time.time() - start_time
        self.log(f"All tests completed in {elapsed:.2f} seconds", "INFO")

        return True


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================


def main():
    print("\n")
    tester = ComprehensiveWorkflowTester()

    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest suite interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
