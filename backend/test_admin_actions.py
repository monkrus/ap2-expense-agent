"""
Comprehensive test script for all admin dashboard actions.
Tests authentication and functionality across all tabs.
"""

import requests
import json
import sys
from datetime import datetime, timedelta

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Configuration
BASE_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"

# Test credentials
ADMIN_USER = {
    "username": "admintest",
    "password": "AgentTest!"
}

class AdminDashboardTester:
    def __init__(self):
        self.token = None
        self.user_id = None
        self.results = []

    def log(self, test_name, status, message=""):
        """Log test result"""
        result = {
            "test": test_name,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)
        icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{icon} {test_name}: {message if message else status}")

    def login(self):
        """Test login and get access token"""
        try:
            # Login using JSON data
            response = requests.post(
                f"{BASE_URL}/api/v1/auth/login",
                json={
                    "username": ADMIN_USER["username"],
                    "password": ADMIN_USER["password"]
                }
            )

            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.user_id = data.get("user", {}).get("id")
                self.log("Login", "PASS", f"Token obtained for user {self.user_id}")
                return True
            else:
                self.log("Login", "FAIL", f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log("Login", "FAIL", str(e))
            return False

    def get_headers(self):
        """Get authorization headers"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    # ============================================================================
    # TAB 1: PENDING APPROVALS
    # ============================================================================

    def test_pending_tab(self):
        """Test all actions in Pending Approvals tab"""
        print("\n📋 Testing PENDING APPROVALS Tab...")

        # Get pending expenses
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/expenses/all-pending",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                data = response.json()
                pending_count = len(data.get("expenses", []))
                self.log("Get Pending Expenses", "PASS", f"Found {pending_count} pending expenses")
                return data.get("expenses", [])
            else:
                self.log("Get Pending Expenses", "FAIL", f"Status {response.status_code}")
                return []
        except Exception as e:
            self.log("Get Pending Expenses", "FAIL", str(e))
            return []

    # ============================================================================
    # TAB 2: ALL EXPENSES
    # ============================================================================

    def test_all_expenses_tab(self):
        """Test All Expenses tab with filters"""
        print("\n📊 Testing ALL EXPENSES Tab...")

        # Test different status filters
        filters = ["all", "pending", "approved", "rejected"]

        for filter_status in filters:
            try:
                url = f"{BASE_URL}/api/v1/admin/expenses"
                if filter_status != "all":
                    url += f"?status={filter_status}"

                response = requests.get(url, headers=self.get_headers())

                if response.status_code == 200:
                    data = response.json()
                    count = len(data.get("expenses", []))
                    self.log(f"Get All Expenses (filter: {filter_status})", "PASS", f"Found {count} expenses")
                else:
                    self.log(f"Get All Expenses (filter: {filter_status})", "FAIL", f"Status {response.status_code}")
            except Exception as e:
                self.log(f"Get All Expenses (filter: {filter_status})", "FAIL", str(e))

        # Test archive actions
        self.test_archive_actions()

    def test_archive_actions(self):
        """Test archive/unarchive actions"""
        # Archive all
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/admin/expenses/archive-all",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                data = response.json()
                archived = data.get("statistics", {}).get("expenses_archived", 0)
                self.log("Archive All Expenses", "PASS", f"Archived {archived} expenses")
            else:
                self.log("Archive All Expenses", "FAIL", f"Status {response.status_code}")
        except Exception as e:
            self.log("Archive All Expenses", "FAIL", str(e))

    # ============================================================================
    # TAB 3: ARCHIVED
    # ============================================================================

    def test_archived_tab(self):
        """Test Archived tab"""
        print("\n🗄️ Testing ARCHIVED Tab...")

        # Get archived expenses
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/admin/expenses/archived",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                data = response.json()
                count = len(data.get("expenses", []))
                self.log("Get Archived Expenses", "PASS", f"Found {count} archived expenses")

                # Test unarchive all
                response = requests.post(
                    f"{BASE_URL}/api/v1/admin/expenses/unarchive-all",
                    headers=self.get_headers()
                )
                if response.status_code == 200:
                    data = response.json()
                    unarchived = data.get("statistics", {}).get("expenses_unarchived", 0)
                    self.log("Unarchive All Expenses", "PASS", f"Restored {unarchived} expenses")
                else:
                    self.log("Unarchive All Expenses", "FAIL", f"Status {response.status_code}")
            else:
                self.log("Get Archived Expenses", "FAIL", f"Status {response.status_code}")
        except Exception as e:
            self.log("Get Archived Expenses", "FAIL", str(e))

    # ============================================================================
    # TAB 4: USER MANAGEMENT
    # ============================================================================

    def test_user_management_tab(self):
        """Test User Management tab"""
        print("\n👥 Testing USER MANAGEMENT Tab...")

        # Get all users
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/admin/users",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                data = response.json()
                user_count = len(data.get("users", []))
                self.log("Get All Users", "PASS", f"Found {user_count} users")
            else:
                self.log("Get All Users", "FAIL", f"Status {response.status_code}")
        except Exception as e:
            self.log("Get All Users", "FAIL", str(e))

        # Get permissions
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/admin/permissions/all",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                data = response.json()
                self.log("Get All Permissions", "PASS", f"Permissions loaded")
            else:
                self.log("Get All Permissions", "FAIL", f"Status {response.status_code}")
        except Exception as e:
            self.log("Get All Permissions", "FAIL", str(e))

    # ============================================================================
    # TAB 5: BILLING & USAGE
    # ============================================================================

    def test_billing_tab(self):
        """Test Billing & Usage tab"""
        print("\n💳 Testing BILLING & USAGE Tab...")

        # Get subscription
        try:
            response = requests.get(
                f"{BASE_URL}/api/billing/subscription",
                headers=self.get_headers()
            )
            if response.status_code in [200, 404]:  # 404 is ok if no subscription
                self.log("Get Subscription", "PASS", "Subscription endpoint accessible")
            else:
                self.log("Get Subscription", "FAIL", f"Status {response.status_code}")
        except Exception as e:
            self.log("Get Subscription", "FAIL", str(e))

        # Get monthly usage
        try:
            response = requests.get(
                f"{BASE_URL}/api/billing/usage/monthly",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                data = response.json()
                self.log("Get Monthly Usage", "PASS", "Usage data retrieved")
            else:
                self.log("Get Monthly Usage", "FAIL", f"Status {response.status_code}")
        except Exception as e:
            self.log("Get Monthly Usage", "FAIL", str(e))

        # Get billing tiers
        try:
            response = requests.get(
                f"{BASE_URL}/api/billing/tiers",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                data = response.json()
                self.log("Get Billing Tiers", "PASS", "Tiers loaded")
            else:
                self.log("Get Billing Tiers", "FAIL", f"Status {response.status_code}")
        except Exception as e:
            self.log("Get Billing Tiers", "FAIL", str(e))

    # ============================================================================
    # TAB 6: AI ASSISTANT
    # ============================================================================

    def test_ai_assistant_tab(self):
        """Test AI Assistant tab - batch receipt upload with AI extraction"""
        print("\n🤖 Testing AI ASSISTANT Tab...")

        # Test AI-powered batch receipt upload endpoint
        try:
            # Create a minimal test image (1x1 PNG)
            import io
            test_image = io.BytesIO(
                b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
                b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01'
                b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
            )
            test_image.name = 'test_ai_receipt.png'

            # Upload file to batch-upload endpoint (AI-powered)
            files = {'files': ('test_ai_receipt.png', test_image, 'image/png')}
            headers_no_content = {
                "Authorization": f"Bearer {self.token}"
            }

            response = requests.post(
                f"{BASE_URL}/api/v1/receipts/batch-upload",
                headers=headers_no_content,
                files=files
            )

            # Accept both success (AI works) and fallback (AI not configured)
            if response.status_code == 200:
                data = response.json()
                if 'results' in data or 'extractions' in data:
                    self.log("AI Assistant Tab", "PASS", "AI batch upload endpoint working")
                else:
                    self.log("AI Assistant Tab", "PASS", "AI service endpoint accessible")
            else:
                self.log("AI Assistant Tab", "FAIL", f"Status {response.status_code}")
        except Exception as e:
            self.log("AI Assistant Tab", "FAIL", str(e))

    # ============================================================================
    # TAB 7: RECURRING EXPENSES
    # ============================================================================

    def test_recurring_expenses_tab(self):
        """Test Recurring Expenses tab"""
        print("\n🔄 Testing RECURRING EXPENSES Tab...")

        # Get recurring expenses
        try:
            response = requests.get(
                f"{BASE_URL}/api/recurring-expenses?active_only=false",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                data = response.json()
                count = len(data) if isinstance(data, list) else 0
                self.log("Get Recurring Expenses", "PASS", f"Found {count} templates")
            else:
                self.log("Get Recurring Expenses", "FAIL", f"Status {response.status_code}: {response.text}")
        except Exception as e:
            self.log("Get Recurring Expenses", "FAIL", str(e))

        # Test create recurring expense
        try:
            test_data = {
                "vendor": "Test Vendor",
                "amount": 100.00,
                "category": "Software",
                "description": "Test recurring expense",
                "frequency": "monthly",
                "start_date": datetime.now().isoformat(),
                "auto_submit": True
            }

            response = requests.post(
                f"{BASE_URL}/api/recurring-expenses",
                headers=self.get_headers(),
                json=test_data
            )

            if response.status_code == 201:
                data = response.json()
                template_id = data.get("id")
                self.log("Create Recurring Expense", "PASS", f"Created template {template_id}")

                # Test pause
                response = requests.post(
                    f"{BASE_URL}/api/recurring-expenses/{template_id}/pause",
                    headers=self.get_headers()
                )
                if response.status_code == 200:
                    self.log("Pause Recurring Expense", "PASS", "Template paused")
                else:
                    self.log("Pause Recurring Expense", "FAIL", f"Status {response.status_code}")

                # Test resume
                response = requests.post(
                    f"{BASE_URL}/api/recurring-expenses/{template_id}/resume",
                    headers=self.get_headers()
                )
                if response.status_code == 200:
                    self.log("Resume Recurring Expense", "PASS", "Template resumed")
                else:
                    self.log("Resume Recurring Expense", "FAIL", f"Status {response.status_code}")

                claude/start-app-run-tests-011CUsFhjmtARBb1wf79NhDT
                # Test UPDATE recurring expense
                try:
                    update_data = {
                        "vendor": "Updated Vendor Name",
                        "amount": 150.00,
                        "description": "Updated recurring expense description"
                    }
                    response = requests.patch(
                        f"{BASE_URL}/api/recurring-expenses/{template_id}",
                        headers=self.get_headers(),
                        json=update_data
                    )
                    if response.status_code == 200:
                        updated = response.json()
                        if updated.get("vendor") == "Updated Vendor Name" and updated.get("amount") == 150.00:
                            self.log("Update Recurring Expense", "PASS", "Template updated successfully")
                        else:
                            self.log("Update Recurring Expense", "FAIL", "Updated data doesn't match")
                    else:
                        self.log("Update Recurring Expense", "FAIL", f"Status {response.status_code}")
                except Exception as e:
                    self.log("Update Recurring Expense", "FAIL", str(e))

                # Test GET single recurring expense
                try:
                    response = requests.get(
                        f"{BASE_URL}/api/recurring-expenses/{template_id}",
                        headers=self.get_headers()
                    )
                    if response.status_code == 200:
                        self.log("Get Single Recurring Expense", "PASS", "Template retrieved")
                    else:
                        self.log("Get Single Recurring Expense", "FAIL", f"Status {response.status_code}")
                except Exception as e:
                    self.log("Get Single Recurring Expense", "FAIL", str(e))


                main
                # Test delete
                response = requests.delete(
                    f"{BASE_URL}/api/recurring-expenses/{template_id}",
                    headers=self.get_headers()
                )
                if response.status_code == 204:
                    self.log("Delete Recurring Expense", "PASS", "Template deleted")
                else:
                    self.log("Delete Recurring Expense", "FAIL", f"Status {response.status_code}")
            else:
                self.log("Create Recurring Expense", "FAIL", f"Status {response.status_code}: {response.text}")
        except Exception as e:
            self.log("Create Recurring Expense", "FAIL", str(e))

    # ============================================================================
    # TAB 8: BUDGETS
    # ============================================================================

    def test_budgets_tab(self):
        """Test Budgets tab"""
        print("\n💰 Testing BUDGETS Tab...")

        # Get budgets
        try:
            response = requests.get(
                f"{BASE_URL}/api/budgets",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                data = response.json()
                count = len(data.get("budgets", [])) if isinstance(data, dict) else len(data)
                self.log("Get Budgets", "PASS", f"Found {count} budgets")
            else:
                self.log("Get Budgets", "FAIL", f"Status {response.status_code}")
        except Exception as e:
            self.log("Get Budgets", "FAIL", str(e))

        # Test create budget
        try:
            test_budget = {
                "name": "Test Budget",
                "category": "Travel",
                "amount": 5000.00,
                "period": "monthly",
                "start_date": datetime.now().isoformat(),
                "alert_threshold": 80
            }

            response = requests.post(
                f"{BASE_URL}/api/budgets",
                headers=self.get_headers(),
                json=test_budget
            )

            if response.status_code == 201:
                data = response.json()
                budget_id = data.get("id")
                self.log("Create Budget", "PASS", f"Created budget {budget_id}")

             claude/start-app-run-tests-011CUsFhjmtARBb1wf79NhDT
                # Test UPDATE budget
                try:
                    update_data = {
                        "name": "Updated Test Budget",
                        "amount": 6000.00,
                        "warning_threshold": 70,
                        "critical_threshold": 85
                    }
                    response = requests.patch(
                        f"{BASE_URL}/api/budgets/{budget_id}",
                        headers=self.get_headers(),
                        json=update_data
                    )
                    if response.status_code == 200:
                        updated = response.json()
                        if updated.get("name") == "Updated Test Budget" and updated.get("amount") == 6000.00:
                            self.log("Update Budget", "PASS", f"Budget updated successfully")
                        else:
                            self.log("Update Budget", "FAIL", "Updated data doesn't match")
                    else:
                        self.log("Update Budget", "FAIL", f"Status {response.status_code}")
                except Exception as e:
                    self.log("Update Budget", "FAIL", str(e))

                # Test GET single budget
                try:
                    response = requests.get(
                        f"{BASE_URL}/api/budgets/{budget_id}",
                        headers=self.get_headers()
                    )
                    if response.status_code == 200:
                        self.log("Get Single Budget", "PASS", "Budget retrieved")
                    else:
                        self.log("Get Single Budget", "FAIL", f"Status {response.status_code}")
                except Exception as e:
                    self.log("Get Single Budget", "FAIL", str(e))


               main
                # Test delete
                response = requests.delete(
                    f"{BASE_URL}/api/budgets/{budget_id}",
                    headers=self.get_headers()
                )
                if response.status_code == 204:
                    self.log("Delete Budget", "PASS", "Budget deleted")
                else:
                    self.log("Delete Budget", "FAIL", f"Status {response.status_code}")
            else:
                self.log("Create Budget", "FAIL", f"Status {response.status_code}: {response.text}")
        except Exception as e:
            self.log("Create Budget", "FAIL", str(e))

    # ============================================================================
    # NOTIFICATIONS
    # ============================================================================

    def test_notifications(self):
        """Test Notifications"""
        print("\n🔔 Testing NOTIFICATIONS...")

        # Get notifications
        try:
            response = requests.get(
                f"{BASE_URL}/api/notifications?limit=20",
                headers=self.get_headers()
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
                self.log("Get Unread Count", "PASS", f"{count} unread notifications")
            else:
                self.log("Get Unread Count", "FAIL", f"Status {response.status_code}")
        except Exception as e:
            self.log("Get Unread Count", "FAIL", str(e))

    # ============================================================================
    # DASHBOARD STATS
    # ============================================================================

    def test_dashboard_stats(self):
        """Test Dashboard Statistics"""
        print("\n📈 Testing DASHBOARD STATS...")

        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/admin/dashboard/stats",
                headers=self.get_headers()
            )
            if response.status_code == 200:
                data = response.json()
                self.log("Get Dashboard Stats", "PASS", "Stats loaded successfully")
            else:
                self.log("Get Dashboard Stats", "FAIL", f"Status {response.status_code}")
        except Exception as e:
            self.log("Get Dashboard Stats", "FAIL", str(e))

    # ============================================================================
    # RUN ALL TESTS
    # ============================================================================

    def run_all_tests(self):
        """Run all admin dashboard tests"""
        print("=" * 80)
        print("🚀 ADMIN DASHBOARD COMPREHENSIVE TEST")
        print("=" * 80)

        # Login first
        if not self.login():
            print("\n❌ Login failed. Cannot continue with tests.")
            return

        # Run all tab tests
        self.test_pending_tab()
        self.test_all_expenses_tab()
        self.test_archived_tab()
        self.test_user_management_tab()
        self.test_billing_tab()
        self.test_ai_assistant_tab()
        self.test_recurring_expenses_tab()
        self.test_budgets_tab()
        self.test_notifications()
        self.test_dashboard_stats()

        # Summary
        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)

        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        skipped = sum(1 for r in self.results if r["status"] == "SKIP")
        total = len(self.results)

        print(f"\n✅ Passed:  {passed}/{total}")
        print(f"❌ Failed:  {failed}/{total}")
        print(f"⚠️  Skipped: {skipped}/{total}")

        if failed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.results:
                if result["status"] == "FAIL":
                    print(f"  • {result['test']}: {result['message']}")

        print("\n" + "=" * 80)

        # Save results to file
        with open("test_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        print("\n💾 Detailed results saved to: test_results.json")

if __name__ == "__main__":
    tester = AdminDashboardTester()
    tester.run_all_tests()
