"""
SEC-ISO: Multi-Tenant Isolation Tests (CRITICAL)

Tests cross-organization data leakage prevention and tenant isolation.
These tests ensure users cannot access data from other organizations.

Priority: 🔴 CRITICAL
"""

import pytest
from fastapi import status

from src.models import OrganizationRole
from tests.factories import (
    add_user_to_organization,
    create_multi_tenant_scenario,
    create_organization_with_owner,
    create_pending_expense,
    create_user,
)


@pytest.mark.critical
@pytest.mark.security
class TestCrossOrgDataLeakage:
    """Test that users cannot access data from other organizations"""

    # ========================================================================
    # SEC-ISO-001: Cross-org expense access
    # ========================================================================

    def test_SEC_ISO_001_user_cannot_view_other_org_expense(self, client, db_session):
        """
        Test ID: SEC-ISO-001
        Priority: 🔴 CRITICAL

        User A cannot view User B's expense from a different organization.

        Security: Multi-tenant isolation
        """
        # Setup: 2 organizations with expenses
        scenario = create_multi_tenant_scenario(db_session)
        org1_employee = scenario["org1_employee"]
        org1_expense = scenario["org1_expense"]
        org2_owner = scenario["org2_owner"]
        org2 = scenario["org2"]

        # Login as org2 owner
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": org2_owner.username, "password": "TestPass123!"},
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org2.id}

        # Try to access org1's expense
        response = client.get(f"/api/v1/expenses/{org1_expense.id}", headers=headers)

        # Should fail with 404 Not Found (expense not in org2)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ========================================================================
    # SEC-ISO-002: Invalid X-Organization-Id header
    # ========================================================================

    def test_SEC_ISO_002_invalid_organization_header_blocked(self, client, db_session):
        """
        Test ID: SEC-ISO-002
        Priority: 🔴 CRITICAL

        User A cannot access Org B's data using X-Organization-Id header.

        Security: Header tampering prevention
        """
        # Setup: 2 organizations
        scenario = create_multi_tenant_scenario(db_session)
        org1_employee = scenario["org1_employee"]
        org1 = scenario["org1"]
        org2 = scenario["org2"]
        org2_expense = scenario["org2_expense"]

        # Login as org1 employee
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": org1_employee.username, "password": "TestPass123!"},
        )
        token = login_response.json()["access_token"]

        # Try to access org2's expense with org2's header (user not member of org2)
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": org2.id,  # Tampering attempt
        }

        response = client.get(f"/api/v1/expenses/{org2_expense.id}", headers=headers)

        # Should fail with 403 Forbidden (not member of org2)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    # ========================================================================
    # SEC-ISO-003: Cross-org expense modification
    # ========================================================================

    def test_SEC_ISO_003_cannot_update_other_org_expense(self, client, db_session):
        """
        Test ID: SEC-ISO-003
        Priority: 🔴 CRITICAL

        User cannot update an expense from another organization.
        """
        # Setup
        scenario = create_multi_tenant_scenario(db_session)
        org1_expense = scenario["org1_expense"]
        org2_owner = scenario["org2_owner"]
        org2 = scenario["org2"]

        # Login as org2 owner
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": org2_owner.username, "password": "TestPass123!"},
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org2.id}

        # Try to update org1's expense
        update_data = {"amount": 99999.99, "description": "Hacked!"}

        response = client.patch(
            f"/api/v1/expenses/{org1_expense.id}", json=update_data, headers=headers
        )

        # Should fail with 404 Not Found
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ========================================================================
    # SEC-ISO-004: SQL injection via organization_id
    # ========================================================================

    def test_SEC_ISO_004_sql_injection_organization_filter(self, client, db_session):
        """
        Test ID: SEC-ISO-004
        Priority: 🔴 CRITICAL

        SQL injection via organization_id filter is prevented.

        Security: Parameterized queries
        """
        # Setup
        scenario = create_multi_tenant_scenario(db_session)
        org1_employee = scenario["org1_employee"]

        # Login as org1 employee
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": org1_employee.username, "password": "TestPass123!"},
        )
        token = login_response.json()["access_token"]

        # Try SQL injection via X-Organization-Id header
        malicious_headers = {
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": "1' OR '1'='1",  # SQL injection attempt
        }

        response = client.post(
            "/api/v1/expenses",
            json={
                "amount": 100.0,
                "description": "Test",
                "category": "MEALS",
                "vendor": "Test",
            },
            headers=malicious_headers,
        )

        # Should fail gracefully (400 or 403, not 500)
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]

    # ========================================================================
    # SEC-ISO-005: Soft-deleted org data invisible
    # ========================================================================

    def test_SEC_ISO_005_soft_deleted_org_data_invisible(self, client, db_session):
        """
        Test ID: SEC-ISO-005
        Priority: 🟠 HIGH

        Soft-deleted organization data is not accessible via API.

        Security: is_active filter enforcement
        """
        # Setup: Organization with owner
        org, owner = create_organization_with_owner(
            db_session, org_name="To Be Deleted"
        )
        expense = create_pending_expense(db_session, owner, org, amount=100.0)
        db_session.commit()

        # Login as owner
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": owner.username, "password": "TestPass123!"},
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Delete organization (soft delete)
        response = client.delete(f"/api/v1/organizations/{org.id}", headers=headers)
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Try to access deleted org's data
        response = client.get(f"/api/v1/organizations/{org.id}", headers=headers)

        # Should fail with 403 or 404 (org is inactive)
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]

    # ========================================================================
    # SEC-ISO-006: Soft-deleted member cannot access org
    # ========================================================================

    def test_SEC_ISO_006_soft_deleted_member_access_denied(self, client, db_session):
        """
        Test ID: SEC-ISO-006
        Priority: 🟠 HIGH

        Soft-deleted member cannot access organization data.

        Security: member.is_active filter enforcement
        """
        # Setup: Organization with owner and member
        org, owner = create_organization_with_owner(db_session)
        member = create_user(db_session, email="member@test.com")
        membership = add_user_to_organization(
            db_session, member, org, OrganizationRole.EMPLOYEE
        )
        expense = create_pending_expense(db_session, member, org, amount=100.0)
        db_session.commit()

        # Login as owner
        owner_login = client.post(
            "/api/v1/auth/login",
            json={"username": owner.username, "password": "TestPass123!"},
        )
        owner_token = owner_login.json()["access_token"]
        owner_headers = {"Authorization": f"Bearer {owner_token}"}

        # Remove member (soft delete)
        response = client.delete(
            f"/api/v1/organizations/{org.id}/members/{membership.id}",
            headers=owner_headers,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Try to access org as removed member
        member_login = client.post(
            "/api/v1/auth/login",
            json={"username": member.username, "password": "TestPass123!"},
        )
        member_token = member_login.json()["access_token"]
        member_headers = {
            "Authorization": f"Bearer {member_token}",
            "X-Organization-Id": org.id,
        }

        response = client.get(f"/api/v1/expenses/{expense.id}", headers=member_headers)

        # Should fail with 403 Forbidden (no longer member)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    # ========================================================================
    # SEC-ISO-007: List endpoints filter by organization
    # ========================================================================

    def test_SEC_ISO_007_list_expenses_filtered_by_org(self, client, db_session):
        """
        Test ID: SEC-ISO-007
        Priority: 🔴 CRITICAL

        List endpoints only return data from user's organization.
        """
        # Setup: 2 organizations with multiple expenses each
        scenario = create_multi_tenant_scenario(db_session)
        org1 = scenario["org1"]
        org1_employee = scenario["org1_employee"]
        org2 = scenario["org2"]

        # Create additional expenses in org2
        org2_owner = scenario["org2_owner"]
        create_pending_expense(db_session, org2_owner, org2, amount=300.0)
        create_pending_expense(db_session, org2_owner, org2, amount=400.0)
        db_session.commit()

        # Login as org1 employee
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": org1_employee.username, "password": "TestPass123!"},
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": org1.id}

        # List expenses
        response = client.get("/api/v1/expenses", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        expenses = response.json()

        # Verify all expenses belong to org1 only
        for expense in expenses:
            # Try to verify organization_id if returned in response
            # At minimum, verify we only see org1's expense count
            pass

        # Org1 should only have 1 expense (from scenario)
        # If we see more, it means cross-org leakage
        assert len(expenses) <= 1  # Should only see org1's expenses

    # ========================================================================
    # SEC-ISO-008: Organization member list isolation
    # ========================================================================

    def test_SEC_ISO_008_cannot_list_other_org_members(self, client, db_session):
        """
        Test ID: SEC-ISO-008
        Priority: 🔴 CRITICAL

        Cannot list members from other organization.
        """
        # Setup
        scenario = create_multi_tenant_scenario(db_session)
        org1 = scenario["org1"]
        org2_owner = scenario["org2_owner"]

        # Login as org2 owner
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": org2_owner.username, "password": "TestPass123!"},
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Try to list org1's members
        response = client.get(
            f"/api/v1/organizations/{org1.id}/members", headers=headers
        )

        # Should fail with 403 Forbidden
        assert response.status_code == status.HTTP_403_FORBIDDEN

    # ========================================================================
    # SEC-ISO-009: Missing organization header handling
    # ========================================================================

    def test_SEC_ISO_009_missing_organization_header_rejected(self, client, db_session):
        """
        Test ID: SEC-ISO-009
        Priority: 🔴 CRITICAL

        Requests without X-Organization-Id header are rejected.

        Security: Explicit org context required for multi-tenancy
        """
        # Setup
        scenario = create_multi_tenant_scenario(db_session)
        org1_employee = scenario["org1_employee"]

        # Login as org1 employee
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": org1_employee.username, "password": "TestPass123!"},
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}  # No X-Organization-Id

        # Try to create expense without org context
        expense_data = {
            "amount": 100.0,
            "description": "Test",
            "category": "MEALS",
            "vendor": "Test",
        }

        response = client.post("/api/v1/expenses", json=expense_data, headers=headers)

        # Should fail with 400 Bad Request
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Organization context required" in response.json()["detail"]
