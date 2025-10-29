"""
Test script to verify user disable functionality with live testing
"""
import requests
import sys
import io
import time

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_BASE_URL = "http://localhost:8000"

def test_disable_user_live():
    """Test the complete disable user flow"""

    print("=" * 70)
    print("LIVE USER DISABLE TEST")
    print("=" * 70)

    # Step 1: Login as admin
    print("\n[1] Logging in as admin...")
    admin_login = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={"username": "admintest", "password": "AgentTest!"}
    )

    if admin_login.status_code != 200:
        print(f"   ❌ Admin login failed: {admin_login.status_code}")
        return False

    admin_data = admin_login.json()
    admin_token = admin_data["access_token"]
    print(f"   ✅ Admin logged in successfully")

    # Step 2: Use emptest2 as test subject
    test_username = "emptest2"
    test_password = "AgentTest!"

    print(f"\n[2] Getting user details for {test_username}...")
    users_list = requests.get(
        f"{API_BASE_URL}/api/v1/admin/users?search={test_username}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    if users_list.status_code != 200:
        print(f"   ❌ Failed to get users: {users_list.status_code}")
        return False

    users = users_list.json()["users"]
    if not users:
        print(f"   ❌ User {test_username} not found")
        return False

    test_user = users[0]
    user_id = test_user['id']
    print(f"   ✅ Found user: {test_user['username']}")
    print(f"   User ID: {user_id}")
    print(f"   Current status: {'Active ✅' if test_user['is_active'] else 'Suspended ❌'}")

    # Make sure user is active first
    if not test_user['is_active']:
        print(f"\n   → User is suspended, activating first...")
        activate_response = requests.post(
            f"{API_BASE_URL}/api/v1/admin/users/{user_id}/activate",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if activate_response.status_code == 200:
            print(f"   ✅ User activated")
        else:
            print(f"   ❌ Failed to activate: {activate_response.status_code}")
            return False

    # Step 3: Login as test user and get token
    print(f"\n[3] Logging in as {test_username}...")
    user_login = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={"username": test_username, "password": test_password}
    )

    if user_login.status_code != 200:
        print(f"   ❌ Login failed: {user_login.status_code}")
        return False

    user_data = user_login.json()
    user_token = user_data["access_token"]
    print(f"   ✅ User logged in successfully")
    print(f"   Token: {user_token[:30]}...")

    # Step 4: Verify user can access API before suspension
    print(f"\n[4] Testing API access BEFORE suspension...")
    profile_before = requests.get(
        f"{API_BASE_URL}/api/v1/users/me",
        headers={"Authorization": f"Bearer {user_token}"}
    )

    print(f"   Status: {profile_before.status_code}")
    if profile_before.status_code == 200:
        print(f"   ✅ User can access API (expected)")
    else:
        print(f"   ⚠️  Unexpected status: {profile_before.status_code}")

    # Step 5: Admin suspends the user
    print(f"\n[5] Admin suspending {test_username}...")
    suspend_response = requests.post(
        f"{API_BASE_URL}/api/v1/admin/users/{user_id}/suspend",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"reason": "Live testing"}
    )

    if suspend_response.status_code != 200:
        print(f"   ❌ Failed to suspend: {suspend_response.status_code}")
        print(f"   Response: {suspend_response.text}")
        return False

    suspend_data = suspend_response.json()
    print(f"   ✅ User suspended successfully")
    print(f"   Sessions revoked: {suspend_data.get('sessions_revoked', 'N/A')}")
    print(f"   Tokens revoked: {suspend_data.get('tokens_revoked', 'N/A')}")

    # Step 6: Verify user is marked as inactive
    print(f"\n[6] Verifying user status in database...")
    user_details = requests.get(
        f"{API_BASE_URL}/api/v1/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    if user_details.status_code != 200:
        print(f"   ❌ Failed to get user details: {user_details.status_code}")
        return False

    user_info = user_details.json()
    if not user_info["is_active"]:
        print(f"   ✅ Database: is_active = False (correctly suspended)")
    else:
        print(f"   ❌ Database: is_active = True (NOT suspended - BUG!)")
        return False

    # Step 7: Try to use the OLD TOKEN immediately after suspension
    print(f"\n[7] Testing API access with OLD TOKEN (immediately after suspension)...")
    print(f"   This is the critical test - should return 403!")

    profile_after = requests.get(
        f"{API_BASE_URL}/api/v1/users/me",
        headers={"Authorization": f"Bearer {user_token}"}
    )

    print(f"   Status: {profile_after.status_code}")

    if profile_after.status_code == 403:
        try:
            error_data = profile_after.json()
            print(f"   ✅ Access DENIED with 403 (correct!)")
            print(f"   Error message: {error_data.get('detail', 'N/A')}")
        except:
            print(f"   ✅ Access DENIED with 403 (correct!)")
    elif profile_after.status_code == 401:
        print(f"   ✅ Access DENIED with 401 (acceptable)")
    elif profile_after.status_code == 200:
        print(f"   ❌❌❌ CRITICAL BUG: User CAN STILL ACCESS API!")
        print(f"   This means the user is NOT being logged out!")
        print(f"   Frontend is NOT detecting the suspension!")
    else:
        print(f"   ⚠️  Unexpected status: {profile_after.status_code}")

    # Step 8: Try to make a NEW login with suspended account
    print(f"\n[8] Attempting NEW login as suspended user...")
    suspended_login = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={"username": test_username, "password": test_password}
    )

    print(f"   Status: {suspended_login.status_code}")

    if suspended_login.status_code == 403:
        try:
            error_data = suspended_login.json()
            print(f"   ✅ Login BLOCKED with 403 (correct!)")
            print(f"   Error message: {error_data.get('detail', 'N/A')}")
        except:
            print(f"   ✅ Login BLOCKED with 403 (correct!)")
    elif suspended_login.status_code == 200:
        print(f"   ❌ CRITICAL BUG: Suspended user can still login!")
    else:
        print(f"   Status: {suspended_login.status_code}")
        print(f"   Response: {suspended_login.text}")

    # Step 9: Reactivate for cleanup
    print(f"\n[9] Reactivating user for cleanup...")
    activate_response = requests.post(
        f"{API_BASE_URL}/api/v1/admin/users/{user_id}/activate",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    if activate_response.status_code == 200:
        print(f"   ✅ User reactivated")
    else:
        print(f"   ⚠️  Failed to reactivate: {activate_response.status_code}")

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print("\nSUMMARY:")
    print("• User suspension: ✅ Working (is_active = False)")
    print("• New logins blocked: Check step [8] above")
    print("• Existing sessions blocked: Check step [7] above")
    print("\nIf step [7] shows status 200, the frontend is NOT detecting")
    print("suspended users and they can continue using the app!")

    return True

if __name__ == "__main__":
    try:
        test_disable_user_live()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
