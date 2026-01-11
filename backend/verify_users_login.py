"""Verify that both users can authenticate via API"""
import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

import requests
import json

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/v1"

print("=" * 70)
print("VERIFYING USER LOGIN - API TEST")
print("=" * 70)
print()

# Test credentials
users = [
    {
        "username": "adminfree",
        "password": "Passowrd123!",
        "expected_role": "admin",
        "expected_email": "sergeigodev@gmail.com"
    },
    {
        "username": "user1",
        "password": "Passowrd123!",
        "expected_role": "user",
        "expected_email": "sergeisqa@gmail.com"
    }
]

all_passed = True

for i, user in enumerate(users, 1):
    print(f"{i}. Testing login for: {user['username']}")
    print("-" * 70)

    try:
        # Attempt login
        response = requests.post(
            f"{API_URL}/auth/login",
            json={
                "username": user["username"],
                "password": user["password"]
            },
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Login successful!")
            print(f"   Status Code: {response.status_code}")

            # Check if we got a token
            if "access_token" in data:
                print(f"   ✅ Access token received")
                print(f"   Token type: {data.get('token_type', 'N/A')}")

                # Try to get user info with the token
                me_response = requests.get(
                    f"{API_URL}/auth/me",
                    headers={"Authorization": f"Bearer {data['access_token']}"}
                )

                if me_response.status_code == 200:
                    user_info = me_response.json()
                    print(f"   ✅ User info retrieved")
                    print(f"   Username: {user_info.get('username', 'N/A')}")
                    print(f"   Email: {user_info.get('email', 'N/A')}")
                    print(f"   Role: {user_info.get('role', 'N/A')}")
                    print(f"   Is Active: {user_info.get('is_active', 'N/A')}")

                    # Verify expected values
                    if user_info.get('email') == user['expected_email']:
                        print(f"   ✅ Email matches expected: {user['expected_email']}")
                    else:
                        print(f"   ❌ Email mismatch! Expected: {user['expected_email']}, Got: {user_info.get('email')}")
                        all_passed = False

                    if user_info.get('role') == user['expected_role']:
                        print(f"   ✅ Role matches expected: {user['expected_role']}")
                    else:
                        print(f"   ❌ Role mismatch! Expected: {user['expected_role']}, Got: {user_info.get('role')}")
                        all_passed = False
                else:
                    print(f"   ❌ Failed to get user info: {me_response.status_code}")
                    print(f"   Response: {me_response.text}")
                    all_passed = False
            else:
                print(f"   ❌ No access token in response")
                print(f"   Response: {json.dumps(data, indent=2)}")
                all_passed = False
        else:
            print(f"   ❌ Login failed!")
            print(f"   Status Code: {response.status_code}")
            print(f"   Response: {response.text}")
            all_passed = False

    except requests.exceptions.ConnectionError:
        print(f"   ❌ Connection Error - Is the backend running on {BASE_URL}?")
        all_passed = False
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        all_passed = False

    print()

print("=" * 70)
if all_passed:
    print("✅ ALL TESTS PASSED - Both users can login successfully!")
else:
    print("❌ SOME TESTS FAILED - Please review the output above")
print("=" * 70)
print()
print("Next steps:")
print("  1. Open browser: http://localhost:5173")
print("  2. Login with: adminfree / Passowrd123!")
print("  3. Or login with: user1 / Passowrd123!")
print()
