"""
Tests for Multi-Tenant Isolation
Ensures cross-tenant data leakage is prevented
"""

import pytest
from fastapi import status
from src.repository import ExpenseRepository
from src.models import Expense, ExpenseCategory, ExpenseStatus


class TestTenantIsolation:
    """Test tenant isolation and cross-tenant data protection"""

    def test_expense_repository_filters_by_organization(
        self,
        db_session,
        test_organization,
        second_organization,
        test_user,
        second_org_user,
    ):
        """Test that repository automatically filters by organization"""
        # Create expenses in different organizations
        expense1 = Expense(
            id="exp_org1",
            organization_id=test_organization.id,
            user_id=test_user.id,
            amount=100.00,
            vendor="Test Vendor 1",
            description="Org 1 expense",
            category=ExpenseCategory.MEALS,
            status=ExpenseStatus.PENDING,
        )
        expense2 = Expense(
            id="exp_org2",
            organization_id=second_organization.id,
            user_id=second_org_user.id,
            amount=200.00,
            vendor="Test Vendor 2",
            description="Org 2 expense",
            category=ExpenseCategory.MEALS,
            status=ExpenseStatus.PENDING,
        )
        db_session.add_all([expense1, expense2])
        db_session.commit()

        # Repository for org 1 should only see org 1 expenses
        repo1 = ExpenseRepository(db_session, organization_id=test_organization.id)
        expenses1 = repo1.get_all()
        assert len(expenses1) == 1
        assert expenses1[0].id == "exp_org1"

        # Repository for org 2 should only see org 2 expenses
        repo2 = ExpenseRepository(db_session, organization_id=second_organization.id)
        expenses2 = repo2.get_all()
        assert len(expenses2) == 1
        assert expenses2[0].id == "exp_org2"

    def test_cannot_access_other_organization_expense_by_id(
        self,
        db_session,
        test_organization,
        second_organization,
        test_user,
        second_org_user,
    ):
        """Test that you cannot access another organization's expense by ID"""
        # Create expense in org 2
        expense = Expense(
            id="exp_secret",
            organization_id=second_organization.id,
            user_id=second_org_user.id,
            amount=100.00,
            vendor="Secret Vendor",
            description="Secret expense",
            category=ExpenseCategory.MEALS,
            status=ExpenseStatus.PENDING,
        )
        db_session.add(expense)
        db_session.commit()

        # Try to access with org 1 repository
        repo1 = ExpenseRepository(db_session, organization_id=test_organization.id)
        result = repo1.get_by_id("exp_secret")

        # Should return None (not found in this organization)
        assert result is None

    def test_api_endpoint_respects_organization_header(
        self,
        client,
        test_organization,
        second_organization,
        user_with_organization,
        second_org_user,
        org_headers,
        second_org_headers,
    ):
        """Test that API endpoints respect X-Organization-Id header"""
        # Create expense via API with org 1 headers
        expense_data = {
            "user_id": user_with_organization.id,
            "amount": 150.00,
            "vendor": "Test Vendor",
            "description": "Test expense",
            "category": "MEALS",
        }

        response = client.post(
            "/api/v1/expenses", json=expense_data, headers=org_headers
        )
        assert response.status_code == status.HTTP_201_CREATED
        expense_id = response.json()["expense"]["id"]

        # User from org 1 should see the expense
        response = client.get(f"/api/v1/expenses/{expense_id}", headers=org_headers)
        assert response.status_code == status.HTTP_200_OK

        # User from org 2 should NOT see the expense (different organization)
        response = client.get(
            f"/api/v1/expenses/{expense_id}", headers=second_org_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_expenses_only_shows_own_organization(
        self,
        client,
        test_organization,
        second_organization,
        user_with_organization,
        second_org_user,
        org_headers,
        second_org_headers,
    ):
        """Test that listing expenses only shows expenses from user's organization"""
        # Create expenses for both organizations
        expense_data_1 = {
            "user_id": user_with_organization.id,
            "amount": 100.00,
            "vendor": "Vendor 1",
            "description": "Org 1 expense",
            "category": "MEALS",
        }

        expense_data_2 = {
            "user_id": second_org_user.id,
            "amount": 200.00,
            "vendor": "Vendor 2",
            "description": "Org 2 expense",
            "category": "TRAVEL",
        }

        # Create expense in org 1
        client.post("/api/v1/expenses", json=expense_data_1, headers=org_headers)

        # Create expense in org 2
        client.post("/api/v1/expenses", json=expense_data_2, headers=second_org_headers)

        # List expenses for org 1 - should only see 1
        response = client.get("/api/v1/expenses", headers=org_headers)
        assert response.status_code == status.HTTP_200_OK
        expenses = response.json()
        assert len(expenses) == 1
        assert expenses[0]["description"] == "Org 1 expense"

        # List expenses for org 2 - should only see 1
        response = client.get("/api/v1/expenses", headers=second_org_headers)
        assert response.status_code == status.HTTP_200_OK
        expenses = response.json()
        assert len(expenses) == 1
        assert expenses[0]["description"] == "Org 2 expense"

    def test_cannot_update_other_organization_expense(
        self,
        client,
        test_organization,
        second_organization,
        user_with_organization,
        second_org_user,
        org_headers,
        second_org_headers,
    ):
        """Test that you cannot update an expense from another organization"""
        # Create expense in org 1
        expense_data = {
            "user_id": user_with_organization.id,
            "amount": 100.00,
            "vendor": "Vendor 1",
            "description": "Org 1 expense",
            "category": "MEALS",
        }
        response = client.post(
            "/api/v1/expenses", json=expense_data, headers=org_headers
        )
        expense_id = response.json()["expense"]["id"]

        # Try to update with org 2 credentials
        update_data = {"amount": 999.99, "description": "Hacked!"}
        response = client.patch(
            f"/api/v1/expenses/{expense_id}",
            json=update_data,
            headers=second_org_headers,
        )

        # Should fail with 404 (not found in org 2)
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Verify expense unchanged in org 1
        response = client.get(f"/api/v1/expenses/{expense_id}", headers=org_headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["amount"] == 100.00
        assert response.json()["description"] == "Org 1 expense"

    def test_cannot_delete_other_organization_expense(
        self,
        client,
        test_organization,
        second_organization,
        user_with_organization,
        second_org_user,
        org_headers,
        second_org_headers,
    ):
        """Test that you cannot delete an expense from another organization"""
        # Create expense in org 1
        expense_data = {
            "user_id": user_with_organization.id,
            "amount": 100.00,
            "vendor": "Vendor 1",
            "description": "Org 1 expense",
            "category": "MEALS",
        }
        response = client.post(
            "/api/v1/expenses", json=expense_data, headers=org_headers
        )
        expense_id = response.json()["expense"]["id"]

        # Try to delete with org 2 credentials
        response = client.delete(
            f"/api/v1/expenses/{expense_id}", headers=second_org_headers
        )

        # Should fail with 404 (not found in org 2)
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Verify expense still exists in org 1
        response = client.get(f"/api/v1/expenses/{expense_id}", headers=org_headers)
        assert response.status_code == status.HTTP_200_OK

    def test_organization_member_list_isolation(
        self,
        client,
        test_organization,
        second_organization,
        admin_with_organization,
        second_org_user,
        admin_org_headers,
        second_org_headers,
    ):
        """Test that organization member lists are isolated"""
        # Get members for org 1
        response = client.get(
            f"/api/v1/organizations/{test_organization.id}/members",
            headers=admin_org_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        org1_members = response.json()

        # User from org 2 should not be able to see org 1 members
        response = client.get(
            f"/api/v1/organizations/{test_organization.id}/members",
            headers=second_org_headers,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_missing_organization_header_returns_error(
        self, client, user_with_organization, auth_headers
    ):
        """Test that requests without X-Organization-Id header are rejected"""
        expense_data = {
            "user_id": user_with_organization.id,
            "amount": 100.00,
            "vendor": "Test Vendor",
            "description": "Test expense",
            "category": "MEALS",
        }

        # Try to create expense without organization header
        response = client.post(
            "/api/v1/expenses",
            json=expense_data,
            headers=auth_headers,  # No X-Organization-Id
        )

        # Should fail (organization context required)
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]
