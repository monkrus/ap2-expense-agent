"""
Test AP2 Complete Flow to verify everything is working
"""

import json
import sys

import requests

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://localhost:8000"


def login():
    """Login and get access token"""
    # Try both password variations
    passwords_to_try = ["Password123!", "Passowrd123!"]

    for pwd in passwords_to_try:
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"username": "adminfree", "password": pwd},
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Login successful: {data.get('user', {}).get('username')}")
            return data.get("access_token")

    # If both failed
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"username": "adminfree", "password": passwords_to_try[0]},
    )
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Login successful: {data.get('user', {}).get('username')}")
        return data.get("access_token")
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return None


def create_intent_mandate(token):
    """Create an Intent Mandate (Reusable Authorization)"""
    print("\n--- Testing Intent Mandate Creation ---")

    payload = {
        "constraints": {
            "max_amount": 100.00,
            "categories": ["OFFICE_SUPPLIES", "SOFTWARE"],
            "merchants": ["Amazon", "Microsoft"],
        },
        "expiration_hours": 720,  # 30 days
    }

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    response = requests.post(
        f"{BASE_URL}/api/ap2/intent-mandate", headers=headers, json=payload
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Intent Mandate created successfully")
        print(f"   ID: {data.get('mandate_id', 'N/A')}")
        print(f"   Status: {data.get('status', 'N/A')}")
        return data.get("mandate_id")
    else:
        print(f"❌ Intent Mandate creation failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return None


def execute_complete_flow(token):
    """Execute Complete AP2 Flow (Autonomous Purchase)"""
    print("\n--- Testing Complete AP2 Flow ---")

    payload = {
        "items": [
            {
                "description": "Office Chair",
                "amount": 45.00,
                "category": "OFFICE_SUPPLIES",
            },
            {
                "description": "Desk Organizer",
                "amount": 15.00,
                "category": "OFFICE_SUPPLIES",
            },
        ],
        "merchant": "Amazon",
        "constraints": {
            "max_amount": 100.00,
            "monthly_limit": 500.00,
            "categories": ["OFFICE_SUPPLIES"],
            "merchant": "Amazon",
        },
    }

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    response = requests.post(
        f"{BASE_URL}/api/ap2/complete-flow", headers=headers, json=payload
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Complete Flow executed successfully")
        print(f"   Intent Mandate ID: {data.get('intent_mandate_id', 'N/A')}")
        print(f"   Cart Mandate ID: {data.get('cart_mandate_id', 'N/A')}")
        print(f"   Payment Mandate ID: {data.get('payment_mandate_id', 'N/A')}")
        print(f"   Status: {data.get('status', 'N/A')}")
        return data
    else:
        print(f"❌ Complete Flow failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return None


def get_user_mandates(token):
    """Get all user mandates to verify they were created"""
    print("\n--- Fetching User Mandates ---")

    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(
        f"{BASE_URL}/api/ap2/user/mandates?limit=10", headers=headers
    )

    if response.status_code == 200:
        data = response.json()
        mandates = data.get("mandates", [])
        print(f"✅ Found {len(mandates)} mandates")

        for mandate in mandates[:5]:  # Show first 5
            print(
                f"   - {mandate.get('type', 'N/A')} | Status: {mandate.get('status', 'N/A')} | ID: {mandate.get('id', 'N/A')[:12]}..."
            )

        return mandates
    else:
        print(f"❌ Failed to fetch mandates: {response.status_code}")
        print(f"   Error: {response.text}")
        return []


def main():
    print("=" * 60)
    print("AP2 Flow Testing")
    print("=" * 60)

    # Step 1: Login
    token = login()
    if not token:
        print("\n❌ Cannot proceed without authentication")
        return

    # Step 2: Test Intent Mandate creation (Reusable Authorization)
    intent_id = create_intent_mandate(token)

    # Step 3: Test Complete Flow (Autonomous Purchase)
    flow_result = execute_complete_flow(token)

    # Step 4: Verify mandates were created
    mandates = get_user_mandates(token)

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    print(f"Intent Mandate Creation: {'✅ PASS' if intent_id else '❌ FAIL'}")
    print(f"Complete Flow Execution: {'✅ PASS' if flow_result else '❌ FAIL'}")
    print(f"Mandates Retrieved: {'✅ PASS' if mandates else '❌ FAIL'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
