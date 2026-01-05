"""Create test employees for testing"""
import requests

API_BASE_URL = "http://localhost:8000/api/v1"

# Login as admin
admin_login = requests.post(
    f"{API_BASE_URL}/auth/login",
    json={"username": "adminfree", "password": "password123"}
)

if admin_login.status_code != 200:
    print(f"[FAIL] Admin login failed: {admin_login.text}")
    exit(1)

admin_data = admin_login.json()
admin_token = admin_data["access_token"]
admin_headers = {
    "Authorization": f"Bearer {admin_token}",
}

# Get organization
orgs_response = requests.get(f"{API_BASE_URL}/organizations", headers=admin_headers)
if orgs_response.status_code == 200:
    orgs = orgs_response.json()
    if orgs:
        org_id = orgs[0]["id"]
        print(f"Using organization: {org_id}")
        admin_headers["X-Organization-Id"] = org_id

# Create employee1
employee1_data = {
    "username": "employee1",
    "email": "employee1@test.com",
    "password": "Password123",
    "full_name": "Test Employee 1",
    "role": "employee"
}

print("\nCreating employee1...")
response = requests.post(
    f"{API_BASE_URL}/auth/register",
    json=employee1_data
)

if response.status_code in [200, 201]:
    print(f"[PASS] employee1 created successfully")
    print(f"  Email: employee1@test.com")
    print(f"  Password: Password123")
elif response.status_code == 400 and "already exists" in response.text.lower():
    print(f"[INFO] employee1 already exists")

    # Try to get user to verify
    login_test = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"username": "employee1", "password": "Password123"}
    )
    if login_test.status_code == 200:
        print(f"[PASS] employee1 login verified")
    else:
        print(f"[WARN] employee1 exists but login failed: {login_test.text}")
else:
    print(f"[FAIL] Failed to create employee1: {response.text}")

# Create employee2
employee2_data = {
    "username": "employee2",
    "email": "employee2@test.com",
    "password": "Password123",
    "full_name": "Test Employee 2",
    "role": "employee"
}

print("\nCreating employee2...")
response = requests.post(
    f"{API_BASE_URL}/auth/register",
    json=employee2_data
)

if response.status_code in [200, 201]:
    print(f"[PASS] employee2 created successfully")
    print(f"  Email: employee2@test.com")
    print(f"  Password: Password123")
elif response.status_code == 400 and "already exists" in response.text.lower():
    print(f"[INFO] employee2 already exists")

    # Try to get user to verify
    login_test = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"username": "employee2", "password": "Password123"}
    )
    if login_test.status_code == 200:
        print(f"[PASS] employee2 login verified")
    else:
        print(f"[WARN] employee2 exists but login failed: {login_test.text}")
else:
    print(f"[FAIL] Failed to create employee2: {response.text}")

print("\n" + "="*60)
print("Test users ready!")
print("="*60)
