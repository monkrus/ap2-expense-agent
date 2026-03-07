#!/usr/bin/env python3
"""Test the Google Cloud Marketplace first-user admin safeguard"""

import requests
import json

print("=" * 60)
print("GOOGLE CLOUD MARKETPLACE - FIRST USER SAFEGUARD TEST")
print("=" * 60)

# Test 1: Register first user (requesting USER role)
print("\n[TEST 1] Registering first user with requested role='user'...")
response1 = requests.post(
    "http://localhost:8000/api/v1/auth/register",
    json={
        "email": "marketplace.buyer@company.com",
        "username": "buyer1",
        "full_name": "Marketplace Buyer",
        "password": "BuyerPass123!",
        "role": "employee"  # Request EMPLOYEE role (should be overridden to ADMIN)
    }
)

print(f"Status: {response1.status_code}")
if response1.status_code == 201:
    user1 = response1.json()
    print(f"Username: {user1['username']}")
    print(f"Email: {user1['email']}")
    print(f"Role: {user1['role']}")

    if user1['role'] == 'admin':
        print("PASS - First user automatically became ADMIN!")
    else:
        print(f"FAIL - Expected 'admin', got '{user1['role']}'")
else:
    print(f"FAIL - Registration failed: {response1.text}")

# Test 2: Register second user (should get requested role)
print("\n[TEST 2] Registering second user with role='employee'...")
response2 = requests.post(
    "http://localhost:8000/api/v1/auth/register",
    json={
        "email": "employee@company.com",
        "username": "employee1",
        "full_name": "First Employee",
        "password": "EmpPass123!",
        "role": "employee"
    }
)

print(f"Status: {response2.status_code}")
if response2.status_code == 201:
    user2 = response2.json()
    print(f"Username: {user2['username']}")
    print(f"Email: {user2['email']}")
    print(f"Role: {user2['role']}")

    if user2['role'] == 'employee':
        print("PASS - Second user got requested EMPLOYEE role")
    else:
        print(f"FAIL - Expected 'employee', got '{user2['role']}'")
else:
    print(f"FAIL - Registration failed: {response2.text}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
