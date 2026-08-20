"""Quick test to check if API returns lowercase status values"""

import requests
import json

# Login as employee1
login_url = "http://localhost:8001/api/v1/auth/login"
login_data = {"username": "employee1", "password": "password123"}

try:
    # Login
    response = requests.post(login_url, json=login_data)
    print(f"Login status: {response.status_code}")

    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get("access_token")

        # Get user info to find org ID
        headers = {"Authorization": f"Bearer {access_token}"}
        user_response = requests.get("http://localhost:8001/api/v1/users/me", headers=headers)
        user_data = user_response.json()
        user_id = user_data.get("id")

        # Get organizations
        org_response = requests.get("http://localhost:8001/api/v1/organizations/my", headers=headers)
        if org_response.status_code == 200:
            orgs = org_response.json()
            if orgs:
                org_id = orgs[0]["id"]

                # Add org header
                headers["X-Organization-Id"] = org_id

                # Get expense report
                report_url = f"http://localhost:8001/api/v1/expenses/report?user_id={user_id}"
                report_response = requests.get(report_url, headers=headers)

                print(f"\nExpense report status: {report_response.status_code}")

                if report_response.status_code == 200:
                    report = report_response.json()
                    print(f"Total expenses: {report.get('total_expenses', 0)}")

                    if report.get("expenses"):
                        print("\nExpense statuses:")
                        for expense in report["expenses"][:5]:  # Show first 5
                            status = expense.get("status", "N/A")
                            vendor = expense.get("vendor", "N/A")
                            is_lowercase = status.islower() if status != "N/A" else False
                            print(f"  - {vendor}: status='{status}' (lowercase: {is_lowercase})")
                    else:
                        print("No expenses found in report")
                else:
                    print(f"Error: {report_response.text}")
            else:
                print("No organizations found")
    else:
        print(f"Login failed: {response.text}")

except Exception as e:
    print(f"Error: {e}")
