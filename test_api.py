#!/usr/bin/env python3
"""
Automated API Testing Script for AP2 Expense Agent
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"

class TestResults:
    def __init__(self):
        self.tests = []

    def add(self, name, passed, details=""):
        self.tests.append({
            "name": name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def summary(self):
        total = len(self.tests)
        passed = sum(1 for t in self.tests if t["passed"])
        failed = total - passed

        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed} [PASS]")
        print(f"Failed: {failed} [FAIL]")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        print("="*60 + "\n")

        print("DETAILED RESULTS:")
        print("-"*60)
        for i, test in enumerate(self.tests, 1):
            status = "[PASS]" if test["passed"] else "[FAIL]"
            print(f"{i}. {test['name']}: {status}")
            if test["details"]:
                print(f"   {test['details']}")
        print("-"*60)

results = TestResults()

# Test 1: Health Check
print("Running Test 1: Health Check...")
try:
    response = requests.get(f"{BASE_URL}/health", timeout=5)
    if response.status_code == 200 and response.json().get("status") == "healthy":
        results.add("Health Check", True, f"Status: {response.json()}")
    else:
        results.add("Health Check", False, f"Unexpected response: {response.text}")
except Exception as e:
    results.add("Health Check", False, f"Error: {str(e)}")

# Test 2: Billing Tiers (Unauthenticated)
print("Running Test 2: Billing Tiers...")
try:
    response = requests.get(f"{BASE_URL}/api/billing/tiers", timeout=5)
    if response.status_code == 200:
        tiers = response.json().get("tiers", [])
        results.add("Billing Tiers", True, f"Found {len(tiers)} tiers: {[t['name'] for t in tiers]}")
    else:
        results.add("Billing Tiers", False, f"Status: {response.status_code}")
except Exception as e:
    results.add("Billing Tiers", False, f"Error: {str(e)}")

# Test 3: User Authentication
print("Running Test 3: User Authentication...")
try:
    login_data = {
        "username": "admintest",
        "password": "AgentTest!"
    }
    response = requests.post(f"{API_V1}/auth/login", json=login_data, timeout=5)
    if response.status_code == 200:
        token_data = response.json()
        if "access_token" in token_data:
            results.add("User Authentication", True, f"User: {token_data['user']['username']}, Role: {token_data['user']['role']}")
            ACCESS_TOKEN = token_data["access_token"]
        else:
            results.add("User Authentication", False, "No access token in response")
            ACCESS_TOKEN = None
    else:
        results.add("User Authentication", False, f"Status: {response.status_code}, Response: {response.text}")
        ACCESS_TOKEN = None
except Exception as e:
    results.add("User Authentication", False, f"Error: {str(e)}")
    ACCESS_TOKEN = None

# Tests requiring authentication
if ACCESS_TOKEN:
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

    # Test 4: Get Current User
    print("Running Test 4: Get Current User...")
    try:
        response = requests.get(f"{API_V1}/auth/me", headers=headers, timeout=5)
        if response.status_code == 200:
            user = response.json()
            results.add("Get Current User", True, f"Username: {user['username']}, Email: {user['email']}")
        else:
            results.add("Get Current User", False, f"Status: {response.status_code}")
    except Exception as e:
        results.add("Get Current User", False, f"Error: {str(e)}")

    # Test 5: List All Users (Admin Only)
    print("Running Test 5: List All Users...")
    try:
        response = requests.get(f"{API_V1}/users/", headers=headers, timeout=5)
        if response.status_code == 200:
            users = response.json()
            if isinstance(users, list):
                results.add("List All Users", True, f"Retrieved {len(users)} users")
            elif isinstance(users, dict) and "items" in users:
                results.add("List All Users", True, f"Retrieved {len(users['items'])} users")
            else:
                results.add("List All Users", True, f"Response: {type(users)}")
        else:
            results.add("List All Users", False, f"Status: {response.status_code}")
    except Exception as e:
        results.add("List All Users", False, f"Error: {str(e)}")

    # Test 6: Check API Documentation
    print("Running Test 6: API Documentation...")
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            results.add("API Documentation", True, "API docs accessible")
        else:
            results.add("API Documentation", False, f"Status: {response.status_code}")
    except Exception as e:
        results.add("API Documentation", False, f"Error: {str(e)}")

    # Test 7: Get Billing Subscription
    print("Running Test 7: Get Billing Subscription...")
    try:
        response = requests.get(f"{BASE_URL}/api/billing/subscription", headers=headers, timeout=5)
        if response.status_code == 200:
            subscription = response.json()
            results.add("Get Billing Subscription", True, f"Subscription data retrieved")
        elif response.status_code == 404:
            results.add("Get Billing Subscription", True, "No active subscription (expected for test)")
        else:
            results.add("Get Billing Subscription", False, f"Status: {response.status_code}")
    except Exception as e:
        results.add("Get Billing Subscription", False, f"Error: {str(e)}")
else:
    results.add("Authenticated Tests", False, "Skipped - no access token")

# Test 8: Frontend Accessibility
print("Running Test 8: Frontend Accessibility...")
try:
    response = requests.get("http://localhost:5174", timeout=5)
    if response.status_code == 200:
        results.add("Frontend Accessibility", True, f"Frontend loaded successfully")
    else:
        results.add("Frontend Accessibility", False, f"Status: {response.status_code}")
except Exception as e:
    results.add("Frontend Accessibility", False, f"Error: {str(e)}")

# Print summary
results.summary()
