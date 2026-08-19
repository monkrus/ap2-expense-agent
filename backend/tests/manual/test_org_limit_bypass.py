"""
Test script to verify organization limit bypass vulnerability

This script tests if free tier users can create more than 1 organization
by directly calling the API, bypassing frontend validation.

Expected behavior: Backend should reject with 402 Payment Required after 1 org
Actual behavior: ??? (testing)
"""

import requests
import time

# Configuration
BASE_URL = "http://localhost:8000/api/v1"

def test_organization_limit_bypass():
    """Test if free tier users can bypass organization limit"""

    print("=" * 70)
    print("TESTING: Organization Limit Bypass Vulnerability")
    print("=" * 70)

    # Step 1: Register a new user
    print("\n[Step 1] Registering new test user...")
    username = f"limittest_{int(time.time())}"
    register_data = {
        "username": username,
        "email": f"{username}@test.com",
        "password": "TestPass123!",
        "full_name": "Limit Test User",
        "role": "employee"
    }

    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
        if response.status_code == 201:
            print(f"[OK] User registered: {username}")
            user_data = response.json()
        else:
            print(f"[FAIL] Registration failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return
    except Exception as e:
        print(f"[ERROR] Registration error: {e}")
        return

    # Step 2: Login
    print("\n[Step 2] Logging in...")
    login_data = {
        "username": username,
        "password": "TestPass123!"
    }

    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        if response.status_code == 200:
            print(f"[OK] Login successful")
            login_response = response.json()
            access_token = login_response["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}
        else:
            print(f"[FAIL] Login failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return
    except Exception as e:
        print(f"[ERROR] Login error: {e}")
        return

    # Step 3: Check user's subscription tier
    print("\n[Step 3] Checking user tier...")
    # Note: Free tier users have no subscription initially

    # Step 4: Create first organization
    print("\n[Step 4] Creating FIRST organization...")
    org1_data = {
        "name": f"Test Org 1 {int(time.time())}",
        "slug": f"test-org-1-{int(time.time())}",
        "description": "First test organization",
        "currency": "USD",
        "timezone": "UTC"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/organizations",
            json=org1_data,
            headers=headers
        )
        if response.status_code == 201:
            print(f"[OK] First organization created successfully")
            org1 = response.json()
            print(f"  Organization ID: {org1.get('id')}")
            print(f"  Name: {org1.get('name')}")
        else:
            print(f"[FAIL] First org creation failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return
    except Exception as e:
        print(f"[ERROR] Error creating first org: {e}")
        return

    # Step 5: Attempt to create SECOND organization (should fail for free tier)
    print("\n[Step 5] Creating SECOND organization (testing limit)...")
    org2_data = {
        "name": f"Test Org 2 {int(time.time())}",
        "slug": f"test-org-2-{int(time.time())}",
        "description": "Second test organization - should fail for free tier",
        "currency": "USD",
        "timezone": "UTC"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/organizations",
            json=org2_data,
            headers=headers
        )

        print(f"  Status Code: {response.status_code}")
        print(f"  Response: {response.text}")

        if response.status_code == 201:
            print("\n" + "!" * 70)
            print("WARNING: VULNERABILITY CONFIRMED!")
            print("!" * 70)
            print("Free tier user successfully created 2nd organization!")
            print("Expected: 402 Payment Required")
            print("Actual: 201 Created")
            print("\nThis is a tier limit bypass vulnerability.")
            org2 = response.json()
            print(f"\nSecond organization created:")
            print(f"  ID: {org2.get('id')}")
            print(f"  Name: {org2.get('name')}")
            return True  # Bug confirmed

        elif response.status_code == 402:
            print("\n" + "=" * 70)
            print("[OK] LIMIT ENFORCED CORRECTLY")
            print("=" * 70)
            print("Backend correctly rejected 2nd organization with 402")
            error_data = response.json()
            print(f"Error message: {error_data}")
            return False  # No bug

        else:
            print(f"\n[WARNING] Unexpected response code: {response.status_code}")
            return None

    except Exception as e:
        print(f"[ERROR] Error creating second org: {e}")
        return None

    # Step 6: Attempt to create THIRD organization
    print("\n[Step 6] Creating THIRD organization (further testing)...")
    org3_data = {
        "name": f"Test Org 3 {int(time.time())}",
        "slug": f"test-org-3-{int(time.time())}",
        "description": "Third test organization",
        "currency": "USD",
        "timezone": "UTC"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/organizations",
            json=org3_data,
            headers=headers
        )

        if response.status_code == 201:
            print(f"[WARNING] Third organization also created! Status: {response.status_code}")
            print("  Vulnerability allows unlimited organizations for free tier")
        else:
            print(f"  Third org blocked: {response.status_code}")
    except Exception as e:
        print(f"  Error: {e}")


if __name__ == "__main__":
    test_organization_limit_bypass()

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
