"""
Test free tier organization limit enforcement
- Should allow creating 1 organization
- Should block creating a 2nd organization
"""

import requests
import json

BASE_URL = "http://localhost:8000"

# Test credentials for adminfree user
USERNAME = "adminfree"
PASSWORD = "AdminFree123!"

print("[TEST] Free Tier Organization Limit Enforcement")
print("=" * 70)

# Step 1: Login
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

# Step 2: Check current organization count
print("\n[2] Checking current organizations...")
list_response = requests.get(f"{BASE_URL}/api/v1/organizations", headers=headers)

if list_response.status_code == 200:
    orgs = list_response.json()
    print(f"[OK] Current organizations: {len(orgs)}")
    for i, org in enumerate(orgs, 1):
        print(f"     {i}. {org['name']} (slug: {org['slug']})")
else:
    print(f"[ERROR] Failed to list organizations")
    exit(1)

# Step 3: Create FIRST organization (should succeed for free tier)
print("\n[3] Creating FIRST organization (should succeed)...")
print("    Expected: 201 Created")

create1_response = requests.post(
    f"{BASE_URL}/api/v1/organizations",
    headers=headers,
    json={
        "name": "My First Org",
        "slug": "my-first-org",
        "description": "Testing free tier limit",
    },
)

print(f"    Status: {create1_response.status_code}")

if create1_response.status_code == 201:
    print("[PASS] First organization created successfully")
    org1 = create1_response.json()
    print(f"       Created: {org1['name']} (ID: {org1['id']})")
    org1_id = org1["id"]
elif create1_response.status_code == 402:
    print("[FAIL] First organization was blocked (should be allowed!)")
    print(f"       Response: {create1_response.json()}")
    exit(1)
else:
    print(f"[ERROR] Unexpected status: {create1_response.status_code}")
    print(create1_response.text)
    exit(1)

# Step 4: Verify we now have 1 organization
print("\n[4] Verifying organization count...")
list2_response = requests.get(f"{BASE_URL}/api/v1/organizations", headers=headers)
orgs2 = list2_response.json()
print(f"[OK] Organization count after creation: {len(orgs2)}")

if len(orgs2) != 1:
    print(f"[WARN] Expected 1 organization, got {len(orgs2)}")

# Step 5: Attempt to create SECOND organization (should fail with 402)
print("\n[5] Creating SECOND organization (should FAIL with 402)...")
print("    Expected: 402 Payment Required")

create2_response = requests.post(
    f"{BASE_URL}/api/v1/organizations",
    headers=headers,
    json={
        "name": "My Second Org",
        "slug": "my-second-org",
        "description": "This should be blocked",
    },
)

print(f"    Status: {create2_response.status_code}")

if create2_response.status_code == 402:
    print("[PASS] Second organization blocked with 402 Payment Required")
    error_detail = create2_response.json()["detail"]
    print(f"\n    Error details:")
    print(f"       Error: {error_detail.get('error')}")
    print(f"       Feature: {error_detail.get('feature')}")
    print(f"       Tier: {error_detail.get('current_tier')}")
    print(f"       Limit: {error_detail.get('current_limit')}")
    print(f"       Current: {error_detail.get('current_count')}")
    print(f"       Message: {error_detail.get('message')}")
    print(f"       Upgrade: {error_detail.get('upgrade_message')}")

    upgrade_options = error_detail.get("upgrade_options", [])
    if upgrade_options:
        print(f"\n    Upgrade options:")
        for opt in upgrade_options:
            print(
                f"       - {opt['tier']}: {opt['price']} ({opt['organizations']} orgs, {opt['users']} users)"
            )

elif create2_response.status_code == 201:
    print("[FAIL] Second organization was created (should be blocked!)")
    org2 = create2_response.json()
    print(f"       Created: {org2['name']} (ID: {org2['id']})")
    print("\n    THIS IS A BUG - Free tier should only allow 1 organization!")
else:
    print(f"[ERROR] Unexpected status: {create2_response.status_code}")
    print(create2_response.text)

# Step 6: Final verification
print("\n[6] Final organization count...")
list3_response = requests.get(f"{BASE_URL}/api/v1/organizations", headers=headers)
final_orgs = list3_response.json()
print(f"[OK] Final count: {len(final_orgs)} organization(s)")

for i, org in enumerate(final_orgs, 1):
    print(f"     {i}. {org['name']} (slug: {org['slug']})")

# Summary
print("\n" + "=" * 70)
if len(final_orgs) == 1 and create2_response.status_code == 402:
    print("[SUCCESS] Free tier limit enforcement working correctly!")
    print("          - Allows 1 organization")
    print("          - Blocks 2nd organization with 402 Payment Required")
else:
    print("[FAILED] Free tier limit enforcement NOT working correctly")
    if len(final_orgs) > 1:
        print(f"         - User has {len(final_orgs)} organizations (should be 1)")
    if create2_response.status_code != 402:
        print(
            f"         - Second org returned {create2_response.status_code} (should be 402)"
        )

print("=" * 70)
