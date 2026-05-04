"""
SEC-PERM: Permission Boundary Tests (CRITICAL)

Tests the most critical security fixes and permission boundaries:
- CRITICAL-1: Only OWNER can grant OWNER role
- CRITICAL-2: Users cannot modify their own role
- HIGH-2: Only OWNER can remove ADMINs
- Manager $5K approval limit
- Self-approval prevention

Priority: 🔴 CRITICAL
"""

import pytest
from fastapi import status

from src.models import OrganizationRole, UserRole
from tests.factories import (
    add_user_to_organization,
    create_admin,
    create_employee,
    create_manager,
    create_organization_with_owner,
    create_user,
)


@pytest.mark.critical
@pytest.mark.security
class TestPermissionBoundaries:
    """Critical permission boundary tests"""

    # ========================================================================
    # CRITICAL-1: Only OWNER can grant OWNER role
    # ========================================================================

    def test_SEC_PERM_002_admin_cannot_grant_owner_role(
        self, client, db_session
    ):
        """
        Test ID: SEC-PERM-002
        Priority: 🔴 CRITICAL-1

        ADMIN cannot grant OWNER role to another user.
        Only the current OWNER can transfer ownership.

        Security Fix: organizations.py:607
        """
        # Setup: Organization with OWNER and ADMIN
        org, owner = create_organization_with_owner(db_session)
        admin_user = create_user(db_session, email="admin@test.com")
        add_user_to_organization(db_session, admin_user, org, OrganizationRole.ADMIN)
        regular_member = create_user(db_session, email="member@test.com")
        member_membership = add_user_to_organization(db_session, regular_member, org, OrganizationRole.EMPLOYEE)
        db_session.commit()

        # Login as ADMIN
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": admin_user.username, "password": "TestPass123!"}
        )
        admin_token = login_response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Try to grant OWNER role to member
        response = client.patch(
            f"/api/v1/organizations/{org.id}/members/{member_membership.id}/role",
            headers=admin_headers,
            json={"role": "owner"}
        )

        # Should fail with 403 Forbidden
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Only the organization OWNER can grant OWNER role" in response.json()["detail"]

    def test_SEC_PERM_002_owner_can_grant_owner_role(
        self, client, db_session
    ):
        """
        Test ID: SEC-PERM-002b
        Priority: 🔴 CRITICAL-1

        Verify that OWNER CAN grant OWNER role (ownership transfer).
        """
        # Setup
        org, owner = create_organization_with_owner(db_session)
        new_owner_candidate = create_user(db_session, email="newowner@test.com")
        membership = add_user_to_organization(db_session, new_owner_candidate, org, OrganizationRole.EMPLOYEE)
        db_session.commit()

        # Login as OWNER
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": owner.username, "password": "TestPass123!"}
        )
        owner_token = login_response.json()["access_token"]
        owner_headers = {"Authorization": f"Bearer {owner_token}"}

        # Grant OWNER role
        response = client.patch(
            f"/api/v1/organizations/{org.id}/members/{membership.id}/role",
            headers=owner_headers,
            json={"role": "owner"}
        )

        # Should succeed
        assert response.status_code == status.HTTP_200_OK

    # ========================================================================
    # CRITICAL-2: Users cannot modify their own role
    # ========================================================================

    def test_SEC_PERM_001_user_cannot_modify_own_role(
        self, client, db_session
    ):
        """
        Test ID: SEC-PERM-001
        Priority: 🔴 CRITICAL-2

        User cannot modify their own role (privilege escalation prevention).

        Security Fix: organizations.py:594
        """
        # Setup: Organization with ADMIN
        org, owner = create_organization_with_owner(db_session)
        admin_user = create_user(db_session, email="admin@test.com")
        admin_membership = add_user_to_organization(db_session, admin_user, org, OrganizationRole.ADMIN)
        db_session.commit()

        # Login as ADMIN
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": admin_user.username, "password": "TestPass123!"}
        )
        admin_token = login_response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Try to modify own role to OWNER
        response = client.patch(
            f"/api/v1/organizations/{org.id}/members/{admin_membership.id}/role",
            headers=admin_headers,
            json={"role": "owner"}
        )

        # Should fail with 403 Forbidden
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Cannot modify your own role" in response.json()["detail"]

    def test_SEC_PERM_001_owner_cannot_modify_own_role(
        self, client, db_session
    ):
        """
        Test ID: SEC-PERM-001b
        Priority: 🔴 CRITICAL-2

        Even OWNER cannot modify their own role.
        """
        # Setup
        org, owner = create_organization_with_owner(db_session)
        from src.models import OrganizationMember
        owner_membership = db_session.query(OrganizationMember).filter(
            OrganizationMember.user_id == owner.id,
            OrganizationMember.organization_id == org.id
        ).first()
        db_session.commit()

        # Login as OWNER
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": owner.username, "password": "TestPass123!"}
        )
        owner_token = login_response.json()["access_token"]
        owner_headers = {"Authorization": f"Bearer {owner_token}"}

        # Try to demote self to MEMBER (still modifying own role)
        response = client.patch(
            f"/api/v1/organizations/{org.id}/members/{owner_membership.id}/role",
            headers=owner_headers,
            json={"role": "employee"}
        )

        # Should fail
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Cannot modify your own role" in response.json()["detail"]

    # ========================================================================
    # HIGH-2: Only OWNER can remove ADMINs
    # ========================================================================

    def test_SEC_PERM_003_admin_cannot_remove_another_admin(
        self, client, db_session
    ):
        """
        Test ID: SEC-PERM-003
        Priority: 🟠 HIGH-2

        ADMIN cannot remove another ADMIN.
        Only OWNER has power to remove ADMINs.

        Security Fix: organizations.py:660
        """
        # Setup: Organization with 2 ADMINs
        org, owner = create_organization_with_owner(db_session)
        admin1 = create_user(db_session, email="admin1@test.com")
        add_user_to_organization(db_session, admin1, org, OrganizationRole.ADMIN)
        admin2 = create_user(db_session, email="admin2@test.com")
        admin2_membership = add_user_to_organization(db_session, admin2, org, OrganizationRole.ADMIN)
        db_session.commit()

        # Login as ADMIN1
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": admin1.username, "password": "TestPass123!"}
        )
        admin1_token = login_response.json()["access_token"]
        admin1_headers = {"Authorization": f"Bearer {admin1_token}"}

        # Try to remove ADMIN2
        response = client.delete(
            f"/api/v1/organizations/{org.id}/members/{admin2_membership.id}",
            headers=admin1_headers
        )

        # Should fail with 403 Forbidden
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Only the organization OWNER can remove administrators" in response.json()["detail"]

    def test_SEC_PERM_003_owner_can_remove_admin(
        self, client, db_session
    ):
        """
        Test ID: SEC-PERM-003b
        Priority: 🟠 HIGH-2

        Verify OWNER CAN remove ADMIN.
        """
        # Setup
        org, owner = create_organization_with_owner(db_session)
        admin_user = create_user(db_session, email="admin@test.com")
        admin_membership = add_user_to_organization(db_session, admin_user, org, OrganizationRole.ADMIN)
        db_session.commit()

        # Login as OWNER
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": owner.username, "password": "TestPass123!"}
        )
        owner_token = login_response.json()["access_token"]
        owner_headers = {"Authorization": f"Bearer {owner_token}"}

        # Remove ADMIN
        response = client.delete(
            f"/api/v1/organizations/{org.id}/members/{admin_membership.id}",
            headers=owner_headers
        )

        # Should succeed
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_SEC_PERM_003_admin_can_remove_member(
        self, client, db_session
    ):
        """
        Test ID: SEC-PERM-003c
        Priority: 🟠 HIGH-2

        Verify ADMIN CAN remove regular MEMBERs (just not other ADMINs).
        """
        # Setup
        org, owner = create_organization_with_owner(db_session)
        admin_user = create_user(db_session, email="admin@test.com")
        add_user_to_organization(db_session, admin_user, org, OrganizationRole.ADMIN)
        member = create_user(db_session, email="member@test.com")
        member_membership = add_user_to_organization(db_session, member, org, OrganizationRole.EMPLOYEE)
        db_session.commit()

        # Login as ADMIN
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": admin_user.username, "password": "TestPass123!"}
        )
        admin_token = login_response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Remove MEMBER
        response = client.delete(
            f"/api/v1/organizations/{org.id}/members/{member_membership.id}",
            headers=admin_headers
        )

        # Should succeed
        assert response.status_code == status.HTTP_204_NO_CONTENT

    # ========================================================================
    # ROLE-BASED PERMISSION TESTS
    # ========================================================================

    def test_ROLE_EMP_004_employee_cannot_approve_expense(
        self, client, db_session
    ):
        """
        Test ID: ROLE-EMP-004
        Priority: 🔴 CRITICAL

        EMPLOYEE cannot approve expenses (no approval permission).
        """
        from tests.factories import create_pending_expense

        # Setup: Organization with employee and their expense
        org, owner = create_organization_with_owner(db_session)
        employee = create_employee(db_session)
        add_user_to_organization(db_session, employee, org, OrganizationRole.EMPLOYEE)
        expense = create_pending_expense(db_session, employee, org, amount=100.0)
        db_session.commit()

        # Login as employee
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": employee.username, "password": "TestPass123!"}
        )
        employee_token = login_response.json()["access_token"]
        employee_headers = {
            "Authorization": f"Bearer {employee_token}",
            "X-Organization-Id": org.id
        }

        # Try to approve expense
        response = client.put(  # PUT not POST
            f"/api/v1/expenses/{expense.id}/approve",
            headers=employee_headers
        )

        # Should fail with 403 Forbidden
        assert response.status_code == status.HTTP_403_FORBIDDEN

    # TEMPORARILY DISABLED — ACCOUNTANT role disconnected
    # def test_ROLE_ACC_002_accountant_cannot_approve_expense(
    #     self, client, db_session
    # ):
    #     """
    #     Test ID: ROLE-ACC-002
    #     Priority: 🔴 CRITICAL
    #
    #     ACCOUNTANT cannot approve expenses (read-only role).
    #     """
    #     from tests.factories import create_accountant, create_pending_expense
    #
    #     # Setup
    #     org, owner = create_organization_with_owner(db_session)
    #     accountant = create_accountant(db_session)
    #     add_user_to_organization(db_session, accountant, org, OrganizationRole.EMPLOYEE)
    #     expense = create_pending_expense(db_session, owner, org, amount=100.0)
    #     db_session.commit()
    #
    #     # Login as accountant
    #     login_response = client.post(
    #         "/api/v1/auth/login",
    #         json={"username": accountant.username, "password": "TestPass123!"}
    #     )
    #     accountant_token = login_response.json()["access_token"]
    #     accountant_headers = {
    #         "Authorization": f"Bearer {accountant_token}",
    #         "X-Organization-Id": org.id
    #     }
    #
    #     # Try to approve expense
    #     response = client.put(  # PUT not POST
    #         f"/api/v1/expenses/{expense.id}/approve",
    #         headers=accountant_headers
    #     )
    #
    #     # Should fail with 403 Forbidden
    #     assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_ROLE_MGR_002_manager_cannot_approve_over_5k(
        self, client, db_session
    ):
        """
        Test ID: ROLE-MGR-002
        Priority: 🔴 CRITICAL

        MANAGER cannot approve expenses >$5,000.

        Approval Limit: $5,000 (permissions.py:484)
        """
        from tests.factories import create_manager_approval_scenario

        # Setup: Manager with employee's $10K expense
        scenario = create_manager_approval_scenario(db_session)
        manager = scenario['manager']
        expense_over_5k = scenario['expense_over_5k']
        org = scenario['org']

        # Login as manager
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": manager.username, "password": "TestPass123!"}
        )
        manager_token = login_response.json()["access_token"]
        manager_headers = {
            "Authorization": f"Bearer {manager_token}",
            "X-Organization-Id": org.id
        }

        # Try to approve $10K expense
        response = client.put(  # PUT not POST
            f"/api/v1/expenses/{expense_over_5k.id}/approve",
            headers=manager_headers
        )

        # Should fail with 403 Forbidden
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Expenses over $5000" in response.json()["detail"] or "require admin approval" in response.json()["detail"]

    def test_ROLE_MGR_001_manager_can_approve_under_5k(
        self, client, db_session
    ):
        """
        Test ID: ROLE-MGR-001
        Priority: 🔴 CRITICAL

        MANAGER CAN approve expenses ≤$5,000 from their department.
        """
        from tests.factories import create_manager_approval_scenario

        # Setup: Manager with employee's $3K expense
        scenario = create_manager_approval_scenario(db_session)
        manager = scenario['manager']
        expense_under_5k = scenario['expense_under_5k']
        org = scenario['org']

        # Login as manager
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": manager.username, "password": "TestPass123!"}
        )
        manager_token = login_response.json()["access_token"]
        manager_headers = {
            "Authorization": f"Bearer {manager_token}",
            "X-Organization-Id": org.id
        }

        # Approve $3K expense
        response = client.put(  # PUT not POST
            f"/api/v1/expenses/{expense_under_5k.id}/approve",
            headers=manager_headers
        )

        # Should succeed
        assert response.status_code == status.HTTP_200_OK

    def test_ROLE_MGR_006_manager_cannot_self_approve(
        self, client, db_session
    ):
        """
        Test ID: ROLE-MGR-006
        Priority: 🔴 CRITICAL

        MANAGER cannot approve their own expense (conflict of interest).
        """
        from tests.factories import create_manager, create_pending_expense

        # Setup: Manager with their own expense
        org, owner = create_organization_with_owner(db_session)
        manager = create_manager(db_session, department_id="sales")
        add_user_to_organization(db_session, manager, org, OrganizationRole.ADMIN)
        manager_expense = create_pending_expense(db_session, manager, org, amount=1000.0)
        db_session.commit()

        # Login as manager
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": manager.username, "password": "TestPass123!"}
        )
        manager_token = login_response.json()["access_token"]
        manager_headers = {
            "Authorization": f"Bearer {manager_token}",
            "X-Organization-Id": org.id
        }

        # Try to approve own expense
        response = client.put(  # PUT not POST
            f"/api/v1/expenses/{manager_expense.id}/approve",
            headers=manager_headers
        )

        # Should fail with 403 Forbidden
        # Note: Self-approval is prevented by permissions.py:466
        assert response.status_code == status.HTTP_403_FORBIDDEN or response.status_code == status.HTTP_400_BAD_REQUEST
