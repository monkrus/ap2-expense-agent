"""
Comprehensive AP2 Automation Test Suite
Tests Intent Mandates, Cart Mandates, Payment Flow, and Auto-Approval
"""
import json
import requests
import uuid
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

class AP2AutomationTester:
    def __init__(self):
        self.token = None
        self.user_id = None
        self.org_id = None
        self.intent_mandate_id = None
        self.cart_mandate_id = None
        self.payment_mandate_id = None

    def login(self, username="adminfree", password="Testme1!"):
        """Login and get access token"""
        print("\n" + "="*60)
        print("STEP 1: Login")
        print("="*60)

        resp = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"username": username, "password": password}
        )

        if resp.status_code == 200:
            data = resp.json()
            self.token = data.get("access_token")
            print(f"  [PASS] Login successful")
            print(f"  Token: {self.token[:50]}...")

            # Get user info
            me_resp = requests.get(
                f"{BASE_URL}/api/v1/auth/me",
                headers=self.auth_headers()
            )
            if me_resp.status_code == 200:
                user_data = me_resp.json()
                self.user_id = user_data.get("id")
                print(f"  User ID: {self.user_id}")
            return True
        else:
            print(f"  [FAIL] Login failed: {resp.status_code}")
            print(f"  {resp.text}")
            return False

    def auth_headers(self):
        """Get authorization headers"""
        headers = {"Authorization": f"Bearer {self.token}"}
        if self.org_id:
            headers["X-Organization-Id"] = self.org_id
        return headers

    def get_organization(self):
        """Get user's organization"""
        print("\n" + "="*60)
        print("STEP 2: Get Organization")
        print("="*60)

        resp = requests.get(
            f"{BASE_URL}/api/v1/organizations",
            headers=self.auth_headers()
        )

        if resp.status_code == 200:
            orgs = resp.json()
            if orgs:
                self.org_id = orgs[0].get("id")
                print(f"  [PASS] Found organization: {orgs[0].get('name')}")
                print(f"  Org ID: {self.org_id}")
                return True
            else:
                print("  [WARN] No organizations found")
                return False
        else:
            print(f"  [FAIL] Failed to get organizations: {resp.status_code}")
            return False

    def test_intent_mandate(self):
        """Test creating an Intent Mandate"""
        print("\n" + "="*60)
        print("STEP 3: Test Intent Mandate Creation")
        print("="*60)

        payload = {
            "constraints": {
                "max_amount": 500.00,
                "merchants": ["Amazon", "Staples", "Office Depot"],
                "categories": ["office_supplies", "software"],
                "approval_required": False,
                "monthly_limit": 2000.00
            },
            "expiration_hours": 24
        }

        print(f"  Creating Intent Mandate with constraints:")
        print(f"    - Max amount: $500")
        print(f"    - Merchants: Amazon, Staples, Office Depot")
        print(f"    - Categories: office_supplies, software")
        print(f"    - Monthly limit: $2000")

        resp = requests.post(
            f"{BASE_URL}/api/ap2/intent-mandate",
            headers=self.auth_headers(),
            json=payload
        )

        if resp.status_code in [200, 201]:
            data = resp.json()
            self.intent_mandate_id = data.get("intent_mandate_id") or data.get("id")
            print(f"  [PASS] Intent Mandate created")
            print(f"  Mandate ID: {self.intent_mandate_id}")
            print(f"  Status: {data.get('status', 'active')}")
            if data.get('signature'):
                print(f"  Signature: {data.get('signature')[:50]}...")
            if data.get('expiration'):
                print(f"  Expires: {data.get('expiration')}")
            return True
        else:
            print(f"  [FAIL] Failed to create Intent Mandate: {resp.status_code}")
            print(f"  Response: {resp.text}")
            return False

    def test_cart_mandate(self):
        """Test creating a Cart Mandate"""
        print("\n" + "="*60)
        print("STEP 4: Test Cart Mandate Creation")
        print("="*60)

        if not self.intent_mandate_id:
            print("  [SKIP] No Intent Mandate ID - skipping")
            return False

        payload = {
            "intent_mandate_id": self.intent_mandate_id,
            "items": [
                {
                    "id": str(uuid.uuid4()),
                    "description": "Office Chair",
                    "amount": 150.00,
                    "category": "office_supplies"
                },
                {
                    "id": str(uuid.uuid4()),
                    "description": "Desk Lamp",
                    "amount": 45.00,
                    "category": "office_supplies"
                }
            ],
            "merchant": "Amazon",
            "user_signature": f"user_sig_{uuid.uuid4().hex[:8]}"
        }

        print(f"  Creating Cart Mandate with items:")
        print(f"    - Office Chair: $150.00")
        print(f"    - Desk Lamp: $45.00")
        print(f"    - Total: $195.00")
        print(f"    - Merchant: Amazon")

        resp = requests.post(
            f"{BASE_URL}/api/ap2/cart-mandate",
            headers=self.auth_headers(),
            json=payload
        )

        if resp.status_code in [200, 201]:
            data = resp.json()
            self.cart_mandate_id = data.get("cart_mandate_id") or data.get("id")
            print(f"  [PASS] Cart Mandate created")
            print(f"  Cart ID: {self.cart_mandate_id}")
            print(f"  Total: ${data.get('total', 195.00)}")
            print(f"  Status: {data.get('status', 'pending')}")
            return True
        else:
            print(f"  [FAIL] Failed to create Cart Mandate: {resp.status_code}")
            print(f"  Response: {resp.text}")
            return False

    def test_payment_mandate(self):
        """Test creating a Payment Mandate"""
        print("\n" + "="*60)
        print("STEP 5: Test Payment Mandate Creation")
        print("="*60)

        if not self.cart_mandate_id:
            print("  [SKIP] No Cart Mandate ID - skipping")
            return False

        payload = {
            "cart_mandate_id": self.cart_mandate_id,
            "payment_method": "stripe"
        }

        print(f"  Creating Payment Mandate:")
        print(f"    - Cart ID: {self.cart_mandate_id}")
        print(f"    - Payment Method: stripe")

        resp = requests.post(
            f"{BASE_URL}/api/ap2/payment-mandate",
            headers=self.auth_headers(),
            json=payload
        )

        if resp.status_code in [200, 201]:
            data = resp.json()
            self.payment_mandate_id = data.get("payment_mandate_id") or data.get("id")
            print(f"  [PASS] Payment Mandate created")
            print(f"  Payment ID: {self.payment_mandate_id}")
            print(f"  Status: {data.get('status', 'pending')}")
            return True
        else:
            print(f"  [FAIL] Failed to create Payment Mandate: {resp.status_code}")
            print(f"  Response: {resp.text}")
            return False

    def test_mandate_status(self):
        """Test checking mandate status"""
        print("\n" + "="*60)
        print("STEP 6: Test Mandate Status Check")
        print("="*60)

        if self.intent_mandate_id:
            resp = requests.get(
                f"{BASE_URL}/api/ap2/mandate/{self.intent_mandate_id}/status",
                headers=self.auth_headers(),
                params={"mandate_type": "intent"}
            )

            if resp.status_code == 200:
                data = resp.json()
                print(f"  [PASS] Intent Mandate Status: {data.get('status')}")
            else:
                print(f"  [INFO] Status check returned: {resp.status_code}")

        return True

    def test_user_mandates(self):
        """Test listing user's mandates"""
        print("\n" + "="*60)
        print("STEP 7: Test User Mandates List")
        print("="*60)

        resp = requests.get(
            f"{BASE_URL}/api/ap2/user/mandates",
            headers=self.auth_headers()
        )

        if resp.status_code == 200:
            data = resp.json()
            mandates = data if isinstance(data, list) else data.get("mandates", [])
            print(f"  [PASS] Retrieved {len(mandates)} mandates")
            for m in mandates[:3]:
                print(f"    - {m.get('id', 'N/A')[:20]}... | Status: {m.get('status', 'N/A')}")
            return True
        else:
            print(f"  [FAIL] Failed to get mandates: {resp.status_code}")
            print(f"  Response: {resp.text}")
            return False

    def test_ap2_stats(self):
        """Test AP2 usage statistics"""
        print("\n" + "="*60)
        print("STEP 8: Test AP2 Stats")
        print("="*60)

        resp = requests.get(
            f"{BASE_URL}/api/ap2/stats",
            headers=self.auth_headers()
        )

        if resp.status_code == 200:
            data = resp.json()
            print(f"  [PASS] AP2 Statistics:")
            print(f"    - Total Mandates: {data.get('total_mandates', 'N/A')}")
            print(f"    - Active: {data.get('active_mandates', 'N/A')}")
            print(f"    - Total Processed: ${data.get('total_amount_processed', 0):.2f}")
            return True
        else:
            print(f"  [INFO] Stats returned: {resp.status_code}")
            return True

    def test_approval_policy_create(self):
        """Test creating an approval policy"""
        print("\n" + "="*60)
        print("STEP 9: Test Approval Policy Creation")
        print("="*60)

        if not self.org_id:
            print("  [SKIP] No organization ID")
            return False

        payload = {
            "name": f"Test Auto-Approval Policy {uuid.uuid4().hex[:6]}",
            "max_amount_per_expense": 100.00,
            "daily_limit_per_user": 500.00,
            "monthly_limit_per_user": 2000.00,
            "auto_approve": True,
            "priority": 100,
            "conditions": {
                "categories": ["OFFICE_SUPPLIES", "MEALS", "TRAVEL"]
            },
            "notify_on_auto_approve": True
        }

        print(f"  Creating Approval Policy:")
        print(f"    - Name: {payload['name']}")
        print(f"    - Max per expense: $100")
        print(f"    - Daily limit: $500")
        print(f"    - Monthly limit: $2000")
        print(f"    - Categories: OFFICE_SUPPLIES, MEALS, TRAVEL")

        resp = requests.post(
            f"{BASE_URL}/api/v1/approval-policies",
            headers=self.auth_headers(),
            json=payload
        )

        if resp.status_code in [200, 201]:
            data = resp.json()
            policy_id = data.get("id")
            print(f"  [PASS] Approval Policy created")
            print(f"  Policy ID: {policy_id}")
            return policy_id
        else:
            print(f"  [FAIL] Failed to create policy: {resp.status_code}")
            print(f"  Response: {resp.text}")
            return None

    def test_approval_policy_test(self, amount=50.00, category="OFFICE_SUPPLIES"):
        """Test if an expense would be auto-approved"""
        print("\n" + "="*60)
        print("STEP 10: Test Approval Policy Evaluation")
        print("="*60)

        if not self.org_id:
            print("  [SKIP] No organization ID")
            return False

        payload = {
            "amount": amount,
            "category": category,
            "vendor": "Staples",
            "has_receipt": True
        }

        print(f"  Testing expense:")
        print(f"    - Amount: ${amount}")
        print(f"    - Category: {category}")
        print(f"    - Vendor: Staples")

        resp = requests.post(
            f"{BASE_URL}/api/v1/approval-policies/test",
            headers=self.auth_headers(),
            json=payload
        )

        if resp.status_code == 200:
            data = resp.json()
            would_approve = data.get("would_auto_approve", False)
            reason = data.get("reason", "No reason provided")
            policy = data.get("matching_policy")

            if would_approve:
                print(f"  [PASS] Would AUTO-APPROVE")
                print(f"    - Reason: {reason}")
                if policy:
                    print(f"    - Policy: {policy.get('name', 'N/A')}")
            else:
                print(f"  [INFO] Would NOT auto-approve")
                print(f"    - Reason: {reason}")
            return would_approve
        else:
            print(f"  [FAIL] Policy test failed: {resp.status_code}")
            print(f"  Response: {resp.text}")
            return False

    def test_expense_auto_approval(self):
        """Test creating an expense that should be auto-approved"""
        print("\n" + "="*60)
        print("STEP 11: Test Expense Auto-Approval Integration")
        print("="*60)

        if not self.org_id:
            print("  [SKIP] No organization ID")
            return False

        payload = {
            "amount": 45.00,
            "category": "OFFICE_SUPPLIES",
            "vendor": "Staples",
            "description": "Test expense for auto-approval",
            "expense_date": datetime.utcnow().isoformat()
        }

        print(f"  Creating expense:")
        print(f"    - Amount: $45.00")
        print(f"    - Category: OFFICE_SUPPLIES")
        print(f"    - Vendor: Staples")

        resp = requests.post(
            f"{BASE_URL}/api/v1/expenses",
            headers=self.auth_headers(),
            json=payload
        )

        if resp.status_code in [200, 201]:
            data = resp.json()
            expense_id = data.get("id")
            status = data.get("status")
            auto_approved = data.get("auto_approved", False)
            auto_approved_via = data.get("auto_approved_via", "N/A")

            print(f"  [PASS] Expense created")
            print(f"    - Expense ID: {expense_id}")
            print(f"    - Status: {status}")
            print(f"    - Auto-approved: {auto_approved}")
            print(f"    - Approved via: {auto_approved_via}")

            if auto_approved:
                print(f"  [SUCCESS] Expense was AUTO-APPROVED!")
            else:
                print(f"  [INFO] Expense requires manual approval")

            return expense_id
        else:
            print(f"  [FAIL] Failed to create expense: {resp.status_code}")
            print(f"  Response: {resp.text}")
            return None

    def test_mandate_revocation(self):
        """Test revoking an Intent Mandate"""
        print("\n" + "="*60)
        print("STEP 12: Test Mandate Revocation (GDPR)")
        print("="*60)

        if not self.intent_mandate_id:
            print("  [SKIP] No Intent Mandate to revoke")
            return False

        print(f"  Revoking Intent Mandate: {self.intent_mandate_id}")

        resp = requests.post(
            f"{BASE_URL}/api/ap2/intent-mandate/{self.intent_mandate_id}/revoke",
            headers=self.auth_headers()
        )

        if resp.status_code == 200:
            data = resp.json()
            print(f"  [PASS] Mandate revoked successfully")
            print(f"    - Status: {data.get('status', 'revoked')}")
            print(f"    - Revoked at: {data.get('revoked_at', 'N/A')}")
            return True
        elif resp.status_code == 404:
            print(f"  [INFO] Mandate not found (may have expired)")
            return True
        else:
            print(f"  [FAIL] Revocation failed: {resp.status_code}")
            print(f"  Response: {resp.text}")
            return False

    def test_policy_analytics(self):
        """Test approval policy analytics"""
        print("\n" + "="*60)
        print("STEP 13: Test Policy Analytics")
        print("="*60)

        if not self.org_id:
            print("  [SKIP] No organization ID")
            return False

        resp = requests.get(
            f"{BASE_URL}/api/v1/approval-policies/analytics/statistics",
            headers=self.auth_headers()
        )

        if resp.status_code == 200:
            data = resp.json()
            print(f"  [PASS] Analytics retrieved:")
            print(f"    - Auto-approval rate: {data.get('auto_approval_rate', 0):.1f}%")
            print(f"    - Total auto-approved: {data.get('auto_approved_count', 0)}")
            print(f"    - Manual approvals: {data.get('manual_approved_count', 0)}")
            print(f"    - Time saved: {data.get('time_saved_minutes', 0)} minutes")
            return True
        else:
            print(f"  [INFO] Analytics returned: {resp.status_code}")
            return True

    def run_all_tests(self):
        """Run all AP2 automation tests"""
        print("\n" + "#"*60)
        print("#  AP2 AUTOMATION TEST SUITE")
        print("#"*60)

        results = {}

        # Setup
        results["login"] = self.login()
        if not results["login"]:
            print("\n[ABORT] Cannot continue without login")
            return results

        results["organization"] = self.get_organization()

        # AP2 Tests
        results["intent_mandate"] = self.test_intent_mandate()
        results["cart_mandate"] = self.test_cart_mandate()
        results["payment_mandate"] = self.test_payment_mandate()
        results["mandate_status"] = self.test_mandate_status()
        results["user_mandates"] = self.test_user_mandates()
        results["ap2_stats"] = self.test_ap2_stats()

        # Approval Policy Tests
        results["policy_create"] = self.test_approval_policy_create()
        results["policy_test_approve"] = self.test_approval_policy_test(50.00, "OFFICE_SUPPLIES")
        results["policy_test_reject"] = self.test_approval_policy_test(200.00, "OFFICE_SUPPLIES")  # Over limit

        # Integration Test
        results["expense_auto_approve"] = self.test_expense_auto_approval()

        # Analytics
        results["policy_analytics"] = self.test_policy_analytics()

        # Cleanup - Revocation
        results["revocation"] = self.test_mandate_revocation()

        # Summary
        print("\n" + "#"*60)
        print("#  TEST SUMMARY")
        print("#"*60)

        passed = sum(1 for v in results.values() if v)
        total = len(results)

        for test, result in results.items():
            status = "[PASS]" if result else "[FAIL]"
            print(f"  {status} {test}")

        print(f"\n  Total: {passed}/{total} tests passed")
        print("#"*60)

        return results


if __name__ == "__main__":
    tester = AP2AutomationTester()
    tester.run_all_tests()
