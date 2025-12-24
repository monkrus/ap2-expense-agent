"""
Test organization limit with existing user 'adminfree'
This user should already have 1 organization from manual testing
"""

import requests

BASE_URL = "http://localhost:8000/api/v1"

def test_with_existing_user():
    print("=" * 70)
    print("Testing organization limit with existing user 'adminfree'")
    print("=" * 70)

    # Login with existing user
    print("\n[Step 1] Logging in as 'adminfree'...")
    login_data = {
        "username": "adminfree",
        "password": "1"
    }

    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code != 200:
        print(f"[FAIL] Login failed: {response.status_code}")
        print(f"  Response: {response.text}")
        return

    print(f"[OK] Login successful")
    login_response = response.json()
    access_token = login_response["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Check existing organizations
    print("\n[Step 2] Checking existing organizations...")
    response = requests.get(f"{BASE_URL}/organizations", headers=headers)
    if response.status_code == 200:
        orgs = response.json()
        print(f"  User has {len(orgs)} organization(s)")
        for org in orgs:
            print(f"    - {org['name']} (ID: {org['id']})")
    else:
        print(f"[WARN] Could not fetch organizations: {response.status_code}")

    # Try to create another organization
    print("\n[Step 3] Attempting to create a new organization...")
    import time
    org_data = {
        "name": f"Test New Org {int(time.time())}",
        "slug": f"test-new-org-{int(time.time())}",
        "description": "Testing organization limit enforcement",
        "currency": "USD",
        "timezone": "UTC"
    }

    response = requests.post(
        f"{BASE_URL}/organizations",
        json=org_data,
        headers=headers
    )

    print(f"  Status Code: {response.status_code}")
    print(f"  Response: {response.text}")

    if response.status_code == 402:
        print("\n" + "=" * 70)
        print("[SUCCESS] Organization limit is NOW ENFORCED!")
        print("=" * 70)
        print("Backend correctly rejected organization creation with 402")
        error_data = response.json()
        print(f"\nError details:")
        print(f"  Feature: {error_data.get('feature')}")
        print(f"  Current: {error_data.get('current_count')}")
        print(f"  Limit: {error_data.get('current_limit')}")
        print(f"  Message: {error_data.get('message')}")
        return True

    elif response.status_code == 201:
        print("\n" + "!" * 70)
        print("[FAIL] Vulnerability still exists!")
        print("!" * 70)
        print("Organization was created despite limit")
        return False

    else:
        print(f"\n[WARN] Unexpected status code: {response.status_code}")
        return None


if __name__ == "__main__":
    result = test_with_existing_user()

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    if result == True:
        print("RESULT: FIX WORKS - Limit is enforced")
    elif result == False:
        print("RESULT: FIX FAILED - Limit not enforced")
    else:
        print("RESULT: INCONCLUSIVE")
    print("=" * 70)
