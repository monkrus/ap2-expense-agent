"""Setup test users for AP2 automation testing"""
import requests
import sys

BASE_URL = "http://localhost:8000"

def create_test_user(username, email, password, full_name="Test User"):
    """Create a test user via registration"""
    try:
        payload = {
            "username": username,
            "email": email,
            "password": password,
            "full_name": full_name
        }

        response = requests.post(
            f"{BASE_URL}/api/v1/auth/register",
            json=payload
        )

        if response.status_code in [200, 201]:
            print(f"[+] Created user: {username} ({email})")
            return True
        elif response.status_code == 400:
            error_msg = response.json().get("detail", response.text)
            if "already exists" in error_msg.lower():
                print(f"[+] User already exists: {username}")

                # Verify login works
                login_response = requests.post(
                    f"{BASE_URL}/api/v1/auth/login",
                    json={"username": username, "password": password}
                )
                if login_response.status_code == 200:
                    print(f"    [+] Login verified for {username}")
                    return True
                else:
                    print(f"    [-] Login failed for {username}: {login_response.status_code}")
                    return False
            else:
                print(f"[-] Failed to create {username}: {error_msg}")
                return False
        else:
            print(f"[-] Failed to create {username}: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"[-] Error creating {username}: {e}")
        return False

def main():
    print("="*70)
    print("AP2 AUTOMATION TEST - USER SETUP")
    print("="*70)
    print()

    # Check backend is running
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=5)
        if health.status_code == 200:
            print(f"[+] Backend is running: {BASE_URL}")
        else:
            print(f"[-] Backend returned: {health.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"[-] Backend is not accessible: {e}")
        sys.exit(1)

    print()
    print("Creating test users...")
    print()

    # Create test users
    users = [
        ("user1", "sergeisqa@gmail.com", "Passowrd123!", "Test User 1"),
        ("adminfree", "sergeigodev@gmail.com", "Passowrd123!", "Admin Free"),
        ("employee1", "employee1@test.com", "Password123!", "Employee One"),
        ("employee2", "employee2@test.com", "Password123!", "Employee Two"),
    ]

    success_count = 0
    for username, email, password, full_name in users:
        if create_test_user(username, email, password, full_name):
            success_count += 1
        print()

    print("="*70)
    print(f"Setup Complete: {success_count}/{len(users)} users ready")
    print("="*70)
    print()
    print("Test Credentials:")
    print("  user1       : Passowrd123!")
    print("  adminfree   : Passowrd123!")
    print("  employee1   : Password123!")
    print("  employee2   : Password123!")
    print()

if __name__ == "__main__":
    main()
