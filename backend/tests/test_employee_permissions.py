"""
ROLE-EMP: Employee Permission Tests (CRITICAL)

Tests that EMPLOYEE role has correct permissions:
- Can submit and view own expenses
- Cannot view others' expenses
- Cannot approve expenses
- Cannot manage organization
- Read-only access to org data

Priority: 🔴 CRITICAL
"""

import pytest
from fastapi import status

from src.models import ExpenseStatus, OrganizationRole
from tests.factories import (
    add_user_to_organization,
    create_employee,
    create_multi_tenant_scenario,
    create_organization_with_owner,
    create_pending_expense,
    create_user,
)


@pytest.mark.critical
@pytest.mark.permissions
@pytest.mark.role_emp
class TestEmployeePermissions:
    """Test EMPLOYEE role permissions"""

    # ========================================================================
    # ROLE-EMP-001: Employee can submit expense
    # ========================================================================

    def test_ROLE_EMP_001_employee_can_submit_expense(
        self, client, db_session
    ):
        """
        Test ID: ROLE-EMP-001
        Priority: 🔴 CRITICAL

        EMPLOYEE can submit expenses in their organization.
        """
        # Setup: Employee in organization
        org, owner = create_organization_with_owner(db_session)
        employee = create_employee(db_session)
        add_user_to_organization(db_session, employee, org, OrganizationRole.MEMBER)
        db_session.commit()

        # Login as employee
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": employee.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": org.id
        }

        # Submit expense
        expense_data = {
            "amount": 100.0,
            "description": "Business lunch",
            "category": "MEALS",
            "vendor": "Restaurant",
        }

        response = client.post(
            "/api/v1/expenses",
            json=expense_data,
            headers=headers
        )

        # Should succeed
        assert response.status_code == status.HTTP_201_CREATED
        expense = response.json()
        assert expense["amount"] == 100.0
        assert expense["status"] == "PENDING"  # API returns uppercase

    # ========================================================================
    # ROLE-EMP-002: Employee can view own expense
    # ========================================================================

    def test_ROLE_EMP_002_employee_can_view_own_expense(
        self, client, db_session
    ):
        """
        Test ID: ROLE-EMP-002
        Priority: 🔴 CRITICAL

        EMPLOYEE can view their own expenses.
        """
        # Setup
        org, owner = create_organization_with_owner(db_session)
        employee = create_employee(db_session)
        add_user_to_organization(db_session, employee, org, OrganizationRole.MEMBER)
        expense = create_pending_expense(db_session, employee, org, amount=100.0)
        db_session.commit()

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": employee.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": org.id
        }

        # View own expense
        response = client.get(
            f"/api/v1/expenses/{expense.id}",
            headers=headers
        )

        # Should succeed
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == expense.id

    # ========================================================================
    # ROLE-EMP-003: Employee cannot view others' expense
    # ========================================================================

    def test_ROLE_EMP_003_employee_cannot_view_others_expense(
        self, client, db_session
    ):
        """
        Test ID: ROLE-EMP-003
        Priority: 🔴 CRITICAL

        EMPLOYEE cannot view another user's expense (same org).

        Security: Role-based access control
        """
        # Setup: 2 employees in same org
        org, owner = create_organization_with_owner(db_session)
        employee1 = create_employee(db_session, email="emp1@test.com")
        employee2 = create_employee(db_session, email="emp2@test.com")
        add_user_to_organization(db_session, employee1, org, OrganizationRole.MEMBER)
        add_user_to_organization(db_session, employee2, org, OrganizationRole.MEMBER)

        # Employee2's expense
        employee2_expense = create_pending_expense(db_session, employee2, org, amount=200.0)
        db_session.commit()

        # Login as employee1
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": employee1.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": org.id
        }

        # Try to view employee2's expense
        response = client.get(
            f"/api/v1/expenses/{employee2_expense.id}",
            headers=headers
        )

        # Should fail with 403 Forbidden
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "can only access your own expenses" in response.json()["detail"].lower()

    # ========================================================================
    # ROLE-EMP-005: Employee can edit own pending expense
    # ========================================================================

    def test_ROLE_EMP_005_employee_can_edit_own_pending_expense(
        self, client, db_session
    ):
        """
        Test ID: ROLE-EMP-005
        Priority: 🟠 HIGH

        EMPLOYEE can edit their own PENDING expense.
        """
        # Setup
        org, owner = create_organization_with_owner(db_session)
        employee = create_employee(db_session)
        add_user_to_organization(db_session, employee, org, OrganizationRole.MEMBER)
        expense = create_pending_expense(db_session, employee, org, amount=100.0)
        db_session.commit()

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": employee.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": org.id
        }

        # Edit own pending expense
        update_data = {
            "amount": 150.0,
            "description": "Updated description"
        }

        response = client.patch(
            f"/api/v1/expenses/{expense.id}",
            json=update_data,
            headers=headers
        )

        # Should succeed
        assert response.status_code == status.HTTP_200_OK
        updated_expense = response.json()
        assert updated_expense["amount"] == 150.0

    # ========================================================================
    # ROLE-EMP-006: Employee cannot edit approved expense
    # ========================================================================

    def test_ROLE_EMP_006_employee_cannot_edit_approved_expense(
        self, client, db_session
    ):
        """
        Test ID: ROLE-EMP-006
        Priority: 🟠 HIGH

        EMPLOYEE cannot edit APPROVED expenses (immutable after approval).
        """
        from tests.factories import create_approved_expense

        # Setup
        org, owner = create_organization_with_owner(db_session)
        employee = create_employee(db_session)
        add_user_to_organization(db_session, employee, org, OrganizationRole.MEMBER)
        approved_expense = create_approved_expense(
            db_session,
            employee,
            org,
            amount=100.0,
            approved_by=owner.id
        )
        db_session.commit()

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": employee.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": org.id
        }

        # Try to edit approved expense
        update_data = {
            "amount": 999.99,
            "description": "Trying to change approved expense"
        }

        response = client.patch(
            f"/api/v1/expenses/{approved_expense.id}",
            json=update_data,
            headers=headers
        )

        # Should fail (403 or 400 depending on implementation)
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST]

    # ========================================================================
    # ROLE-EMP-007: Employee can upload receipt
    # ========================================================================

    def test_ROLE_EMP_007_employee_can_upload_receipt(
        self, client, db_session
    ):
        """
        Test ID: ROLE-EMP-007
        Priority: 🟠 HIGH

        EMPLOYEE can upload receipts for their expenses.
        """
        # Setup
        org, owner = create_organization_with_owner(db_session)
        employee = create_employee(db_session)
        add_user_to_organization(db_session, employee, org, OrganizationRole.MEMBER)
        expense = create_pending_expense(db_session, employee, org, amount=100.0)
        db_session.commit()

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": employee.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": org.id
        }

        # Upload receipt (multipart/form-data)
        import io
        receipt_file = io.BytesIO(b"fake image data")

        response = client.post(
            f"/api/v1/receipts/upload/{expense.id}",  # Correct endpoint path
            files={"file": ("receipt.jpg", receipt_file, "image/jpeg")},
            headers=headers
        )

        # Should succeed (201 or 200 depending on endpoint)
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]

    # ========================================================================
    # ROLE-EMP-008: Employee can view org members (read-only)
    # ========================================================================

    def test_ROLE_EMP_008_employee_can_view_org_members(
        self, client, db_session
    ):
        """
        Test ID: ROLE-EMP-008
        Priority: 🟡 MEDIUM

        EMPLOYEE can view organization members (read-only access).
        """
        # Setup: Organization with multiple members
        org, owner = create_organization_with_owner(db_session)
        employee = create_employee(db_session)
        add_user_to_organization(db_session, employee, org, OrganizationRole.MEMBER)
        db_session.commit()

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": employee.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # View org members
        response = client.get(
            f"/api/v1/organizations/{org.id}/members",
            headers=headers
        )

        # Should succeed (read-only access)
        assert response.status_code == status.HTTP_200_OK
        members = response.json()
        assert len(members) >= 2  # Owner + employee

    # ========================================================================
    # ROLE-EMP-009: Employee cannot invite members
    # ========================================================================

    def test_ROLE_EMP_009_employee_cannot_invite_members(
        self, client, db_session
    ):
        """
        Test ID: ROLE-EMP-009
        Priority: 🟠 HIGH

        EMPLOYEE cannot invite new members (OWNER/ADMIN only).
        """
        # Setup
        org, owner = create_organization_with_owner(db_session)
        employee = create_employee(db_session)
        add_user_to_organization(db_session, employee, org, OrganizationRole.MEMBER)
        db_session.commit()

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": employee.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Try to invite someone
        invitation_data = {
            "email": "newuser@test.com",
            "role": "member"
        }

        response = client.post(
            f"/api/v1/organizations/{org.id}/invitations",
            json=invitation_data,
            headers=headers
        )

        # Should fail with 403 Forbidden
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Only organization owners and admins can invite" in response.json()["detail"]

    # ========================================================================
    # ROLE-EMP-010: Employee cannot delete others' expenses
    # ========================================================================

    def test_ROLE_EMP_010_employee_cannot_delete_others_expenses(
        self, client, db_session
    ):
        """
        Test ID: ROLE-EMP-010
        Priority: 🔴 CRITICAL

        EMPLOYEE cannot delete another user's expense.

        Security: Prevent unauthorized deletion
        """
        # Setup: 2 employees in same org
        org, owner = create_organization_with_owner(db_session)
        employee1 = create_employee(db_session, email="emp1@test.com")
        employee2 = create_employee(db_session, email="emp2@test.com")
        add_user_to_organization(db_session, employee1, org, OrganizationRole.MEMBER)
        add_user_to_organization(db_session, employee2, org, OrganizationRole.MEMBER)

        # Employee2's expense
        employee2_expense = create_pending_expense(db_session, employee2, org, amount=200.0)
        db_session.commit()

        # Login as employee1
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": employee1.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": org.id
        }

        # Try to delete employee2's expense
        response = client.delete(
            f"/api/v1/expenses/{employee2_expense.id}",
            headers=headers
        )

        # Should fail with 403 Forbidden
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]

    # ========================================================================
    # ROLE-EMP-011: Employee can list own expenses only
    # ========================================================================

    def test_ROLE_EMP_011_employee_lists_own_expenses_only(
        self, client, db_session
    ):
        """
        Test ID: ROLE-EMP-011
        Priority: 🔴 CRITICAL

        EMPLOYEE listing expenses only sees their own (not others in org).
        """
        # Setup: 2 employees with expenses
        org, owner = create_organization_with_owner(db_session)
        employee1 = create_employee(db_session, email="emp1@test.com")
        employee2 = create_employee(db_session, email="emp2@test.com")
        add_user_to_organization(db_session, employee1, org, OrganizationRole.MEMBER)
        add_user_to_organization(db_session, employee2, org, OrganizationRole.MEMBER)

        # Create expenses for both
        emp1_expense = create_pending_expense(db_session, employee1, org, amount=100.0)
        emp2_expense = create_pending_expense(db_session, employee2, org, amount=200.0)
        db_session.commit()

        # Login as employee1
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": employee1.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": org.id
        }

        # List expenses
        response = client.get(
            "/api/v1/expenses",
            headers=headers
        )

        assert response.status_code == status.HTTP_200_OK
        expenses = response.json()

        # Should only see own expense
        assert len(expenses) == 1
        assert expenses[0]["id"] == emp1_expense.id

    # ========================================================================
    # ROLE-EMP-012: Employee cannot update organization settings
    # ========================================================================

    def test_ROLE_EMP_012_employee_cannot_update_org_settings(
        self, client, db_session
    ):
        """
        Test ID: ROLE-EMP-012
        Priority: 🟠 HIGH

        EMPLOYEE cannot update organization settings (OWNER/ADMIN only).
        """
        # Setup
        org, owner = create_organization_with_owner(db_session)
        employee = create_employee(db_session)
        add_user_to_organization(db_session, employee, org, OrganizationRole.MEMBER)
        db_session.commit()

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": employee.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Try to update org settings
        update_data = {
            "name": "Hacked Organization",
            "description": "Employee trying to change settings"
        }

        response = client.patch(
            f"/api/v1/organizations/{org.id}",
            json=update_data,
            headers=headers
        )

        # Should fail with 403 Forbidden
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Only organization owners and admins" in response.json()["detail"]
