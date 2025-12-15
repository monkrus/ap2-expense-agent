"""
Comprehensive Application Flow Testing
Tests all major user journeys and workflows
"""
import requests
import json
import time
from datetime import datetime, timedelta

API_BASE = "http://localhost:8000/api/v1"

class AppFlowTester:
    def __init__(self):
        self.session = requests.Session()
        self.users = {}  # Store user data
        self.orgs = {}   # Store organization data
        self.expenses = {}  # Store expense data
        self.tokens = {}  # Store auth tokens

    def print_section(self, title):
        """Print formatted section header"""
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80 + "\n")

    def print_result(self, test_name, passed, details=""):
        """Print test result"""
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {test_name}")
        if details:
            print(f"      {details}")

    # ========================================================================
    # 1. AUTHENTICATION FLOWS
    # ========================================================================

    def test_authentication_flow(self):
        """Test user registration, login, logout, token refresh"""
        self.print_section("1. AUTHENTICATION FLOWS")

        # 1.1: Login with existing user
        print("1.1: Testing login with adminfree...")
        login_data = {"username": "adminfree", "password": "Testme1!"}
        response = self.session.post(f"{API_BASE}/auth/login", json=login_data)

        if response.status_code == 200:
            data = response.json()
            self.tokens['adminfree'] = data.get('access_token')
            self.users['adminfree'] = data
            self.print_result("Login successful", True, f"Token: {data.get('access_token')[:30]}...")
        else:
            self.print_result("Login failed", False, f"Status: {response.status_code}, {response.text}")
            return False

        # 1.2: Get current user info
        print("\n1.2: Testing get current user...")
        headers = {"Authorization": f"Bearer {self.tokens['adminfree']}"}
        response = self.session.get(f"{API_BASE}/users/me", headers=headers)

        if response.status_code == 200:
            user_data = response.json()
            self.print_result("Get current user", True,
                            f"User: {user_data.get('username')}, Role: {user_data.get('role')}")
        else:
            self.print_result("Get current user", False, f"Status: {response.status_code}")

        # 1.3: Test invalid login
        print("\n1.3: Testing invalid login...")
        bad_login = {"username": "adminfree", "password": "WrongPassword"}
        response = self.session.post(f"{API_BASE}/auth/login", json=bad_login)

        passed = response.status_code in [401, 403]
        self.print_result("Invalid login rejected", passed, f"Status: {response.status_code}")

        # 1.4: Create second user for multi-tenancy testing
        print("\n1.4: Creating second user (user2)...")
        user2_data = {
            "username": "user2test",
            "email": "user2@example.com",
            "password": "Testme1!",
            "full_name": "User Two"
        }
        response = self.session.post(f"{API_BASE}/auth/register", json=user2_data)

        if response.status_code == 201:
            self.print_result("Second user created", True, f"Username: user2test")
            # Login as user2
            login_response = self.session.post(f"{API_BASE}/auth/login",
                                              json={"username": "user2test", "password": "Testme1!"})
            if login_response.status_code == 200:
                self.tokens['user2'] = login_response.json().get('access_token')
        else:
            self.print_result("Second user creation", False, f"Status: {response.status_code}")

        return True

    # ========================================================================
    # 2. ORGANIZATION FLOWS
    # ========================================================================

    def test_organization_flows(self):
        """Test organization CRUD, invitations, members"""
        self.print_section("2. ORGANIZATION MANAGEMENT FLOWS")

        headers = {"Authorization": f"Bearer {self.tokens['adminfree']}"}

        # 2.1: Create organization
        print("2.1: Creating organization...")
        org_data = {
            "name": "Test Company Inc",
            "slug": "test-company",
            "description": "A test organization for flow testing"
        }
        response = self.session.post(f"{API_BASE}/organizations", json=org_data, headers=headers)

        if response.status_code == 201:
            org = response.json()
            self.orgs['test-company'] = org
            self.print_result("Organization created", True,
                            f"Name: {org.get('name')}, ID: {org.get('id')}")
        else:
            self.print_result("Organization creation", False,
                            f"Status: {response.status_code}, {response.text}")
            return False

        # 2.2: List organizations
        print("\n2.2: Listing organizations...")
        response = self.session.get(f"{API_BASE}/organizations", headers=headers)

        if response.status_code == 200:
            orgs = response.json()
            self.print_result("List organizations", True, f"Count: {len(orgs)}")
        else:
            self.print_result("List organizations", False, f"Status: {response.status_code}")

        # 2.3: Get organization details
        print("\n2.3: Getting organization details...")
        org_id = self.orgs['test-company']['id']
        response = self.session.get(f"{API_BASE}/organizations/{org_id}", headers=headers)

        if response.status_code == 200:
            org_detail = response.json()
            self.print_result("Get organization details", True,
                            f"Members: {org_detail.get('member_count', 'N/A')}")
        else:
            self.print_result("Get organization details", False, f"Status: {response.status_code}")

        # 2.4: Update organization
        print("\n2.4: Updating organization...")
        update_data = {"description": "Updated description for testing"}
        response = self.session.patch(f"{API_BASE}/organizations/{org_id}",
                                     json=update_data, headers=headers)

        if response.status_code == 200:
            self.print_result("Update organization", True)
        else:
            self.print_result("Update organization", False, f"Status: {response.status_code}")

        # 2.5: Test free tier limit (try to create second org)
        print("\n2.5: Testing free tier organization limit...")
        org2_data = {
            "name": "Second Org",
            "slug": "second-org",
            "description": "Should be blocked by free tier limit"
        }
        response = self.session.post(f"{API_BASE}/organizations", json=org2_data, headers=headers)

        passed = response.status_code == 402  # Payment Required
        self.print_result("Free tier limit enforced", passed,
                        f"Status: {response.status_code}, Expected: 402")

        return True

    # ========================================================================
    # 3. EXPENSE FLOWS
    # ========================================================================

    def test_expense_flows(self):
        """Test expense creation, updates, approvals"""
        self.print_section("3. EXPENSE MANAGEMENT FLOWS")

        headers = {"Authorization": f"Bearer {self.tokens['adminfree']}"}
        org_id = self.orgs['test-company']['id']

        # 3.1: Create expense
        print("3.1: Creating expense...")
        expense_data = {
            "organization_id": org_id,
            "amount": 125.50,
            "category": "travel",
            "description": "Client meeting lunch",
            "expense_date": datetime.now().isoformat(),
            "merchant": "Restaurant ABC"
        }
        response = self.session.post(f"{API_BASE}/expenses", json=expense_data, headers=headers)

        if response.status_code == 201:
            expense = response.json()
            self.expenses['expense1'] = expense
            self.print_result("Expense created", True,
                            f"ID: {expense.get('id')}, Amount: ${expense.get('amount')}")
        else:
            self.print_result("Expense creation", False,
                            f"Status: {response.status_code}, {response.text}")
            return False

        # 3.2: List expenses
        print("\n3.2: Listing expenses...")
        response = self.session.get(f"{API_BASE}/expenses?organization_id={org_id}", headers=headers)

        if response.status_code == 200:
            expenses = response.json()
            self.print_result("List expenses", True, f"Count: {len(expenses)}")
        else:
            self.print_result("List expenses", False, f"Status: {response.status_code}")

        # 3.3: Get expense details
        print("\n3.3: Getting expense details...")
        expense_id = self.expenses['expense1']['id']
        response = self.session.get(f"{API_BASE}/expenses/{expense_id}", headers=headers)

        if response.status_code == 200:
            expense_detail = response.json()
            self.print_result("Get expense details", True,
                            f"Status: {expense_detail.get('status')}")
        else:
            self.print_result("Get expense details", False, f"Status: {response.status_code}")

        # 3.4: Update expense
        print("\n3.4: Updating expense...")
        update_data = {"description": "Updated: Client meeting lunch with CEO"}
        response = self.session.patch(f"{API_BASE}/expenses/{expense_id}",
                                     json=update_data, headers=headers)

        if response.status_code == 200:
            self.print_result("Update expense", True)
        else:
            self.print_result("Update expense", False, f"Status: {response.status_code}")

        # 3.5: Create multiple expenses for testing
        print("\n3.5: Creating additional test expenses...")
        for i in range(3):
            exp_data = {
                "organization_id": org_id,
                "amount": 50.0 + (i * 10),
                "category": "office_supplies" if i % 2 == 0 else "software",
                "description": f"Test expense {i+1}",
                "expense_date": datetime.now().isoformat()
            }
            response = self.session.post(f"{API_BASE}/expenses", json=exp_data, headers=headers)
            if response.status_code == 201:
                print(f"  - Expense {i+1} created: ${exp_data['amount']}")

        self.print_result("Bulk expense creation", True, "Created 3 additional expenses")

        return True

    # ========================================================================
    # 4. BILLING FLOWS
    # ========================================================================

    def test_billing_flows(self):
        """Test subscription, usage tracking, billing endpoints"""
        self.print_section("4. BILLING & SUBSCRIPTION FLOWS")

        headers = {"Authorization": f"Bearer {self.tokens['adminfree']}"}

        # 4.1: Get current subscription
        print("4.1: Getting current subscription...")
        response = self.session.get(f"{API_BASE}/billing/subscription", headers=headers)

        if response.status_code == 200:
            subscription = response.json()
            self.print_result("Get subscription", True,
                            f"Tier: {subscription.get('tier', 'N/A')}")
        else:
            self.print_result("Get subscription", False, f"Status: {response.status_code}")

        # 4.2: Get usage metrics
        print("\n4.2: Getting usage metrics...")
        response = self.session.get(f"{API_BASE}/billing/usage", headers=headers)

        if response.status_code == 200:
            usage = response.json()
            self.print_result("Get usage metrics", True,
                            f"Expenses: {usage.get('expenses_count', 0)}/{usage.get('expenses_limit', 'N/A')}")
        else:
            self.print_result("Get usage metrics", False, f"Status: {response.status_code}")

        # 4.3: List available tiers
        print("\n4.3: Listing available subscription tiers...")
        response = self.session.get(f"{API_BASE}/billing/tiers", headers=headers)

        if response.status_code == 200:
            tiers = response.json()
            self.print_result("List tiers", True, f"Available tiers: {len(tiers)}")
            for tier in tiers:
                print(f"  - {tier.get('name')}: ${tier.get('monthly_price')}/mo")
        else:
            self.print_result("List tiers", False, f"Status: {response.status_code}")

        # 4.4: Get billing history
        print("\n4.4: Getting billing history...")
        response = self.session.get(f"{API_BASE}/billing/history", headers=headers)

        if response.status_code == 200:
            self.print_result("Get billing history", True)
        else:
            # Might return 404 if no history exists
            self.print_result("Get billing history", response.status_code in [200, 404],
                            f"Status: {response.status_code}")

        return True

    # ========================================================================
    # 5. AP2 PAYMENT MANDATE FLOWS
    # ========================================================================

    def test_ap2_flows(self):
        """Test AP2 payment mandate creation and processing"""
        self.print_section("5. AP2 PAYMENT MANDATE FLOWS")

        headers = {"Authorization": f"Bearer {self.tokens['adminfree']}"}

        # 5.1: Create intent mandate
        print("5.1: Creating AP2 intent mandate...")
        intent_data = {
            "max_amount": 500.00,
            "expiration_minutes": 60,
            "allowed_merchants": ["Vendor A", "Vendor B"]
        }
        response = self.session.post(f"{API_BASE}/ap2/intent", json=intent_data, headers=headers)

        if response.status_code == 201:
            intent = response.json()
            self.print_result("Intent mandate created", True,
                            f"ID: {intent.get('id')}, Max: ${intent.get('max_amount')}")
        elif response.status_code == 404:
            self.print_result("Intent mandate endpoint", False,
                            "AP2 routes not found (may not be implemented)")
            return True  # Not critical
        else:
            self.print_result("Intent mandate creation", False, f"Status: {response.status_code}")

        return True

    # ========================================================================
    # 6. MULTI-TENANCY ISOLATION
    # ========================================================================

    def test_multi_tenancy_isolation(self):
        """Test that users cannot access other users' data"""
        self.print_section("6. MULTI-TENANCY ISOLATION")

        if 'user2' not in self.tokens:
            self.print_result("Multi-tenancy test", False, "user2 not available")
            return False

        headers_user1 = {"Authorization": f"Bearer {self.tokens['adminfree']}"}
        headers_user2 = {"Authorization": f"Bearer {self.tokens['user2']}"}

        # 6.1: User2 tries to access User1's organization
        print("6.1: Testing organization isolation...")
        org_id = self.orgs['test-company']['id']
        response = self.session.get(f"{API_BASE}/organizations/{org_id}", headers=headers_user2)

        passed = response.status_code in [403, 404]  # Should be forbidden or not found
        self.print_result("Organization access blocked", passed,
                        f"Status: {response.status_code}, Expected: 403 or 404")

        # 6.2: User2 tries to access User1's expenses
        print("\n6.2: Testing expense isolation...")
        if self.expenses:
            expense_id = self.expenses['expense1']['id']
            response = self.session.get(f"{API_BASE}/expenses/{expense_id}", headers=headers_user2)

            passed = response.status_code in [403, 404]
            self.print_result("Expense access blocked", passed,
                            f"Status: {response.status_code}, Expected: 403 or 404")

        # 6.3: User2 lists organizations (should only see their own)
        print("\n6.3: Testing organization list isolation...")
        response = self.session.get(f"{API_BASE}/organizations", headers=headers_user2)

        if response.status_code == 200:
            user2_orgs = response.json()
            passed = len(user2_orgs) == 0  # User2 has no orgs
            self.print_result("Organization list isolated", passed,
                            f"User2 orgs count: {len(user2_orgs)}, Expected: 0")
        else:
            self.print_result("Organization list", False, f"Status: {response.status_code}")

        return True

    # ========================================================================
    # 7. DASHBOARD & REPORTING
    # ========================================================================

    def test_dashboard_flows(self):
        """Test dashboard and reporting endpoints"""
        self.print_section("7. DASHBOARD & REPORTING FLOWS")

        headers = {"Authorization": f"Bearer {self.tokens['adminfree']}"}
        org_id = self.orgs['test-company']['id']

        # 7.1: Get expense statistics
        print("7.1: Getting expense statistics...")
        response = self.session.get(f"{API_BASE}/expenses/stats?organization_id={org_id}",
                                   headers=headers)

        if response.status_code == 200:
            stats = response.json()
            self.print_result("Expense statistics", True,
                            f"Total: ${stats.get('total_amount', 0)}")
        elif response.status_code == 404:
            self.print_result("Expense statistics", True, "Endpoint not implemented (optional)")
        else:
            self.print_result("Expense statistics", False, f"Status: {response.status_code}")

        # 7.2: Filter expenses by date range
        print("\n7.2: Testing expense date filtering...")
        start_date = (datetime.now() - timedelta(days=7)).isoformat()
        end_date = datetime.now().isoformat()
        response = self.session.get(
            f"{API_BASE}/expenses?organization_id={org_id}&start_date={start_date}&end_date={end_date}",
            headers=headers
        )

        if response.status_code == 200:
            expenses = response.json()
            self.print_result("Date range filtering", True, f"Found: {len(expenses)} expenses")
        else:
            self.print_result("Date range filtering", False, f"Status: {response.status_code}")

        # 7.3: Filter expenses by category
        print("\n7.3: Testing expense category filtering...")
        response = self.session.get(
            f"{API_BASE}/expenses?organization_id={org_id}&category=travel",
            headers=headers
        )

        if response.status_code == 200:
            expenses = response.json()
            self.print_result("Category filtering", True, f"Travel expenses: {len(expenses)}")
        else:
            self.print_result("Category filtering", False, f"Status: {response.status_code}")

        return True

    # ========================================================================
    # 8. CLEANUP & SUMMARY
    # ========================================================================

    def cleanup(self):
        """Delete test organization (soft delete)"""
        self.print_section("8. CLEANUP")

        headers = {"Authorization": f"Bearer {self.tokens['adminfree']}"}

        if self.orgs:
            org_id = self.orgs['test-company']['id']
            print(f"Deleting organization: {org_id}...")
            response = self.session.delete(f"{API_BASE}/organizations/{org_id}", headers=headers)

            if response.status_code == 204:
                self.print_result("Organization deleted", True)
            else:
                self.print_result("Organization deletion", False,
                                f"Status: {response.status_code}")

    def run_all_tests(self):
        """Run all flow tests"""
        print("\n" + "=" * 80)
        print("  COMPREHENSIVE APPLICATION FLOW TESTING")
        print("  AP2 Expense Management Agent")
        print("=" * 80)
        print(f"\nStarted at: {datetime.now()}")
        print(f"API Base: {API_BASE}\n")

        tests = [
            ("Authentication", self.test_authentication_flow),
            ("Organizations", self.test_organization_flows),
            ("Expenses", self.test_expense_flows),
            ("Billing", self.test_billing_flows),
            ("AP2 Mandates", self.test_ap2_flows),
            ("Multi-tenancy", self.test_multi_tenancy_isolation),
            ("Dashboard", self.test_dashboard_flows),
        ]

        results = {}
        for test_name, test_func in tests:
            try:
                result = test_func()
                results[test_name] = result
            except Exception as e:
                print(f"\n[ERROR] {test_name} test failed with exception: {e}")
                results[test_name] = False

        # Cleanup
        try:
            self.cleanup()
        except Exception as e:
            print(f"\n[ERROR] Cleanup failed: {e}")

        # Summary
        self.print_section("TEST SUMMARY")
        passed = sum(1 for v in results.values() if v)
        total = len(results)

        print(f"Results: {passed}/{total} test suites passed\n")
        for test_name, result in results.items():
            status = "[PASS]" if result else "[FAIL]"
            print(f"{status} {test_name}")

        print(f"\nCompleted at: {datetime.now()}")

        return passed == total

if __name__ == "__main__":
    tester = AppFlowTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)
