#!/usr/bin/env python3
"""
Quick API test script for authentication endpoints
Run this after starting the backend server
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
COLORS = {
    'GREEN': '\033[92m',
    'RED': '\033[91m',
    'YELLOW': '\033[93m',
    'BLUE': '\033[94m',
    'END': '\033[0m'
}

def print_success(msg):
    print(f"{COLORS['GREEN']}✓ {msg}{COLORS['END']}")

def print_error(msg):
    print(f"{COLORS['RED']}✗ {msg}{COLORS['END']}")

def print_info(msg):
    print(f"{COLORS['BLUE']}ℹ {msg}{COLORS['END']}")

def print_section(msg):
    print(f"\n{COLORS['YELLOW']}{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}{COLORS['END']}\n")

def test_health():
    """Test health check endpoint"""
    print_info("Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print_success("Health check passed")
            return True
        else:
            print_error(f"Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Cannot connect to backend: {e}")
        print_info("Make sure backend is running: uvicorn src.api:app --reload")
        return False

def test_register():
    """Test user registration"""
    print_info("Testing user registration...")

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    user_data = {
        "email": f"test{timestamp}@example.com",
        "username": f"testuser{timestamp}",
        "password": "TestPass123!",
        "full_name": "Test User",
        "role": "employee"
    }

    try:
        response = requests.post(f"{BASE_URL}/api/v1/auth/register", json=user_data)
        if response.status_code == 201:
            data = response.json()
            print_success(f"User registered: {data['username']} ({data['email']})")
            print_info(f"  User ID: {data['id']}")
            print_info(f"  Role: {data['role']}")
            return user_data
        else:
            print_error(f"Registration failed: {response.status_code}")
            print_error(f"  {response.json()}")
            return None
    except Exception as e:
        print_error(f"Registration error: {e}")
        return None

def test_login(username, password):
    """Test user login"""
    print_info(f"Testing login for {username}...")

    login_data = {
        "username": username,
        "password": password
    }

    try:
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Login successful for {data['user']['username']}")
            print_info(f"  Access Token: {data['access_token'][:30]}...")
            print_info(f"  Refresh Token: {data['refresh_token'][:30]}...")
            print_info(f"  Expires in: {data['expires_in']} seconds")
            return data['access_token']
        else:
            print_error(f"Login failed: {response.status_code}")
            print_error(f"  {response.json()}")
            return None
    except Exception as e:
        print_error(f"Login error: {e}")
        return None

def test_get_me(token):
    """Test getting current user info"""
    print_info("Testing /auth/me endpoint...")

    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print_success("Got current user info:")
            print_info(f"  Username: {data['username']}")
            print_info(f"  Email: {data['email']}")
            print_info(f"  Role: {data['role']}")
            print_info(f"  2FA Enabled: {data['totp_enabled']}")
            return True
        else:
            print_error(f"Failed to get user info: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False

def test_list_users(token):
    """Test listing users (requires manager/admin)"""
    print_info("Testing user listing (requires manager/admin)...")

    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(f"{BASE_URL}/api/v1/users/", headers=headers)
        if response.status_code == 200:
            users = response.json()
            print_success(f"Retrieved {len(users)} users")
            for user in users[:3]:  # Show first 3
                print_info(f"  - {user['username']} ({user['role']})")
            return True
        elif response.status_code == 403:
            print_error("Access denied (need manager/admin role)")
            return False
        else:
            print_error(f"Failed: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False

def test_2fa_setup(token):
    """Test 2FA setup"""
    print_info("Testing 2FA setup...")

    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.post(f"{BASE_URL}/api/v1/auth/2fa/setup", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print_success("2FA setup successful")
            print_info(f"  Secret: {data['secret']}")
            print_info(f"  Backup codes: {len(data['backup_codes'])} generated")
            print_info(f"  QR Code: {data['qr_code_url'][:50]}...")
            return True
        else:
            print_error(f"2FA setup failed: {response.status_code}")
            error = response.json()
            if "already enabled" in error.get('detail', ''):
                print_info("  2FA already set up for this user")
            return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False

def test_password_reset(email):
    """Test password reset request"""
    print_info(f"Testing password reset for {email}...")

    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/password/reset-request",
            json={"email": email}
        )
        if response.status_code == 200:
            data = response.json()
            print_success("Password reset requested")
            if 'reset_token' in data:
                print_info(f"  Reset token (DEV ONLY): {data['reset_token'][:30]}...")
            return True
        else:
            print_error(f"Failed: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False

def main():
    print_section("AP2 Expense Management - Authentication Test Suite")

    # Test 1: Health check
    if not test_health():
        print_error("\nBackend is not running. Exiting...")
        return 1

    # Test 2: Login with default admin
    print_section("Test 1: Admin Login")
    admin_token = test_login("admin", "Admin123!")

    if admin_token:
        # Test 3: Get current user
        print_section("Test 2: Get Current User Info")
        test_get_me(admin_token)

        # Test 4: List users (admin only)
        print_section("Test 3: List Users (Admin)")
        test_list_users(admin_token)

        # Test 5: 2FA setup
        print_section("Test 4: 2FA Setup")
        test_2fa_setup(admin_token)
    else:
        print_error("\nAdmin login failed. Run setup_auth.py to create admin user")
        print_info("  python backend/setup_auth.py")

    # Test 6: User registration
    print_section("Test 5: User Registration")
    new_user = test_register()

    if new_user:
        # Test 7: Login with new user
        print_section("Test 6: New User Login")
        user_token = test_login(new_user['username'], new_user['password'])

        if user_token:
            # Test 8: Get user info
            print_section("Test 7: New User Info")
            test_get_me(user_token)

            # Test 9: Try to list users (should fail - not admin)
            print_section("Test 8: RBAC Test (Employee can't list users)")
            test_list_users(user_token)

            # Test 10: Password reset
            print_section("Test 9: Password Reset")
            test_password_reset(new_user['email'])

    print_section("Test Suite Completed!")
    print_info("Check the results above for any failures")
    print_info("\nNext steps:")
    print_info("  1. Open http://localhost:8000/docs for interactive API docs")
    print_info("  2. Open http://localhost:5173 for frontend UI")
    print_info("  3. See TEST_AUTHENTICATION.md for detailed testing guide")

    return 0

if __name__ == "__main__":
    import sys
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print_error("\n\nTest interrupted by user")
        sys.exit(1)
