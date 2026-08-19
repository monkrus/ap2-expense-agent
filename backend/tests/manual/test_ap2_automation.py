"""
Automated AP2 Automation Test Suite
Tests all major AP2 features including Intent Mandates, auto-approval, and constraints
"""

import requests
import json
from datetime import datetime, timedelta
import time
from typing import Dict, Any, Optional

BASE_URL = "http://localhost:8000"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

class AP2TestSuite:
    def __init__(self):
        self.token = None
        self.user_id = None
        self.org_id = None
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.test_results = []

    def log_test(self, section: str, test_name: str, passed: bool, message: str = ""):
        status = f"{Colors.GREEN}[PASS]{Colors.RESET}" if passed else f"{Colors.RED}[FAIL]{Colors.RESET}"
        print(f"{status} | {section} | {test_name}")
        if message:
            print(f"       {message}")

        if passed:
            self.passed += 1
        else:
            self.failed += 1

        self.test_results.append({
            "section": section,
            "test": test_name,
            "passed": passed,
            "message": message
        })

    def login(self, username: str = "employee1", password: str = "Password123!") -> bool:
        """Login and get access token"""
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/auth/login",
                json={"username": username, "password": password}
            )

            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.user_id = data.get("user", {}).get("id")
                self.org_id = data.get("user", {}).get("organization_id")
                print(f"{Colors.BLUE}Logged in as {username}{Colors.RESET}")
                return True
            else:
                print(f"{Colors.RED}Login failed: {response.status_code}{Colors.RESET}")
                return False
        except Exception as e:
            print(f"{Colors.RED}Login error: {e}{Colors.RESET}")
            return False

    def get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    # ===== SECTION 1: INTENT MANDATE CREATION =====

    def test_1_1_create_basic_intent_mandate(self):
        """Test 1.1: Create Basic Intent Mandate via API"""
        try:
            payload = {
                "constraints": {
                    "max_amount": 200.00,
                    "monthly_limit": 1000.00,
                    "category": "OFFICE_SUPPLIES",
                    "merchant": "Amazon"
                },
                "expiration": (datetime.now() + timedelta(days=1)).isoformat()
            }

            response = requests.post(
                f"{BASE_URL}/api/ap2/intent-mandate",
                headers=self.get_headers(),
                json=payload
            )

            if response.status_code == 201:
                data = response.json()
                checks = [
                    data.get("intent_mandate_id") is not None,
                    data.get("signature") is not None,
                    data.get("status") == "active"
                ]

                if all(checks):
                    self.log_test("1. Intent Mandate Creation", "1.1 Create Basic Mandate", True,
                                f"ID: {data.get('intent_mandate_id')[:8]}...")
                    return data.get("intent_mandate_id")
                else:
                    self.log_test("1. Intent Mandate Creation", "1.1 Create Basic Mandate", False,
                                f"Missing fields in response")
            else:
                self.log_test("1. Intent Mandate Creation", "1.1 Create Basic Mandate", False,
                            f"Status {response.status_code}: {response.text[:100]}")
        except Exception as e:
            self.log_test("1. Intent Mandate Creation", "1.1 Create Basic Mandate", False, str(e))

        return None

    def test_1_2_multiple_merchants(self):
        """Test 1.2: Create Intent Mandate with Multiple Merchants"""
        try:
            payload = {
                "constraints": {
                    "max_amount": 500.00,
                    "monthly_limit": 2000.00,
                    "category": "SOFTWARE",
                    "merchants": ["Microsoft", "Adobe", "Atlassian"]
                },
                "expiration": (datetime.now() + timedelta(days=1)).isoformat()
            }

            response = requests.post(
                f"{BASE_URL}/api/ap2/intent-mandate",
                headers=self.get_headers(),
                json=payload
            )

            passed = response.status_code == 201
            self.log_test("1. Intent Mandate Creation", "1.2 Multiple Merchants", passed,
                        f"Status: {response.status_code}")

            return response.json().get("intent_mandate_id") if passed else None
        except Exception as e:
            self.log_test("1. Intent Mandate Creation", "1.2 Multiple Merchants", False, str(e))
            return None

    def test_1_3_multiple_categories(self):
        """Test 1.3: Create Intent Mandate with Multiple Categories"""
        try:
            payload = {
                "constraints": {
                    "max_amount": 300.00,
                    "monthly_limit": 1500.00,
                    "categories": ["OFFICE_SUPPLIES", "TRAVEL", "MEALS"],
                    "merchant": "Costco"
                },
                "expiration": (datetime.now() + timedelta(days=1)).isoformat()
            }

            response = requests.post(
                f"{BASE_URL}/api/ap2/intent-mandate",
                headers=self.get_headers(),
                json=payload
            )

            passed = response.status_code == 201
            self.log_test("1. Intent Mandate Creation", "1.3 Multiple Categories", passed,
                        f"Status: {response.status_code}")

            return response.json().get("intent_mandate_id") if passed else None
        except Exception as e:
            self.log_test("1. Intent Mandate Creation", "1.3 Multiple Categories", False, str(e))
            return None

    def test_1_5_invalid_constraints(self):
        """Test 1.5: Attempt to Create Intent Mandate with Invalid Constraints"""
        test_cases = [
            ("1.5a Negative Amount", {"constraints": {"max_amount": -50.00}}),
            ("1.5b Monthly < Max", {"constraints": {"max_amount": 500.00, "monthly_limit": 100.00}}),
            ("1.5d Past Expiration", {"constraints": {"max_amount": 100}, "expiration": "2020-01-01T00:00:00"})
        ]

        for test_name, payload in test_cases:
            try:
                response = requests.post(
                    f"{BASE_URL}/api/ap2/intent-mandate",
                    headers=self.get_headers(),
                    json=payload
                )

                passed = response.status_code == 400
                self.log_test("1. Intent Mandate Creation", test_name, passed,
                            f"Status: {response.status_code}")
            except Exception as e:
                self.log_test("1. Intent Mandate Creation", test_name, False, str(e))

    # ===== SECTION 2: INTENT MANDATE MANAGEMENT =====

    def test_2_1_list_mandates(self):
        """Test 2.1: List All User Mandates"""
        try:
            response = requests.get(
                f"{BASE_URL}/api/ap2/user/mandates",
                headers=self.get_headers()
            )

            if response.status_code == 200:
                mandates = response.json()
                passed = isinstance(mandates, list)
                self.log_test("2. Mandate Management", "2.1 List Mandates", passed,
                            f"Found {len(mandates)} mandates")
                return mandates
            else:
                self.log_test("2. Mandate Management", "2.1 List Mandates", False,
                            f"Status: {response.status_code}")
                return []
        except Exception as e:
            self.log_test("2. Mandate Management", "2.1 List Mandates", False, str(e))
            return []

    def test_2_4_revoke_mandate(self, mandate_id: str):
        """Test 2.4: Delete/Revoke Intent Mandate"""
        if not mandate_id:
            self.log_test("2. Mandate Management", "2.4 Revoke Mandate", False, "No mandate ID provided")
            return

        try:
            response = requests.post(
                f"{BASE_URL}/api/ap2/intent-mandate/{mandate_id}/revoke",
                headers=self.get_headers()
            )

            passed = response.status_code == 200
            self.log_test("2. Mandate Management", "2.4 Revoke Mandate", passed,
                        f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("2. Mandate Management", "2.4 Revoke Mandate", False, str(e))

    # ===== SECTION 3: AUTO-APPROVAL WORKFLOW =====

    def test_3_1_basic_auto_approval(self, mandate_id: str):
        """Test 3.1: Basic Auto-Approval via Intent Mandate"""
        if not mandate_id:
            self.log_test("3. Auto-Approval", "3.1 Basic Auto-Approval", False, "No mandate ID")
            return None

        try:
            # Submit expense matching the mandate
            expense_payload = {
                "amount": 45.99,
                "vendor": "Amazon",
                "category": "OFFICE_SUPPLIES",
                "description": "Test auto-approval - keyboard and mouse",
                "date": datetime.now().isoformat()
            }

            response = requests.post(
                f"{BASE_URL}/api/v1/expenses",
                headers=self.get_headers(),
                json=expense_payload
            )

            if response.status_code in [200, 201]:
                data = response.json()

                # Check auto-approval fields
                checks = {
                    "status_approved": data.get("status") == "APPROVED",
                    "auto_approved": data.get("auto_approved") == True,
                    "via_intent_mandate": data.get("auto_approved_via") == "intent_mandate",
                    "mandate_linked": data.get("intent_mandate_id") is not None
                }

                all_passed = all(checks.values())
                details = ", ".join([f"{k}: {v}" for k, v in checks.items()])

                self.log_test("3. Auto-Approval", "3.1 Basic Auto-Approval", all_passed, details)
                return data.get("id")
            else:
                self.log_test("3. Auto-Approval", "3.1 Basic Auto-Approval", False,
                            f"Status: {response.status_code}, Response: {response.text[:200]}")
        except Exception as e:
            self.log_test("3. Auto-Approval", "3.1 Basic Auto-Approval", False, str(e))

        return None

    def test_3_3_amount_exceeds_limit(self):
        """Test 3.3: Auto-Approval Rejection - Amount Exceeds Limit"""
        try:
            # Create mandate with low limit
            mandate_payload = {
                "constraints": {
                    "max_amount": 50.00,
                    "category": "OFFICE_SUPPLIES",
                    "merchant": "Amazon"
                },
                "expiration": (datetime.now() + timedelta(hours=1)).isoformat()
            }

            response = requests.post(
                f"{BASE_URL}/api/ap2/intent-mandate",
                headers=self.get_headers(),
                json=mandate_payload
            )

            if response.status_code != 201:
                self.log_test("3. Auto-Approval", "3.3 Amount Exceeds", False, "Failed to create test mandate")
                return

            # Submit expense exceeding limit
            expense_payload = {
                "amount": 150.00,  # Exceeds $50 limit
                "vendor": "Amazon",
                "category": "OFFICE_SUPPLIES",
                "description": "Test amount exceeds limit",
                "date": datetime.now().isoformat()
            }

            response = requests.post(
                f"{BASE_URL}/api/v1/expenses",
                headers=self.get_headers(),
                json=expense_payload
            )

            if response.status_code in [200, 201]:
                data = response.json()

                # Should NOT be auto-approved
                passed = data.get("status") == "PENDING" and not data.get("auto_approved")
                self.log_test("3. Auto-Approval", "3.3 Amount Exceeds", passed,
                            f"Status: {data.get('status')}, auto_approved: {data.get('auto_approved')}")
            else:
                self.log_test("3. Auto-Approval", "3.3 Amount Exceeds", False,
                            f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("3. Auto-Approval", "3.3 Amount Exceeds", False, str(e))

    def test_3_4_wrong_category(self):
        """Test 3.4: Auto-Approval Rejection - Wrong Category"""
        try:
            # Create mandate for OFFICE_SUPPLIES
            mandate_payload = {
                "constraints": {
                    "max_amount": 100.00,
                    "category": "OFFICE_SUPPLIES"
                },
                "expiration": (datetime.now() + timedelta(hours=1)).isoformat()
            }

            response = requests.post(
                f"{BASE_URL}/api/ap2/intent-mandate",
                headers=self.get_headers(),
                json=mandate_payload
            )

            if response.status_code != 201:
                self.log_test("3. Auto-Approval", "3.4 Wrong Category", False, "Failed to create test mandate")
                return

            # Submit TRAVEL expense
            expense_payload = {
                "amount": 50.00,
                "vendor": "Delta Airlines",
                "category": "TRAVEL",
                "description": "Test wrong category",
                "date": datetime.now().isoformat()
            }

            response = requests.post(
                f"{BASE_URL}/api/v1/expenses",
                headers=self.get_headers(),
                json=expense_payload
            )

            if response.status_code in [200, 201]:
                data = response.json()

                # Should NOT be auto-approved
                passed = data.get("status") == "PENDING" and not data.get("auto_approved")
                self.log_test("3. Auto-Approval", "3.4 Wrong Category", passed,
                            f"Status: {data.get('status')}, auto_approved: {data.get('auto_approved')}")
            else:
                self.log_test("3. Auto-Approval", "3.4 Wrong Category", False,
                            f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("3. Auto-Approval", "3.4 Wrong Category", False, str(e))

    def test_3_6_case_insensitive(self):
        """Test 3.6: Auto-Approval with Case-Insensitive Matching"""
        try:
            # Create mandate with lowercase
            mandate_payload = {
                "constraints": {
                    "max_amount": 100.00,
                    "category": "office_supplies",
                    "merchant": "amazon"
                },
                "expiration": (datetime.now() + timedelta(hours=1)).isoformat()
            }

            response = requests.post(
                f"{BASE_URL}/api/ap2/intent-mandate",
                headers=self.get_headers(),
                json=mandate_payload
            )

            if response.status_code != 201:
                self.log_test("3. Auto-Approval", "3.6 Case Insensitive", False, "Failed to create test mandate")
                return

            # Submit expense with uppercase
            expense_payload = {
                "amount": 50.00,
                "vendor": "AMAZON",
                "category": "OFFICE_SUPPLIES",
                "description": "Test case insensitive",
                "date": datetime.now().isoformat()
            }

            response = requests.post(
                f"{BASE_URL}/api/v1/expenses",
                headers=self.get_headers(),
                json=expense_payload
            )

            if response.status_code in [200, 201]:
                data = response.json()

                # Should be auto-approved
                passed = data.get("status") == "APPROVED" and data.get("auto_approved")
                self.log_test("3. Auto-Approval", "3.6 Case Insensitive", passed,
                            f"Status: {data.get('status')}, auto_approved: {data.get('auto_approved')}")
            else:
                self.log_test("3. Auto-Approval", "3.6 Case Insensitive", False,
                            f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("3. Auto-Approval", "3.6 Case Insensitive", False, str(e))

    # ===== SECTION 5: CONSTRAINT MATCHING =====

    def test_5_5_combined_constraints(self):
        """Test 5.5: Combined Constraints (AND logic)"""
        try:
            # Create mandate with multiple constraints
            mandate_payload = {
                "constraints": {
                    "max_amount": 200.00,
                    "category": "OFFICE_SUPPLIES",
                    "merchant": "Amazon"
                },
                "expiration": (datetime.now() + timedelta(hours=1)).isoformat()
            }

            response = requests.post(
                f"{BASE_URL}/api/ap2/intent-mandate",
                headers=self.get_headers(),
                json=mandate_payload
            )

            if response.status_code != 201:
                self.log_test("5. Constraint Matching", "5.5 Combined Constraints", False, "Failed to create mandate")
                return

            test_cases = [
                # (amount, vendor, category, should_match)
                (50.00, "Amazon", "OFFICE_SUPPLIES", True),
                (250.00, "Amazon", "OFFICE_SUPPLIES", False),  # Amount exceeds
                (50.00, "Microsoft", "OFFICE_SUPPLIES", False),  # Wrong vendor
                (50.00, "Amazon", "TRAVEL", False),  # Wrong category
            ]

            results = []
            for amount, vendor, category, should_match in test_cases:
                expense_payload = {
                    "amount": amount,
                    "vendor": vendor,
                    "category": category,
                    "description": f"Test combined: {vendor}/{category}/${amount}",
                    "date": datetime.now().isoformat()
                }

                response = requests.post(
                    f"{BASE_URL}/api/v1/expenses",
                    headers=self.get_headers(),
                    json=expense_payload
                )

                if response.status_code in [200, 201]:
                    data = response.json()
                    is_auto_approved = data.get("auto_approved", False)

                    # Check if result matches expectation
                    correct = (is_auto_approved == should_match)
                    results.append(correct)

                time.sleep(0.2)  # Small delay between requests

            all_passed = all(results)
            self.log_test("5. Constraint Matching", "5.5 Combined Constraints", all_passed,
                        f"{sum(results)}/{len(results)} cases passed")
        except Exception as e:
            self.log_test("5. Constraint Matching", "5.5 Combined Constraints", False, str(e))

    # ===== SECTION 7: COMPLETE AP2 FLOW =====

    def test_7_1_complete_flow(self):
        """Test 7.1: Complete AP2 Flow - Success Path"""
        try:
            payload = {
                "items": [
                    {
                        "description": "Office chair",
                        "amount": 299.99,
                        "category": "OFFICE_SUPPLIES"
                    }
                ],
                "merchant": "Amazon",
                "constraints": {
                    "max_amount": 500.00,
                    "monthly_limit": 2000.00,
                    "category": "OFFICE_SUPPLIES",
                    "merchant": "Amazon"
                }
            }

            response = requests.post(
                f"{BASE_URL}/api/ap2/complete-flow",
                headers=self.get_headers(),
                json=payload
            )

            if response.status_code == 200:
                data = response.json()

                checks = {
                    "intent_mandate": data.get("intent_mandate_id") is not None,
                    "cart_mandate": data.get("cart_mandate_id") is not None,
                    "payment_mandate": data.get("payment_mandate_id") is not None,
                    "flow_complete": data.get("ap2_flow_complete") == True
                }

                all_passed = all(checks.values())
                details = ", ".join([f"{k}: {v}" for k, v in checks.items()])

                self.log_test("7. Complete AP2 Flow", "7.1 Complete Flow", all_passed, details)
            else:
                self.log_test("7. Complete AP2 Flow", "7.1 Complete Flow", False,
                            f"Status: {response.status_code}, Response: {response.text[:200]}")
        except Exception as e:
            self.log_test("7. Complete AP2 Flow", "7.1 Complete Flow", False, str(e))

    # ===== SECTION 10: BILLING & USAGE =====

    def test_10_5_usage_stats(self):
        """Test 10.5: Usage Statistics API"""
        try:
            response = requests.get(
                f"{BASE_URL}/api/ap2/stats",
                headers=self.get_headers()
            )

            if response.status_code == 200:
                data = response.json()
                has_stats = len(data) > 0
                self.log_test("10. Billing & Usage", "10.5 Usage Stats", has_stats,
                            f"Stats keys: {list(data.keys())}")
            else:
                self.log_test("10. Billing & Usage", "10.5 Usage Stats", False,
                            f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("10. Billing & Usage", "10.5 Usage Stats", False, str(e))

    # ===== SECTION 12: ERROR HANDLING =====

    def test_12_3_duplicate_prevention(self):
        """Test 12.3: Duplicate Expense Submission"""
        try:
            expense_payload = {
                "amount": 99.99,
                "vendor": "TestVendor",
                "category": "OFFICE_SUPPLIES",
                "description": "Duplicate test expense",
                "date": datetime.now().isoformat()
            }

            # First submission
            response1 = requests.post(
                f"{BASE_URL}/api/v1/expenses",
                headers=self.get_headers(),
                json=expense_payload
            )

            # Immediate duplicate submission
            response2 = requests.post(
                f"{BASE_URL}/api/v1/expenses",
                headers=self.get_headers(),
                json=expense_payload
            )

            # First should succeed, second should fail
            passed = response1.status_code in [200, 201] and response2.status_code == 409
            self.log_test("12. Error Handling", "12.3 Duplicate Prevention", passed,
                        f"First: {response1.status_code}, Second: {response2.status_code}")
        except Exception as e:
            self.log_test("12. Error Handling", "12.3 Duplicate Prevention", False, str(e))

    def test_12_4_invalid_expense_data(self):
        """Test 12.4: Invalid Expense Data"""
        test_cases = [
            ("12.4a Missing Fields", {"amount": 50.00}),
            ("12.4b Negative Amount", {"amount": -50.00, "vendor": "Amazon", "category": "OFFICE_SUPPLIES"}),
        ]

        for test_name, payload in test_cases:
            try:
                response = requests.post(
                    f"{BASE_URL}/api/v1/expenses",
                    headers=self.get_headers(),
                    json=payload
                )

                passed = response.status_code == 400 or response.status_code == 422
                self.log_test("12. Error Handling", test_name, passed,
                            f"Status: {response.status_code}")
            except Exception as e:
                self.log_test("12. Error Handling", test_name, False, str(e))

    # ===== MAIN TEST RUNNER =====

    def run_all_tests(self):
        """Run all AP2 automation tests"""
        print(f"\n{Colors.BLUE}{'='*70}{Colors.RESET}")
        print(f"{Colors.BLUE}AP2 AUTOMATION TEST SUITE{Colors.RESET}")
        print(f"{Colors.BLUE}{'='*70}{Colors.RESET}\n")

        # Login
        if not self.login():
            print(f"\n{Colors.RED}Login failed. Cannot proceed with tests.{Colors.RESET}")
            return

        print(f"\n{Colors.YELLOW}Running tests...{Colors.RESET}\n")

        # Section 1: Intent Mandate Creation
        print(f"\n{Colors.BLUE}=== SECTION 1: Intent Mandate Creation ==={Colors.RESET}")
        mandate_id_1 = self.test_1_1_create_basic_intent_mandate()
        mandate_id_2 = self.test_1_2_multiple_merchants()
        mandate_id_3 = self.test_1_3_multiple_categories()
        self.test_1_5_invalid_constraints()

        # Section 2: Mandate Management
        print(f"\n{Colors.BLUE}=== SECTION 2: Intent Mandate Management ==={Colors.RESET}")
        mandates = self.test_2_1_list_mandates()
        if mandate_id_3:
            self.test_2_4_revoke_mandate(mandate_id_3)

        # Section 3: Auto-Approval Workflow
        print(f"\n{Colors.BLUE}=== SECTION 3: Auto-Approval Workflow ==={Colors.RESET}")
        if mandate_id_1:
            self.test_3_1_basic_auto_approval(mandate_id_1)
        self.test_3_3_amount_exceeds_limit()
        self.test_3_4_wrong_category()
        self.test_3_6_case_insensitive()

        # Section 5: Constraint Matching
        print(f"\n{Colors.BLUE}=== SECTION 5: Constraint Matching ==={Colors.RESET}")
        self.test_5_5_combined_constraints()

        # Section 7: Complete AP2 Flow
        print(f"\n{Colors.BLUE}=== SECTION 7: Complete AP2 Flow ==={Colors.RESET}")
        self.test_7_1_complete_flow()

        # Section 10: Billing & Usage
        print(f"\n{Colors.BLUE}=== SECTION 10: Billing & Usage ==={Colors.RESET}")
        self.test_10_5_usage_stats()

        # Section 12: Error Handling
        print(f"\n{Colors.BLUE}=== SECTION 12: Error Handling ==={Colors.RESET}")
        self.test_12_3_duplicate_prevention()
        self.test_12_4_invalid_expense_data()

        # Print Summary
        self.print_summary()

    def print_summary(self):
        """Print test results summary"""
        total = self.passed + self.failed + self.skipped
        pass_rate = (self.passed / total * 100) if total > 0 else 0

        print(f"\n{Colors.BLUE}{'='*70}{Colors.RESET}")
        print(f"{Colors.BLUE}TEST SUMMARY{Colors.RESET}")
        print(f"{Colors.BLUE}{'='*70}{Colors.RESET}")
        print(f"{Colors.GREEN}Passed:  {self.passed}{Colors.RESET}")
        print(f"{Colors.RED}Failed:  {self.failed}{Colors.RESET}")
        print(f"{Colors.YELLOW}Skipped: {self.skipped}{Colors.RESET}")
        print(f"Total:   {total}")
        print(f"Pass Rate: {pass_rate:.1f}%")
        print(f"{Colors.BLUE}{'='*70}{Colors.RESET}\n")

        # Failed tests detail
        if self.failed > 0:
            print(f"\n{Colors.RED}Failed Tests:{Colors.RESET}")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"  - {result['section']} | {result['test']}")
                    if result["message"]:
                        print(f"    {result['message']}")

if __name__ == "__main__":
    suite = AP2TestSuite()
    suite.run_all_tests()
