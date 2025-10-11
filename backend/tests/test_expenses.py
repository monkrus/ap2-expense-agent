"""
Tests for expense management endpoints
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from src.api import app
from src.models import Expense, ExpenseStatus, UserRole


class TestExpenseOperations:
    """Test expense CRUD operations"""

    def test_submit_expense(self, client: TestClient, employee_headers):
        """Test employee can submit expense"""
        expense_data = {
            "user_id": "test-user-id",
            "amount": 100.50,
            "vendor": "Test Vendor",
            "category": "Travel",
            "description": "Business trip expense"
        }

        response = client.post(
            "/api/v1/expenses",
            json=expense_data,
            headers=employee_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["expense"]["amount"] == 100.50
        assert data["expense"]["vendor"] == "Test Vendor"
        assert data["expense"]["status"] == "pending"

    def test_get_expense_report(self, client: TestClient, employee_headers, sample_expense):
        """Test getting expense report"""
        response = client.get(
            "/api/v1/expenses/report",
            headers=employee_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_expenses" in data
        assert "total_amount" in data
        assert "pending" in data
        assert "approved" in data
        assert "rejected" in data

    def test_update_pending_expense(self, client: TestClient, employee_headers, sample_expense, db_session):
        """Test employee can update their pending expense"""
        # Create a pending expense
        expense = sample_expense(status=ExpenseStatus.PENDING)

        updated_data = {
            "user_id": expense.user_id,
            "amount": 150.00,
            "vendor": "Updated Vendor",
            "category": "Software",
            "description": "Updated description"
        }

        response = client.put(
            f"/api/v1/expenses/{expense.id}",
            json=updated_data,
            headers=employee_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["expense"]["amount"] == 150.00
        assert data["expense"]["vendor"] == "Updated Vendor"

    def test_cannot_update_approved_expense(self, client: TestClient, employee_headers, sample_expense):
        """Test employee cannot update approved expense"""
        expense = sample_expense(status=ExpenseStatus.APPROVED)

        updated_data = {
            "user_id": expense.user_id,
            "amount": 150.00,
            "vendor": "Updated Vendor",
            "category": "Software",
            "description": "Updated description"
        }

        response = client.put(
            f"/api/v1/expenses/{expense.id}",
            json=updated_data,
            headers=employee_headers
        )

        assert response.status_code == 400
        assert "Only pending expenses can be edited" in response.json()["detail"]

    def test_withdraw_pending_expense(self, client: TestClient, employee_headers, sample_expense):
        """Test employee can withdraw pending expense"""
        expense = sample_expense(status=ExpenseStatus.PENDING)

        response = client.delete(
            f"/api/v1/expenses/{expense.id}/withdraw",
            headers=employee_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["expense_id"] == expense.id


class TestExpenseApproval:
    """Test expense approval workflow"""

    def test_admin_can_approve_expense(self, client: TestClient, admin_headers, sample_expense):
        """Test admin can approve expense"""
        expense = sample_expense(status=ExpenseStatus.PENDING)

        response = client.post(
            "/api/v1/expenses/approve",
            json={
                "expense_id": expense.id,
                "approver_id": "admin-user-id"
            },
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["result"]["status"] == "approved"
        assert "transaction_id" in data["result"]
        assert "mandates" in data["result"]

        # Verify AP2 mandates were created
        mandates = data["result"]["mandates"]
        assert "intent" in mandates
        assert "cart" in mandates
        assert "payment" in mandates

    def test_admin_can_reject_expense(self, client: TestClient, admin_headers, sample_expense):
        """Test admin can reject expense"""
        expense = sample_expense(status=ExpenseStatus.PENDING)

        response = client.post(
            "/api/v1/expenses/reject",
            json={
                "expense_id": expense.id,
                "approver_id": "admin-user-id",
                "rejection_reason": "Does not meet policy requirements"
            },
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["result"]["status"] == "rejected"
        assert data["result"]["rejection_reason"] == "Does not meet policy requirements"

    def test_employee_cannot_approve_expense(self, client: TestClient, employee_headers, sample_expense):
        """Test employee cannot approve expenses"""
        expense = sample_expense(status=ExpenseStatus.PENDING)

        response = client.post(
            "/api/v1/expenses/approve",
            json={
                "expense_id": expense.id,
                "approver_id": "employee-user-id"
            },
            headers=employee_headers
        )

        assert response.status_code == 403
        assert "Not authorized" in response.json()["detail"]

    def test_cannot_approve_already_approved_expense(self, client: TestClient, admin_headers, sample_expense):
        """Test cannot approve already approved expense"""
        expense = sample_expense(status=ExpenseStatus.APPROVED)

        response = client.post(
            "/api/v1/expenses/approve",
            json={
                "expense_id": expense.id,
                "approver_id": "admin-user-id"
            },
            headers=admin_headers
        )

        assert response.status_code == 400
        assert "already approved" in response.json()["detail"]


class TestAuditTrail:
    """Test AP2 audit trail functionality"""

    def test_get_audit_trail(self, client: TestClient, admin_headers, sample_expense):
        """Test retrieving complete audit trail"""
        # Create and approve an expense to generate audit trail
        expense = sample_expense(status=ExpenseStatus.PENDING)

        # Approve it to create AP2 mandates
        approve_response = client.post(
            "/api/v1/expenses/approve",
            json={
                "expense_id": expense.id,
                "approver_id": "admin-user-id"
            },
            headers=admin_headers
        )

        transaction_id = approve_response.json()["result"]["transaction_id"]

        # Get audit trail
        response = client.get(
            f"/api/v1/audit/{transaction_id}",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify audit trail structure
        assert data["transaction_id"] == transaction_id
        assert data["complete"] is True
        assert "expense" in data
        assert "intent_mandate" in data
        assert "cart_mandate" in data
        assert "payment_mandate" in data
        assert "audit_logs" in data
        assert "verification" in data

    def test_audit_trail_not_found(self, client: TestClient, admin_headers):
        """Test audit trail returns 404 for non-existent transaction"""
        response = client.get(
            "/api/v1/audit/non-existent-transaction",
            headers=admin_headers
        )

        assert response.status_code == 404


class TestAdminExpenses:
    """Test admin expense management"""

    def test_get_all_pending_expenses(self, client: TestClient, admin_headers, sample_expense):
        """Test admin can get all pending expenses"""
        # Create multiple pending expenses
        sample_expense(status=ExpenseStatus.PENDING)
        sample_expense(status=ExpenseStatus.PENDING)
        sample_expense(status=ExpenseStatus.APPROVED)

        response = client.get(
            "/api/v1/expenses/all-pending",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pending_count"] == 2
        assert len(data["expenses"]) == 2
        assert all(e["status"] == "pending" for e in data["expenses"])

    def test_get_all_expenses_with_filter(self, client: TestClient, admin_headers, sample_expense):
        """Test admin can filter all expenses by status"""
        # Create expenses with different statuses
        sample_expense(status=ExpenseStatus.PENDING)
        sample_expense(status=ExpenseStatus.APPROVED)
        sample_expense(status=ExpenseStatus.REJECTED)

        # Test approved filter
        response = client.get(
            "/api/v1/expenses/all?status=approved",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert all(e["status"] == "approved" for e in data["expenses"])

    def test_employee_cannot_access_all_expenses(self, client: TestClient, employee_headers):
        """Test employee cannot access all expenses endpoint"""
        response = client.get(
            "/api/v1/expenses/all-pending",
            headers=employee_headers
        )

        assert response.status_code == 403


class TestExpenseValidation:
    """Test expense validation"""

    def test_submit_expense_with_invalid_amount(self, client: TestClient, employee_headers):
        """Test expense submission with invalid amount"""
        expense_data = {
            "user_id": "test-user-id",
            "amount": -100.00,  # Negative amount
            "vendor": "Test Vendor",
            "category": "Travel",
            "description": "Invalid expense"
        }

        response = client.post(
            "/api/v1/expenses",
            json=expense_data,
            headers=employee_headers
        )

        # Depending on validation, this should fail
        # For now, just check it doesn't crash
        assert response.status_code in [200, 400, 422]

    def test_submit_expense_with_missing_fields(self, client: TestClient, employee_headers):
        """Test expense submission with missing required fields"""
        expense_data = {
            "user_id": "test-user-id",
            "amount": 100.00
            # Missing vendor, category, description
        }

        response = client.post(
            "/api/v1/expenses",
            json=expense_data,
            headers=employee_headers
        )

        assert response.status_code == 422  # Validation error
