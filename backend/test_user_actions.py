"""
Comprehensive test script for all user/employee dashboard actions.
Tests authentication and functionality from an employee perspective.
"""

import requests
import json
import sys
from datetime import datetime, timedelta
import time

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Configuration
BASE_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"

# Test credentials - use employee account
EMPLOYEE_USER = {
    "username": "emptest",
    "password": "EmpTest!"
}

# Also test with manager account
MANAGER_USER = {
    "username": "testuser",
    "password": "TestUser!"
}

class UserDashboardTester:
    def __init__(self, username, password, role="Employee", org_id=None):
        self.username = username
        self.password = password
        self.role = role
        self.token = None
        self.user_id = None
        self.org_id = org_id
        self.results = []
        self.created_expense_id = None

    def log(self, test_name, status, message=""):
        """Log test result"""
        result = {
            "test": test_name,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "role": self.role
        }
        self.results.append(result)
        icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{icon} {test_name}: {message if message else status}")

    def login(self):
        """Test login and get access token"""
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/auth/login",
                json={
                    "username": self.username,
                    "password": self.password
                }
            )

            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.user_id = data.get("user", {}).get("id")
                role = data.get("user", {}).get("role")
                self.log("Login", "PASS", f"Token obtained for {self.username} (role: {role})")
                return True
            else:
                self.log("Login", "FAIL", f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log("Login", "FAIL", str(e))
            return False

    def get_headers(self):
        """Get authorization headers"""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        if self.org_id:
            headers["X-Organization-Id"] = self.org_id
        return headers

    # ============================================================================
    # EXPENSE MANAGEMENT
    # ============================================================================

    def test_expense_lifecycle(self):
        """Test complete expense lifecycle: create, view, update, withdraw"""
        print(f"\n💵 Testing EXPENSE MANAGEMENT for {self.role}...")

        # 1. Create an expense
        try:
            expense_data = {
                "vendor": f"Test Vendor {int(time.time())}",
                "amount": 125.50,
                "category": "Meals",
                "description": f"Test expense created by {self.username}",
                "date": datetime.now().isoformat(),
                "payment_method": "credit_card",
                "currency": "USD",
                "user_id": self.user_id
            }

            response = requests.post(
                f"{BASE_URL}/api/v1/expenses",
                headers=self.get_headers(),
                json=expense_data
            )

            if response.status_code == 201:
                data = response.json()
                self.created_expense_id = data.get("id")
                self.log("Create Expense", "PASS", f"Created expense {self.created_expense_id}")
            else:
                self.log("Create Expense", "FAIL", f"Status {response.status_code}: {response.text}")
                return
        except Exception as e:
            self.log("Create Expense", "FAIL", str(e))
            return

        # 2. Get own expenses
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/expenses",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                data = response.json()
                # Handle both dict and list responses
                if isinstance(data, dict):
                    expenses = data.get("expenses", [])
                else:
                    expenses = data
                self.log("Get My Expenses", "PASS", f"Found {len(expenses)} expenses")
            else:
                self.log("Get My Expenses", "FAIL", f"Status {response.status_code}")
        except Exception as e:
            self.log("Get My Expenses", "FAIL", str(e))

        # 3. Get specific expense details
        if self.created_expense_id:
            try:
                response = requests.get(
                    f"{BASE_URL}/api/v1/expenses/{self.created_expense_id}",
                    headers=self.get_headers()
                )
                if response.status_code == 200:
                    data = response.json()
                    self.log("Get Expense Details", "PASS", f"Retrieved details for {self.created_expense_id}")
                else:
                    self.log("Get Expense Details", "FAIL", f"Status {response.status_code}")
            except Exception as e:
                self.log("Get Expense Details", "FAIL", str(e))

            # 4. Update expense
            try:
                update_data = {
                    "description": f"Updated expense by {self.username}",
                    "amount": 150.00
                }
                response = requests.patch(
                    f"{BASE_URL}/api/v1/expenses/{self.created_expense_id}",
                    headers=self.get_headers(),
                    json=update_data
                )
                if response.status_code == 200:
                    self.log("Update Expense", "PASS", "Expense updated successfully")
                else:
                    self.log("Update Expense", "FAIL", f"Status {response.status_code}")
            except Exception as e:
                self.log("Update Expense", "FAIL", str(e))

            # 5. Withdraw expense (delete before approval)
            try:
                response = requests.delete(
                    f"{BASE_URL}/api/v1/expenses/{self.created_expense_id}/withdraw",
                    headers=self.get_headers()
                )
                if response.status_code == 204:
                    self.log("Withdraw Expense", "PASS", "Expense withdrawn successfully")
                elif response.status_code == 200:
                    self.log("Withdraw Expense", "PASS", "Expense withdrawn successfully")
                else:
                    self.log("Withdraw Expense", "FAIL", f"Status {response.status_code}")
            except Exception as e:
                self.log("Withdraw Expense", "FAIL", str(e))

    # ============================================================================
    # RECEIPTS
    # ============================================================================

    def test_receipts(self):
        """Test receipt management"""
        print(f"\n📄 Testing RECEIPT MANAGEMENT for {self.role}...")

        # Create expense for receipt testing
        try:
            expense_data = {
                "vendor": "Receipt Test Vendor",
                "amount": 50.00,
                "category": "Office Supplies",
                "description": "Test for receipt upload",
                "date": datetime.now().isoformat(),
                "payment_method": "cash",
                "currency": "USD",
                "user_id": self.user_id
            }

            response = requests.post(
                f"{BASE_URL}/api/v1/expenses",
                headers=self.get_headers(),
                json=expense_data
            )

            if response.status_code == 201:
                expense_id = response.json().get("id")
                self.log("Create Expense for Receipt", "PASS", f"Created {expense_id}")

                # Note: Actual file upload would require multipart/form-data
                # For now, just test the endpoint availability
                self.log("Receipt Upload", "SKIP", "File upload requires multipart/form-data testing")
            else:
                self.log("Create Expense for Receipt", "FAIL", f"Status {response.status_code}")
        except Exception as e:
            self.log("Create Expense for Receipt", "FAIL", str(e))

    # ============================================================================
    # RECURRING EXPENSES
    # ============================================================================

    def test_recurring_expenses(self):
        """Test recurring expenses from user perspective"""
        print(f"\n🔄 Testing RECURRING EXPENSES for {self.role}...")

        # 1. View recurring expenses
        try:
            response = requests.get(
                f"{BASE_URL}/api/recurring-expenses",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                data = response.json()
                count = len(data) if isinstance(data, list) else 0
                self.log("View Recurring Expenses", "PASS", f"Found {count} templates")
            else:
                self.log("View Recurring Expenses", "FAIL", f"Status {response.status_code}")
        except Exception as e:
            self.log("View Recurring Expenses", "FAIL", str(e))

        # 2. Create recurring expense (managers and admins only)
        if self.role != "Employee":
            try:
                template_data = {
                    "vendor": "Monthly Subscription",
                    "amount": 99.99,
                    "category": "Software",
                    "description": "Test recurring expense",
                    "frequency": "monthly",
                    "start_date": datetime.now().isoformat(),
                    "auto_submit": True,
                    "user_id": self.user_id
                }

                response = requests.post(
                    f"{BASE_URL}/api/recurring-expenses",
                    headers=self.get_headers(),
                    json=template_data
                )

                if response.status_code == 201:
                    template_id = response.json().get("id")
                    self.log("Create Recurring Template", "PASS", f"Created {template_id}")

                    # Clean up
                    requests.delete(
                        f"{BASE_URL}/api/recurring-expenses/{template_id}",
                        headers=self.get_headers()
                    )
                else:
                    self.log("Create Recurring Template", "FAIL", f"Status {response.status_code}")
            except Exception as e:
                self.log("Create Recurring Template", "FAIL", str(e))

    # ============================================================================
    # BUDGETS
    # ============================================================================

    def test_budgets(self):
        """Test budget viewing from user perspective"""
        print(f"\n💰 Testing BUDGET VIEWING for {self.role}...")

        try:
            response = requests.get(
                f"{BASE_URL}/api/budgets",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                data = response.json()
                count = len(data.get("budgets", [])) if isinstance(data, dict) else len(data)
                self.log("View Budgets", "PASS", f"Found {count} budgets")
            else:
                self.log("View Budgets", "FAIL", f"Status {response.status_code}")
        except Exception as e:
            self.log("View Budgets", "FAIL", str(e))

    # ============================================================================
    # NOTIFICATIONS
    # ============================================================================

    def test_notifications(self):
        """Test notification system"""
        print(f"\n🔔 Testing NOTIFICATIONS for {self.role}...")

        # Get notifications
        try:
            response = requests.get(
                f"{BASE_URL}/api/notifications",
                headers=self.get_headers(),
                params={"limit": 10}
            )
            if response.status_code == 200:
                data = response.json()
                count = len(data) if isinstance(data, list) else 0
                self.log("Get Notifications", "PASS", f"Found {count} notifications")
            else:
                self.log("Get Notifications", "FAIL", f"Status {response.status_code}")
        except Exception as e:
            self.log("Get Notifications", "FAIL", str(e))

        # Get unread count
        try:
            response = requests.get(
                f"{BASE_URL}/api/notifications/unread-count",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                data = response.json()
                count = data.get("unread_count", 0)
                self.log("Unread Notifications", "PASS", f"{count} unread")
            else:
                self.log("Unread Notifications", "FAIL", f"Status {response.status_code}")
        except Exception as e:
            self.log("Unread Notifications", "FAIL", str(e))

    # ============================================================================
    # DASHBOARD
    # ============================================================================

    def test_dashboard(self):
        """Test dashboard statistics"""
        print(f"\n📊 Testing DASHBOARD for {self.role}...")

        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/expenses/report",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                self.log("Get Expense Report", "PASS", "Report generated successfully")
            else:
                self.log("Get Expense Report", "FAIL", f"Status {response.status_code}")
        except Exception as e:
            self.log("Get Expense Report", "FAIL", str(e))

    # ============================================================================
    # RUN ALL TESTS
    # ============================================================================

    def run_all_tests(self):
        """Run all user dashboard tests"""
        print("=" * 80)
        print(f"🚀 {self.role.upper()} DASHBOARD COMPREHENSIVE TEST")
        print("=" * 80)

        # Login first
        if not self.login():
            print(f"\n❌ Login failed for {self.username}. Cannot continue with tests.")
            return []

        # Run all tests
        self.test_expense_lifecycle()
        self.test_receipts()
        self.test_recurring_expenses()
        self.test_budgets()
        self.test_notifications()
        self.test_dashboard()

        # Summary
        return self.print_summary()

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print(f"📊 {self.role.upper()} TEST SUMMARY")
        print("=" * 80)

        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        skipped = sum(1 for r in self.results if r["status"] == "SKIP")
        total = len(self.results)

        print(f"\n✅ Passed:  {passed}/{total}")
        print(f"❌ Failed:  {failed}/{total}")
        print(f"⚠️  Skipped: {skipped}/{total}")

        if failed > 0:
            print(f"\n❌ FAILED TESTS ({self.role}):")
            for result in self.results:
                if result["status"] == "FAIL":
                    print(f"  • {result['test']}: {result['message']}")

        print("\n" + "=" * 80)

        return self.results


if __name__ == "__main__":
    # Get organization ID
    import sys
    sys.path.insert(0, '/home/user/ap2-expense-agent/backend')
    from src.database import SessionLocal
    from src.models import Organization
    from sqlalchemy import select

    db = SessionLocal()
    org = db.execute(select(Organization).where(Organization.name == 'Test Organization')).scalar_one_or_none()
    org_id = org.id if org else None
    db.close()

    if not org_id:
        print("⚠️  Warning: Test Organization not found. Some tests may fail.")
    else:
        print(f"✅ Using organization: {org_id}")

    # Test with employee account
    print("\n" + "=" * 80)
    print("TESTING WITH EMPLOYEE ACCOUNT")
    print("=" * 80)
    employee_tester = UserDashboardTester(
        EMPLOYEE_USER["username"],
        EMPLOYEE_USER["password"],
        role="Employee",
        org_id=org_id
    )
    employee_results = employee_tester.run_all_tests()

    # Test with manager account
    print("\n\n" + "=" * 80)
    print("TESTING WITH MANAGER ACCOUNT")
    print("=" * 80)
    manager_tester = UserDashboardTester(
        MANAGER_USER["username"],
        MANAGER_USER["password"],
        role="Manager",
        org_id=org_id
    )
    manager_results = manager_tester.run_all_tests()

    # Combined summary
    print("\n\n" + "=" * 80)
    print("📊 COMBINED USER TESTING SUMMARY")
    print("=" * 80)

    all_results = (employee_results or []) + (manager_results or [])
    total_passed = sum(1 for r in all_results if r["status"] == "PASS")
    total_failed = sum(1 for r in all_results if r["status"] == "FAIL")
    total_skipped = sum(1 for r in all_results if r["status"] == "SKIP")
    total_tests = len(all_results)

    print(f"\n✅ Total Passed:  {total_passed}/{total_tests}")
    print(f"❌ Total Failed:  {total_failed}/{total_tests}")
    print(f"⚠️  Total Skipped: {total_skipped}/{total_tests}")
    if total_tests > 0:
        print(f"\n📈 Success Rate: {(total_passed/total_tests*100):.1f}%")
    else:
        print("\n⚠️  No tests were run")

    # Save combined results
    with open("test_user_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    print("\n💾 Detailed results saved to: test_user_results.json")
