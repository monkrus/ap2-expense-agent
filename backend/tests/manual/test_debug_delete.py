"""Debug organization deletion"""

import requests
import json

BASE_URL = "http://localhost:8000"
USERNAME = "orgtest_20251127_160348"
PASSWORD = "TestPassword123!"

# Login
response = requests.post(
    f"{BASE_URL}/api/v1/auth/login", json={"username": USERNAME, "password": PASSWORD}
)
token = response.json()["access_token"]

# Create org
print("Creating organization...")
response = requests.post(
    f"{BASE_URL}/api/v1/organizations",
    headers={"Authorization": f"Bearer {token}"},
    json={"name": "Debug Test Org", "slug": "debug-test"},
)
print(f"Create response: {response.status_code}")
if response.status_code == 201:
    org_id = response.json()["id"]
    print(f"Org ID: {org_id}")

    # List orgs
    response = requests.get(
        f"{BASE_URL}/api/v1/organizations", headers={"Authorization": f"Bearer {token}"}
    )
    print(f"\nActive orgs: {len(response.json())}")

    # Delete
    print(f"\nDeleting org {org_id}...")
    response = requests.delete(
        f"{BASE_URL}/api/v1/organizations/{org_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    print(f"Delete response: {response.status_code}")

    # List orgs again
    response = requests.get(
        f"{BASE_URL}/api/v1/organizations", headers={"Authorization": f"Bearer {token}"}
    )
    print(f"\nActive orgs after delete: {len(response.json())}")

    # Try to recreate immediately
    print("\nTrying to recreate with same slug...")
    response = requests.post(
        f"{BASE_URL}/api/v1/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Debug Test Org Recreated", "slug": "debug-test"},
    )
    print(f"Recreate response: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    if response.status_code == 201:
        # Clean up
        org_id2 = response.json()["id"]
        requests.delete(
            f"{BASE_URL}/api/v1/organizations/{org_id2}",
            headers={"Authorization": f"Bearer {token}"},
        )
        print("Cleaned up successfully")
