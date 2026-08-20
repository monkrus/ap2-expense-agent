"""
Complete AP2 Auto-Approval Test

This test will:
1. Login as user1
2. Create an Intent Mandate for Amazon OFFICE_SUPPLIES
3. Submit a matching expense
4. Verify it auto-approves via AP2
"""
import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/v1"
AP2_URL = f"{BASE_URL}/api/ap2"

print("=" * 70)
print("AP2 AUTO-APPROVAL TEST")
print("=" * 70)
print()

# Step 1: Login
print("Step 1: Logging in as user1...")
print("-" * 70)
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

# Get user info
me_response = requests.get(
    f"{API_URL}/auth/me",
    headers={"Authorization": f"Bearer {token}"}
)
user_data = me_response.json()
print(f"   User: {user_data['username']} ({user_data['email']})")
print(f"   User ID: {user_data['id']}")

# Get organization
orgs_response = requests.get(
    f"{API_URL}/organizations",
    headers={"Authorization": f"Bearer {token}"}
)
org_data = orgs_response.json()[0]
org_id = org_data["id"]
print(f"   Organization: {org_data['name']}")
print(f"   Org ID: {org_id}")
print()

# Step 2: Create Intent Mandate
print("Step 2: Creating Intent Mandate...")
print("-" * 70)

mandate_constraints = {
    "merchant": "Amazon",  # Will match "Amazon" or "amazon"
    "category": "OFFICE_SUPPLIES",  # Will match this category
    "max_amount": 200.00,  # Per-expense limit
    "monthly_limit": 1000.00  # Monthly spending limit
}

print("Intent Mandate Constraints:")
print(json.dumps(mandate_constraints, indent=2))
print()

intent_mandate_response = requests.post(
    f"{AP2_URL}/intent-mandate",
    json={
        "constraints": mandate_constraints,
        "expiration_hours": 720  # 30 days
    },
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
)

if intent_mandate_response.status_code not in [200, 201]:
    print(f"❌ Failed to create Intent Mandate: {intent_mandate_response.status_code}")
    print(intent_mandate_response.text)
    exit(1)

intent_mandate = intent_mandate_response.json()
print("✅ Intent Mandate created successfully!")
print(f"   Mandate ID: {intent_mandate.get('intent_mandate_id') or intent_mandate.get('id')}")
print(f"   Status: {intent_mandate.get('status')}")
print(f"   Expires: {intent_mandate.get('expiration', 'N/A')}")
print()

# Step 3: Submit matching expense
print("Step 3: Submitting matching expense...")
print("-" * 70)

expense_data = {
    "amount": 75.50,
    "vendor": "Amazon",  # Matches intent mandate
    "category": "OFFICE_SUPPLIES",  # Matches intent mandate
    "description": "Wireless keyboard and mouse - AP2 test",
    "date": datetime.utcnow().isoformat()
}

print("Expense details:")
print(f"   Amount: ${expense_data['amount']}")
print(f"   Vendor: {expense_data['vendor']}")
print(f"   Category: {expense_data['category']}")
print(f"   Description: {expense_data['description']}")
print()

expense_response = requests.post(
    f"{API_URL}/expenses",
    json=expense_data,
    headers={
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": org_id,
        "Content-Type": "application/json"
    }
)

if expense_response.status_code != 201:
    print(f"❌ Failed to submit expense: {expense_response.status_code}")
    print(expense_response.text)
    exit(1)

expense = expense_response.json()
print("✅ Expense submitted successfully!")
print(f"   Expense ID: {expense['id']}")
print()

# Step 4: Verify auto-approval
print("Step 4: Verifying AP2 auto-approval...")
print("-" * 70)

# Check expense details
if expense.get('auto_approved'):
    print("✅ EXPENSE WAS AUTO-APPROVED! 🎉")
    print()
    print("   Auto-approval Details:")
    print(f"   • Status: {expense.get('status', 'N/A')}")
    print(f"   • Auto-approved: {expense.get('auto_approved')}")
    print(f"   • Auto-approved via: {expense.get('auto_approved_via', 'N/A')}")
    if expense.get('intent_mandate_id'):
        print(f"   • Intent Mandate ID: {expense.get('intent_mandate_id')}")
        print(f"   • Matches our mandate: {expense.get('intent_mandate_id') == intent_mandate['id']}")
    print()
    print(f"   Message: {expense.get('message', 'N/A')}")

    # Verify it's the correct mandate
    mandate_id = intent_mandate.get('intent_mandate_id') or intent_mandate.get('id')
    if expense.get('intent_mandate_id') == mandate_id:
        print()
        print("✅ VERIFIED: Expense was auto-approved via our Intent Mandate!")
    else:
        print()
        print("⚠️  WARNING: Expense was auto-approved but not via our mandate")
        print(f"   Expected mandate: {mandate_id}")
        print(f"   Got mandate: {expense.get('intent_mandate_id')}")
else:
    print("❌ EXPENSE WAS NOT AUTO-APPROVED")
    print()
    print("   Expense Details:")
    print(f"   • Status: {expense.get('status', 'N/A')}")
    print(f"   • Auto-approved: {expense.get('auto_approved', False)}")
    print(f"   • Message: {expense.get('message', 'N/A')}")
    print()
    print("   Possible reasons:")
    print("   - Intent Mandate expired")
    print("   - Expense doesn't match constraints")
    print("   - Monthly limit exceeded")
    print("   - Backend AP2 service not configured")

print()
print("=" * 70)
print("TEST COMPLETE!")
print("=" * 70)
print()

# Summary
mandate_id = intent_mandate.get('intent_mandate_id') or intent_mandate.get('id')
print("SUMMARY:")
print(f"  ✅ Intent Mandate created: {mandate_id}")
print(f"  ✅ Expense submitted: {expense['id']}")
if expense.get('auto_approved'):
    print(f"  ✅ Auto-approved: YES via {expense.get('auto_approved_via', 'unknown')}")
else:
    print(f"  ❌ Auto-approved: NO (status: {expense.get('status')})")

print()
print("Next steps:")
print("  1. Check the expense in the UI: http://localhost:5173")
print("  2. Look for the '✨ AI Agent' badge on the expense")
print("  3. View Intent Mandate details (if UI available)")
print()
