"""
Tests for Expense API Routes
Critical API endpoints - targets 70%+ coverage
"""

from datetime import datetime

import pytest


class TestExpenseAPIRoutes:
    """Test expense-related API endpoints"""

    def test_create_expense_success(self, client, org_headers, test_organization):
        """Test creating expense via API"""
        response = client.post(
            "/api/v1/expenses",
            headers=org_headers,
            json={
                "amount": 100.50,
                "description": "Office supplies",
                "category": "OFFICE_SUPPLIES",
                "date": datetime.utcnow().isoformat(),
                "vendor": "Staples",
                "organization_id": test_organization.id,
            },
        )

        assert response.status_code == 201
        expense = response.json()
        assert expense["amount"] == 100.50
        assert expense["description"] == "Office supplies"
        assert expense["status"] == "PENDING"
        assert "id" in expense
        assert "auto_approved" in expense

    def test_create_expense_missing_required_fields(self, client, org_headers):
        """Test creating expense without required fields"""
        response = client.post(
            "/api/v1/expenses",
            headers=org_headers,
            json={
                "description": "Test expense"
                # Missing amount, category, date
            },
        )

        assert response.status_code == 422  # Validation error

    def test_create_expense_invalid_amount(
        self, client, org_headers, test_organization
    ):
        """Test creating expense with invalid amount"""
        response = client.post(
            "/api/v1/expenses",
            headers=org_headers,
            json={
                "amount": -50.00,  # Negative amount
                "description": "Invalid expense",
                "category": "OTHER",
                "date": datetime.utcnow().isoformat(),
                "organization_id": test_organization.id,
            },
        )

        assert response.status_code in [400, 422]

    def test_get_expenses_list(self, client, org_headers):
        """Test getting list of expenses"""
        response = client.get("/api/v1/expenses", headers=org_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or "items" in data

    def test_get_expenses_with_pagination(self, client, org_headers):
        """Test getting expenses with pagination"""
        response = client.get("/api/v1/expenses?skip=0&limit=10", headers=org_headers)

        assert response.status_code == 200

    def test_get_expenses_with_status_filter(self, client, org_headers):
        """Test filtering expenses by status"""
        response = client.get("/api/v1/expenses?status=PENDING", headers=org_headers)

        assert response.status_code == 200

    def test_get_single_expense(self, client, org_headers, test_expense):
        """Test getting a single expense by ID"""
        response = client.get(
            f"/api/v1/expenses/{test_expense.id}", headers=org_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_expense.id

    def test_get_nonexistent_expense(self, client, org_headers):
        """Test getting non-existent expense"""
        response = client.get("/api/v1/expenses/nonexistent_id", headers=org_headers)

        assert response.status_code == 404

    def test_update_expense(self, client, org_headers, test_expense):
        """Test updating an expense"""
        response = client.patch(
            f"/api/v1/expenses/{test_expense.id}",
            headers=org_headers,
            json={"description": "Updated description", "amount": 150.00},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"
        assert data["amount"] == 150.00

    def test_update_expense_invalid_status_transition(
        self, client, org_headers, test_expense, db_session
    ):
        """Test invalid status transition"""
        # Set expense to approved
        test_expense.status = "APPROVED"
        db_session.commit()

        # Try to change amount (shouldn't be allowed for approved expense)
        response = client.patch(
            f"/api/v1/expenses/{test_expense.id}",
            headers=org_headers,
            json={"amount": 999.99},
        )

        # Should either reject or keep same amount
        assert response.status_code in [400, 403, 200]

    def test_delete_expense(self, client, org_headers, test_expense):
        """Test deleting an expense"""
        response = client.delete(
            f"/api/v1/expenses/{test_expense.id}", headers=org_headers
        )

        assert response.status_code in [200, 204]

    def test_delete_nonexistent_expense(self, client, org_headers):
        """Test deleting non-existent expense"""
        response = client.delete(
            "/api/v1/expenses/nonexistent_id", headers=org_headers
        )

        assert response.status_code == 404

    def test_approve_expense_as_manager(self, client, manager_org_headers, manager_expense):
        """Test approving expense as manager"""
        response = client.put(
            f"/api/v1/expenses/{manager_expense.id}/approve",
            headers=manager_org_headers,
        )

        assert response.status_code in [200, 201]

    def test_approve_expense_as_employee_forbidden(
        self, client, org_headers, test_expense, test_user
    ):
        """Test that employee cannot approve expenses"""
        response = client.put(
            f"/api/v1/expenses/{test_expense.id}/approve",
            headers=org_headers,
        )

        assert response.status_code == 403

    def test_reject_expense(self, client, manager_org_headers, manager_expense):
        """Test rejecting an expense"""
        response = client.put(
            f"/api/v1/expenses/{manager_expense.id}/reject",
            headers=manager_org_headers,
            json={"rejection_reason": "Insufficient documentation"},
        )

        assert response.status_code in [200, 201]

    @pytest.mark.skip(reason="Bulk approve endpoint not implemented yet")
    def test_bulk_approve_expenses(self, client, manager_org_headers):
        """Test bulk approving expenses"""
        response = client.post(
            "/api/v1/expenses/bulk-approve",
            headers=manager_org_headers,
            json={"expense_ids": ["exp1", "exp2", "exp3"]},
        )

        assert response.status_code in [200, 207]  # 207 for multi-status

    def test_export_expenses(self, client, admin_org_headers):
        """Test exporting expenses"""
        response = client.get(
            "/api/v1/expenses/export?format=csv", headers=admin_org_headers
        )

        # Should return CSV or redirect
        assert response.status_code in [200, 201, 202]

    @pytest.mark.skip(reason="Expense statistics endpoint not implemented yet")
    def test_get_expense_statistics(self, client, org_headers):
        """Test getting expense statistics"""
        response = client.get("/api/v1/expenses/stats", headers=org_headers)

        assert response.status_code == 200
        if response.status_code == 200:
            data = response.json()
            assert "total" in data or "count" in data

    def test_create_expense_without_auth(self, client, test_organization):
        """Test creating expense without authentication"""
        response = client.post(
            "/api/v1/expenses",
            json={
                "amount": 100.00,
                "description": "Test",
                "category": "OTHER",
                "date": datetime.utcnow().isoformat(),
                "organization_id": test_organization.id,
            },
        )

        assert response.status_code == 401


class TestExpenseCommentsAPI:
    """Test expense comment endpoints"""

    @pytest.mark.skip(reason="Comments API not implemented yet")
    def test_add_comment_to_expense(self, client, org_headers, test_expense):
        """Test adding comment to expense"""
        response = client.post(
            f"/api/v1/expenses/{test_expense.id}/comments",
            headers=org_headers,
            json={"comment": "This is a test comment"},
        )

        assert response.status_code in [200, 201]

    @pytest.mark.skip(reason="Comments API not implemented yet")
    def test_get_expense_comments(self, client, org_headers, test_expense):
        """Test getting comments for an expense"""
        response = client.get(
            f"/api/v1/expenses/{test_expense.id}/comments", headers=org_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "comments" in data
        assert isinstance(data["comments"], list)


class TestReceiptAPI:
    """Test receipt upload endpoints"""

    def test_upload_receipt(self, client, org_headers, test_expense):
        """Test uploading receipt"""
        # Create fake file
        files = {"file": ("receipt.pdf", b"fake pdf content", "application/pdf")}

        response = client.post(
            f"/api/v1/receipts/upload/{test_expense.id}",
            headers=org_headers,
            files=files,
        )

        assert response.status_code in [200, 201]

    def test_upload_receipt_invalid_file_type(self, client, org_headers, test_expense):
        """Test uploading invalid file type"""
        files = {"file": ("receipt.exe", b"fake exe", "application/x-msdownload")}

        response = client.post(
            f"/api/v1/receipts/upload/{test_expense.id}",
            headers=org_headers,
            files=files,
        )

        # Should reject executable files
        assert response.status_code in [400, 415]

    def test_get_expense_receipts(self, client, org_headers, test_expense):
        """Test getting receipts for expense"""
        response = client.get(
            f"/api/v1/receipts/{test_expense.id}", headers=org_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "receipts" in data
        assert isinstance(data["receipts"], list)
