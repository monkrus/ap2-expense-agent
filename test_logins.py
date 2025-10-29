#!/usr/bin/env python
"""Test login for all users"""
import requests
import json

API_URL = "http://localhost:8000/api/v1/auth/login"
PASSWORD = "AgentTest!"

users = [
    {"username": "admintest", "role": "ADMIN"},
    {"username": "testuser", "role": "MANAGER"},
    {"username": "emptest", "role": "EMPLOYEE"},
    {"username": "employee2", "role": "EMPLOYEE"}
]

print("=" * 80)
print("TESTING LOGIN FOR ALL 4 USERS")
print("=" * 80)
print(f"Password for all users: {PASSWORD}")
print()

for user in users:
    username = user["username"]
    role = user["role"]

    try:
        response = requests.post(
            API_URL,
            json={"username": username, "password": PASSWORD},
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            data = response.json()
            if "access_token" in data:
                print(f"[OK] {username:15} ({role:10}) - LOGIN SUCCESS")
            else:
                print(f"[FAIL] {username:15} ({role:10}) - FAILED: {data}")
        else:
            print(f"[FAIL] {username:15} ({role:10}) - HTTP {response.status_code}: {response.text[:100]}")
    except Exception as e:
        print(f"[ERROR] {username:15} ({role:10}) - ERROR: {str(e)}")

print()
print("=" * 80)
print("All users configured with username/password: [username] / AgentTest!")
print("=" * 80)
