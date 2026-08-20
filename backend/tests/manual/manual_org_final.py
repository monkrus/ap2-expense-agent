"""
Final Organization Test - Comprehensive validation test
Creates fresh user to avoid database pollution
"""

import json
import time

import requests

BASE_URL = "http://localhost:8000"


def print_test(name, response, expected_status):
    success = response.status_code == expected_status
    icon = "[PASS]" if success else "[FAIL]"
    print(f"\n{icon} {name}")
    print(f"    Status: {response.status_code} (expected: {expected_status})")
    if not success or response.status_code >= 400:
        try:
            print(f"    Response: {json.dumps(response.json(), indent=8)}")
        except:
            print(f"    Response: {response.text}")
    return success


# Create unique test user
timestamp = int(time.time())
username = f"orgfinal_{timestamp}"
password = "TestPassword123!"
email = f"{username}@test.com"

print("=" * 80)
print("ORGANIZATION VALIDATION TEST SUITE")
print("=" * 80)
print(f"Test user: {username}")

# Register
print("\n[1] Registering new test user...")
response = requests.post(
    f"{BASE_URL}/api/v1/auth/register",
    json={
        "username": username,
        "email": email,
        "password": password,
        "full_name": f"Test User {username}",
    },
)

if response.status_code != 201:
    print(f"[SKIP] Registration failed (rate limited): {response.status_code}")
    print("Using existing test user instead...")
    username = "orgtest_20251127_160348"
    password = "TestPassword123!"

# Login
print(f"\n[2] Logging in as {username}...")
response = requests.post(
    f"{BASE_URL}/api/v1/auth/login", json={"username": username, "password": password}
)

if response.status_code != 200:
    print(f"[FAIL] Login failed: {response.text}")
    exit(1)

token = response.json()["access_token"]
print("[OK] Logged in successfully")

# Clean up ALL existing organizations
print("\n[3] Cleaning up existing organizations...")
response = requests.get(
    f"{BASE_URL}/api/v1/organizations", headers={"Authorization": f"Bearer {token}"}
)
existing_orgs = response.json() if response.status_code == 200 else []
for org in existing_orgs:
    requests.delete(
        f"{BASE_URL}/api/v1/organizations/{org['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
print(f"[OK] Cleaned up {len(existing_orgs)} organization(s)")

# Start tests
test_results = []

print("\n" + "=" * 80)
print("TEST 1: Create First Organization")
print("=" * 80)
response = requests.post(
    f"{BASE_URL}/api/v1/organizations",
    headers={"Authorization": f"Bearer {token}"},
    json={"name": "Acme Corporation", "slug": "acme-corp"},
)
result = print_test("Create first organization", response, 201)
test_results.append(("Create first org", result))
org1_id = response.json()["id"] if response.status_code == 201 else None

print("\n" + "=" * 80)
print("TEST 2: Duplicate Slug Validation")
print("=" * 80)
response = requests.post(
    f"{BASE_URL}/api/v1/organizations",
    headers={"Authorization": f"Bearer {token}"},
    json={"name": "Different Company", "slug": "acme-corp"},
)
result = print_test("Reject duplicate slug", response, 400)
test_results.append(("Duplicate slug rejected", result))

print("\n" + "=" * 80)
print("TEST 3: Duplicate Name Validation (Exact Match)")
print("=" * 80)
response = requests.post(
    f"{BASE_URL}/api/v1/organizations",
    headers={"Authorization": f"Bearer {token}"},
    json={"name": "Acme Corporation", "slug": "different-slug-1"},
)
result = print_test("Reject duplicate name (exact)", response, 400)
test_results.append(("Duplicate name (exact) rejected", result))

print("\n" + "=" * 80)
print("TEST 4: Duplicate Name Validation (Case Insensitive)")
print("=" * 80)
response = requests.post(
    f"{BASE_URL}/api/v1/organizations",
    headers={"Authorization": f"Bearer {token}"},
    json={"name": "ACME CORPORATION", "slug": "different-slug-2"},
)
result = print_test("Reject duplicate name (case-insensitive)", response, 400)
test_results.append(("Duplicate name (case-insensitive) rejected", result))

response = requests.post(
    f"{BASE_URL}/api/v1/organizations",
    headers={"Authorization": f"Bearer {token}"},
    json={"name": "acme corporation", "slug": "different-slug-3"},
)
result = print_test("Reject duplicate name (lowercase)", response, 400)
test_results.append(("Duplicate name (lowercase) rejected", result))

print("\n" + "=" * 80)
print("TEST 5: Free Tier Organization Limit")
print("=" * 80)
response = requests.post(
    f"{BASE_URL}/api/v1/organizations",
    headers={"Authorization": f"Bearer {token}"},
    json={"name": "Second Company", "slug": "second-company"},
)
result = print_test("Reject second org on Free tier", response, 402)
test_results.append(("Free tier limit enforced", result))

print("\n" + "=" * 80)
print("TEST 6: Delete and Recreate")
print("=" * 80)
if org1_id:
    response = requests.delete(
        f"{BASE_URL}/api/v1/organizations/{org1_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    result = print_test("Delete organization", response, 204)
    test_results.append(("Delete organization", result))

    # Verify slug is freed after deletion
    response = requests.post(
        f"{BASE_URL}/api/v1/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Acme Corporation", "slug": "acme-corp"},
    )
    result = print_test("Recreate with same slug and name after delete", response, 201)
    test_results.append(("Recreate after delete", result))
    org2_id = response.json()["id"] if response.status_code == 201 else None

    # Clean up
    if org2_id:
        requests.delete(
            f"{BASE_URL}/api/v1/organizations/{org2_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

# Summary
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)
passed = sum(1 for _, result in test_results if result)
total = len(test_results)
print(f"\nPassed: {passed}/{total}")
for test_name, result in test_results:
    icon = "[PASS]" if result else "[FAIL]"
    print(f"  {icon} {test_name}")

if passed == total:
    print("\n[SUCCESS] All tests passed!")
else:
    print(f"\n[PARTIAL] {total - passed} test(s) failed")
