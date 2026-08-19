"""
Test the complete approval workflow:
1. Employee submits expense
2. Admin sees it in pending queue
3. Admin approves it
4. Expense status changes to approved

Usage:
    python test_approval_workflow.py <admin_user> <admin_pass> <emp_user> <emp_pass>

Example:
    python test_approval_workflow.py adminfree MyPass123! emp1 EmpPass123!
"""

import requests
import json
import time
import sys
from datetime import datetime

BASE_URL = "http://localhost:8000"


def test_approval_workflow(admin_username, admin_password, emp_username, emp_password):
    print("=" * 80)
    print("Testing Approval Workflow: Employee Submit -> Admin Approve")
    print("=" * 80)
    print()

    # Step 1: Login as admin
    print(f"[1] Logging in as admin: {admin_username}...")
    admin_login = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"username": admin_username, "password": admin_password},
    )

    if admin_login.status_code != 200:
        print(f"[X] Admin login failed: {admin_login.status_code}")
        print(admin_login.text)
        return False

    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print(f"[+] Admin logged in successfully")
    print()

    # Get admin's organization
    orgs_response = requests.get(
        f"{BASE_URL}/api/v1/organizations", headers=admin_headers
    )
    if orgs_response.status_code != 200:
        print("[X] Failed to get organizations")
        return False

    orgs = orgs_response.json()
    if not orgs:
        print("[X] No organizations found")
        return False

    org_id = orgs[0]["id"]
    org_name = orgs[0]["name"]
    print(f"[+] Using organization: {org_name} ({org_id})")

    # Add organization header
    admin_headers["X-Organization-Id"] = org_id
    print()

    # Step 2: Login as employee user
    print(f"[2] Logging in as employee: {emp_username}...")
    employee_login = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"username": emp_username, "password": emp_password},
    )

    if employee_login.status_code != 200:
        print(f"[X] Employee login failed: {employee_login.status_code}")
        print(employee_login.text)
        return False

    employee_token = employee_login.json()["access_token"]
    employee_user_id = employee_login.json()["user"]["id"]
    employee_headers = {
        "Authorization": f"Bearer {employee_token}",
        "X-Organization-Id": org_id,
    }
    print(f"[+] Employee logged in successfully")
    print()

    # Step 3: Check if employee is in the organization (add if needed)
    print("[3] Checking employee organization membership...")

    # Try to add employee to organization (admin action)
    try:
        add_member = requests.post(
            f"{BASE_URL}/api/v1/organizations/{org_id}/members",
            headers=admin_headers,
            json={"user_id": employee_user_id, "role": "member"},
        )

        if add_member.status_code == 201:
            print(f"[+] Employee added to organization")
        elif add_member.status_code == 400 and "already a member" in add_member.text:
            print(f"[+] Employee already in organization")
        elif add_member.status_code == 402:
            print(f"[!] User limit reached (Free tier: 2 users)")
            print(f"    This is expected - testing with existing members")
        else:
            print(f"[!] Add member response: {add_member.status_code}")
            print(add_member.text[:200])
    except Exception as e:
        print(f"[!] Could not add employee to org: {e}")
    print()

    # Step 4: Employee submits an expense
    print("[4] Employee submitting expense...")
    expense_data = {
        "amount": 150.00,
        "vendor": "Test Coffee Shop",
        "category": "Meals",
        "description": "Team lunch meeting - approval workflow test",
        "date": datetime.now().strftime("%Y-%m-%d"),
    }

    submit_response = requests.post(
        f"{BASE_URL}/api/v1/expenses", headers=employee_headers, json=expense_data
    )

    if submit_response.status_code != 201:
        print(f"[X] Expense submission failed: {submit_response.status_code}")
        print(submit_response.text)
        return False

    expense = submit_response.json()
    expense_id = expense["id"]
    print(f"[+] Expense submitted successfully!")
    print(f"    ID: {expense_id}")
    print(f"    Amount: ${expense['amount']}")
    print(f"    Status: {expense.get('status', 'N/A')}")
    print(f"    Auto-approved: {expense.get('auto_approved', False)}")

    # Check if it was auto-approved
    if expense.get("auto_approved"):
        print()
        print("[!] WARNING: Expense was AUTO-APPROVED!")
        print(f"    Reason: {expense.get('message', 'Unknown')}")
        print(f"    Policy ID: {expense.get('approval_policy_id', 'N/A')}")
        print()
        print("    This means auto-approval policies are active.")
        print("    Manual approval testing skipped.")
        return True
    print()

    # Step 5: Admin checks pending expenses
    print("[5] Admin checking pending expenses...")
    time.sleep(1)  # Brief pause to ensure database is updated

    pending_response = requests.get(
        f"{BASE_URL}/api/v1/expenses?status=pending", headers=admin_headers
    )

    if pending_response.status_code != 200:
        print(f"[X] Failed to get pending expenses: {pending_response.status_code}")
        print(pending_response.text)
        return False

    pending_data = pending_response.json()
    pending_expenses = pending_data.get("expenses", [])

    print(f"[+] Found {len(pending_expenses)} pending expense(s)")

    # Find our expense
    our_expense = None
    for exp in pending_expenses:
        if exp["id"] == expense_id:
            our_expense = exp
            break

    if not our_expense:
        print(f"[X] Submitted expense not found in pending queue!")
        print(f"    Looking for: {expense_id}")
        print(f"    Pending expenses: {[e['id'] for e in pending_expenses]}")
        return False

    print(f"[+] Expense found in pending queue:")
    print(f"    ID: {our_expense['id']}")
    print(f"    Amount: ${our_expense['amount']}")
    print(f"    Vendor: {our_expense['vendor']}")
    print(f"    Status: {our_expense['status']}")
    print()

    # Step 6: Admin approves the expense
    print("[6] Admin approving expense...")

    approve_response = requests.put(
        f"{BASE_URL}/api/v1/expenses/{expense_id}/approve", headers=admin_headers
    )

    if approve_response.status_code != 200:
        print(f"[X] Approval failed: {approve_response.status_code}")
        print(approve_response.text)
        return False

    approval_result = approve_response.json()
    print(f"[+] Expense APPROVED successfully!")
    print(f"    Status: {approval_result.get('status', 'N/A')}")
    print(f"    Approved by: {approval_result.get('approved_by', 'N/A')}")
    print(f"    Approved at: {approval_result.get('approved_at', 'N/A')}")
    print(f"    Message: {approval_result.get('message', 'N/A')}")
    print()

    # Step 7: Verify expense is no longer pending
    print("[7] Verifying expense status change...")

    verify_response = requests.get(
        f"{BASE_URL}/api/v1/expenses/{expense_id}", headers=admin_headers
    )

    if verify_response.status_code != 200:
        print(f"[X] Failed to verify expense: {verify_response.status_code}")
        return False

    verified_expense = verify_response.json()
    final_status = verified_expense.get("status", "unknown")

    if final_status.lower() == "approved":
        print(f"[+] VERIFIED: Expense status is now APPROVED")
        print(f"    Transaction ID: {verified_expense.get('transaction_id', 'N/A')}")
    else:
        print(f"[X] ERROR: Expense status is '{final_status}' (expected 'approved')")
        return False

    print()
    print("=" * 80)
    print("APPROVAL WORKFLOW TEST: PASSED")
    print("=" * 80)
    print()
    print("Summary:")
    print(f"  1. Employee '{emp_username}' submitted expense: {expense_id}")
    print(f"  2. Expense appeared in admin's pending queue")
    print(f"  3. Admin '{admin_username}' approved the expense")
    print(f"  4. Expense status changed to APPROVED")
    print()
    return True


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print(
            "Usage: python test_approval_workflow.py <admin_user> <admin_pass> <emp_user> <emp_pass>"
        )
        print("\nExample:")
        print(
            "  python test_approval_workflow.py adminfree MyPass123! emp1 EmpPass123!"
        )
        print("\nCurrent users in database:")
        print("  - adminfree (admin role)")
        print("  - emp1 (employee role)")
        exit(1)

    admin_username = sys.argv[1]
    admin_password = sys.argv[2]
    emp_username = sys.argv[3]
    emp_password = sys.argv[4]

    try:
        success = test_approval_workflow(
            admin_username, admin_password, emp_username, emp_password
        )
        exit(0 if success else 1)
    except requests.exceptions.ConnectionError:
        print("\n[X] ERROR: Cannot connect to backend server")
        print("    Make sure the backend is running on http://localhost:8000")
        exit(1)
    except Exception as e:
        print(f"\n[X] ERROR: {str(e)}")
        import traceback

        traceback.print_exc()
        exit(1)
