"""
Test script to verify duplicate expense submission prevention
"""
import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

import requests
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/v1"

print("=" * 70)
print("TESTING DUPLICATE EXPENSE SUBMISSION PREVENTION")
print("=" * 70)
print()

# Login as user1
print("1. Logging in as user1...")
login_response = requests.post(
    f"{API_URL}/auth/login",
    json={
        "username": "user1",
        "password": "Passowrd123!"
    }
)

if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.status_code}")
    print(login_response.text)
    exit(1)

token = login_response.json()["access_token"]
print("✅ Logged in successfully")
print()

# Get organization ID
me_response = requests.get(
    f"{API_URL}/auth/me",
    headers={"Authorization": f"Bearer {token}"}
)
user_data = me_response.json()
print(f"User: {user_data['username']}")

# Get organization
orgs_response = requests.get(
    f"{API_URL}/organizations",
    headers={"Authorization": f"Bearer {token}"}
)
org_id = orgs_response.json()[0]["id"]
print(f"Organization ID: {org_id}")
print()

# Test expense data
expense_data = {
    "amount": 75.50,
    "vendor": "Test Vendor",
    "category": "OFFICE_SUPPLIES",
    "description": "Duplicate prevention test expense",
    "date": datetime.utcnow().isoformat()
}

headers = {
    "Authorization": f"Bearer {token}",
    "X-Organization-Id": org_id,
    "Content-Type": "application/json"
}

print("2. Submitting first expense...")
response1 = requests.post(
    f"{API_URL}/expenses",
    json=expense_data,
    headers=headers
)

if response1.status_code == 201:
    print("✅ First expense submitted successfully")
    expense1_id = response1.json()["id"]
    print(f"   Expense ID: {expense1_id}")
else:
    print(f"❌ First expense failed: {response1.status_code}")
    print(response1.text)
    exit(1)

print()
print("3. Attempting immediate duplicate submission (should be blocked)...")
response2 = requests.post(
    f"{API_URL}/expenses",
    json=expense_data,
    headers=headers
)

if response2.status_code == 409:  # Conflict
    print("✅ Duplicate submission blocked successfully!")
    print(f"   Status: {response2.status_code}")
    print(f"   Message: {response2.json().get('detail', 'No message')}")
elif response2.status_code == 201:
    print("❌ FAILURE: Duplicate was NOT blocked - expense was created!")
    print(f"   This should not happen!")
    expense2_id = response2.json()["id"]
    print(f"   Duplicate Expense ID: {expense2_id}")
else:
    print(f"⚠️  Unexpected response: {response2.status_code}")
    print(response2.text)

print()
print("4. Waiting 11 seconds to test time window...")
time.sleep(11)

print("5. Attempting submission after time window (should succeed)...")
response3 = requests.post(
    f"{API_URL}/expenses",
    json=expense_data,
    headers=headers
)

if response3.status_code == 201:
    print("✅ Expense submitted successfully after time window")
    expense3_id = response3.json()["id"]
    print(f"   Expense ID: {expense3_id}")
elif response3.status_code == 409:
    print("⚠️  Still blocked after 11 seconds (might be cached)")
else:
    print(f"❌ Unexpected response: {response3.status_code}")
    print(response3.text)

print()
print("=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print(f"✅ First submission: SUCCESS (ID: {expense1_id if 'expense1_id' in locals() else 'N/A'})")
print(f"{'✅' if response2.status_code == 409 else '❌'} Immediate duplicate: {'BLOCKED' if response2.status_code == 409 else 'NOT BLOCKED'}")
print(f"{'✅' if response3.status_code == 201 else '❌'} After time window: {'SUCCESS' if response3.status_code == 201 else 'FAILED'}")
print()

# Cleanup - let user know
print("Note: Created expenses were left in database for manual review")
print("Run 'python clear_all_data.py' to clean up if needed")
print()
