"""
Integration Tests for Expense Approval Workflow

Tests the complete end-to-end flow:
1. Admin creates employee
2. Employee submits expense
3. Admin approves/rejects expense
4. Employee views result
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from src.api import app
from src.database import Base, get_db
from src.models import User, Organization, OrganizationMember, OrganizationRole


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_workflow.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module")
def client():
    """Create test client"""
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def admin_auth(client):
    """Create and authenticate admin user"""
    # Register admin
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "testadmin",
            "email": "admin@test.com",
            "password": "Admin123!",
        },
    )
    assert response.status_code == 201

    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testadmin", "password": "Admin123!"},
    )
    assert response.status_code == 200
    data = response.json()

    return {
        "token": data["access_token"],
        "user_id": data["user"]["id"],
    }


@pytest.fixture(scope="module")
def organization(client, admin_auth):
    """Create test organization"""
    response = client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {admin_auth['token']}"},
        json={
            "name": "Test Organization",
            "slug": "test-org",
            "description": "Test organization",
            "currency": "USD",
            "timezone": "UTC",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_complete_expense_workflow(client, admin_auth, organization):
    """Test complete expense approval workflow"""

    org_id = organization["id"]
    admin_token = admin_auth["token"]

    # Step 1: Admin creates employee user
    response = client.post(
        "/api/v1/admin/users/create",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Organization-Id": org_id,
        },
        json={
            "email": "employee@test.com",
            "username": "testemployee",
            "full_name": "Test Employee",
            "password": "Employee123!",
            "role": "employee",
        },
    )

    # CRITICAL: Check response structure (prevents "undefined" bug)
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert data["success"] is True
    assert "user" in data, "Response must have nested 'user' key"
    assert "username" in data["user"], "User object must have username"

    employee_user = data["user"]
    assert employee_user["username"] == "testemployee"

    # Step 2: Employee logs in
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testemployee", "password": "Employee123!"},
    )
    assert response.status_code == 200
    employee_token = response.json()["access_token"]

    # Step 3: Employee submits expense
    response = client.post(
        "/api/v1/expenses",
        headers={
            "Authorization": f"Bearer {employee_token}",
            "X-Organization-Id": org_id,
        },
        json={
            "amount": 150.00,
            "vendor": "Office Depot",
            "category": "OFFICE_SUPPLIES",
            "description": "Office supplies",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "payment_method": "PERSONAL_CARD",
            "currency": "USD",
        },
    )
    assert response.status_code == 201
    expense = response.json()
    expense_id = expense["id"]
    assert expense["status"] == "PENDING"

    # Step 4: Admin views pending expenses
    response = client.get(
        "/api/v1/expenses?status=PENDING",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Organization-Id": org_id,
        },
    )
    assert response.status_code == 200
    expenses = response.json()
    assert len(expenses) == 1
    assert expenses[0]["id"] == expense_id

    # Step 5: Admin approves expense
    response = client.put(
        f"/api/v1/expenses/{expense_id}/approve",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Organization-Id": org_id,
        },
    )
    assert response.status_code == 200
    approved_expense = response.json()
    assert approved_expense["status"] == "APPROVED"
    assert approved_expense["approved_by"] is not None

    # Step 6: Employee views approved expense
    response = client.get(
        f"/api/v1/expenses/{expense_id}",
        headers={
            "Authorization": f"Bearer {employee_token}",
            "X-Organization-Id": org_id,
        },
    )
    assert response.status_code == 200
    final_expense = response.json()
    assert final_expense["status"] == "APPROVED"


def test_missing_organization_header_error(client, admin_auth):
    """Test that missing X-Organization-Id header returns proper error"""

    response = client.post(
        "/api/v1/admin/users/create",
        headers={"Authorization": f"Bearer {admin_auth['token']}"},
        json={
            "email": "test@test.com",
            "username": "testuser",
            "password": "Test123!",
            "role": "employee",
        },
    )

    # Should return 400 with standardized error
    assert response.status_code == 400
    data = response.json()

    # Check for standardized error structure
    assert "detail" in data
    error_detail = data["detail"]

    assert error_detail["success"] is False
    assert error_detail["error"] == "MISSING_REQUIRED_HEADER"
    assert error_detail["required_header"] == "X-Organization-Id"
    assert "X-Organization-Id" in error_detail["detail"]


def test_expense_rejection_workflow(client, admin_auth, organization):
    """Test expense rejection flow"""

    org_id = organization["id"]
    admin_token = admin_auth["token"]

    # Login as employee (from previous test)
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testemployee", "password": "Employee123!"},
    )
    assert response.status_code == 200
    employee_token = response.json()["access_token"]

    # Submit expense
    response = client.post(
        "/api/v1/expenses",
        headers={
            "Authorization": f"Bearer {employee_token}",
            "X-Organization-Id": org_id,
        },
        json={
            "amount": 500.00,
            "vendor": "Expensive Restaurant",
            "category": "MEALS_ENTERTAINMENT",
            "description": "Team dinner",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "payment_method": "PERSONAL_CARD",
            "currency": "USD",
        },
    )
    assert response.status_code == 201
    expense_id = response.json()["id"]

    # Admin rejects with reason
    response = client.put(
        f"/api/v1/expenses/{expense_id}/reject",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Organization-Id": org_id,
        },
        json={"reason": "Exceeds policy limit"},
    )
    assert response.status_code == 200
    rejected = response.json()

    assert rejected["status"] == "REJECTED"
    assert rejected["rejection_reason"] == "Exceeds policy limit"


def test_user_deletion_cleanup(client, admin_auth, organization):
    """Test that deleting a user properly cleans up all data"""

    org_id = organization["id"]
    admin_token = admin_auth["token"]

    # Create temporary user
    response = client.post(
        "/api/v1/admin/users/create",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Organization-Id": org_id,
        },
        json={
            "email": "temp@test.com",
            "username": "tempuser",
            "password": "Temp123!",
            "role": "employee",
        },
    )
    assert response.status_code == 200
    user_id = response.json()["user"]["id"]

    # Delete user
    response = client.delete(
        f"/api/v1/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "deleted successfully" in data["message"].lower()

    # Verify user is gone
    response = client.get(
        f"/api/v1/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404
