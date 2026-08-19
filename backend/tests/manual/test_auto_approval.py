"""
Test the core AP2 auto-approval feature
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"


def test_auto_approval():
    print("=" * 70)
    print("AP2 AUTO-APPROVAL FEATURE TEST")
    print("=" * 70)
    print()

    # Step 1: Login
    print("[1/4] Logging in...")
    login_response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"username": "employee1", "password": "Password123!"},
    )

    if login_response.status_code != 200:
        print(f"[FAIL] Login failed: {login_response.status_code}")
        return

    login_data = login_response.json()
    token = login_data["access_token"]
    org_id = login_data.get("user", {}).get("organization_id")

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    if org_id:
        headers["X-Organization-Id"] = org_id
        print(f"[PASS] Logged in successfully (Org: {org_id})\n")
    else:
        print("[PASS] Logged in successfully (No org)\n")

    # Step 2: Create Intent Mandate
    print("[2/4] Creating Intent Mandate...")
    mandate_payload = {
        "constraints": {
            "max_amount": 200.00,
            "monthly_limit": 1000.00,
            "category": "OFFICE_SUPPLIES",
            "merchant": "Amazon",
        },
        "expiration": (datetime.now() + timedelta(days=1)).isoformat(),
    }

    mandate_response = requests.post(
        f"{BASE_URL}/api/ap2/intent-mandate", headers=headers, json=mandate_payload
    )

    if mandate_response.status_code != 200:
        print(f"[FAIL] Mandate creation failed: {mandate_response.status_code}")
        print(f"Response: {mandate_response.text}")
        return

    mandate_data = mandate_response.json()
    mandate_id = mandate_data.get("intent_mandate_id")
    print(f"[PASS] Intent Mandate created: {mandate_id[:8]}...")
    print(
        f"      Constraints: max_amount=$200, category=OFFICE_SUPPLIES, merchant=Amazon"
    )
    print()

    # Step 3: Submit matching expense
    print("[3/4] Submitting expense that matches mandate...")
    expense_payload = {
        "amount": 75.50,
        "vendor": "Amazon",
        "category": "OFFICE_SUPPLIES",
        "description": "Test auto-approval - office supplies from Amazon",
        "date": datetime.now().isoformat(),
    }

    expense_response = requests.post(
        f"{BASE_URL}/api/v1/expenses", headers=headers, json=expense_payload
    )

    print(f"Status: {expense_response.status_code}")
    print(f"Response: {expense_response.text[:500]}")
    print()

    if expense_response.status_code in [200, 201]:
        expense_data = expense_response.json()
        print("[4/4] Checking auto-approval...")
        print()
        print("=" * 70)
        print("RESULTS")
        print("=" * 70)
        print(f"Expense ID: {expense_data.get('id', 'N/A')}")
        print(f"Status: {expense_data.get('status', 'N/A')}")
        print(f"Auto-Approved: {expense_data.get('auto_approved', 'N/A')}")
        print(f"Auto-Approved Via: {expense_data.get('auto_approved_via', 'N/A')}")
        print(f"Intent Mandate ID: {expense_data.get('intent_mandate_id', 'N/A')}")
        print()

        if expense_data.get("status") == "APPROVED" and expense_data.get(
            "auto_approved"
        ):
            print("[SUCCESS] Auto-approval is WORKING!")
            print("The expense was automatically approved by the Intent Mandate.")
        else:
            print("[FAIL] Auto-approval did NOT work")
            print("Expected: status=APPROVED, auto_approved=true")
            print(
                f"Got: status={expense_data.get('status')}, auto_approved={expense_data.get('auto_approved')}"
            )
    else:
        print("[FAIL] Expense submission failed")
        print(f"Status: {expense_response.status_code}")

    print()
    print("=" * 70)


if __name__ == "__main__":
    test_auto_approval()
