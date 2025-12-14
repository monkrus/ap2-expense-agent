"""
Test: Free Tier Organization Limit (402 Payment Required)

This test verifies that free tier users get a proper upgrade prompt
when trying to create a second organization.
"""

import requests
import time
import sys
import io

# Fix Unicode encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000"

def test_free_tier_organization_limit():
    """
    Test that free tier users get 402 Payment Required with upgrade info
    when trying to create a second organization
    """

    print("\n" + "="*70)
    print("TEST: Free Tier Organization Limit & Upgrade Prompt")
    print("="*70)

    # Step 1: Register a new user (Free tier by default)
    print("\n1. Registering new free tier user...")
    username = f"freetier_{int(time.time())}"
    register_data = {
        "username": username,
        "email": f"{username}@test.com",
        "password": "TestPass123!",
        "full_name": "Free Tier User"
    }

    register_response = requests.post(
        f"{BASE_URL}/api/v1/auth/register",
        json=register_data
    )

    if register_response.status_code != 201:
        print(f"❌ Registration failed: {register_response.status_code}")
        print(register_response.json())
        return

    print(f"✅ User registered: {username}")

    # Step 2: Login
    print("\n2. Logging in...")
    login_response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={
            "username": username,
            "password": "TestPass123!"
        }
    )

    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        return

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"✅ Logged in successfully")

    # Step 3: Create first organization (should succeed)
    print("\n3. Creating first organization (should succeed)...")
    org1_data = {
        "name": f"First Org {int(time.time())}",
        "slug": f"first-org-{int(time.time())}",
        "description": "First organization - should succeed"
    }

    org1_response = requests.post(
        f"{BASE_URL}/api/v1/organizations",
        json=org1_data,
        headers=headers
    )

    if org1_response.status_code == 201:
        print(f"✅ First organization created successfully!")
        print(f"   Name: {org1_response.json()['name']}")
    else:
        print(f"❌ Failed to create first org: {org1_response.status_code}")
        print(org1_response.json())
        return

    # Step 4: Try to create second organization (should return 402)
    print("\n4. Attempting to create second organization (should get 402)...")
    org2_data = {
        "name": f"Second Org {int(time.time())}",
        "slug": f"second-org-{int(time.time())}",
        "description": "Second organization - should trigger upgrade prompt"
    }

    org2_response = requests.post(
        f"{BASE_URL}/api/v1/organizations",
        json=org2_data,
        headers=headers
    )

    print(f"\n📊 RESPONSE STATUS: {org2_response.status_code}")

    if org2_response.status_code == 402:
        print("\n✅ CORRECT: Got 402 Payment Required!")

        # Parse the upgrade prompt data
        response_data = org2_response.json()
        print("\n📋 Upgrade Prompt Details:")
        print("="*70)

        if "detail" in response_data:
            detail = response_data["detail"]
            print(f"  Message: {detail.get('message', 'N/A')}")
            print(f"  Current Tier: {detail.get('current_tier', 'N/A')}")
            print(f"  Current Limit: {detail.get('current_limit', 'N/A')}")
            print(f"  Current Count: {detail.get('current_count', 'N/A')}")

            if detail.get('upgrade_options'):
                opts = detail['upgrade_options']
                print(f"\n  🎯 Recommended Upgrade:")
                print(f"     → {opts.get('next_tier', 'N/A')} Plan")
                print(f"     → {opts.get('price', 'N/A')}")
                print(f"     → Up to {opts.get('next_tier_orgs', 'N/A')} organizations")

        print("\n" + "="*70)
        print("✅ TEST PASSED: Free tier users correctly get upgrade prompt!")
        print("="*70)

    elif org2_response.status_code == 201:
        print("\n❌ TEST FAILED: Second org created successfully (should have been blocked)")
        print("   This means tier limits are NOT being enforced!")

    else:
        print(f"\n❌ TEST FAILED: Unexpected status code: {org2_response.status_code}")
        print(response_data)

    print("\n" + "="*70)
    print("Test Complete")
    print("="*70 + "\n")

if __name__ == "__main__":
    try:
        test_free_tier_organization_limit()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
