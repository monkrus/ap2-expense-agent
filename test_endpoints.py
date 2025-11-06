#!/usr/bin/env python3
"""Test critical API endpoints"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_endpoints():
    print("=" * 80)
    print("AP2 EXPENSE AGENT - API ENDPOINT TESTS")
    print("=" * 80)

    # Test 1: Health check
    print("\n1. Testing Health Endpoint")
    try:
        r = requests.get(f"{BASE_URL}/health")
        print(f"   Status: {r.status_code}")
        print(f"   Response: {r.json()}")
    except Exception as e:
        print(f"   ERROR: {e}")

    # Test 2: Login
    print("\n2. Testing Login Endpoint")
    try:
        r = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "username": "admintest",
            "password": "AgentTest!"
        })
        print(f"   Status: {r.status_code}")
        data = r.json()
        print(f"   User: {data.get('user', {}).get('username')}")
        print(f"   Role: {data.get('user', {}).get('role')}")
        token = data.get('access_token')
        print(f"   Token: {token[:50]}...")
    except Exception as e:
        print(f"   ERROR: {e}")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # Test 3: Get current user
    print("\n3. Testing GET /api/v1/auth/me")
    try:
        r = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)
        print(f"   Status: {r.status_code}")
        data = r.json()
        print(f"   Username: {data.get('username')}")
        print(f"   Email: {data.get('email')}")
    except Exception as e:
        print(f"   ERROR: {e}")

    # Test 4: List users
    print("\n4. Testing GET /api/v1/users")
    try:
        r = requests.get(f"{BASE_URL}/api/v1/users", headers=headers)
        print(f"   Status: {r.status_code}")
        data = r.json()
        if isinstance(data, list):
            print(f"   Users found: {len(data)}")
        else:
            print(f"   Response: {data}")
    except Exception as e:
        print(f"   ERROR: {e}")

    # Test 5: Get billing tiers
    print("\n5. Testing GET /api/billing/org/tiers")
    try:
        r = requests.get(f"{BASE_URL}/api/billing/org/tiers")
        print(f"   Status: {r.status_code}")
        data = r.json()
        if isinstance(data, list):
            print(f"   Tiers found: {len(data)}")
            for tier in data:
                print(f"   - {tier.get('tier_name')}: ${tier.get('base_price_monthly')}/month")
        else:
            print(f"   Response: {data}")
    except Exception as e:
        print(f"   ERROR: {e}")

    # Test 6: OpenAPI docs
    print("\n6. Testing GET /docs (OpenAPI)")
    try:
        r = requests.get(f"{BASE_URL}/docs")
        print(f"   Status: {r.status_code}")
        print(f"   Content-Type: {r.headers.get('content-type')}")
    except Exception as e:
        print(f"   ERROR: {e}")

    print("\n" + "=" * 80)
    print("API TESTS COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    test_endpoints()
