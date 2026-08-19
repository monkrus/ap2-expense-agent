"""
Test AP2 Autonomous Purchase - Accept and Deny scenarios
"""
import requests
import json
import sys

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://localhost:8000"

def login():
    """Login and get access token"""
    passwords_to_try = ["Password123!", "Passowrd123!"]

    for pwd in passwords_to_try:
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={
                "username": "adminfree",
                "password": pwd
            }
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Login successful: {data.get('user', {}).get('username')}")
            return data.get("access_token")

    print(f"❌ Login failed")
    return None

def test_accepted_request(token):
    """Test a request that SHOULD be accepted"""
    print("\n" + "="*60)
    print("TEST 1: Request Within Constraints (Should ACCEPT)")
    print("="*60)

    payload = {
        "items": [
            {
                "description": "Desk Lamp",
                "amount": 25.00,
                "category": "OFFICE_SUPPLIES"
            },
            {
                "description": "Notebooks",
                "amount": 15.00,
                "category": "OFFICE_SUPPLIES"
            }
        ],
        "merchant": "Staples",
        "constraints": {
            "max_amount": 100.00,
            "monthly_limit": 500.00,
            "category": "OFFICE_SUPPLIES",
            "merchant": "Staples"
        }
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print(f"\n📋 Request Details:")
    print(f"   Items: {len(payload['items'])}")
    print(f"   Total Amount: ${sum(item['amount'] for item in payload['items']):.2f}")
    print(f"   Merchant: {payload['merchant']}")
    print(f"   Category: {payload['constraints']['category']}")
    print(f"   Max Amount Constraint: ${payload['constraints']['max_amount']:.2f}")

    response = requests.post(
        f"{BASE_URL}/api/ap2/complete-flow",
        headers=headers,
        json=payload
    )

    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ REQUEST ACCEPTED")
        print(f"   Intent Mandate: {data.get('intent_mandate_id', 'N/A')[:16]}...")
        print(f"   Cart Mandate: {data.get('cart_mandate_id', 'N/A')[:16]}...")
        print(f"   Payment Mandate: {data.get('payment_mandate_id', 'N/A')[:16]}...")
        print(f"   Status: {data.get('status', 'N/A')}")
        return True
    else:
        print(f"\n❌ REQUEST REJECTED (Unexpected)")
        print(f"   Status Code: {response.status_code}")
        print(f"   Error: {response.text}")
        return False

def test_denied_amount_exceeded(token):
    """Test a request that SHOULD be denied - amount exceeds constraint"""
    print("\n" + "="*60)
    print("TEST 2: Amount Exceeds Constraint (Should DENY)")
    print("="*60)

    payload = {
        "items": [
            {
                "description": "Expensive Office Chair",
                "amount": 500.00,
                "category": "OFFICE_SUPPLIES"
            }
        ],
        "merchant": "Staples",
        "constraints": {
            "max_amount": 100.00,  # Max is $100, but item is $500
            "monthly_limit": 1000.00,
            "category": "OFFICE_SUPPLIES",
            "merchant": "Staples"
        }
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print(f"\n📋 Request Details:")
    print(f"   Items: {len(payload['items'])}")
    print(f"   Total Amount: ${sum(item['amount'] for item in payload['items']):.2f}")
    print(f"   Max Amount Constraint: ${payload['constraints']['max_amount']:.2f}")
    print(f"   ⚠️  Amount EXCEEDS constraint by ${500.00 - 100.00:.2f}")

    response = requests.post(
        f"{BASE_URL}/api/ap2/complete-flow",
        headers=headers,
        json=payload
    )

    if response.status_code == 400 or response.status_code == 422:
        error_data = response.json()
        print(f"\n✅ REQUEST DENIED (Expected)")
        print(f"   Reason: {error_data.get('detail', 'Validation error')}")
        return True
    elif response.status_code == 200:
        print(f"\n❌ REQUEST ACCEPTED (Should have been denied!)")
        print(f"   This is a bug - amount exceeds constraint")
        return False
    else:
        print(f"\n⚠️  Unexpected response")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def test_denied_category_mismatch(token):
    """Test a request that SHOULD be denied - category mismatch"""
    print("\n" + "="*60)
    print("TEST 3: Category Mismatch (Should DENY)")
    print("="*60)

    payload = {
        "items": [
            {
                "description": "Software License",
                "amount": 50.00,
                "category": "SOFTWARE"  # Constraint only allows OFFICE_SUPPLIES
            }
        ],
        "merchant": "Microsoft",
        "constraints": {
            "max_amount": 100.00,
            "monthly_limit": 500.00,
            "category": "OFFICE_SUPPLIES",  # Only allows OFFICE_SUPPLIES
            "merchant": "Microsoft"
        }
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print(f"\n📋 Request Details:")
    print(f"   Item Category: SOFTWARE")
    print(f"   Constraint Category: OFFICE_SUPPLIES")
    print(f"   ⚠️  Category MISMATCH")

    response = requests.post(
        f"{BASE_URL}/api/ap2/complete-flow",
        headers=headers,
        json=payload
    )

    if response.status_code == 400 or response.status_code == 422:
        error_data = response.json()
        print(f"\n✅ REQUEST DENIED (Expected)")
        print(f"   Reason: {error_data.get('detail', 'Validation error')}")
        return True
    elif response.status_code == 200:
        print(f"\n❌ REQUEST ACCEPTED (Should have been denied!)")
        print(f"   This is a bug - category doesn't match constraint")
        return False
    else:
        print(f"\n⚠️  Unexpected response")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def main():
    print("="*60)
    print("AP2 Accept/Deny Testing")
    print("="*60)

    # Login
    token = login()
    if not token:
        print("\n❌ Cannot proceed without authentication")
        return

    # Run tests
    test1_pass = test_accepted_request(token)
    test2_pass = test_denied_amount_exceeded(token)
    test3_pass = test_denied_category_mismatch(token)

    # Summary
    print("\n" + "="*60)
    print("Test Summary:")
    print("="*60)
    print(f"Test 1 - Accept Valid Request:     {'✅ PASS' if test1_pass else '❌ FAIL'}")
    print(f"Test 2 - Deny Amount Exceeded:     {'✅ PASS' if test2_pass else '❌ FAIL'}")
    print(f"Test 3 - Deny Category Mismatch:   {'✅ PASS' if test3_pass else '❌ FAIL'}")
    print("="*60)

    all_pass = test1_pass and test2_pass and test3_pass
    if all_pass:
        print("\n🎉 All tests PASSED - AP2 validation working correctly!")
    else:
        print("\n⚠️  Some tests FAILED - Review results above")

if __name__ == "__main__":
    main()
