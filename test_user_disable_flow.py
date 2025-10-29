"""
Test script to verify user disable/suspend functionality
Tests the complete flow of disabling a user and authentication checks
"""
import requests
import json
import time
import sys
import io

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_BASE_URL = "http://localhost:8000"

def test_user_disable_flow():
    """Test the complete user disable flow"""

    print("=" * 70)
    print("TESTING USER DISABLE FLOW")
    print("=" * 70)

    # Step 1: Login as admin
    print("\n[1] Logging in as admin...")
    admin_login = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={"username": "admintest", "password": "AgentTest!"}
    )

    if admin_login.status_code != 200:
        print(f"   ❌ Admin login failed: {admin_login.status_code}")
        print(f"   Response: {admin_login.text}")
        return False

    admin_data = admin_login.json()
    admin_token = admin_data["access_token"]
    print(f"   ✅ Admin logged in successfully")
    print(f"   Admin Token: {admin_token[:30]}...")

    # Step 2: Use existing employee test user (emptest2)
    print("\n[2] Using existing test employee user (emptest2)...")
    test_username = "emptest2"
    test_password = "AgentTest!"

    # Step 2.5: Get list of users to find our test user first
    print("\n[2.5] Getting user details...")
    users_list = requests.get(
        f"{API_BASE_URL}/api/v1/admin/users?search={test_username}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    if users_list.status_code != 200:
        print(f"   ❌ Failed to get users: {users_list.status_code}")
        return False

    users = users_list.json()["users"]
    if users:
        test_user = users[0]
        user_id = test_user['id']
        print(f"   ✅ Found existing test user: {test_user['username']}")
        print(f"   User ID: {user_id}")
        print(f"   Current status: {'Active' if test_user['is_active'] else 'Suspended'}")

        # If user is suspended, activate them first
        if not test_user['is_active']:
            print(f"   → User is suspended, activating first...")
            activate_response = requests.post(
                f"{API_BASE_URL}/api/v1/admin/users/{user_id}/activate",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            if activate_response.status_code == 200:
                print(f"   ✅ User activated")
            else:
                print(f"   ⚠️  Failed to activate: {activate_response.status_code}")
    else:
        print(f"   ❌ Test user not found")
        return False

    # Step 3: Login as test user
    print("\n[3] Logging in as test user (before suspension)...")
    user_login = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={"username": test_username, "password": test_password}
    )

    if user_login.status_code != 200:
        print(f"   ❌ Test user login failed: {user_login.status_code}")
        print(f"   Response: {user_login.text}")
        print(f"   Note: This may mean the user is still suspended or doesn't exist")
        if user_id is None:
            return False
        # Continue with existing user_id if we found it
        user_token = None
    else:
        user_data = user_login.json()
        user_token = user_data["access_token"]
        user_id = user_data["user"]["id"]
        print(f"   ✅ Test user logged in successfully")
        print(f"   User ID: {user_id}")
        print(f"   User Token: {user_token[:30]}...")

    # Step 4: Test user can access protected endpoint (before suspension)
    if user_token:
        print("\n[4] Testing access to protected endpoint (before suspension)...")
        expenses_before = requests.get(
            f"{API_BASE_URL}/api/v1/expenses",
            headers={"Authorization": f"Bearer {user_token}"}
        )

        if expenses_before.status_code == 200:
            print(f"   ✅ User can access protected endpoint (as expected)")
        else:
            print(f"   ⚠️  Unexpected response: {expenses_before.status_code}")
    else:
        print("\n[4] Skipping protected endpoint test (no user token)")

    # Step 5: Verify current user status
    print("\n[5] Verifying current user status...")
    user_details = requests.get(
        f"{API_BASE_URL}/api/v1/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    if user_details.status_code != 200:
        print(f"   ❌ Failed to get user details: {user_details.status_code}")
        return False

    user_info = user_details.json()
    print(f"   ✅ User status: {'Active' if user_info['is_active'] else 'Suspended'}")

    # Step 6: Admin suspends the test user
    print("\n[6] Admin suspending test user...")
    suspend_response = requests.post(
        f"{API_BASE_URL}/api/v1/admin/users/{user_id}/suspend",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"reason": "Testing user disable flow"}
    )

    if suspend_response.status_code != 200:
        print(f"   ❌ Failed to suspend user: {suspend_response.status_code}")
        print(f"   Response: {suspend_response.text}")
        return False

    suspend_data = suspend_response.json()
    print(f"   ✅ User suspended successfully")
    print(f"   Response: {suspend_data}")

    # Step 7: Verify user is marked as inactive in database
    print("\n[7] Verifying user status in database...")
    user_details = requests.get(
        f"{API_BASE_URL}/api/v1/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    if user_details.status_code != 200:
        print(f"   ❌ Failed to get user details: {user_details.status_code}")
        return False

    user_info = user_details.json()
    if not user_info["is_active"]:
        print(f"   ✅ User is_active = False (correctly suspended)")
    else:
        print(f"   ❌ User is_active = True (NOT suspended - BUG!)")
        return False

    # Step 8: Try to access protected endpoint with old token
    if user_token:
        print("\n[8] Testing access with EXISTING token (after suspension)...")
        print("   NOTE: This tests if existing sessions/tokens are still valid")
        expenses_after = requests.get(
            f"{API_BASE_URL}/api/v1/expenses",
            headers={"Authorization": f"Bearer {user_token}"}
        )

        if expenses_after.status_code == 403:
            print(f"   ✅ Access denied with existing token (status: 403)")
            print(f"   Message: {expenses_after.json().get('detail', 'N/A')}")
        elif expenses_after.status_code == 401:
            print(f"   ✅ Access denied with existing token (status: 401)")
            print(f"   Message: {expenses_after.json().get('detail', 'N/A')}")
        else:
            print(f"   ⚠️  WARNING: User can still access with old token!")
            print(f"   Status: {expenses_after.status_code}")
            print(f"   This means existing sessions are NOT invalidated!")
            print(f"   POTENTIAL SECURITY ISSUE!")
    else:
        print("\n[8] Skipping existing token test (no token available)")

    # Step 9: Try to login as suspended user (new login attempt)
    print("\n[9] Attempting NEW login as suspended user...")
    suspended_login = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={"username": test_username, "password": test_password}
    )

    if suspended_login.status_code == 403:
        print(f"   ✅ Login blocked for suspended user (status: 403)")
        print(f"   Message: {suspended_login.json().get('detail', 'N/A')}")
    else:
        print(f"   ❌ Suspended user was able to login!")
        print(f"   Status: {suspended_login.status_code}")
        print(f"   Response: {suspended_login.text}")
        return False

    # Step 10: Admin reactivates the user
    print("\n[10] Admin reactivating test user...")
    activate_response = requests.post(
        f"{API_BASE_URL}/api/v1/admin/users/{user_id}/activate",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    if activate_response.status_code != 200:
        print(f"   ❌ Failed to activate user: {activate_response.status_code}")
        print(f"   Response: {activate_response.text}")
        return False

    activate_data = activate_response.json()
    print(f"   ✅ User reactivated successfully")
    print(f"   Response: {activate_data}")

    # Step 11: Try to login again after reactivation
    print("\n[11] Attempting login after reactivation...")
    reactivated_login = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={"username": test_username, "password": test_password}
    )

    if reactivated_login.status_code == 200:
        print(f"   ✅ Login successful after reactivation")
        new_user_data = reactivated_login.json()
        print(f"   New Token: {new_user_data['access_token'][:30]}...")
    else:
        print(f"   ❌ Login failed after reactivation: {reactivated_login.status_code}")
        print(f"   Response: {reactivated_login.text}")
        return False

    # Step 12: Cleanup - Note: we don't delete the default test user
    print("\n[12] Cleanup - skipping deletion of default test user..."
)
    print(f"   ℹ️  Default test users are preserved for future tests")

    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    return True


if __name__ == "__main__":
    try:
        success = test_user_disable_flow()
        if success:
            print("\n✅ All tests passed!")
        else:
            print("\n❌ Some tests failed - review output above")
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
