"""Test what the 402 error response actually looks like"""
import requests
import json

# First, log in as admin1 to get a token
login_response = requests.post(
    "http://127.0.0.1:8000/api/v1/auth/login",
    json={"username": "admin1", "password": "AgentTest!"}
)

if login_response.status_code != 200:
    print(f"Login failed: {login_response.status_code}")
    print(login_response.text)
    exit(1)

token = login_response.json()["access_token"]
print(f"Logged in as admin1")
print(f"Token: {token[:50]}...")

# Try to create a second organization
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

org_data = {
    "name": "Second Test Org",
    "slug": "second-test-org",
    "description": "This should fail",
    "currency": "USD",
    "timezone": "UTC"
}

print(f"\nAttempting to create organization...")
create_response = requests.post(
    "http://127.0.0.1:8000/api/v1/organizations",
    headers=headers,
    json=org_data
)

print(f"\nResponse Status: {create_response.status_code}")
print(f"Response Text: {repr(create_response.text)}")
print(f"Response Headers Content-Type: {create_response.headers.get('content-type')}")
print(f"\nResponse Body:")
try:
    print(json.dumps(create_response.json(), indent=2))
except Exception as e:
    print(f"Could not parse as JSON: {e}")

if create_response.status_code == 402:
    print("\n>>> Got 402 Payment Required (expected!)")
    response_data = create_response.json()

    print("\n>>> Checking response structure:")
    print(f"  - Has 'detail' key: {'detail' in response_data}")

    if 'detail' in response_data:
        detail = response_data['detail']
        print(f"  - detail type: {type(detail)}")

        if isinstance(detail, dict):
            print(f"\n>>> Detail contains:")
            print(f"  - message: {detail.get('message', 'N/A')}")
            print(f"  - current_tier: {detail.get('current_tier', 'N/A')}")
            print(f"  - current_limit: {detail.get('current_limit', 'N/A')}")
            print(f"  - current_count: {detail.get('current_count', 'N/A')}")
            print(f"  - upgrade_options: {detail.get('upgrade_options', 'N/A')}")
        else:
            print(f"  - detail value: {detail}")
else:
    print(f"\n>>> Unexpected status code: {create_response.status_code}")
