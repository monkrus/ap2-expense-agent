import requests
import json

# First login to get token
login_data = {
    'username': 'emptest',
    'password': 'AgentTest!'
}

print("1. Logging in as emptest...")
login_response = requests.post(
    'http://localhost:8000/api/v1/auth/login',
    json=login_data  # Changed from 'data' to 'json'
)

print(f"Login Status: {login_response.status_code}")
print(f"Login Response: {login_response.text}\n")

if login_response.status_code == 200:
    token_data = login_response.json()
    access_token = token_data.get('access_token')

    print(f"Got access token: {access_token[:20]}...\n")

    # Get user info
    print("2. Getting user info...")
    headers = {'Authorization': f'Bearer {access_token}'}
    user_response = requests.get(
        'http://localhost:8000/api/users/me',
        headers=headers
    )
    print(f"User Status: {user_response.status_code}")
    user_data = user_response.json()
    print(f"User ID: {user_data.get('id')}")
    print(f"User Email: {user_data.get('email')}\n")

    # Submit expense
    print("3. Submitting expense...")
    expense_data = {
        'user_id': user_data.get('id'),
        'amount': 125.50,
        'vendor': 'Test Vendor',
        'category': 'Travel',
        'description': 'Test expense submission'
    }

    expense_response = requests.post(
        'http://localhost:8000/api/v1/expenses',
        headers={'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'},
        json=expense_data
    )

    print(f"Expense Status: {expense_response.status_code}")
    print(f"Expense Response: {json.dumps(expense_response.json(), indent=2)}")
else:
    print("Login failed!")
