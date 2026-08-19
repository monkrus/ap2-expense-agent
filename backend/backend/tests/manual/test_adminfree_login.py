"""Test adminfree login"""

import requests
import json

login_url = "http://localhost:8001/api/v1/auth/login"
login_data = {"username": "adminfree", "password": "Testme1!"}

try:
    response = requests.post(login_url, json=login_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    if response.status_code == 200:
        data = response.json()
        print(f"\nUser role: {data.get('user', {}).get('role')}")
        print(f"User ID: {data.get('user', {}).get('id')}")

        # Test organizations endpoint
        token = data.get('access_token')
        if token:
            org_response = requests.get(
                "http://localhost:8001/api/v1/organizations",
                headers={"Authorization": f"Bearer {token}"}
            )
            print(f"\nOrganizations status: {org_response.status_code}")
            if org_response.status_code == 200:
                orgs = org_response.json()
                print(f"Organizations: {json.dumps(orgs, indent=2)}")
            else:
                print(f"Organizations error: {org_response.text}")

except Exception as e:
    print(f"Error: {e}")
