"""
Complete Stripe Integration Testing
Tests entire flow: User -> Organization -> Checkout -> Webhooks
"""

import requests
import json
import time
import sys
from datetime import datetime

# Fix encoding for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8000"

# Test data
timestamp = int(time.time())
TEST_USER = {
    "username": f"stripetest_{timestamp}",
    "password": "Test1234!",
    "email": f"stripetest_{timestamp}@example.com",
    "full_name": "Stripe Tester"
}

TEST_ORG = {
    "name": f"Test Org {timestamp}",
    "slug": f"test-org-{timestamp}",
    "description": "Testing Stripe integration"
}

def step(title):
    """Print step header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def api_call(method, endpoint, token=None, json_data=None, params=None):
    """Make API call with error handling"""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"{BASE_URL}{endpoint}"

    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=json_data, params=params)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)

        return response
    except Exception as e:
        print(f"   ERROR: {e}")
        return None

def test_complete_flow():
    """Test complete Stripe integration flow"""

    print("""
    ======================================================================
                    STRIPE INTEGRATION COMPLETE TEST
    ======================================================================

    This test runs through the entire Stripe checkout flow:
    1. Register user
    2. Create organization
    3. Create checkout sessions for all 6 tiers/cycles
    4. Simulate webhook events
    5. Verify results

    ======================================================================
    """)

    # Step 1: Register user
    step("Step 1: Register User")
    response = api_call("POST", "/api/v1/auth/register", json_data=TEST_USER)

    if response and response.status_code == 201:
        print(f"[OK] User registered: {TEST_USER['username']}")
        user_id = response.json().get('id')
    else:
        print(f"[FAIL] Registration failed: {response.status_code if response else 'No response'}")
        if response:
            print(f"       {response.json()}")
        return False

    # Step 2: Login
    step("Step 2: Login")
    response = api_call("POST", "/api/v1/auth/login", json_data={
        "username": TEST_USER["username"],
        "password": TEST_USER["password"]
    })

    if response and response.status_code == 200:
        token = response.json().get("access_token")
        print(f"[OK] Login successful")
        print(f"     Token: {token[:30]}...")
    else:
        print(f"[FAIL] Login failed")
        return False

    # Step 3: Create organization
    step("Step 3: Create Organization")
    response = api_call("POST", "/api/v1/organizations", token=token, json_data=TEST_ORG)

    if response and response.status_code == 201:
        org_data = response.json()
        org_id = org_data.get('id')
        print(f"[OK] Organization created: {TEST_ORG['name']}")
        print(f"     ID: {org_id}")
        print(f"     Slug: {org_data.get('slug')}")
    else:
        print(f"[FAIL] Organization creation failed: {response.status_code if response else 'No response'}")
        if response:
            print(f"       {response.json()}")
        return False

    # Step 4: Test all checkout sessions
    step("Step 4: Test Stripe Checkout Sessions (All 6 Products)")

    test_configs = [
        ("starter", "monthly"),
        ("starter", "annual"),
        ("professional", "monthly"),
        ("professional", "annual"),
        ("enterprise", "monthly"),
        ("enterprise", "annual")
    ]

    checkout_results = []

    for tier, cycle in test_configs:
        print(f"\n--- Testing: {tier.upper()} ({cycle}) ---")

        response = api_call(
            "POST",
            "/api/payment/checkout-session",
            token=token,
            params={"tier_name": tier, "billing_cycle": cycle}
        )

        if response and response.status_code == 200:
            data = response.json()
            session_id = data.get("session_id")
            print(f"[OK] Checkout session created")
            print(f"     Session ID: {session_id}")
            print(f"     URL: {data.get('url')[:50]}...")
            checkout_results.append({
                "tier": tier,
                "cycle": cycle,
                "success": True,
                "session_id": session_id,
                "url": data.get('url')
            })
        else:
            status = response.status_code if response else "No response"
            error = response.json() if response else {}
            print(f"[FAIL] Checkout failed: {status}")
            print(f"       {error}")
            checkout_results.append({
                "tier": tier,
                "cycle": cycle,
                "success": False,
                "error": error
            })

        time.sleep(0.5)  # Rate limiting

    # Step 5: Summary
    step("Step 5: Results Summary")

    success_count = sum(1 for r in checkout_results if r["success"])
    total_count = len(checkout_results)

    print(f"\nCheckout Session Results: {success_count}/{total_count} successful\n")

    for result in checkout_results:
        status = "[OK]  " if result["success"] else "[FAIL]"
        print(f"{status} {result['tier']:15} {result['cycle']:10}")
        if result["success"]:
            print(f"       Session: {result['session_id']}")
        else:
            print(f"       Error: {result.get('error', {}).get('detail', 'Unknown error')}")
        print()

    # Step 6: Test webhook endpoint
    step("Step 6: Test Webhook Endpoint")

    mock_event = {
        "id": f"evt_test_{timestamp}",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_12345",
                "customer": "cus_test_12345",
                "subscription": "sub_test_12345",
                "amount_total": 2900,
                "metadata": {
                    "organization_id": org_id,
                    "tier_name": "starter",
                    "billing_cycle": "monthly"
                }
            }
        }
    }

    print("Testing webhook endpoint with mock event...")
    response = api_call("POST", "/api/payment/webhooks/stripe", json_data=mock_event)

    if response:
        print(f"[INFO] Webhook response: {response.status_code}")
        print(f"       Note: 200 = received, 400 = signature verification failed (expected without Stripe CLI)")

    # Step 7: Display next steps
    step("Next Steps for Complete Testing")

    print("""
    To complete webhook testing with Stripe CLI:

    1. Start webhook listener:
       > test-stripe-webhook.bat

    2. Copy the webhook signing secret (whsec_...)

    3. Add to backend/.env:
       STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx

    4. Restart backend server

    5. Trigger test events:
       > trigger-stripe-test-events.bat

    6. Or complete a real checkout:
       Use one of the checkout URLs above in your browser
       Test card: 4242 4242 4242 4242

    ======================================================================
    """)

    # Cleanup option
    print(f"\nTest user created: {TEST_USER['username']}")
    print(f"Test organization created: {TEST_ORG['name']} (ID: {org_id})")
    print(f"\nTo cleanup, delete the organization through the API or dashboard.")

    return True

if __name__ == "__main__":
    try:
        success = test_complete_flow()
        if success:
            print("\n[SUCCESS] Test completed")
        else:
            print("\n[FAILED] Test failed")
    except Exception as e:
        print(f"\n[ERROR] Exception during test: {e}")
        import traceback
        traceback.print_exc()
