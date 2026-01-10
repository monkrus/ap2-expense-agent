"""
Live Test: Submit actual expense and verify AP2 auto-approval
Tests the complete end-to-end flow with real API calls
"""
import asyncio
import requests
import json
from datetime import datetime, date

BASE_URL = "http://localhost:8000"

async def test_live_autoapproval():
    print("=" * 70)
    print("LIVE AP2 AUTO-APPROVAL TEST")
    print("=" * 70)
    print()

    # =====================================================================
    # STEP 1: Login and get token
    # =====================================================================
    print("STEP 1: Authenticating...")
    print("-" * 70)

    login_response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={
            "username": "adminfree",
            "password": "adminfree"
        }
    )

    if login_response.status_code != 200:
        print(f"[ERROR] Login failed: {login_response.status_code}")
        print(login_response.text)
        return

    token = login_response.json()["access_token"]
    user_id = login_response.json()["user"]["id"]
    print(f"✓ Authenticated as: {login_response.json()['user']['username']}")
    print(f"  User ID: {user_id}")
    print()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # =====================================================================
    # STEP 2: Get user's organizations
    # =====================================================================
    print("STEP 2: Getting organizations...")
    print("-" * 70)

    orgs_response = requests.get(
        f"{BASE_URL}/api/v1/organizations/user-organizations",
        headers=headers
    )

    if orgs_response.status_code != 200 or not orgs_response.json():
        print(f"[ERROR] No organizations found")
        return

    org = orgs_response.json()[0]
    org_id = org["id"]
    print(f"✓ Using organization: {org['name']}")
    print(f"  Org ID: {org_id}")
    print()

    # Update headers with org context
    headers["X-Organization-Id"] = org_id

    # =====================================================================
    # STEP 3: Check existing Intent Mandates
    # =====================================================================
    print("STEP 3: Checking existing Intent Mandates...")
    print("-" * 70)

    mandates_response = requests.get(
        f"{BASE_URL}/api/ap2/user/mandates?limit=50",
        headers=headers
    )

    if mandates_response.status_code == 200:
        mandates = mandates_response.json().get("mandates", [])
        intent_mandates = [m for m in mandates if m.get("type") == "intent"]
        print(f"✓ Found {len(intent_mandates)} Intent Mandates")

        for mandate in intent_mandates[:3]:
            print(f"  - {mandate['id'][:20]}... (status: {mandate['status']})")
    else:
        print(f"[WARNING] Could not fetch mandates: {mandates_response.status_code}")
    print()

    # =====================================================================
    # STEP 4: Submit MATCHING expense (should auto-approve via AP2)
    # =====================================================================
    print("STEP 4: Submitting MATCHING expense (Amazon, $45, office_supplies)...")
    print("-" * 70)

    expense_data = {
        "user_id": user_id,
        "amount": 45.00,
        "vendor": "Amazon",
        "category": "OFFICE_SUPPLIES",
        "description": "USB cables for office - AP2 test",
        "date": date.today().isoformat()
    }

    expense_response = requests.post(
        f"{BASE_URL}/api/v1/expenses",
        headers=headers,
        json=expense_data
    )

    print(f"Response Status: {expense_response.status_code}")

    if expense_response.status_code in [200, 201]:
        result = expense_response.json()

        print()
        print("RESULT:")
        print(f"  Expense ID: {result.get('id')}")
        print(f"  Status: {result.get('status', 'N/A').upper()}")
        print(f"  Auto-approved: {result.get('auto_approved', False)}")
        print(f"  Auto-approved via: {result.get('auto_approved_via', 'N/A')}")
        print(f"  Message: {result.get('message', 'N/A')}")
        print()

        if result.get('auto_approved') and result.get('auto_approved_via') == 'intent_mandate':
            print("✅ SUCCESS! Expense auto-approved via Intent Mandate (AP2)")
            print("   ✨ AI Agent approved instantly - NO manager intervention needed!")

            # Show AP2 mandate IDs
            if result.get('intent_mandate_id'):
                print(f"   Intent Mandate: {result.get('intent_mandate_id')[:20]}...")
            if result.get('cart_mandate_id'):
                print(f"   Cart Mandate: {result.get('cart_mandate_id')[:20]}...")
            if result.get('payment_mandate_id'):
                print(f"   Payment Mandate: {result.get('payment_mandate_id')[:20]}...")

        elif result.get('auto_approved') and result.get('auto_approved_via') == 'approval_policy':
            print("✅ Auto-approved via Approval Policy (free feature)")
        else:
            print("ℹ️  Expense submitted for manual approval (expected if no matching mandate)")
    else:
        print(f"[ERROR] Expense submission failed")
        print(expense_response.text)

    print()

    # =====================================================================
    # STEP 5: Submit NON-MATCHING expense (should require manual approval)
    # =====================================================================
    print("STEP 5: Submitting NON-MATCHING expense (Staples, $45, office_supplies)...")
    print("-" * 70)

    non_matching_data = {
        "user_id": user_id,
        "amount": 45.00,
        "vendor": "Staples",  # Different merchant
        "category": "OFFICE_SUPPLIES",
        "description": "Pens from Staples - should NOT auto-approve",
        "date": date.today().isoformat()
    }

    non_matching_response = requests.post(
        f"{BASE_URL}/api/v1/expenses",
        headers=headers,
        json=non_matching_data
    )

    print(f"Response Status: {non_matching_response.status_code}")

    if non_matching_response.status_code in [200, 201]:
        result2 = non_matching_response.json()

        print()
        print("RESULT:")
        print(f"  Expense ID: {result2.get('id')}")
        print(f"  Status: {result2.get('status', 'N/A').upper()}")
        print(f"  Auto-approved: {result2.get('auto_approved', False)}")
        print(f"  Message: {result2.get('message', 'N/A')}")
        print()

        if result2.get('status', '').lower() == 'pending':
            print("✅ CORRECT! Non-matching expense requires manual approval")
            print("   📋 Manager will need to review this expense")
        else:
            print("⚠️  Unexpected: Non-matching expense was auto-approved")
    else:
        print(f"[ERROR] Expense submission failed")
        print(non_matching_response.text)

    print()

    # =====================================================================
    # SUMMARY
    # =====================================================================
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print()
    print("✓ Authentication successful")
    print("✓ Organization context loaded")
    print("✓ Intent Mandates checked")
    print("✓ Matching expense submitted")
    print("✓ Non-matching expense submitted")
    print()
    print("EXPECTED RESULTS:")
    print("1. Amazon expense: ✨ Auto-approved by AI agent (AP2)")
    print("2. Staples expense: 📋 Awaiting manual approval")
    print()
    print("VERIFICATION:")
    print("- Check frontend at http://localhost:5173")
    print("- Look for purple '✨ AI Agent' badge on Amazon expense")
    print("- Look for yellow 'PENDING' badge on Staples expense")
    print()

if __name__ == '__main__':
    asyncio.run(test_live_autoapproval())
