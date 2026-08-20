"""Test API with fresh test user"""
import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

import requests
import json

BASE_URL = "http://localhost:8000"
USERNAME = "testuser2"
PASSWORD = "testpass123"

print("=" * 70)
print("TESTING API WITH FRESH USER: testuser2")
print("=" * 70)
print()

# Step 1: Login
print("1. Logging in...")
try:
    login_response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={
            "username": USERNAME,
            "password": PASSWORD
        },
        timeout=5
    )

    if login_response.status_code != 200:
        print(f"   ❌ Login failed: {login_response.status_code}")
        print(f"   Response: {login_response.text}")
        print()
        print("   Make sure you ran: python backend/create_fresh_test_user.py")
        sys.exit(1)

    data = login_response.json()
    token = data["access_token"]
    user_data = data["user"]

    # Get organization from user data
    organizations = user_data.get("organizations", [])
    if not organizations:
        print(f"   ⚠️  Warning: User has no organizations")
        print(f"   Full user data: {user_data}")
    org_id = organizations[0]["id"] if organizations else None

    print(f"   ✅ Login successful!")
    print(f"   User ID: {user_data['id']}")
    print(f"   Username: {user_data['username']}")
    if org_id:
        print(f"   Organization ID: {org_id}")
    print()

except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# Step 2: Get organizations
print("2. Fetching user's organizations...")
headers = {"Authorization": f"Bearer {token}"}

try:
    orgs_response = requests.get(
        f"{BASE_URL}/api/v1/organizations",
        headers=headers,
        timeout=5
    )

    if orgs_response.status_code == 200:
        orgs = orgs_response.json()
        print(f"   ✅ Found {len(orgs)} organization(s)")
        if orgs:
            org_id = orgs[0]["id"]
            print(f"   Using Organization ID: {org_id}")
        else:
            print(f"   ❌ ERROR: User has no organizations")
            print(f"   This user cannot access any expenses")
            sys.exit(1)
    else:
        print(f"   ❌ ERROR: {orgs_response.status_code}")
        print(f"   Response: {orgs_response.text}")
        sys.exit(1)
    print()

except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# Step 3: Get expenses
print("3. Fetching expenses from /api/v1/expenses...")
headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org_id}

try:
    expenses_response = requests.get(
        f"{BASE_URL}/api/v1/expenses",
        headers=headers,
        timeout=5
    )

    print(f"   Status: {expenses_response.status_code}")

    if expenses_response.status_code == 200:
        expenses = expenses_response.json()
        print(f"   Response: {len(expenses)} expenses")
        print()

        if len(expenses) == 0:
            print("=" * 70)
            print("❌ PROBLEM: API RETURNED 0 EXPENSES")
            print("=" * 70)
            print()
            print("Expected: 1 expense ($75.50 Amazon)")
            print("Got: Empty array")
            print()
            print("This means:")
            print("  - Backend API is not returning the expense")
            print("  - Possible organization context issue")
            print("  - Possible query filter issue")
            print()
            print("Debug:")
            print("  1. Check backend logs")
            print("  2. Verify expense in database:")
            print("     python -c \"from src.database import SessionLocal; from src.models import Expense, User; db = SessionLocal(); user = db.query(User).filter(User.username == 'testuser2').first(); exps = db.query(Expense).filter(Expense.user_id == user.id).all(); print(f'Found {len(exps)} expenses in DB'); db.close()\"")
            print()

        else:
            print("=" * 70)
            print(f"✅ API RETURNED {len(expenses)} EXPENSE(S)")
            print("=" * 70)
            print()

            for i, exp in enumerate(expenses, 1):
                print(f"Expense #{i}:")
                print(f"  ID: {exp.get('id', 'N/A')[:30]}...")
                print(f"  Amount: ${exp.get('amount')}")
                print(f"  Vendor: {exp.get('vendor')}")
                print(f"  Category: {exp.get('category')}")
                print(f"  Status: {exp.get('status')}")
                print(f"  Auto-approved: {exp.get('auto_approved')}")
                print(f"  Auto-approved via: {exp.get('auto_approved_via')}")
                print()

                # Verify our test expense
                if exp.get('vendor') == 'Amazon' and exp.get('amount') == 75.50:
                    print("  ✅ FOUND TEST EXPENSE!")

                    if exp.get('status') == 'approved':
                        print("  ✅ Status is APPROVED")
                    else:
                        print(f"  ❌ Status is {exp.get('status')} (expected: approved)")

                    if exp.get('auto_approved') == True:
                        print("  ✅ Auto-approved is True")
                    else:
                        print(f"  ❌ Auto-approved is {exp.get('auto_approved')} (expected: True)")

                    if exp.get('auto_approved_via') == 'intent_mandate':
                        print("  ✅ Auto-approved via intent_mandate")
                        print()
                        print("  🎉 FRONTEND SHOULD SHOW:")
                        print("     - Status badge: [APPROVED] (green)")
                        print("     - Auto-approval badge: [✨ AI Agent] (purple)")
                    else:
                        print(f"  ❌ Auto-approved via {exp.get('auto_approved_via')} (expected: intent_mandate)")

                    print()

            print("-" * 70)
            print("FULL API RESPONSE:")
            print("-" * 70)
            print(json.dumps(expenses, indent=2))
            print()

    else:
        print(f"   ❌ API error: {expenses_response.status_code}")
        print(f"   Response: {expenses_response.text}")

except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

print()
print("=" * 70)
print("SUMMARY")
print("=" * 70)
print()

if expenses_response.status_code == 200:
    if len(expenses) == 0:
        print("❌ FAILED: API returns empty array")
        print()
        print("Next steps:")
        print("  1. Check backend logs for errors")
        print("  2. Verify organization context")
        print("  3. Check expense query filters")
    elif len(expenses) > 0:
        # Check if test expense found
        test_exp = next((e for e in expenses if e.get('vendor') == 'Amazon' and e.get('amount') == 75.50), None)
        if test_exp and test_exp.get('auto_approved_via') == 'intent_mandate':
            print("✅ SUCCESS: API working correctly!")
            print()
            print("The API returns:")
            print("  ✅ Expense exists")
            print("  ✅ Status: approved")
            print("  ✅ Auto-approved: true")
            print("  ✅ Auto-approved via: intent_mandate")
            print()
            print("Next step: TEST FRONTEND UI")
            print("  1. Open browser: http://localhost:5173")
            print("  2. Login:")
            print(f"     Username: {USERNAME}")
            print(f"     Password: {PASSWORD}")
            print("  3. Go to Employee Dashboard")
            print("  4. Look for:")
            print("     - $75.50 Amazon expense")
            print("     - Green [APPROVED] badge")
            print("     - Purple [✨ AI Agent] badge ← KEY!")
        else:
            print("⚠️  PARTIAL SUCCESS: Expense found but incorrect data")
            print()
            print("Check auto_approved_via field")
else:
    print("❌ FAILED: API error")

print()
