"""
Test organization limit enforcement for free tier user
"""

import json

import requests

BASE_URL = "http://localhost:8000"

# Test credentials for adminfree user
USERNAME = "adminfree"
PASSWORD = "AdminFree123!"

print("[TEST] Organization Limit Enforcement for Free Tier")
print("=" * 60)

# Step 1: Login as adminfree
print("\n[1] Logging in as adminfree...")
login_response = requests.post(
    f"{BASE_URL}/api/v1/auth/login", json={"username": USERNAME, "password": PASSWORD}
)

if login_response.status_code != 200:
    print(f"[ERROR] Login failed: {login_response.status_code}")
    print(login_response.text)
    exit(1)

token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("[OK] Login successful")

# Step 2: List current organizations
print("\n[2] Listing current organizations...")
list_response = requests.get(f"{BASE_URL}/api/v1/organizations", headers=headers)

if list_response.status_code == 200:
    orgs = list_response.json()
    print(f"[OK] Current organizations: {len(orgs)}")
    for i, org in enumerate(orgs, 1):
        print(f"   {i}. {org['name']} (slug: {org['slug']})")
else:
    print(f"[ERROR] Failed to list organizations: {list_response.status_code}")
    exit(1)

# Step 3: Attempt to create a 2nd organization (should fail with 402)
print("\n[3] Attempting to create a 2nd organization...")
print("    Expected: 402 Payment Required (limit exceeded)")

create_response = requests.post(
    f"{BASE_URL}/api/v1/organizations",
    headers=headers,
    json={
        "name": "Test Org 4",
        "slug": "test-org-4",
        "description": "This should be blocked by tier limits",
    },
)

print(f"\n[RESULT] Status Code: {create_response.status_code}")

if create_response.status_code == 402:
    print("[PASS] ✓ Creation blocked with 402 Payment Required")
    error_detail = create_response.json()
    print("\nError details:")
    print(f"   Error: {error_detail.get('detail', {}).get('error', 'N/A')}")
    print(f"   Feature: {error_detail.get('detail', {}).get('feature', 'N/A')}")
    print(
        f"   Current tier: {error_detail.get('detail', {}).get('current_tier', 'N/A')}"
    )
    print(f"   Limit: {error_detail.get('detail', {}).get('current_limit', 'N/A')}")
    print(
        f"   Current count: {error_detail.get('detail', {}).get('current_count', 'N/A')}"
    )
    print(f"   Message: {error_detail.get('detail', {}).get('message', 'N/A')}")
    print(
        f"   Upgrade message: {error_detail.get('detail', {}).get('upgrade_message', 'N/A')}"
    )

    upgrade_options = error_detail.get("detail", {}).get("upgrade_options", [])
    if upgrade_options:
        print("\n   Upgrade options:")
        for option in upgrade_options:
            print(
                f"      - {option.get('tier')}: {option.get('price')} ({option.get('organizations')} orgs, {option.get('users')} users)"
            )

elif create_response.status_code == 201:
    print("[FAIL] ✗ Organization was created (should have been blocked!)")
    org = create_response.json()
    print(f"   Created: {org.get('name')} (id: {org.get('id')})")
    print("\n   THIS IS A BUG - Free tier should only allow 1 organization!")
else:
    print(f"[UNEXPECTED] Got status code {create_response.status_code}")
    print(f"Response: {create_response.text}")

# Step 4: Verify organization count is still 1
print("\n[4] Verifying organization count...")
verify_response = requests.get(f"{BASE_URL}/api/v1/organizations", headers=headers)

if verify_response.status_code == 200:
    final_orgs = verify_response.json()
    print(f"[OK] Final organization count: {len(final_orgs)}")

    if len(final_orgs) == 1:
        print("[PASS] ✓ User still has exactly 1 organization")
    else:
        print(f"[FAIL] ✗ User has {len(final_orgs)} organizations (expected 1)")

print("\n" + "=" * 60)
print("[DONE] Test complete")
