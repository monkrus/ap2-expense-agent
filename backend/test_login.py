"""Simple admin login check against the running API."""

import json
import requests


def main():
    resp = requests.post(
        "http://localhost:8000/api/v1/auth/login",
        json={"username": "adminfree", "password": "Testme1!"},
    )
    print(f"Admin Login Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print("[OK] Login successful!")
        print(f"  User: {data.get('user', {}).get('username')}")
        print(f"  Role: {data.get('user', {}).get('role')}")
        print(f"  Token: {data.get('access_token')[:50]}...")
    else:
        try:
            error_payload = resp.json()
        except json.JSONDecodeError:
            error_payload = resp.text
        print(f"[FAIL] Login failed: {error_payload}")


if __name__ == "__main__":
    main()
