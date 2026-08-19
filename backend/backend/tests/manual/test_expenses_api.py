"""Test the expenses API endpoint directly"""
import sys
sys.path.insert(0, 'src')

from fastapi.testclient import TestClient
from src.api import app
from src.database import SessionLocal
from src.models import User, OrganizationMember

# Create test client
client = TestClient(app)

# Get an admin user and their org
db = SessionLocal()
admin = db.query(User).filter(User.role == 'admin').first()

if not admin:
    print("No admin user found")
    exit(1)

# Get admin's organization
membership = db.query(OrganizationMember).filter(
    OrganizationMember.user_id == admin.id
).first()

if not membership:
    print("Admin not in any organization")
    exit(1)

print(f"Testing as: {admin.email}")
print(f"Organization: {membership.organization_id}")

# Login to get token
login_response = client.post("/api/v1/auth/login", json={
    "username": admin.username,
    "password": "admin123"  # Default password - change if different
})

if login_response.status_code != 200:
    print(f"Login failed: {login_response.status_code}")
    print(login_response.text)
    exit(1)

token = login_response.json()["access_token"]
print(f"✓ Logged in successfully")

# Test the expenses endpoint
headers = {
    "Authorization": f"Bearer {token}",
    "X-Organization-Id": membership.organization_id
}

print(f"\nTesting GET /api/v1/expenses?status_filter=pending")
response = client.get(
    "/api/v1/expenses?status_filter=pending",
    headers=headers
)

print(f"Status: {response.status_code}")
print(f"\nResponse:")
import json
print(json.dumps(response.json(), indent=2))
