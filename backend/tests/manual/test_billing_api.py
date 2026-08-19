"""
Quick test to check what the billing API is returning
"""

import requests
import json

# Get your token from browser localStorage (open DevTools -> Console -> type: localStorage.getItem('access_token'))
# Paste it here:
TOKEN = input("Paste your access_token from browser (or press Enter to skip): ").strip()

if not TOKEN:
    print("\n❌ No token provided. To get your token:")
    print("1. Open browser DevTools (F12)")
    print("2. Go to Console tab")
    print("3. Type: localStorage.getItem('access_token')")
    print("4. Copy the token (without quotes)")
    print("5. Run this script again and paste it\n")
    exit(1)

headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

print("\n🔍 Testing Billing API Endpoints...\n")

# Test subscription endpoint
print("=" * 60)
print("1. Testing /api/billing/org/subscription")
print("=" * 60)
try:
    response = requests.get(
        "http://127.0.0.1:8000/api/billing/org/subscription", headers=headers
    )
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print("\n✅ Response:")
        print(json.dumps(data, indent=2))

        if "limits" in data:
            print("\n📊 Limits Found:")
            for key, value in data["limits"].items():
                print(f"  - {key}: {value}")
        else:
            print("\n❌ NO LIMITS IN RESPONSE!")
    else:
        print(f"❌ Error: {response.text}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("2. Testing /api/billing/org/usage/monthly")
print("=" * 60)
try:
    response = requests.get(
        "http://127.0.0.1:8000/api/billing/org/usage/monthly", headers=headers
    )
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print("\n✅ Response:")
        print(json.dumps(data, indent=2))
    else:
        print(f"❌ Error: {response.text}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("Done!")
print("=" * 60)
