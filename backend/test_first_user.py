#!/usr/bin/env python3
"""Test the first-user admin safeguard"""

import requests
import json

# Test registering the first user
print("Testing first-user admin safeguard...")
print("-" * 50)

response = requests.post(
    "http://localhost:8000/api/v1/auth/register",
    json={
        "email": "firstuser@company.com",
        "username": "firstadmin",
        "full_name": "First Admin",
        "password": "AdminPass123!",
        "role": "user"  # Request USER role
    }
)

print(f"Status Code: {response.status_code}")
print(f"Response:")
print(json.dumps(response.json(), indent=2))

if response.status_code == 201:
    user_data = response.json()
    role = user_data.get("role")
    print(f"\n✅ User created successfully!")
    print(f"Role: {role}")

    if role == "admin":
        print("\n🎉 SAFEGUARD WORKING: First user automatically became ADMIN!")
    else:
        print(f"\n⚠️  SAFEGUARD FAILED: User has role '{role}', expected 'admin'")
else:
    print(f"\n❌ Registration failed: {response.json()}")
