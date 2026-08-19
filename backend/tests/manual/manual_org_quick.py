"""
Quick Organization Test - Uses existing test user to avoid rate limits
"""

import json

import requests

BASE_URL = "http://localhost:8000"

# Use one of the existing test users we created earlier
USERNAME = "orgtest_20251127_160348"
PASSWORD = "TestPassword123!"


def print_test(name, response, expected_status):
    success = response.status_code == expected_status
    icon = "[OK]" if success else "[FAIL]"
    print(f"\n{icon} {name}")
    print(f"   Status: {response.status_code} (expected: {expected_status})")
    try:
        print(f"   Response: {json.dumps(response.json(), indent=6)}")
    except:
        print(f"   Response: {response.text}")


# Login
print("Logging in...")
response = requests.post(
    f"{BASE_URL}/api/v1/auth/login", json={"username": USERNAME, "password": PASSWORD}
)

if response.status_code != 200:
    print(f"[FAIL] Login failed: {response.text}")
    exit(1)

token = response.json()["access_token"]
print(f"[OK] Logged in as {USERNAME}")

# List current orgs
print("\n" + "=" * 80)
print("Current Organizations")
print("=" * 80)
response = requests.get(
    f"{BASE_URL}/api/v1/organizations", headers={"Authorization": f"Bearer {token}"}
)
print_test("List Organizations", response, 200)
current_orgs = response.json()

# Delete all existing orgs for clean test
for org in current_orgs:
    print(f"\nCleaning up organization: {org['name']}")
    response = requests.delete(
        f"{BASE_URL}/api/v1/organizations/{org['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    print(f"   Deleted: {response.status_code == 204}")

# Test 1: Create first org
print("\n" + "=" * 80)
print("TEST 1: Create First Organization")
print("=" * 80)
response = requests.post(
    f"{BASE_URL}/api/v1/organizations",
    headers={"Authorization": f"Bearer {token}"},
    json={"name": "My Test Company", "slug": "my-test-company"},
)
print_test("Create First Org", response, 201)
org1_id = response.json()["id"] if response.status_code == 201 else None

# Test 2: Try duplicate slug
print("\n" + "=" * 80)
print("TEST 2: Duplicate Slug (Should Fail)")
print("=" * 80)
response = requests.post(
    f"{BASE_URL}/api/v1/organizations",
    headers={"Authorization": f"Bearer {token}"},
    json={"name": "Different Name", "slug": "my-test-company"},
)
print_test("Duplicate Slug", response, 400)

# Test 3: Try duplicate name (exact match)
print("\n" + "=" * 80)
print("TEST 3: Duplicate Name - Exact Match (Should Fail)")
print("=" * 80)
response = requests.post(
    f"{BASE_URL}/api/v1/organizations",
    headers={"Authorization": f"Bearer {token}"},
    json={"name": "My Test Company", "slug": "different-slug"},
)
print_test("Duplicate Name (exact)", response, 400)

# Test 4: Try duplicate name (case insensitive)
print("\n" + "=" * 80)
print("TEST 4: Duplicate Name - Case Insensitive (Should Fail)")
print("=" * 80)
response = requests.post(
    f"{BASE_URL}/api/v1/organizations",
    headers={"Authorization": f"Bearer {token}"},
    json={"name": "MY TEST COMPANY", "slug": "another-slug"},
)
print_test("Duplicate Name (case-insensitive)", response, 400)

# Test 5: Try creating second org (Free tier limit)
print("\n" + "=" * 80)
print("TEST 5: Second Organization on Free Tier (Should Fail)")
print("=" * 80)
response = requests.post(
    f"{BASE_URL}/api/v1/organizations",
    headers={"Authorization": f"Bearer {token}"},
    json={"name": "Second Company", "slug": "second-company"},
)
print_test("Second Org on Free Tier", response, 402)

# Test 6: Delete and recreate
if org1_id:
    print("\n" + "=" * 80)
    print("TEST 6: Delete First Organization")
    print("=" * 80)
    response = requests.delete(
        f"{BASE_URL}/api/v1/organizations/{org1_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    print_test("Delete Org", response, 204)

    print("\n" + "=" * 80)
    print("TEST 7: Create Organization After Delete (Should Succeed)")
    print("=" * 80)
    response = requests.post(
        f"{BASE_URL}/api/v1/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "My Test Company", "slug": "my-test-company"},
    )
    print_test("Recreate After Delete", response, 201)
    org2_id = response.json()["id"] if response.status_code == 201 else None

    # Cleanup
    if org2_id:
        print("\n" + "=" * 80)
        print("CLEANUP")
        print("=" * 80)
        response = requests.delete(
            f"{BASE_URL}/api/v1/organizations/{org2_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        print(f"Cleanup: {response.status_code == 204}")

print("\n" + "=" * 80)
print("ALL TESTS COMPLETED")
print("=" * 80)
