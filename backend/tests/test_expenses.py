"""
Expense management tests - streamlined and focused
"""

import pytest
from datetime import datetime, timedelta


class TestExpenseCreation:
    """Test expense creation"""

    def test_create_expense_success(self, client, org_headers, test_organization):
        """Test creating a new expense"""
        response = client.post(
            "/api/v1/expenses",
            headers=org_headers,
            json={
                "amount": 150.00,
                "vendor": "Test Restaurant",
                "description": "Business lunch",
                "category": "MEALS",
                "date": datetime.utcnow().isoformat(),
                "organization_id": test_organization.id,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] == True
        expense = data["expense"]
        assert expense["amount"] == 150.00
        assert expense["vendor"] == "Test Restaurant"
        assert expense["status"] == "PENDING"

    def test_create_expense_without_auth(self, client, test_organization):
        """Test creating expense without authentication fails"""
        response = client.post(
            "/api/v1/expenses",
            json={
                "amount": 100.00,
                "vendor": "Test Vendor",
                "description": "Test",
                "category": "TRAVEL",
                "date": datetime.utcnow().isoformat(),
                "organization_id": test_organization.id,
            },
        )
        assert response.status_code == 401

    def test_create_expense_invalid_amount(
        self, client, org_headers, test_organization
    ):
        """Test creating expense with invalid amount fails"""
        response = client.post(
            "/api/v1/expenses",
            headers=org_headers,
            json={
                "amount": -50.00,
                "vendor": "Test Vendor",
                "description": "Test",
                "category": "TRAVEL",
                "date": datetime.utcnow().isoformat(),
                "organization_id": test_organization.id,
            },
        )
        assert response.status_code == 422  # API returns 422 for validation errors


class TestExpenseRetrieval:
    """Test expense retrieval"""

    def test_get_expenses_list(self, client, org_headers, test_expense):
        """Test getting list of expenses"""
        response = client.get("/api/v1/expenses", headers=org_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_get_single_expense(self, client, org_headers, test_expense):
        """Test getting a single expense by ID"""
        response = client.get(
            f"/api/v1/expenses/{test_expense.id}", headers=org_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_expense.id
        assert data["amount"] == 150.00

    def test_get_nonexistent_expense(self, client, org_headers):
        """Test getting nonexistent expense returns 404"""
        response = client.get("/api/v1/expenses/nonexistent_id", headers=org_headers)
        assert response.status_code == 404


class TestExpenseUpdate:
    """Test expense updates"""

    def test_update_expense(self, client, org_headers, test_expense):
        """Test updating an expense"""
        response = client.put(
            f"/api/v1/expenses/{test_expense.id}",
            headers=org_headers,
            json={
                "amount": 200.00,
                "vendor": "Updated Vendor",
                "description": "Updated description",
                "category": "TRAVEL",
                "date": datetime.utcnow().isoformat(),
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        expense = data["expense"]
        assert expense["amount"] == 200.00
        assert expense["vendor"] == "Updated Vendor"

    def test_cannot_update_others_expense(
        self, client, second_org_headers, test_expense
    ):
        """Test user cannot update another user's expense"""
        response = client.put(
            f"/api/v1/expenses/{test_expense.id}",
            headers=second_org_headers,
            json={
                "amount": 999.00,
                "vendor": "Hacker",
                "description": "Trying to update",
                "category": "TRAVEL",
                "date": datetime.utcnow().isoformat(),
            },
        )
        # Should be 404 (not found due to tenant isolation) or 403 (forbidden)
        assert response.status_code in [403, 404]


class TestExpenseDelete:
    """Test expense deletion"""

    def test_delete_expense(self, client, org_headers, test_expense):
        """Test deleting an expense"""
        response = client.delete(
            f"/api/v1/expenses/{test_expense.id}", headers=org_headers
        )
        assert response.status_code in [200, 204]

        # Verify expense is deleted
        get_response = client.get(
            f"/api/v1/expenses/{test_expense.id}", headers=org_headers
        )
        assert get_response.status_code == 404


class TestExpenseFiltering:
    """Test expense filtering and search"""

    def test_filter_expenses_by_status(self, client, org_headers, multiple_expenses):
        """Test filtering expenses by status"""
        response = client.get("/api/v1/expenses?status=PENDING", headers=org_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_filter_expenses_by_date_range(
        self, client, org_headers, multiple_expenses
    ):
        """Test filtering expenses by date range"""
        start_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
        end_date = datetime.utcnow().isoformat()

        response = client.get(
            f"/api/v1/expenses?start_date={start_date}&end_date={end_date}",
            headers=org_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestTenantIsolation:
    """Test multi-tenant isolation"""

    def test_cannot_see_other_org_expenses(
        self, client, org_headers, second_org_headers, test_expense
    ):
        """Test that users cannot see expenses from other organizations"""
        # First org can see their expense
        response1 = client.get(
            f"/api/v1/expenses/{test_expense.id}", headers=org_headers
        )
        assert response1.status_code == 200

        # Second org cannot see first org's expense
        response2 = client.get(
            f"/api/v1/expenses/{test_expense.id}", headers=second_org_headers
        )
        assert response2.status_code == 404
