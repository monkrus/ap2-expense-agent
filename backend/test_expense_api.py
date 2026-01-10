"""Test if the expense API returns data correctly"""
import requests

BASE_URL = "http://localhost:8000"

print("=" * 70)
print("TESTING EXPENSE API ENDPOINT")
print("=" * 70)
print()

# 1. Login
print("1. Logging in as adminfree...")
login_response = requests.post(
    f"{BASE_URL}/api/v1/auth/login",
    json={
        "username": "adminfree",
        "password": "adminfree"
    }
)

if login_response.status_code == 200:
    data = login_response.json()
    token = data["access_token"]
    user_id = data["user"]["id"]
    print(f"   SUCCESS! User ID: {user_id}")
    print()

    # 2. Get expenses
    print("2. Fetching expenses...")
    headers = {"Authorization": f"Bearer {token}"}

    expenses_response = requests.get(
        f"{BASE_URL}/api/v1/expenses",
        headers=headers
    )

    if expenses_response.status_code == 200:
        expenses = expenses_response.json()
        print(f"   SUCCESS! Got {len(expenses)} expenses")
        print()

        if expenses:
            amazon_expense = next((e for e in expenses if e.get('vendor') == 'Amazon'), None)
            if amazon_expense:
                print("FOUND AMAZON EXPENSE IN API:")
                print(f"  Amount: ${amazon_expense.get('amount')}")
                print(f"  Status: {amazon_expense.get('status')}")
                print(f"  Auto-approved: {amazon_expense.get('auto_approved')}")
                print(f"  Auto-approved via: {amazon_expense.get('auto_approved_via')}")
                
                if amazon_expense.get('auto_approved_via') == 'intent_mandate':
                    print()
                    print("API IS CORRECT - Frontend should show badge!")
                else:
                    print()
                    print("PROBLEM: auto_approved_via field missing in API response")
    else:
        print(f"   ERROR: {expenses_response.status_code}")
else:
    print(f"   ERROR: Login failed ({login_response.status_code})")
    print(f"   Response: {login_response.text[:200]}")
