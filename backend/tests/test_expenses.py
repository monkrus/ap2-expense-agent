"""
Tests for expense management endpoints
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from src.models import ExpenseStatus, ExpenseCategory


class TestExpenseSubmission:
    """Test expense submission"""

    def test_submit_expense(self, client, test_user, auth_headers):
        """Test employee can submit expense"""
        expense_data = {
            "user_id": test_user.id,
            "amount": 100.50,
            "vendor": "Test Vendor",
            "category": "Travel",
            "description": "Business trip expense"
        }

        response = client.post(
            "/api/v1/expenses",
            json=expense_data,
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["expense"]["amount"] == 100.50
        assert data["expense"]["vendor"] == "Test Vendor"
        assert data["expense"]["status"] == "pending"

    def test_submit_expense_invalid_amount(self, client, test_user, auth_headers):
        """Test submitting expense with invalid amount"""
        expense_data = {
            "user_id": test_user.id,
            "amount": -50.00,
            "vendor": "Test Vendor",
            "category": "Travel",
            "description": "Invalid amount"
        }

        response = client.post(
            "/api/v1/expenses",
            json=expense_data,
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "positive" in response.json()["detail"].lower()

    def test_submit_expense_invalid_category(self, client, test_user, auth_headers):
        """Test submitting expense with invalid category"""
        expense_data = {
            "user_id": test_user.id,
            "amount": 100.00,
            "vendor": "Test Vendor",
            "category": "InvalidCategory",
            "description": "Invalid category"
        }

        response = client.post(
            "/api/v1/expenses",
            json=expense_data,
            headers=auth_headers
        )

        assert response.status_code == 400


class TestExpenseRetrieval:
    """Test expense retrieval"""

    def test_get_user_expenses(self, client, auth_headers, test_expense):
        """Test getting expenses for current user"""
        response = client.get(
            "/api/v1/expenses",
            headers=auth_headers
        )

        assert response.status_code == 200
        expenses = response.json()
        assert isinstance(expenses, list)
        assert len(expenses) >= 1

    def test_get_expense_report(self, client, auth_headers, test_expense):
        """Test getting expense report"""
        response = client.get(
            "/api/v1/expenses/report",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_expenses" in data
        assert "total_amount" in data
        assert "pending" in data
        assert "approved" in data
        assert "rejected" in data

    def test_get_expense_by_id(self, client, auth_headers, test_expense):
        """Test getting a specific expense by ID"""
        response = client.get(
            f"/api/v1/expenses/{test_expense.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_expense.id
        assert data["amount"] == float(test_expense.amount)


class TestExpenseUpdate:
    """Test expense update"""

    def test_update_pending_expense(self, client, auth_headers, sample_expense, test_user):
        """Test employee can update their pending expense"""
        expense = sample_expense(user=test_user, status=ExpenseStatus.PENDING)

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
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["expense"]["amount"] == 150.00
        assert data["expense"]["vendor"] == "Updated Vendor"

    def test_cannot_update_approved_expense(self, client, auth_headers, sample_expense, test_user):
        """Test employee cannot update approved expense"""
        expense = sample_expense(user=test_user, status=ExpenseStatus.APPROVED)

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
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "pending" in response.json()["detail"].lower()

    def test_cannot_update_others_expense(self, client, sample_user, sample_expense, test_user, test_organization, db_session):
        """Test employee cannot update another user's expense"""
        # Create another user
        other_user = sample_user(email="other@example.com")

        # Create expense for other user
        expense = sample_expense(user=other_user, status=ExpenseStatus.PENDING)

        # Try to update with test_user's auth
        from src.auth import AuthService
        # Login as test_user to get auth headers
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "TestPass123!"
            }
        )
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

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
            headers=headers
        )

        assert response.status_code == 403


class TestExpenseWithdrawal:
    """Test expense withdrawal"""

    def test_withdraw_pending_expense(self, client, auth_headers, sample_expense, test_user):
        """Test employee can withdraw pending expense"""
        expense = sample_expense(user=test_user, status=ExpenseStatus.PENDING)

        response = client.delete(
            f"/api/v1/expenses/{expense.id}/withdraw",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "withdrawn" in data["message"].lower()

    def test_cannot_withdraw_approved_expense(self, client, auth_headers, sample_expense, test_user):
        """Test employee cannot withdraw approved expense"""
        expense = sample_expense(user=test_user, status=ExpenseStatus.APPROVED)

        response = client.delete(
            f"/api/v1/expenses/{expense.id}/withdraw",
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "pending" in response.json()["detail"].lower()


class TestExpenseApproval:
    """Test expense approval (manager/admin)"""

    def test_manager_approve_expense(self, client, manager_headers, sample_expense, test_user):
        """Test manager can approve expense"""
        expense = sample_expense(user=test_user, status=ExpenseStatus.PENDING, amount=500.00)

        response = client.post(
            "/api/v1/expenses/approve",
            json={
                "expense_id": expense.id,
                "notes": "Approved"
            },
            headers=manager_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["expense_id"] == expense.id
        assert data["status"] == "approved"

    def test_manager_reject_expense(self, client, manager_headers, sample_expense, test_user):
        """Test manager can reject expense"""
        expense = sample_expense(user=test_user, status=ExpenseStatus.PENDING)

        response = client.post(
            "/api/v1/expenses/reject",
            json={
                "expense_id": expense.id,
                "rejection_reason": "Insufficient documentation"
            },
            headers=manager_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["expense_id"] == expense.id
        assert data["status"] == "rejected"

    def test_cannot_approve_already_approved(self, client, manager_headers, sample_expense, test_user):
        """Test cannot approve already approved expense"""
        expense = sample_expense(user=test_user, status=ExpenseStatus.APPROVED)

        response = client.post(
            "/api/v1/expenses/approve",
            json={
                "expense_id": expense.id,
                "notes": "Approved again"
            },
            headers=manager_headers
        )

        assert response.status_code == 400
        assert "already" in response.json()["detail"].lower()


class TestExpenseDelete:
    """Test expense deletion"""

    def test_delete_pending_expense(self, client, auth_headers, sample_expense, test_user):
        """Test employee can delete pending expense"""
        expense = sample_expense(user=test_user, status=ExpenseStatus.PENDING)

        response = client.delete(
            f"/api/v1/expenses/{expense.id}",
            headers=auth_headers
        )

        assert response.status_code == 204

    def test_cannot_delete_approved_expense(self, client, auth_headers, sample_expense, test_user):
        """Test employee cannot delete approved expense"""
        expense = sample_expense(user=test_user, status=ExpenseStatus.APPROVED)

        response = client.delete(
            f"/api/v1/expenses/{expense.id}",
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "pending" in response.json()["detail"].lower()


class TestExpenseComments:
    """Test expense comments"""

    def test_add_comment_to_expense(self, client, auth_headers, test_expense):
        """Test adding a comment to an expense"""
        response = client.post(
            f"/api/v1/expenses/{test_expense.id}/comments",
            json={"comment": "This is a test comment"},
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["comment"] == "This is a test comment"

    def test_get_expense_comments(self, client, auth_headers, test_expense):
        """Test getting comments for an expense"""
        # Add a comment first
        client.post(
            f"/api/v1/expenses/{test_expense.id}/comments",
            json={"comment": "Test comment"},
            headers=auth_headers
        )

        # Get comments
        response = client.get(
            f"/api/v1/expenses/{test_expense.id}/comments",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "comments" in data
        assert len(data["comments"]) >= 1


class TestBulkOperations:
    """Test bulk expense operations"""

    def test_get_all_pending_expenses(self, client, manager_headers, multiple_expenses):
        """Test manager can get all pending expenses"""
        response = client.get(
            "/api/v1/expenses/all-pending",
            headers=manager_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "expenses" in data
        assert len(data["expenses"]) >= 1

    def test_get_all_expenses_with_filter(self, client, manager_headers, multiple_expenses):
        """Test manager can get all expenses with status filter"""
        response = client.get(
            "/api/v1/expenses/all?status=pending",
            headers=manager_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "expenses" in data
