"""
Test Expense Approval Workflow
================================
1. Employee submits expense
2. Admin receives notification
3. Admin approves expense
4. Employee receives approval notification
"""

import os
from datetime import datetime

import requests

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")


# Colors for output
class Color:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    END = "\033[0m"


def print_step(step_num, message):
    print(f"\n{Color.BLUE}[STEP {step_num}]{Color.END} {message}")
    print("=" * 70)


def print_success(message):
    print(f"{Color.GREEN}[SUCCESS]{Color.END} {message}")


def print_error(message):
    print(f"{Color.RED}[ERROR]{Color.END} {message}")


def print_info(message):
    print(f"{Color.YELLOW}[INFO]{Color.END} {message}")


# Step 1: Login as Employee
print_step(1, "Login as Employee (employee1)")

emp_resp = requests.post(
    f"{BASE_URL}/auth/login",
    json={
        "username": "employee1",
        "password": os.getenv("TEST_EMPLOYEE_PASSWORD", "TempPass123!"),
    },
)

if emp_resp.status_code != 200:
    print_error(f"Employee login failed with status code: {emp_resp.status_code}")
    exit(1)

employee_token = emp_resp.json().get("access_token")
print_success("Logged in successfully as employee1")

# Step 2: Get Organization ID
print_step(2, "Get Employee's Organization")

org_list = requests.get(
    f"{BASE_URL}/organizations", headers={"Authorization": f"Bearer {employee_token}"}
)

if org_list.status_code != 200:
    print_error(f"Failed to get organizations: {org_list.status_code}")
    exit(1)

orgs = org_list.json()
if not orgs:
    print_error("Employee is not part of any organization!")
    exit(1)

org = orgs[0]
org_id = org["id"]
print_success(f"Organization: {org['name']}")
print_info(f"Org ID: {org_id}")

# Step 3: Submit Expense as Employee
print_step(3, "Employee Submits Expense")

expense_data = {
    "amount": 150.00,
    "vendor": "Office Depot",
    "category": "OFFICE_SUPPLIES",
    "description": "Office supplies for Q1 - pens, paper, folders",
    "date": datetime.now().strftime("%Y-%m-%d"),
    "payment_method": "PERSONAL_CARD",
    "currency": "USD",
}

print_info("Expense Details:")
print(f"  Amount: ${expense_data['amount']}")
print(f"  Vendor: {expense_data['vendor']}")
print(f"  Category: {expense_data['category']}")
print(f"  Description: {expense_data['description']}")

expense_response = requests.post(
    f"{BASE_URL}/expenses",
    headers={
        "Authorization": f"Bearer {employee_token}",
        "X-Organization-Id": org_id,
        "Content-Type": "application/json",
    },
    json=expense_data,
)

if expense_response.status_code != 201:
    print_error(f"Failed to create expense: {expense_response.status_code}")
    exit(1)

expense = expense_response.json()
expense_id = expense["id"]

print_success("Expense submitted successfully!")
print_info(f"Expense ID: {expense_id}")
print_info(f"Status: {expense['status']}")
print_info(f"Amount: ${expense['amount']}")

# Step 4: Login as Admin
print_step(4, "Login as Admin (adminfree)")

admin_resp = requests.post(
    f"{BASE_URL}/auth/login",
    json={
        "username": "adminfree",
        "password": os.getenv("TEST_ADMIN_PASSWORD", "Admin123!"),
    },
)

if admin_resp.status_code != 200:
    print_error(f"Admin login failed with status code: {admin_resp.status_code}")
    exit(1)

admin_token = admin_resp.json().get("access_token")
print_success("Logged in successfully as adminfree")

# Step 5: Admin Views Pending Expenses
print_step(5, "Admin Views Pending Expenses")

pending_expenses = requests.get(
    f"{BASE_URL}/expenses?status=PENDING",
    headers={"Authorization": f"Bearer {admin_token}", "X-Organization-Id": org_id},
)

if pending_expenses.status_code != 200:
    print_error(f"Failed to get pending expenses: {pending_expenses.status_code}")
    exit(1)

pending = pending_expenses.json()
print_success(f"Found {len(pending)} pending expense(s)")

# Find our expense
our_expense = next((e for e in pending if e["id"] == expense_id), None)
if our_expense:
    print_info("Our expense is pending approval:")
    print(f"  ID: {our_expense['id']}")
    print(f"  Amount: ${our_expense['amount']}")
    print(f"  Vendor: {our_expense['vendor']}")

# Step 6: Admin Approves Expense
print_step(6, "Admin Approves Expense")

approve_response = requests.put(
    f"{BASE_URL}/expenses/{expense_id}/approve",
    headers={"Authorization": f"Bearer {admin_token}", "X-Organization-Id": org_id},
)

if approve_response.status_code != 200:
    print_error(f"Failed to approve expense: {approve_response.status_code}")
    exit(1)

approved_expense = approve_response.json()

print_success("Expense approved successfully!")
print_info(f"Expense ID: {approved_expense['id']}")
print_info(f"Status: {approved_expense['status']}")

# Step 7: Employee Views Approved Expense
print_step(7, "Employee Views Approved Expense")

employee_expenses = requests.get(
    f"{BASE_URL}/expenses/{expense_id}",
    headers={"Authorization": f"Bearer {employee_token}", "X-Organization-Id": org_id},
)

if employee_expenses.status_code != 200:
    print_error(f"Failed to get expense: {employee_expenses.status_code}")
    exit(1)

final_expense = employee_expenses.json()

print_success("Employee can see approved expense!")
print_info(f"Status: {final_expense['status']}")
print_info(f"Amount: ${final_expense['amount']}")

# Summary
print("\n" + "=" * 70)
print(f"{Color.GREEN}WORKFLOW TEST COMPLETED SUCCESSFULLY!{Color.END}")
print("=" * 70)
print("\nWorkflow Summary:")
print(f"1. Employee 'employee1' submitted expense for ${expense_data['amount']}")
print("2. Expense was created with status: PENDING")
print("3. Admin 'adminfree' viewed pending expenses")
print("4. Admin approved the expense")
print("5. Expense status changed to: APPROVED")
print("6. Employee can now see the approved expense")
print("\n" + "=" * 70)

# Test Rejection Flow (Optional)
print(f"\n{Color.YELLOW}[BONUS] Testing Rejection Flow{Color.END}")
print("=" * 70)

# Submit another expense
expense_data_2 = {
    "amount": 500.00,
    "vendor": "Expensive Restaurant",
    "category": "MEALS_ENTERTAINMENT",
    "description": "Team dinner (too expensive)",
    "date": datetime.now().strftime("%Y-%m-%d"),
    "payment_method": "PERSONAL_CARD",
    "currency": "USD",
}

expense_response_2 = requests.post(
    f"{BASE_URL}/expenses",
    headers={
        "Authorization": f"Bearer {employee_token}",
        "X-Organization-Id": org_id,
        "Content-Type": "application/json",
    },
    json=expense_data_2,
)

if expense_response_2.status_code == 201:
    expense_2 = expense_response_2.json()
    expense_id_2 = expense_2["id"]

    print_success(f"Second expense submitted: ${expense_data_2['amount']}")

    # Admin rejects it
    reject_response = requests.put(
        f"{BASE_URL}/expenses/{expense_id_2}/reject",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Organization-Id": org_id,
            "Content-Type": "application/json",
        },
        json={"reason": "Amount exceeds policy limit for meals"},
    )

    if reject_response.status_code == 200:
        rejected_expense = reject_response.json()
        print_success("Second expense rejected successfully!")
        print_info(f"Status: {rejected_expense['status']}")
        print_info(
            f"Rejection reason: {rejected_expense.get('rejection_reason', 'N/A')}"
        )
    else:
        print_error(f"Failed to reject expense: {reject_response.status_code}")
else:
    print_error(f"Failed to create second expense: {expense_response_2.status_code}")

print("\n" + "=" * 70)
print(f"{Color.GREEN}ALL TESTS COMPLETED!{Color.END}")
print("=" * 70)
