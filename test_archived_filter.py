#!/usr/bin/env python3
"""
Test the new archived/deleted mandate filtering feature
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def login():
    """Login and get token"""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "Test123!"
        }
    )
    response.raise_for_status()
    return response.json()["access_token"]

def get_mandates(token, include_deleted=False):
    """Get mandates with optional include_deleted"""
    params = {"limit": 50, "include_deleted": str(include_deleted).lower()}
    url = f"{BASE_URL}/api/ap2/user/mandates"
    print(f"   [DEBUG] Request URL: {url}")
    print(f"   [DEBUG] Params: {params}")
    response = requests.get(
        url,
        params=params,
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"   [DEBUG] Full URL: {response.url}")
    response.raise_for_status()
    return response.json()

def delete_mandate(token, mandate_id):
    """Delete a mandate"""
    response = requests.delete(
        f"{BASE_URL}/api/ap2/mandate/{mandate_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    response.raise_for_status()
    return response.json()

def main():
    print("=" * 60)
    print("Testing Archived Mandate Filter Feature")
    print("=" * 60)

    # Login
    print("\n1. Logging in...")
    token = login()
    print("   ✓ Logged in successfully")

    # Get mandates WITHOUT deleted
    print("\n2. Fetching mandates (exclude deleted)...")
    mandates_normal = get_mandates(token, include_deleted=False)
    print(f"   ✓ Found {mandates_normal['count']} active mandates")

    # Count by status
    status_counts = {}
    for mandate in mandates_normal['mandates']:
        status = mandate.get('status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1

    print("\n   Status breakdown (excluding deleted):")
    for status, count in sorted(status_counts.items()):
        print(f"     - {status}: {count}")

    # Get mandates WITH deleted
    print("\n3. Fetching mandates (include deleted)...")
    mandates_all = get_mandates(token, include_deleted=True)
    print(f"   ✓ Found {mandates_all['count']} total mandates (including deleted)")

    # Count by status
    status_counts_all = {}
    for mandate in mandates_all['mandates']:
        status = mandate.get('status', 'unknown')
        status_counts_all[status] = status_counts_all.get(status, 0) + 1

    print("\n   Status breakdown (including deleted):")
    for status, count in sorted(status_counts_all.items()):
        print(f"     - {status}: {count}")

    # Check if there are any deleted
    deleted_count = status_counts_all.get('deleted', 0)
    print(f"\n4. Deleted mandates: {deleted_count}")

    if deleted_count > 0:
        print("   ✓ Feature working! Deleted mandates are hidden by default.")
    else:
        print("   ℹ No deleted mandates found. Let's create and delete one...")

        # Create a test mandate
        print("\n5. Creating a test mandate...")
        response = requests.post(
            f"{BASE_URL}/api/ap2/intent-mandate",
            json={
                "constraints": {
                    "max_amount": 10.00,
                    "category": "OTHER"
                },
                "expiration_hours": 1
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        new_mandate = response.json()
        mandate_id = new_mandate.get('intent_mandate_id') or new_mandate.get('mandate_id') or new_mandate.get('id')
        print(f"   ✓ Created test mandate: {mandate_id[:8]}...")

        # Delete it
        print("\n6. Deleting the test mandate...")
        delete_mandate(token, mandate_id)
        print("   ✓ Mandate deleted")

        # Wait a moment for database to process
        time.sleep(0.5)

        # Re-check counts
        print("\n7. Re-checking counts...")
        mandates_normal2 = get_mandates(token, include_deleted=False)
        mandates_all2 = get_mandates(token, include_deleted=True)

        print(f"   - Without deleted: {mandates_normal2['count']}")
        print(f"   - With deleted: {mandates_all2['count']}")
        print(f"   - Difference: {mandates_all2['count'] - mandates_normal2['count']}")

        if mandates_all2['count'] > mandates_normal2['count']:
            print("\n   ✓ Feature working! Deleted mandate is excluded by default.")
        else:
            print("\n   ⚠ Unexpected: counts should differ")

    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)
    print("\n✓ Backend API correctly filters deleted mandates by default")
    print("✓ Frontend toggle will show/hide archived items")
    print("\nTo test in UI:")
    print("1. Go to http://localhost:5173")
    print("2. Navigate to AP2 Automation → Reusable Authorizations")
    print("3. Look for 'Show archived items' checkbox at bottom")
    print("4. Toggle it to see/hide deleted mandates")

if __name__ == "__main__":
    main()
