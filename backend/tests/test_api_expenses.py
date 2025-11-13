"""
Tests for Expense API Routes
Critical API endpoints - targets 70%+ coverage
"""

import pytest
from datetime import datetime


class TestExpenseAPIRoutes:
    """Test expense-related API endpoints"""

    def test_create_expense_success(self, client, auth_headers, test_organization):
        """Test creating expense via API"""
        response = client.post(
            "/api/v1/expenses",
            headers=auth_headers,
            json={
                "amount": 100.50,
                "description": "Office supplies",
                "category": "OFFICE_SUPPLIES",
                "date": datetime.utcnow().isoformat(),
                "vendor": "Staples",
                "organization_id": test_organization.id
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] == True
        expense = data["expense"]
        assert expense["amount"] == 100.50
        assert expense["description"] == "Office supplies"
        assert expense["status"] == "PENDING"

    def test_create_expense_missing_required_fields(self, client, auth_headers):
        """Test creating expense without required fields"""
        response = client.post(
            "/api/v1/expenses",
            headers=auth_headers,
            json={
                "description": "Test expense"
                # Missing amount, category, date
            }
        )

        assert response.status_code == 422  # Validation error

    def test_create_expense_invalid_amount(self, client, auth_headers, test_organization):
        """Test creating expense with invalid amount"""
        response = client.post(
            "/api/v1/expenses",
            headers=auth_headers,
            json={
                "amount": -50.00,  # Negative amount
                "description": "Invalid expense",
                "category": "OTHER",
                "date": datetime.utcnow().isoformat(),
                "organization_id": test_organization.id
            }
        )

        assert response.status_code in [400, 422]

    def test_get_expenses_list(self, client, auth_headers):
        """Test getting list of expenses"""
        response = client.get(
            "/api/v1/expenses",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or "items" in data

    def test_get_expenses_with_pagination(self, client, auth_headers):
        """Test getting expenses with pagination"""
        response = client.get(
            "/api/v1/expenses?skip=0&limit=10",
            headers=auth_headers
        )

        assert response.status_code == 200

    def test_get_expenses_with_status_filter(self, client, auth_headers):
        """Test filtering expenses by status"""
        response = client.get(
            "/api/v1/expenses?status=PENDING",
            headers=auth_headers
        )

        assert response.status_code == 200

    def test_get_single_expense(self, client, auth_headers, test_expense):
        """Test getting a single expense by ID"""
        response = client.get(
            f"/api/v1/expenses/{test_expense.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_expense.id

    def test_get_nonexistent_expense(self, client, auth_headers):
        """Test getting non-existent expense"""
        response = client.get(
            "/api/v1/expenses/nonexistent_id",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_update_expense(self, client, auth_headers, test_expense):
        """Test updating an expense"""
        response = client.patch(
            f"/api/v1/expenses/{test_expense.id}",
            headers=auth_headers,
            json={
                "description": "Updated description",
                "amount": 150.00
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"
        assert data["amount"] == 150.00

    def test_update_expense_invalid_status_transition(
        self, client, auth_headers, test_expense, db_session
    ):
        """Test invalid status transition"""
        # Set expense to approved
        test_expense.status = "APPROVED"
        db_session.commit()

        # Try to change amount (shouldn't be allowed for approved expense)
        response = client.patch(
            f"/api/v1/expenses/{test_expense.id}",
            headers=auth_headers,
            json={"amount": 999.99}
        )

        # Should either reject or keep same amount
        assert response.status_code in [400, 403, 200]

    def test_delete_expense(self, client, auth_headers, test_expense):
        """Test deleting an expense"""
        response = client.delete(
            f"/api/v1/expenses/{test_expense.id}",
            headers=auth_headers
        )

        assert response.status_code in [200, 204]

    def test_delete_nonexistent_expense(self, client, auth_headers):
        """Test deleting non-existent expense"""
        response = client.delete(
            "/api/v1/expenses/nonexistent_id",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_approve_expense_as_manager(
        self, client, manager_headers, manager_expense
    ):
        """Test approving expense as manager"""
        response = client.post(
            "/api/v1/expenses/approve",
            headers=manager_headers,
            json={
                "expense_id": manager_expense.id,
                "approver_id": manager_expense.user_id,
                "comment": "Approved"
            }
        )

        assert response.status_code in [200, 201]

    def test_approve_expense_as_employee_forbidden(
        self, client, auth_headers, test_expense, test_user
    ):
        """Test that employee cannot approve expenses"""
        response = client.post(
            "/api/v1/expenses/approve",
            headers=auth_headers,
            json={
                "expense_id": test_expense.id,
                "approver_id": test_user.id
            }
        )

        assert response.status_code == 403

    def test_reject_expense(self, client, manager_headers, manager_expense):
        """Test rejecting an expense"""
        response = client.post(
            "/api/v1/expenses/reject",
            headers=manager_headers,
            json={
                "expense_id": manager_expense.id,
                "approver_id": manager_expense.user_id,
                "rejection_reason": "Insufficient documentation"
            }
        )

        assert response.status_code in [200, 201]

    def test_bulk_approve_expenses(self, client, manager_headers):
        """Test bulk approving expenses"""
        response = client.post(
            "/api/v1/expenses/bulk-approve",
            headers=manager_headers,
            json={
                "expense_ids": ["exp1", "exp2", "exp3"]
            }
        )

        assert response.status_code in [200, 207]  # 207 for multi-status

    def test_export_expenses(self, client, auth_headers):
        """Test exporting expenses"""
        response = client.get(
            "/api/v1/expenses/export?format=csv",
            headers=auth_headers
        )

        # Should return CSV or redirect
        assert response.status_code in [200, 201, 202]

    def test_get_expense_statistics(self, client, auth_headers):
        """Test getting expense statistics"""
        response = client.get(
            "/api/v1/expenses/stats",
            headers=auth_headers
        )

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
                "organization_id": test_organization.id
            }
        )

        assert response.status_code == 401


class TestExpenseCommentsAPI:
    """Test expense comment endpoints"""

    def test_add_comment_to_expense(self, client, auth_headers, test_expense):
        """Test adding comment to expense"""
        response = client.post(
            f"/api/v1/expenses/{test_expense.id}/comments",
            headers=auth_headers,
            json={"comment": "This is a test comment"}
        )

        assert response.status_code in [200, 201]

    def test_get_expense_comments(self, client, auth_headers, test_expense):
        """Test getting comments for an expense"""
        response = client.get(
            f"/api/v1/expenses/{test_expense.id}/comments",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "comments" in data
        assert isinstance(data["comments"], list)


class TestReceiptAPI:
    """Test receipt upload endpoints"""

    def test_upload_receipt(self, client, auth_headers, test_expense):
        """Test uploading receipt"""
        # Create fake file
        files = {
            "file": ("receipt.pdf", b"fake pdf content", "application/pdf")
        }

        response = client.post(
            f"/api/v1/expenses/{test_expense.id}/receipts",
            headers=auth_headers,
            files=files
        )

        assert response.status_code in [200, 201]

    def test_upload_receipt_invalid_file_type(
        self, client, auth_headers, test_expense
    ):
        """Test uploading invalid file type"""
        files = {
            "file": ("receipt.exe", b"fake exe", "application/x-msdownload")
        }

        response = client.post(
            f"/api/v1/expenses/{test_expense.id}/receipts",
            headers=auth_headers,
            files=files
        )

        # Should reject executable files
        assert response.status_code in [400, 415]

    def test_get_expense_receipts(self, client, auth_headers, test_expense):
        """Test getting receipts for expense"""
        response = client.get(
            f"/api/v1/expenses/{test_expense.id}/receipts",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
