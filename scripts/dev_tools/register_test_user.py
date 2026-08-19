"""
Register a test user via API
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def register_user():
    """Register a new test user"""
    print("Registering test user via API...")

    payload = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "Test123!",
        "full_name": "Test User"
    }

    response = requests.post(
        f"{BASE_URL}/api/v1/auth/register",
        json=payload
    )

    if response.status_code == 200:
        data = response.json()
        print("Test user registered successfully!")
        print(f"   Username: testuser")
        print(f"   Email: test@example.com")
        print(f"   Password: Test123!")
        return True
    else:
        print(f"Registration failed: {response.status_code}")
        print(f"Error: {response.text}")
        return False

if __name__ == "__main__":
    register_user()
