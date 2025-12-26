"""
Test script to verify admin notifications when employees submit expenses
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_admin_notifications():
    print("=" * 60)
    print("TESTING ADMIN NOTIFICATIONS ON EXPENSE SUBMISSION")
    print("=" * 60)

    # Step 1: Login as admin
    print("\n[1] Logging in as admin...")
    admin_login = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"username": "admin1", "password": "Admin123!"},
        headers={"Content-Type": "application/json"}
    )

    if admin_login.status_code != 200:
        print(f"[FAIL] Admin login failed: {admin_login.status_code}")
        print(f"Response: {admin_login.text}")
        return False

    admin_data = admin_login.json()
    admin_token = admin_data.get("access_token")
    admin_user = admin_data.get("user")
    print(f"[OK] Admin logged in: {admin_user.get('username')} (ID: {admin_user.get('id')})")

    # Get admin's organization
    admin_org_id = None
    orgs_response = requests.get(
        f"{BASE_URL}/api/v1/organizations",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    if orgs_response.status_code == 200:
        orgs = orgs_response.json()
        if orgs and len(orgs) > 0:
            admin_org_id = orgs[0]["id"]
            print(f"[OK] Admin organization: {orgs[0]['name']} (ID: {admin_org_id})")

    if not admin_org_id:
        print("[FAIL] Could not get admin's organization")
        return False

    # Check admin's notifications BEFORE expense submission
    print("\n[2] Checking admin notifications BEFORE expense submission...")
    notif_before = requests.get(
        f"{BASE_URL}/api/notifications",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    if notif_before.status_code != 200:
        print(f"[FAIL] Failed to get notifications: {notif_before.status_code}")
        return False

    notif_before_data = notif_before.json()
    unread_before = notif_before_data.get("unread_count", 0)
    print(f"[OK] Admin has {unread_before} unread notifications")

    # Step 2: Login as employee
    print("\n[3] Logging in as employee...")
    employee_login = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"username": "emp1", "password": "Emp123!"},
        headers={"Content-Type": "application/json"}
    )

    if employee_login.status_code != 200:
        print(f"[FAIL] Employee login failed: {employee_login.status_code}")
        print(f"Response: {employee_login.text}")
        return False

    employee_data = employee_login.json()
    employee_token = employee_data.get("access_token")
    employee_user = employee_data.get("user")
    print(f"[OK] Employee logged in: {employee_user.get('username')} (ID: {employee_user.get('id')})")

    # Step 3: Submit expense as employee
    print("\n[4] Submitting expense as employee...")
    expense_data = {
        "user_id": employee_user.get("id"),
        "amount": 125.50,
        "vendor": "Test Vendor for Notification",
        "category": "MEALS",
        "description": "Testing admin notification system",
        "date": time.strftime("%Y-%m-%d")
    }

    submit_response = requests.post(
        f"{BASE_URL}/api/v1/expenses",
        headers={
            "Authorization": f"Bearer {employee_token}",
            "X-Organization-Id": admin_org_id,
            "Content-Type": "application/json"
        },
        json=expense_data
    )

    if submit_response.status_code != 201:
        print(f"[FAIL] Expense submission failed: {submit_response.status_code}")
        print(f"Response: {submit_response.text}")
        return False

    expense = submit_response.json()
    print(f"[OK] Expense submitted: ID={expense.get('id')}, Amount=${expense.get('amount')}, Status={expense.get('status')}")

    # Step 4: Check admin notifications AFTER expense submission
    print("\n[5] Checking admin notifications AFTER expense submission...")
    time.sleep(1)  # Brief pause to ensure notification is created

    notif_after = requests.get(
        f"{BASE_URL}/api/notifications",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    if notif_after.status_code != 200:
        print(f"[FAIL] Failed to get notifications: {notif_after.status_code}")
        return False

    notif_after_data = notif_after.json()
    unread_after = notif_after_data.get("unread_count", 0)
    notifications = notif_after_data.get("notifications", [])

    print(f"[OK] Admin now has {unread_after} unread notifications")

    # Step 5: Verify new notification
    print("\n[6] Verifying notification details...")

    if unread_after <= unread_before:
        print(f"[FAIL] No new notifications received! Before: {unread_before}, After: {unread_after}")
        return False

    # Find the most recent notification
    if notifications:
        latest_notif = notifications[0]  # Notifications are ordered by created_at desc
        print(f"\nLatest Notification:")
        print(f"   Type: {latest_notif.get('notification_type')}")
        print(f"   Title: {latest_notif.get('title')}")
        print(f"   Message: {latest_notif.get('message')}")
        print(f"   Expense ID: {latest_notif.get('expense_id')}")
        print(f"   Is Read: {latest_notif.get('is_read')}")
        print(f"   Created: {latest_notif.get('created_at')}")

        # Verify it's the correct notification
        if latest_notif.get("notification_type") == "expense_submitted":
            if latest_notif.get("expense_id") == expense.get("id"):
                print(f"\n[SUCCESS] Admin received notification for the submitted expense!")
                return True
            else:
                print(f"\n[WARN] Notification received but expense_id doesn't match")
                print(f"   Expected: {expense.get('id')}")
                print(f"   Got: {latest_notif.get('expense_id')}")
                return False
        else:
            print(f"\n[WARN] Notification received but type is not 'expense_submitted'")
            return False
    else:
        print(f"[FAIL] No notifications found in response")
        return False

if __name__ == "__main__":
    print("\nPREREQUISITES:")
    print("   - Backend server must be running on http://localhost:8000")
    print("   - Admin user 'admin1' with password 'Admin123!' must exist")
    print("   - Employee user 'emp1' with password 'Emp123!' must exist")
    print("   - Both users must be in the same organization")
    print()

    success = test_admin_notifications()

    print("\n" + "=" * 60)
    if success:
        print("TEST PASSED: Admin notifications are working correctly!")
    else:
        print("TEST FAILED: Admin notifications are not working as expected")
    print("=" * 60)
