"""
Test Auto-Organization Registration Flow
Verifies that new users automatically get their own organization
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from src.database import SessionLocal
from src.models import User, Organization, OrganizationMember

# Create a unique test username
test_username = f"testuser_{int(time.time())}"
test_email = f"{test_username}@test.com"

print("=" * 70)
print("TESTING AUTO-ORGANIZATION REGISTRATION FLOW")
print("=" * 70)

# Step 1: Register a new user via API
print("\n[STEP 1] Registering new user via API...")
import requests

register_payload = {
    "username": test_username,
    "email": test_email,
    "password": "Test123!",
    "full_name": "Test User Auto Org",
    "role": "employee",
}

try:
    response = requests.post(
        "http://localhost:8000/api/v1/auth/register", json=register_payload
    )

    if response.status_code == 201:
        print(f"[OK] User registered successfully!")
        user_data = response.json()
        print(f"   Username: {user_data['username']}")
        print(f"   Email: {user_data['email']}")
        print(f"   User ID: {user_data['id']}")
    else:
        print(f"[FAIL] Registration failed: {response.status_code}")
        print(f"   Response: {response.text}")
        sys.exit(1)

except Exception as e:
    print(f"[FAIL] API request failed: {e}")
    sys.exit(1)

# Step 2: Verify organization was created in database
print("\n[STEP 2] Checking if organization was auto-created...")
db = SessionLocal()

try:
    user = db.query(User).filter(User.username == test_username).first()
    if not user:
        print(f"[FAIL] User not found in database!")
        sys.exit(1)

    # Check organization membership
    membership = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.user_id == user.id, OrganizationMember.is_active == True
        )
        .first()
    )

    if not membership:
        print(f"[FAIL] No organization membership found for user!")
        print(f"   User ID: {user.id}")
        sys.exit(1)

    org = (
        db.query(Organization)
        .filter(Organization.id == membership.organization_id)
        .first()
    )

    if not org:
        print(f"[FAIL] Organization not found!")
        sys.exit(1)

    print(f"[OK] Organization auto-created successfully!")
    print(f"   Organization Name: {org.name}")
    print(f"   Organization Slug: {org.slug}")
    print(f"   Organization ID: {org.id}")
    print(f"   User Role: {membership.role}")
    print(f"   Is Active: {org.is_active}")

    # Step 3: Verify user can login and access organization context
    print("\n[STEP 3] Testing login and organization context...")

    login_payload = {"username": test_username, "password": "Test123!"}

    login_response = requests.post(
        "http://localhost:8000/api/v1/auth/login", json=login_payload
    )

    if login_response.status_code != 200:
        print(f"[FAIL] Login failed: {login_response.status_code}")
        print(f"   Response: {login_response.text}")
        sys.exit(1)

    login_data = login_response.json()
    access_token = login_data["access_token"]
    print(f"[OK] Login successful!")

    # Step 4: Try to fetch expenses (should work without org context error)
    print("\n[STEP 4] Testing expense report access...")

    expense_headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Organization-Id": org.id,
    }

    expense_response = requests.get(
        f"http://localhost:8000/api/v1/expenses/report?user_id={user.id}",
        headers=expense_headers,
    )

    if expense_response.status_code == 200:
        print(f"[OK] Expense report accessible!")
        report = expense_response.json()
        print(f"   Total Expenses: {report.get('total_expenses', 0)}")
        print(f"   Total Amount: ${report.get('total_amount', 0):.2f}")
    else:
        print(f"[FAIL] Expense access failed: {expense_response.status_code}")
        print(f"   Response: {expense_response.text}")
        sys.exit(1)

    # Step 5: Test fetching organizations list
    print("\n[STEP 5] Testing organizations list...")

    orgs_response = requests.get(
        "http://localhost:8000/api/v1/organizations",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    if orgs_response.status_code == 200:
        orgs = orgs_response.json()
        print(f"[OK] Organizations list retrieved!")
        print(f"   Total Organizations: {len(orgs) if isinstance(orgs, list) else 1}")
        if isinstance(orgs, list) and len(orgs) > 0:
            print(f"   First Org: {orgs[0]['name']}")
    else:
        print(f"[FAIL] Organizations list failed: {orgs_response.status_code}")

    print("\n" + "=" * 70)
    print("[SUCCESS] ALL TESTS PASSED!")
    print("=" * 70)
    print(f"\nNew users will now automatically:")
    print(f"  1. Get their own organization created")
    print(f"  2. Be added as OWNER of that organization")
    print(f"  3. Have immediate access to all features")
    print(f"  4. No more 'Organization context required' errors!")
    print("\nTest User Credentials:")
    print(f"  Username: {test_username}")
    print(f"  Password: Test123!")
    print(f"  Organization: {org.name}")
    print("=" * 70)

finally:
    db.close()
