"""Create adminfree user on free tier"""
import requests
import json

API_BASE = "http://localhost:8000/api/v1"

def create_user():
    """Register new user"""

    # Registration data
    data = {
        "username": "adminfree",
        "email": "adminfree@example.com",
        "password": "Testme1!",
        "full_name": "Admin Free Tier"
    }

    # Register user
    print("Registering user: adminfree")
    response = requests.post(f"{API_BASE}/auth/register", json=data)

    if response.status_code == 201:
        print("[SUCCESS] User created successfully!")
        user_data = response.json()
        print(f"User ID: {user_data.get('id')}")
        print(f"Username: {user_data.get('username')}")
        print(f"Email: {user_data.get('email')}")
        print(f"Role: {user_data.get('role', 'N/A')}")

        # Login to get access token
        login_data = {
            "username": "adminfree",
            "password": "Testme1!"
        }

        print("\nLogging in...")
        login_response = requests.post(f"{API_BASE}/auth/login", json=login_data)

        if login_response.status_code == 200:
            token_data = login_response.json()
            print("[SUCCESS] Login successful!")
            print(f"Access Token: {token_data.get('access_token')[:50]}...")

            # Get user details
            headers = {"Authorization": f"Bearer {token_data.get('access_token')}"}
            me_response = requests.get(f"{API_BASE}/users/me", headers=headers)

            if me_response.status_code == 200:
                me_data = me_response.json()
                print("\nUser Details:")
                print(json.dumps(me_data, indent=2))
        else:
            print(f"[ERROR] Login failed: {login_response.status_code}")
            print(login_response.text)

    else:
        print(f"[ERROR] Registration failed: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    create_user()
