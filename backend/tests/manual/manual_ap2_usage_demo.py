"""
Test AP2 Flow to demonstrate when mandates become "used"
This script shows AP2 stats before and after payment execution
"""

import requests
import json
import sys
import time
from datetime import datetime
import uuid

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://localhost:8000"


def login():
    """Login and get access token"""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"username": "testuser", "password": "Test123!"},
    )
    if response.status_code == 200:
        data = response.json()
        print(f"Login successful: {data.get('user', {}).get('username')}")
        return data.get("access_token")

    print(f"Login failed: {response.status_code}")
    return None


def get_ap2_stats(token):
    """Get AP2 usage statistics"""
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(f"{BASE_URL}/api/ap2/stats", headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Failed to get stats: {response.status_code}")
        return None


def print_stats(stats, label="AP2 Statistics"):
    """Print AP2 stats in a readable format"""
    print(f"\n{'='*60}")
    print(f"{label}")
    print(f"{'='*60}")

    if not stats:
        print("No stats available")
        return

    print("\n📊 Intent Mandates:")
    for status, count in stats.get("intent_mandates", {}).items():
        print(f"   {status}: {count}")

    print("\n🛒 Cart Mandates:")
    for status, count in stats.get("cart_mandates", {}).items():
        print(f"   {status}: {count}")

    print("\n💳 Payment Mandates:")
    payment_mandates = stats.get("payment_mandates", {})
    for status, count in payment_mandates.items():
        print(f"   {status}: {count}")

    # Calculate total "used" mandates (completed payments)
    used_count = payment_mandates.get("completed", 0)
    print(f"\n✨ USED MANDATES (completed payments): {used_count}")

    total_amount = stats.get("total_amount_processed", 0)
    print(f"💰 Total Amount Processed: ${total_amount:.2f}")
    print(f"{'='*60}\n")


def execute_complete_flow(token):
    """Execute Complete AP2 Flow (this is what makes mandates "used")"""
    print("\n🚀 Executing AP2 Complete Flow (Payment Execution)...")
    print("   This will create and execute a payment, marking a mandate as 'used'\n")

    payload = {
        "items": [
            {
                "description": "Test Office Supplies",
                "amount": 25.00,
                "category": "OFFICE_SUPPLIES",
            }
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
        print(f"✅ Payment Executed Successfully!")
        print(f"   Intent Mandate ID: {data.get('intent_mandate_id', 'N/A')}")
        print(f"   Cart Mandate ID: {data.get('cart_mandate_id', 'N/A')}")
        print(f"   Payment Mandate ID: {data.get('payment_mandate_id', 'N/A')}")
        print(f"   Status: {data.get('status', 'N/A')}")
        return True
    else:
        print(f"❌ Complete Flow failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return False


def execute_step_by_step_flow(token):
    """Execute AP2 flow step by step to show the full process"""
    print("\n🔍 Executing Step-by-Step AP2 Flow...")

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Step 1: Create Intent Mandate
    print("\n1️⃣ Creating Intent Mandate (Authorization)...")
    intent_response = requests.post(
        f"{BASE_URL}/api/ap2/intent-mandate",
        headers=headers,
        json={
            "constraints": {
                "max_amount": 100.00,
                "categories": ["OFFICE_SUPPLIES"],
                "merchant": "Amazon",
            },
            "expiration_hours": 24,
        },
    )

    if intent_response.status_code != 200:
        print(f"❌ Intent mandate creation failed: {intent_response.text}")
        return False

    intent_id = intent_response.json().get("intent_mandate_id")
    print(f"✅ Intent Mandate created: {intent_id}")

    # Step 2: Create Cart Mandate
    print("\n2️⃣ Creating Cart Mandate (Shopping Cart)...")
    cart_response = requests.post(
        f"{BASE_URL}/api/ap2/cart-mandate",
        headers=headers,
        json={
            "intent_mandate_id": intent_id,
            "items": [
                {
                    "id": f"item-{uuid.uuid4()}",
                    "description": "Desk Lamp",
                    "amount": 35.00,
                    "category": "OFFICE_SUPPLIES",
                }
            ],
            "merchant": "Amazon",
            "user_signature": f"sig-{uuid.uuid4()}",
        },
    )

    if cart_response.status_code != 200:
        print(f"❌ Cart mandate creation failed: {cart_response.text}")
        return False

    cart_id = cart_response.json().get("cart_mandate_id")
    print(f"✅ Cart Mandate created: {cart_id}")

    # Step 3: Create Payment Mandate
    print("\n3️⃣ Creating Payment Mandate (Payment Preparation)...")
    payment_response = requests.post(
        f"{BASE_URL}/api/ap2/payment-mandate",
        headers=headers,
        json={"cart_mandate_id": cart_id, "payment_method": "stripe"},
    )

    if payment_response.status_code != 200:
        print(f"❌ Payment mandate creation failed: {payment_response.text}")
        return False

    payment_id = payment_response.json().get("payment_mandate_id")
    print(f"✅ Payment Mandate created: {payment_id}")

    # Step 4: Execute Payment (THIS IS WHEN IT BECOMES "USED")
    print("\n4️⃣ Executing Payment (THIS MARKS THE MANDATE AS USED)...")
    execute_response = requests.post(
        f"{BASE_URL}/api/ap2/execute-payment",
        headers=headers,
        json={
            "payment_mandate_id": payment_id,
            "nonce": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
    )

    if execute_response.status_code == 200:
        print(f"✅ Payment Executed! Mandate is now USED!")
        return True
    else:
        print(f"❌ Payment execution failed: {execute_response.text}")
        return False


def main():
    print("=" * 60)
    print("AP2 MANDATE USAGE DEMONSTRATION")
    print("Showing when mandates become 'used'")
    print("=" * 60)

    # Step 1: Login
    token = login()
    if not token:
        print("\n❌ Cannot proceed without authentication")
        return

    # Step 2: Get initial stats
    initial_stats = get_ap2_stats(token)
    print_stats(initial_stats, "BEFORE Payment Execution")

    initial_used = (
        initial_stats.get("payment_mandates", {}).get("completed", 0)
        if initial_stats
        else 0
    )

    # Step 3: Ask user which flow to test
    print("\nChoose test method:")
    print("1. Quick test (complete-flow endpoint - one API call)")
    print("2. Detailed test (step-by-step flow - four API calls)")

    # For automation, we'll use the quick test
    print("\nUsing Quick Test (complete-flow)...")
    time.sleep(1)

    # Step 4: Execute payment (this makes mandates "used")
    success = execute_complete_flow(token)

    if not success:
        print("\n❌ Payment execution failed. No mandates were marked as used.")
        return

    # Step 5: Get stats after execution
    time.sleep(1)  # Give database time to update
    final_stats = get_ap2_stats(token)
    print_stats(final_stats, "AFTER Payment Execution")

    # Step 6: Show the difference
    final_used = (
        final_stats.get("payment_mandates", {}).get("completed", 0)
        if final_stats
        else 0
    )
    difference = final_used - initial_used

    print("\n" + "=" * 60)
    print("SUMMARY: When Do Mandates Become 'Used'?")
    print("=" * 60)
    print(f"\n📌 Initial Used Mandates: {initial_used}")
    print(f"📌 Final Used Mandates: {final_used}")
    print(f"📌 New Used Mandates: +{difference}")

    print("\n💡 KEY INSIGHT:")
    print("   Mandates become 'used' when you execute a payment.")
    print("   Simply creating intent/cart/payment mandates does NOT")
    print("   count as 'used' - only completed payments count!")

    print("\n📋 The Flow:")
    print("   1. Create Intent Mandate ❌ Not used yet")
    print("   2. Create Cart Mandate   ❌ Not used yet")
    print("   3. Create Payment Mandate ❌ Not used yet")
    print("   4. Execute Payment       ✅ NOW IT'S USED!")

    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
