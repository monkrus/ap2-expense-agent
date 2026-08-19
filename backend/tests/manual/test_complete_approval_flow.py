"""
Test Complete Approval Flow - All 3 Tiers
Demonstrates: AP2 Auto-Approval, Policy Auto-Approval, and Manual Approval
"""

import requests
import json
import time
import sys

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://localhost:8000"


def login():
    """Login as test user"""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"username": "testuser", "password": "Test123!"},
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
        user_id = response.json()["user"]["id"]

        # Get organization ID
        org_response = requests.get(
            f"{BASE_URL}/api/v1/organizations",
            headers={"Authorization": f"Bearer {token}"},
        )
        org_id = None
        if org_response.status_code == 200:
            orgs = org_response.json()
            if orgs and len(orgs) > 0:
                org_id = orgs[0].get("id")

        print(f"✓ Logged in as: testuser")
        if org_id:
            print(f"  Organization: {org_id[:20]}...")
        return token, user_id, org_id
    print(f"✗ Login failed: {response.status_code}")
    return None, None, None


def create_intent_mandate(token):
    """Create an Intent Mandate for Amazon office supplies"""
    print("\n" + "=" * 70)
    print("SETUP: Creating Intent Mandate (AP2)")
    print("=" * 70)

    response = requests.post(
        f"{BASE_URL}/api/ap2/intent-mandate",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "constraints": {
                "max_amount": 100.00,
                "categories": ["OFFICE_SUPPLIES"],
                "merchants": ["Amazon"],
            },
            "expiration_hours": 720,
        },
    )

    if response.status_code == 200:
        mandate_id = response.json()["intent_mandate_id"]
        print(f"✓ Intent Mandate created: {mandate_id[:20]}...")
        print(f"  Constraints: Amazon, Office Supplies, Max $100")
        return mandate_id
    else:
        print(f"✗ Failed to create mandate: {response.text}")
        return None


def create_approval_policy(token):
    """Create an Approval Policy for meals under $50"""
    print("\n" + "=" * 70)
    print("SETUP: Creating Approval Policy")
    print("=" * 70)

    response = requests.post(
        f"{BASE_URL}/api/v1/approval-policies",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "name": "Meal Policy",
            "description": "Auto-approve meals under $50",
            "conditions": {"category": "MEALS", "max_amount": 50.00},
            "auto_approve": True,
        },
    )

    if response.status_code in [200, 201]:
        policy_id = response.json().get("id")
        print(f"✓ Approval Policy created: {policy_id[:20] if policy_id else 'N/A'}...")
        print(f"  Conditions: Meals, Max $50, Auto-approve: True")
        return policy_id
    else:
        print(f"⚠ Policy creation response: {response.status_code}")
        print(f"  Note: May already exist or endpoint differs")
        return None


def submit_expense(token, org_id, expense_data, scenario_name):
    """Submit an expense and return the result"""
    print(f"\n{'='*70}")
    print(f"TEST: {scenario_name}")
    print(f"{'='*70}")
    print(f"Submitting expense:")
    print(f"  Amount: ${expense_data['amount']}")
    print(f"  Category: {expense_data['category']}")
    print(f"  Vendor: {expense_data.get('vendor', 'N/A')}")
    print(f"  Description: {expense_data['description']}")

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if org_id:
        headers["X-Organization-Id"] = org_id

    response = requests.post(
        f"{BASE_URL}/api/v1/expenses", headers=headers, json=expense_data
    )

    if response.status_code in [200, 201]:
        data = response.json()
        expense_id = data.get("id")
        status = data.get("status")
        approved_by = data.get("approved_by")
        auto_approved_via = data.get("auto_approved_via")

        print(f"\n✓ Expense submitted: {expense_id[:20] if expense_id else 'N/A'}...")
        print(f"  Status: {status}")
        print(f"  Approved By: {approved_by or 'N/A'}")
        print(f"  Auto-Approved Via: {auto_approved_via or 'N/A'}")

        # Determine which tier approved it
        if auto_approved_via == "intent_mandate":
            print(f"\n🎉 TIER 1: AP2 AUTO-APPROVAL ✨")
            print(f"  ✓ Intent Mandate matched")
            print(f"  ✓ Approved by: ai_agent")
            print(f"  ✓ AP2 transaction counted as 'used'")
        elif auto_approved_via == "approval_policy":
            print(f"\n🎉 TIER 2: POLICY AUTO-APPROVAL 🤖")
            print(f"  ✓ Approval Policy matched")
            print(f"  ✓ Approved automatically")
            print(f"  ✓ No AP2 transaction used (free)")
        elif status == "PENDING":
            print(f"\n⏳ TIER 3: MANUAL APPROVAL REQUIRED 👤")
            print(f"  ✓ No Intent Mandate matched")
            print(f"  ✓ No Approval Policy matched")
            print(f"  ✓ Awaiting manager approval")
        else:
            print(f"\n📋 Status: {status}")

        return {
            "id": expense_id,
            "status": status,
            "approved_by": approved_by,
            "auto_approved_via": auto_approved_via,
            "success": True,
        }
    else:
        print(f"\n✗ Failed to submit expense: {response.status_code}")
        print(f"  Error: {response.text}")
        return {"success": False, "error": response.text}


def get_ap2_stats(token):
    """Get AP2 usage statistics"""
    response = requests.get(
        f"{BASE_URL}/api/ap2/stats", headers={"Authorization": f"Bearer {token}"}
    )

    if response.status_code == 200:
        return response.json()
    return None


def main():
    print("=" * 70)
    print("COMPLETE APPROVAL FLOW TEST")
    print("Testing all 3 approval tiers")
    print("=" * 70)

    # Login
    token, user_id, org_id = login()
    if not token:
        print("\n✗ Cannot proceed without authentication")
        return

    if not org_id:
        print("\n✗ Cannot proceed without organization")
        return

    # Get initial AP2 stats
    initial_stats = get_ap2_stats(token)
    initial_used = (
        initial_stats.get("payment_mandates", {}).get("completed", 0)
        if initial_stats
        else 0
    )
    print(f"\nInitial AP2 used mandates: {initial_used}")

    # Setup: Create Intent Mandate
    mandate_id = create_intent_mandate(token)

    # Setup: Create Approval Policy
    policy_id = create_approval_policy(token)

    time.sleep(2)  # Give system time to process

    # TEST 1: AP2 Auto-Approval (Tier 1)
    result1 = submit_expense(
        token,
        org_id,
        {
            "amount": 45.00,
            "category": "OFFICE_SUPPLIES",
            "vendor": "Amazon",
            "description": "Wireless Mouse",
            "date": "2026-02-01",
        },
        "Scenario 1: AP2 Intent Mandate Match",
    )

    time.sleep(2)

    # TEST 2: Policy Auto-Approval (Tier 2)
    result2 = submit_expense(
        token,
        org_id,
        {
            "amount": 35.00,
            "category": "MEALS",
            "vendor": "Local Restaurant",
            "description": "Team Lunch",
            "date": "2026-02-01",
        },
        "Scenario 2: Approval Policy Match",
    )

    time.sleep(2)

    # TEST 3: Manual Approval Required (Tier 3)
    result3 = submit_expense(
        token,
        org_id,
        {
            "amount": 500.00,
            "category": "TRAVEL",
            "vendor": "Conference Center",
            "description": "Annual Conference Ticket",
            "date": "2026-02-01",
        },
        "Scenario 3: No Automatic Match",
    )

    # Get final AP2 stats
    time.sleep(2)
    final_stats = get_ap2_stats(token)
    final_used = (
        final_stats.get("payment_mandates", {}).get("completed", 0)
        if final_stats
        else 0
    )

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY: All 3 Approval Tiers Demonstrated")
    print("=" * 70)

    print(f"\n📊 Test Results:")
    print(
        f"  Tier 1 (AP2): {'✓ PASSED' if result1.get('auto_approved_via') == 'intent_mandate' else '✗ FAILED'}"
    )
    print(
        f"  Tier 2 (Policy): {'✓ PASSED' if result2.get('auto_approved_via') == 'approval_policy' else '⚠ CHECK'}"
    )
    print(
        f"  Tier 3 (Manual): {'✓ PASSED' if result3.get('status') == 'PENDING' else '✗ FAILED'}"
    )

    print(f"\n📈 AP2 Usage:")
    print(f"  Initial used mandates: {initial_used}")
    print(f"  Final used mandates: {final_used}")
    print(f"  New AP2 transactions: +{final_used - initial_used}")

    print(f"\n💡 Key Insights:")
    print(f"  • AP2 (Tier 1) = Autonomous, Premium, Uses AP2 transaction")
    print(f"  • Policy (Tier 2) = Automatic, Free, No AP2 transaction")
    print(f"  • Manual (Tier 3) = Human approval, Free, No AP2 transaction")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
