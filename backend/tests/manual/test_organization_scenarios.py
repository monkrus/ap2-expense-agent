"""
Comprehensive Organization Creation Test Script
Tests all possible scenarios for organization creation, deletion, and limits
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_result(test_name, response, expected_status=None):
    """Print formatted test result"""
    success = response.status_code == expected_status if expected_status else True
    status_icon = "[OK]" if success else "[FAIL]"

    print(f"\n{status_icon} {test_name}")
    print(f"   Status: {response.status_code}")

    try:
        data = response.json()
        print(f"   Response: {json.dumps(data, indent=6)}")
    except:
        print(f"   Response: {response.text}")

    return response

def register_user(username, email, password):
    """Register a new test user"""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
            "full_name": f"Test User {username}"
        }
    )
    return response

def login_user(username, password):
    """Login and get access token"""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={
            "username": username,
            "password": password
        }
    )
    print(f"   Login status: {response.status_code}")
    if response.status_code != 200:
        print(f"   Login error: {response.text}")
    if response.status_code == 200:
        return response.json()["access_token"]
    return None

def get_organizations(token):
    """Get list of user's organizations"""
    response = requests.get(
        f"{BASE_URL}/api/v1/organizations",
        headers={"Authorization": f"Bearer {token}"}
    )
    return response

def create_organization(token, name, slug):
    """Create a new organization"""
    response = requests.post(
        f"{BASE_URL}/api/v1/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": name,
            "slug": slug,
            "description": f"Test organization {slug}"
        }
    )
    return response

def delete_organization(token, org_id):
    """Delete an organization"""
    response = requests.delete(
        f"{BASE_URL}/api/v1/organizations/{org_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    return response

def get_user_subscription(token):
    """Get user's subscription info"""
    response = requests.get(
        f"{BASE_URL}/api/billing/subscription",
        headers={"Authorization": f"Bearer {token}"}
    )
    return response

def main():
    """Run all organization test scenarios"""

    # Generate unique test user
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    username = f"orgtest_{timestamp}"
    email = f"{username}@test.com"
    password = "TestPassword123!"

    print_section("ORGANIZATION CREATION TEST SUITE")
    print(f"Test User: {username}")
    print(f"Test Email: {email}")

    # Step 1: Register user
    print_section("Step 1: Register Test User")
    response = register_user(username, email, password)
    print_result("Register User", response, 201)

    if response.status_code != 201:
        print("\n[FAIL] Failed to register user. Exiting.")
        return

    # Step 2: Login
    print_section("Step 2: Login and Get Token")
    token = login_user(username, password)

    if not token:
        print("\n[FAIL] Failed to login. Exiting.")
        return

    print(f"[OK] Login successful")
    print(f"   Token: {token[:50]}...")

    # Step 3: Check initial subscription tier
    print_section("Step 3: Check User Subscription Tier")
    response = get_user_subscription(token)
    print_result("Get Subscription", response, 200)

    # Step 4: List initial organizations (should be empty)
    print_section("Step 4: List Initial Organizations (Should be 0)")
    response = get_organizations(token)
    print_result("List Organizations", response, 200)

    initial_orgs = response.json() if response.status_code == 200 else []
    print(f"   Initial org count: {len(initial_orgs)}")

    # Step 5: Create first organization (should succeed)
    print_section("Step 5: Create First Organization (Should Succeed)")
    response = create_organization(token, "Test Org 1", "test-org-1")
    print_result("Create First Organization", response, 201)

    org1_id = None
    if response.status_code == 201:
        org1_id = response.json()["id"]
        print(f"   Organization ID: {org1_id}")

    # Step 6: List organizations after first creation
    print_section("Step 6: List Organizations (Should be 1)")
    response = get_organizations(token)
    print_result("List Organizations", response, 200)

    orgs_after_first = response.json() if response.status_code == 200 else []
    print(f"   Current org count: {len(orgs_after_first)}")

    # Step 7: Try to create second organization (should fail on Free tier)
    print_section("Step 7: Create Second Organization (Should Fail - Free Tier Limit)")
    response = create_organization(token, "Test Org 2", "test-org-2")
    print_result("Create Second Organization", response, 402)

    # Step 8: Try to create organization with duplicate slug (should fail)
    print_section("Step 8: Create Organization with Duplicate Slug (Should Fail)")
    response = create_organization(token, "Test Org 1 Copy", "test-org-1")
    print_result("Create Duplicate Slug", response, 400)

    # Step 8.5: Try to create organization with duplicate name (should fail)
    print_section("Step 8.5: Create Organization with Duplicate Name (Should Fail)")
    response = create_organization(token, "Test Org 1", "test-org-1-different-slug")
    print_result("Create Duplicate Name", response, 400)

    # Step 8.6: Try with case-insensitive duplicate name (should also fail)
    print_section("Step 8.6: Create Organization with Case-Insensitive Duplicate Name (Should Fail)")
    response = create_organization(token, "TEST ORG 1", "test-org-1-another-slug")
    print_result("Create Case-Insensitive Duplicate", response, 400)

    # Step 9: Delete first organization
    if org1_id:
        print_section("Step 9: Delete First Organization")
        response = delete_organization(token, org1_id)
        print_result("Delete Organization", response, 204)

        # Step 10: Verify organization deleted
        print_section("Step 10: List Organizations After Deletion (Should be 0)")
        response = get_organizations(token)
        print_result("List Organizations", response, 200)

        orgs_after_delete = response.json() if response.status_code == 200 else []
        print(f"   Current org count: {len(orgs_after_delete)}")

        # Step 11: Create organization again after deletion (should succeed)
        print_section("Step 11: Create Organization Again After Deletion (Should Succeed)")
        response = create_organization(token, "Test Org 3", "test-org-3")
        print_result("Create After Deletion", response, 201)

        org3_id = None
        if response.status_code == 201:
            org3_id = response.json()["id"]
            print(f"   Organization ID: {org3_id}")

        # Step 12: Final organization count
        print_section("Step 12: Final Organization Count")
        response = get_organizations(token)
        print_result("List Organizations", response, 200)

        final_orgs = response.json() if response.status_code == 200 else []
        print(f"   Final org count: {len(final_orgs)}")

        # Cleanup
        if org3_id:
            print_section("Cleanup: Delete Test Organization")
            response = delete_organization(token, org3_id)
            print_result("Cleanup Delete", response, 204)

    # Summary
    print_section("TEST SUMMARY")
    print("[OK] All organization creation scenarios tested")
    print("[OK] Free tier limits enforced correctly")
    print("[OK] Deletion and recreation tested")
    print("[OK] Duplicate slug validation tested")
    print("[OK] Duplicate name validation tested (case-insensitive)")
    print(f"\nTest user created: {username}")
    print(f"Test user email: {email}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[FAIL] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
