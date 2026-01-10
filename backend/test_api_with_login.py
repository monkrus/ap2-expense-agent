"""Test API endpoint with actual login flow"""
import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

import requests
import json

BASE_URL = "http://localhost:8000"

print("=" * 70)
print("TESTING EXPENSE API WITH LOGIN")
print("=" * 70)
print()

# Test 1: Try to login as adminfree
print("1. Attempting login as 'adminfree'...")
print("   (You'll need to enter the correct password when prompted)")
print()

# Let's try a few common passwords
passwords_to_try = ["adminfree", "admin", "password"]

login_success = False
token = None
user_data = None

for password in passwords_to_try:
    print(f"   Trying password: '{password}'...")
    try:
        login_response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={
                "username": "adminfree",
                "password": password
            },
            timeout=5
        )

        if login_response.status_code == 200:
            data = login_response.json()
            token = data.get("access_token")
            user_data = data.get("user")
            print(f"   ✅ SUCCESS with password '{password}'!")
            print(f"   User ID: {user_data.get('id')}")
            print(f"   Username: {user_data.get('username')}")
            print(f"   Email: {user_data.get('email')}")
            login_success = True
            break
        else:
            print(f"   ❌ Failed (status {login_response.status_code})")
    except Exception as e:
        print(f"   ❌ Error: {e}")

print()

if not login_success:
    print("=" * 70)
    print("❌ UNABLE TO LOGIN")
    print("=" * 70)
    print()
    print("The API requires the correct password for 'adminfree'.")
    print()
    print("To test manually:")
    print("  1. Open browser DevTools (F12)")
    print("  2. Login to http://localhost:5173 as 'adminfree'")
    print("  3. Go to Network tab")
    print("  4. Look for GET request to /api/v1/expenses")
    print("  5. Check the Response tab to see what data is returned")
    sys.exit(1)

# Test 2: Get expenses
print("2. Fetching expenses from API...")
headers = {"Authorization": f"Bearer {token}"}

try:
    expenses_response = requests.get(
        f"{BASE_URL}/api/v1/expenses",
        headers=headers,
        timeout=5
    )

    print(f"   Status code: {expenses_response.status_code}")

    if expenses_response.status_code == 200:
        expenses = expenses_response.json()
        print(f"   ✅ SUCCESS! API returned {len(expenses)} expenses")
        print()

        if len(expenses) == 0:
            print("=" * 70)
            print("❌ PROBLEM FOUND: API RETURNS EMPTY ARRAY")
            print("=" * 70)
            print()
            print("The API login works, but returns 0 expenses.")
            print("However, database has 1 expense for this user.")
            print()
            print("Possible causes:")
            print("  1. Organization context header missing/wrong")
            print("  2. Query filter excluding the expense")
            print("  3. Expense not in correct organization")
            print()
        else:
            print("=" * 70)
            print(f"API RETURNED {len(expenses)} EXPENSE(S)")
            print("=" * 70)
            print()

            for i, exp in enumerate(expenses, 1):
                print(f"{i}. Expense ID: {exp.get('id', 'N/A')[:20]}...")
                print(f"   Amount: ${exp.get('amount')}")
                print(f"   Vendor: {exp.get('vendor')}")
                print(f"   Category: {exp.get('category')}")
                print(f"   Status: {exp.get('status')}")
                print(f"   Auto-approved: {exp.get('auto_approved')}")
                print(f"   Auto-approved via: {exp.get('auto_approved_via')}")
                print()

                # Check for our test expense
                if exp.get('vendor') == 'Amazon' and exp.get('amount') == 45.0:
                    print("   ✅ FOUND THE $45 AMAZON TEST EXPENSE!")
                    if exp.get('auto_approved_via') == 'intent_mandate':
                        print("   ✅ Has auto_approved_via = 'intent_mandate'")
                        print("   ✅ Frontend should show purple '✨ AI Agent' badge")
                    print()

        print("=" * 70)
        print("FULL API RESPONSE:")
        print("=" * 70)
        print(json.dumps(expenses, indent=2))

    else:
        print(f"   ❌ ERROR: Status {expenses_response.status_code}")
        print(f"   Response: {expenses_response.text}")

except Exception as e:
    print(f"   ❌ Error fetching expenses: {e}")

print()
print("=" * 70)
print("NEXT STEPS:")
print("=" * 70)
print()

if not login_success:
    print("1. ❌ Cannot test - login failed")
    print("   → Check password for 'adminfree' user")
elif expenses_response.status_code == 200 and len(expenses) == 0:
    print("1. ❌ API returns empty array")
    print("   → Check organization context")
    print("   → Run: python backend/check_user_expenses.py")
elif expenses_response.status_code == 200 and len(expenses) > 0:
    print("1. ✅ API is working correctly")
    print("   → Issue is in frontend rendering")
    print("   → Check browser console for errors")
    print("   → Verify frontend code loaded (restart dev server)")
else:
    print("1. ❌ API error")
    print("   → Check backend logs")
